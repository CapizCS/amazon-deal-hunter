import json
from datetime import date


HISTORY_FILE = "price_history.json"


def load_history():
    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=2, ensure_ascii=False)


def update_price(history, product_id, price):
    today = str(date.today())

    if product_id not in history:
        history[product_id] = {
            "category": "unknown",
            "prices": []
        }

    prices = history[product_id]["prices"]

    # Se abbiamo già registrato il prodotto oggi,
    # aggiorniamo il prezzo invece di creare un duplicato.
    for item in prices:
        if item["date"] == today:
            item["price"] = price
            return

    prices.append({
        "date": today,
        "price": price
    })

def search_parse(query, category):
    import os
    import urllib.parse
    import urllib.request

    api_url = (
        "https://api.parse.bot"
        "/scraper/18564612-8aa3-47b4-a88b-4bc5ba70f945"
        "/get_search_results_csv"
    )

    params = urllib.parse.urlencode({
        "query": query
    })

    request = urllib.request.Request(
        f"{api_url}?{params}",
        headers={
            "X-API-Key": os.environ["PARSE_API_KEY"]
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(
            response.read().decode("utf-8")
        )

    products = data.get("data", {}).get("products", [])

    print(f"Ricerca: {query}")
    print(f"Prodotti ricevuti: {len(products)}")

    return products, category


def save_product(history, product, category):

    asin = product.get("asin")
    price = product.get("price")

    if not asin or not price:
        return

    if asin not in history:

        history[asin] = {
            "category": category,
            "title": product.get("title", ""),
            "url": product.get("product_url", ""),
            "image_url": product.get("image_url", ""),
            "rating": product.get("rating"),
            "ratings_count": product.get("ratings_count", 0),
            "prices": []
        }

    else:

        history[asin]["category"] = category
        history[asin]["title"] = product.get(
            "title",
            history[asin].get("title", "")
        )

        history[asin]["url"] = product.get(
            "product_url",
            history[asin].get("url", "")
        )

    update_price(history, asin, float(price))


def main():

    history = load_history()

    searches = [
        ("ssd 1tb", "technology"),
        ("cuffie bluetooth", "technology"),
        ("accessori gaming", "gaming"),
        ("gadget casa", "home")
    ]

    total = 0

    for query, category in searches:

        try:

            products, category = search_parse(
                query,
                category
            )

            for product in products:

                price = product.get("price")

                if price is None:
                    continue

                price = float(price)

                # Il nostro range: 10–50 €
                if MIN_PRICE <= price <= MAX_PRICE:

                    save_product(
                        history,
                        product,
                        category
                    )

                    total += 1

        except Exception as error:

            print()
            print(f"Errore ricerca '{query}':")
            print(type(error).__name__)
            print(str(error))

    save_history(history)

    print()
    print("=" * 60)
    print("Storico aggiornato.")
    print(f"Prodotti nel range 10–50 € elaborati: {total}")
    print(f"Totale prodotti nello storico: {len(history)}")


if __name__ == "__main__":
    main()
