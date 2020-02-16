"""This module contains methods for getting the exchange rate from the Central Bank of Russia
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Mapping, Optional
from urllib.parse import SplitResult, urlsplit

from .exceptions import CurrencyNotSupported, ExchangeRateRequestError
from .interface import IExchageRate

Currencies = Mapping[str, Mapping[str, Decimal]]


class CBR(IExchageRate):
    """Class for interact with the Central Bank of Russia

    Attributes:
        URL: api service address
    """
    URL: str = 'https://www.cbr.ru/scripts/XML_daily.asp'

    def __init__(self, cache_lifetime: int = 0):
        """Init CBR class

        Args:
            cache_lifetime (seconds): lifetime of the currency exchange rate cache
        """
        self._currencies: Currencies = {}
        self._expriration_date: Optional[datetime] = None
        self._cache_lifetime: timedelta = timedelta(seconds=cache_lifetime)

        self._url: SplitResult = urlsplit(self.URL)
        self._query: bytes = (
            f'GET {self._url.path or "/"} HTTP/1.0\r\n'
            f'Host: {self._url.hostname}\r\n'
            f'\r\n'
        ).encode('utf-8')

        self._lock: asyncio.Lock = asyncio.Lock()
        self._logger: logging.Logger = logging.getLogger('apiServer.CBR')

    async def get_exchange_rate(self, base: str, target: str) -> Decimal:
        async with self._lock:
            if not self._is_cache_valid():
                self._logger.info('Cache miss')
                self._currencies = await self._get_exchange_rate_from_server()
            else:
                self._logger.info('Cache hit')

        result = None
        if base in self._currencies:
            exchange_rate = self._currencies[base]
            result = exchange_rate.get(target)
            if result is None:
                raise CurrencyNotSupported(target)

            result = 1 / result
        elif target in self._currencies:
            exchange_rate = self._currencies[target]
            result = exchange_rate.get(base)

        if result is None:
            raise CurrencyNotSupported(base)

        return result

    async def _get_exchange_rate_from_server(self) -> Currencies:
        """Request exchange rate from CBR server
        """
        self._logger.info('Get exchange rate from CBR')

        if self._url.scheme == 'https':
            reader, writer = await asyncio.open_connection(
                self._url.hostname, 443, ssl=True           # type: ignore
            )
        else:
            reader, writer = await asyncio.open_connection(
                self._url.hostname, 80                      # type: ignore
            )

        writer.write(self._query)

        line = await reader.readline()

        # ['HTTP/1.1', '200', 'OK']
        status = line.decode('iso-8859-1').split()
        if status[1] != '200':
            raise ExchangeRateRequestError(
                'CBR', code=status[1], description=status[2]
            )

        # Skip headers
        while line and line != b'\r\n':
            line = await reader.readline()

        xml_data = await reader.readline()
        currencies_matches = re.findall(
            r'''<CharCode>(?P<code>\w+)</CharCode>
                <Nominal>(?P<nominal>\d+)</Nominal>.*?
                <Value>(?P<value>[,\d]+)</Value>''',
            string=xml_data.decode('cp1251'),
            flags=re.VERBOSE
        )

        rub_rate = {}
        for code, str_nominal, str_value in currencies_matches:
            value = Decimal('.'.join(str_value.split(',')))
            nominal = Decimal(str_nominal)

            rub_rate[code.lower()] = value / nominal

        currencies = {'rub': rub_rate}

        if self._cache_lifetime:
            self._expriration_date = datetime.now() + self._cache_lifetime

        return currencies

    def _is_cache_valid(self) -> bool:
        """Cache is up-to-date"""
        return (
            self._expriration_date is not None
            and datetime.now() < self._expriration_date
        )
