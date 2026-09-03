import urllib.request


URL = "https://amzn.eu/d/0iH70vWg"


def main():
    request = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "DealHunterTest/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:

            data = response.read()

            print(f"HTTP status: {response.status}")
            print(f"URL finale: {response.geturl()}")
            print(f"Content-Type: {response.headers.get('Content-Type')}")
            print(f"Dimensione risposta: {len(data)} byte")

    except Exception as error:
        print(f"Richiesta fallita: {type(error).__name__}")
        print(str(error))


if __name__ == "__main__":
    main()
