"""Interface for interacting with the exchange rate service
"""
from abc import ABCMeta, abstractmethod
from decimal import Decimal, InvalidOperation

from .exceptions import ExchangeRateException


class IExchageRate(metaclass=ABCMeta):
    """Base class for implementing exchange rate service
    """
    async def convert(self, from_: str, to_: str, amount: str) -> Decimal:
        """Convert a certain amount of money

        Args:
            from_: base currency
            to: target currenct
            amount: amount of money

        Returns:
            Decimal: converted amount of money
        """
        rate = await self.get_exchange_rate(from_, to_)

        try:
            result = (Decimal(amount) * rate).quantize(Decimal('0.01'))
        except InvalidOperation:
            raise ExchangeRateException('Amount of money is not correct')

        return result

    @abstractmethod
    async def get_exchange_rate(self, base: str, target: str) -> Decimal:
        """Get current exchange rate for the specified currencies

        Args:
            base: base currency
            target: target currency

        Returns:
            Decimal: current exchange rate
        """
        pass
