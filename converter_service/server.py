"""Simple non-production asynchronous server for currency converter service
"""
import asyncio
import json
import logging
import logging.config
from typing import Any, Generator, List, Mapping, Optional, Tuple
from urllib.parse import ParseResult, urlparse

from .exchange_rate import CBR, ExchangeRateException, IExchageRate


class APIServer:
    """Implementation of async api-server

    Attributes:
        HTTP_VERSION: supported version of HTTP-protocol
        ASCII_ENCODING: encoding name for HTTP-headers
        LOGGING_CONFIG: path to ligging config file
        SERVICES: supported services for getting the exchange rate
    """
    HTTP_VERSION: str = 'HTTP/1.1'
    ASCII_ENCODING: str = 'iso-8859-1'
    LOGGING_CONFIG: str = 'logging.conf'

    SERVICES: Mapping[str, IExchageRate] = {
        'cbr': CBR(cache_lifetime=120)
    }

    def __init__(self, host: str, port: int):
        """Init API server

        Args:
            host: host address
            port: number of port
        """
        self._hostaddress: str = host
        self._port: int = port
        self._loger: logging.Logger = self._init_logger()

    def _init_logger(self) -> logging.Logger:
        """Init logger for service
        """
        logging.config.fileConfig(self.LOGGING_CONFIG)
        return logging.getLogger('apiServer')

    async def start(self):
        """Start async server
        """
        server = await asyncio.start_server(
            self._serve_request, self._hostaddress, self._port,
            reuse_port=True
        )

        self._loger.info('Server started')

        async with server:
            await server.serve_forever()

    async def _serve_request(self, reader: asyncio.StreamReader,
                             writer: asyncio.StreamWriter):
        """Callback is called whenever a new client connection is established
        """
        try:
            request = await self._parse_request(reader)
            result = await self._process_request(request)
            response = JSONResponse(200, 'OK', result)
        except ExchangeRateException as ex:
            response = JSONResponse(500, 'Internal Server Error',
                                    ex.message)
            self._loger.warning(f'Converter Error {ex.message}')
        except HTTPError as ex:
            response = JSONResponse(ex.code, ex.reason, ex.message)
            self._loger.warning(
                f'HTTP Error ({ex.code}, {ex.reason}) - {ex.message}'
            )
        except Exception:
            response = JSONResponse(500, 'Internal Server Error')
            self._loger.exception('Internal Server Error')

        writer.writelines(response.get_raw())
        await writer.drain()

        writer.close()

    async def _parse_request(self, reader: asyncio.StreamReader) -> 'Request':
        """Parse client request

        Args:
            reader: stream for reading client request

        Returns:
            Parsed request object

        Raises:
            HTTPError: server could not process the request
        """
        line = await reader.readline()
        request_info = line.decode(self.ASCII_ENCODING).split()

        self._loger.info(f'Request: {request_info}')

        if len(request_info) != 3:
            raise HTTPError(400, ' Bad Request')

        request = Request(*request_info)

        if request.version != self.HTTP_VERSION:
            raise HTTPError(505, 'HTTP Version Not Supported')

        # TODO: read request headers

        if request.method == 'POST':
            raise HTTPError(501, 'Not Implemented')

        return request

    async def _process_request(self, request: 'Request') -> dict:
        """Processing client request
        """
        handler, params = self._get_request_handler(request)
        base_currency, target_currency, amount = params

        result = await handler.convert(base_currency, target_currency, amount)

        return {
            'base_currency': base_currency,
            'target_currency': target_currency,
            'base_amount': amount,
            'result_amount': str(result)
        }

    def _get_request_handler(self, request: 'Request') -> Tuple[IExchageRate, List[str]]:
        """Get handler for client request

        Args:
            request: parsed request

        Returns:
            Implementation of the service for getting
            the exchange rate and list of params
        """
        _, service, *params = request.url.path.split('/')

        handler = self.SERVICES.get(service)

        # TODO: Implement routing system
        if handler is None or len(params) != 3:
            raise HTTPError(404, 'Not Found')

        return (handler, params)


class Request:
    """Parsed HTTP-request

    Attributes:
        method: http method
        url: parsed url from request
        version: version of HTTP-protocol
    """
    def __init__(self, method: str, url: str, version: str):
        self.method: str = method
        self.url: ParseResult = urlparse(url)
        self.version: str = version


class JSONResponse:
    """Response with json body

    Attributes:
        HEADERS: common http-response headers

        code: HTTP status codes
        status: short description of status code
        body: request result
    """
    HEADERS = ['Content-Type: application/json; charset=utf-8']

    def __init__(self, code: int, status: str, body: Any = None):
        self.code: int = code
        self.status: str = status
        self.body: Any = body

    def get_raw(self) -> Generator[bytes, None, None]:
        """Get correct response for HTTP-protocol
        """
        status_line = f'{APIServer.HTTP_VERSION} {self.code} {self.status}\r\n'
        yield status_line.encode(APIServer.ASCII_ENCODING)

        result = {}

        if self.code == 200:
            result['status'] = 'success'
            result['result'] = self.body
        else:
            result['status'] = 'error'
            result['message'] = self.body or self.status

        content = json.dumps(result)
        for header in self.HEADERS:
            yield (header + '\r\n').encode(APIServer.ASCII_ENCODING)

        yield f'Content-Length: {len(content)}\r\n'.encode(APIServer.ASCII_ENCODING)
        yield b'\r\n'

        yield content.encode('utf-8')


class HTTPError(Exception):
    """"Base exception for HTTP error
    """
    def __init__(self, code: int, reason: str, message: str = None):
        super().__init__()

        self.code: int = code
        self.reason: str = reason
        self.message: Optional[str] = message
