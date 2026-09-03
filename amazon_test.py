import re
import urllib.parse
import urllib.request

SEARCH = "ssd 1tb"

url = (
    "https://www.amazon.it/s?k=" +
    urllib.parse.quote(SEARCH)
)

request = urllib.request.Request(
    url,
    headers={
        "User-Agent": "DealHunterTest/1.0",
        "Accept-Language": "it-IT,it;q=0.9"
    }
)

with urllib.request.urlopen(request, timeout=20) as response:
    html = response.read().decode("utf-8", errors="ignore")

print("Dimensione HTML:", len(html))

asins = sorted(set(
    re.findall(r'data-asin="([A-Z0-9]{10})"', html)
))

print(f"ASIN trovati: {len(asins)}")

for asin in asins[:10]:
    print("-", asin)
