import os
import json
import urllib.parse
import urllib.request
from datetime import date

HISTORY_FILE = "price_history.json"

MIN_PRICE = 10
MAX_PRICE = 50

# Parole che indicano spesso risultati poco utili per il nostro progetto.
EXCLUDED_WORDS = [
    "ricambio",
    "sostituzione",
    "replacement",
    "pellicola",
    "adesivo",
    "manuale",
    "ebook",
    "libro",
    "custodia",
    "cover",
    "sticker",
]

# Un prodotto deve avere almeno una parola coerente con la categoria.
CATEGORY_KEYWORDS = {
    "technology": [
        "cuffie",
        "auricolari",
        "headphones",
        "headset",
        "mouse",
        "tastiera",
        "webcam",
        "speaker",
        "altoparlante",
        "sd",
        "nvme",
        "hard disk",
        "power bank",
        "caricatore",
        "hub usb",
        "adattatore",
        "router",
        "smartwatch",
        "monitor",
    ],

    "clothing": [
        "giacca",
        "pantaloni",
        "scarpe",
        "sneakers",
        "felpa",
        "maglia",
        "t-shirt",
        "camicia",
        "jeans",
        "piumino",
        "giubbotto",
        "parka",
        "gilet",
        "vestito",
        "abito",
        "calzini",
        "scarponi",
    ],

    "gaming": [
        "gaming",
        "controller",
        "gamepad",
        "mouse",
        "tastiera",
        "headset",
        "cuffie",
        "auricolari",
        "tappetino",
        "microfono",
        "joystick",
        "volante",
    ],

    "home": [
        "lampada",
        "lampada led",
        "aspirapolvere",
        "umidificatore",
        "deumidificatore",
        "termometro",
        "bilancia",
        "organizer",
        "dispenser",
        "presa smart",
        "sensore",
        "smart home",
        "led",
        "diffusore",
        "ventilatore",
        "macchina",
    ],
}


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}

    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(
            history,
            file,
            indent=2,
            ensure_ascii=False
        )


def search_parse(query):
    api_url = (
        "https://api.parse.bot"
        "/scraper/18564612-8aa3-47b4-a88b-4bc5ba70f945"
        "/get_search_results_csv"
    )

    params = urllib.parse.urlencode({
        "query": query
    })

    url = f"{api_url}?{params}"

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

    # Parse può restituire direttamente una lista
    # oppure una lista dentro un campo contenitore.
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["data", "results", "products", "items"]:
            value = data.get(key)

            if isinstance(value, list):
                return value

        # Fallback: cerca una lista tra i valori della risposta.
        for value in data.values():
            if isinstance(value, list):
                return value

    return []


def product_passes_filter(product, category):
    title = product.get("title", "").strip().lower()

    if not title:
        return False

    # Controllo prezzo.
    try:
        price = float(product.get("price", 0))
    except (TypeError, ValueError):
        return False

    if price < MIN_PRICE or price > MAX_PRICE:
        return False

    # Elimina risultati palesemente poco interessanti.
    for word in EXCLUDED_WORDS:
        if word in title:
            return False

    # Controllo coerenza con la categoria.
    keywords = CATEGORY_KEYWORDS.get(category, [])

    if keywords:
        if not any(keyword in title for keyword in keywords):
            return False

    return True


def save_product(history, product, category):
    asin = product.get("asin")

    if not asin:
        return False

    try:
        price = float(product.get("price", 0))
    except (TypeError, ValueError):
        return False

    today = str(date.today())

    if asin not in history:
        history[asin] = {
            "category": category,
            "title": product.get("title", ""),
            "url": product.get("product_url", ""),
            "image_url": product.get("image_url", ""),
            "rating": product.get("rating", 0),
            "ratings_count": product.get("ratings_count", 0),
            "prices": []
        }

    prices = history[asin]["prices"]

    # Se abbiamo già registrato il prodotto oggi,
    # aggiorniamo il prezzo invece di creare un duplicato.
    existing_today = False

    for item in prices:
        if item.get("date") == today:
            item["price"] = price
            existing_today = True
            break

    if not existing_today:
        prices.append({
            "date": today,
            "price": price
        })

    return True


def main():
    history = load_history()

    searches = [
        ("abbigliamento outdoor", "clothing"),
        ("cuffie bluetooth", "technology"),
        ("accessori gaming", "gaming"),
        ("gadget casa", "home"),
    ]

    total_results = 0
    products_in_range = 0
    products_filtered = 0

    for query, category in searches:
        print()
        print("=" * 70)
        print(f"Ricerca: {query}")

        products = search_parse(query)

        print(f"Risultati Parse: {len(products)}")

        total_results += len(products)

        for product in products:
            if not product_passes_filter(product, category):
                continue

            products_in_range += 1

            if save_product(history, product, category):
                products_filtered += 1

    save_history(history)

    print()
    print("=" * 70)
    print("AGGIORNAMENTO STORICO COMPLETATO")
    print(f"Risultati totali Parse: {total_results}")
    print(f"Prodotti validi nel range 10–50 €: {products_in_range}")
    print(f"Prodotti salvati/aggiornati: {products_filtered}")
    print(f"Totale prodotti nello storico: {len(history)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
