import os
import json
import urllib.parse
import urllib.request


API_URL = (
    "https://api.parse.bot"
    "/scraper/18564612-8aa3-47b4-a88b-4bc5ba70f945"
    "/get_search_results_csv"
)


def main():

    params = urllib.parse.urlencode({
        "query": "ssd 1tb"
    })

    url = f"{API_URL}?{params}"

    request = urllib.request.Request(
        url,
        headers={
            "X-API-Key": os.environ["PARSE_API_KEY"]
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:

        data = json.loads(
            response.read().decode("utf-8")
        )

    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
