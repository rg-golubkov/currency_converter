# Web-service "Currency converter"
Simple non-production asynchronus server with currency converter service

## Installation
```bash
$ git clone git@github.com:rg-golubkov/currency_converter.git
$ cd ./currency_converter
$ docker build -t currency_converter .
```

## Usage
```bash
$ docker run --rm -it -p 5000:5000 currency_converter
```

Now you can visit your browser at the following url template:

`http://localhost:5000/<currency_exchange_rate_source>/<from>/<to>/<amount>`

For example:
```bash
$ curl -i http://localhost:5000/crb/usd/rub/1
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: 129

{
    "status": "success",
    "result": {
        "base_currency": "usd",
        "target_currency": "rub",
        "base_amount": "1",
        "result_amount": "63.45"
    }
}
```

## Currency exchange rate sources
List of supported data sources for getting the exchange rate:

- Central Bank of Russia:
    - URL - `crb`
    - Currencies: the list of supported currencies can be found [here](https://www.cbr.ru/scripts/XML_daily.asp)
