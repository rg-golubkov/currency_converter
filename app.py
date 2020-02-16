import asyncio

from converter_service import APIServer


def main():
    asyncio.run(APIServer(host='0.0.0.0', port=5000).start())


if __name__ == '__main__':
    main()
