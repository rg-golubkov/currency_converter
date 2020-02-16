"""Basic exceptions of exchage_rate package.
"""
from typing import Optional


class ExchangeRateException(Exception):
    """Common parent exception

    Attributes:
        message: exception message
    """
    message: Optional[str] = None

    def __init__(self, message: str = None):
        if message is not None:
            self.message = message

        super().__init__(self.message)


class CurrencyNotSupported(ExchangeRateException):
    """Requested currency is not supported by service
    """
    message = 'Exchange rate for {currency} is not supported'

    def __init__(self, currency):
        super().__init__(self.message.format(currency=currency))


class ExchangeRateRequestError(ExchangeRateException):
    """Request to a third-party service failed
    """
    message = ('Request to the {service} server is failed. '
               'Error {code}: {description}')

    def __init__(self, service, code, description):
        super().__init__(self.message.format(service=service,
                                             code=code,
                                             description=description))
