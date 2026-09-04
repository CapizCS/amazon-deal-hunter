import os
import json
import urllib.parse
import urllib.request
from datetime import date

HISTORY_FILE = "price_history.json"
ROTATION_FILE = "search_rotation.json"

MIN_PRICE = 10
MAX_PRICE = 50

# 2 query per ogni esecuzione.
QUERIES_PER_RUN = 2

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

# Parole che aiutano a verificare che il prodotto appartenga
# realmente alla categoria cercata.
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
        "ssd",
        "hard disk",
        "power bank",
        "caricatore",
        "hub usb",
        "adattatore",
        "router",
        "smartwatch",
        "monitor",
        "microfono",
        "tablet",
        "dock",
        "usb",
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
        "playstation",
        "ps5",
        "ps4",
        "xbox",
        "switch",
        "steam deck",
    ],

    "women_clothing": [
        "donna",
        "donne",
        "woman",
        "women",
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
        "gonna",
        "blusa",
        "cardigan",
        "pullover",
        "cappotto",
        "top",
        "leggings",
    ],

    "outdoor_clothing": [
        "outdoor",
        "trekking",
        "escursionismo",
        "hiking",
        "montagna",
        "alpinismo",
        "running",
        "trail",
        "giacca",
        "pantaloni",
        "scarpe",
        "scarponi",
        "pile",
        "fleece",
        "piumino",
        "giubbotto",
        "parka",
        "gilet",
        "impermeabile",
        "softshell",
        "windbreaker",
    ],

    "sports": [
        "sport",
        "fitness",
        "palestra",
        "running",
        "ciclismo",
        "bicicletta",
        "calcio",
        "tennis",
        "padel",
        "yoga",
        "allenamento",
        "training",
        "escursionismo",
        "trekking",
    ],

    "auto": [
        "auto",
        "automobile",
        "macchina",
        "automotive",
        "car",
        "moto",
        "motocicletta",
        "accessori auto",
        "supporto auto",
        "caricatore auto",
        "compressore",
        "dash cam",
        "telecamera auto",
        "organizer auto",
    ],

    "travel": [
        "viaggio",
        "travel",
        "valigia",
        "trolley",
        "zaino",
        "bagaglio",
        "beauty case",
        "porta passaporto",
        "adattatore viaggio",
        "travel organizer",
        "borsa viaggio",
        "accessori viaggio",
    ],

    "hobbies": [
        "hobby",
        "modellismo",
        "fotografia",
        "musica",
        "strumento musicale",
        "disegno",
        "pittura",
        "craft",
        "fai da te creativo",
        "collezionismo",
        "giochi da tavolo",
        "board game",
        "tempo libero",
    ],
}


# -------------------------------------------------------------------
# QUERY
# -------------------------------------------------------------------
#
# Le query sono distribuite secondo le priorità concordate.
#
# Alta priorità:
#   Tecnologia        30%
#   Gaming            20%
#   Vestiti donna     15%
#   Outdoor           15%
#
# Media:
#   Sport              5%
#   Auto               5%
#   Travel             5%
#   Hobby              5%
#
# La lista è costruita in modo che la rotazione sia continua.
# Lo stato dell'ultima posizione viene salvato in ROTATION_FILE.
#
# Con 180 query/mese, le proporzioni vengono approssimate
# sul lungo periodo.
#

SEARCH_POOL = [
    # TECNOLOGIA - alta priorità
    ("cuffie bluetooth", "technology"),
    ("auricolari bluetooth", "technology"),
    ("mouse wireless", "technology"),
    ("tastiera meccanica", "technology"),
    ("webcam pc", "technology"),
    ("power bank", "technology"),
    ("caricatore usb c", "technology"),
    ("ssd nvme", "technology"),
    ("smartwatch", "technology"),

    # GAMING - alta priorità
    ("controller gaming", "gaming"),
    ("cuffie gaming", "gaming"),
    ("mouse gaming", "gaming"),
    ("tastiera gaming", "gaming"),
    ("accessori ps5", "gaming"),
    ("accessori xbox", "gaming"),

    # VESTITI DONNA - alta priorità
    ("giacca donna", "women_clothing"),
    ("scarpe donna", "women_clothing"),
    ("sneakers donna", "women_clothing"),
    ("felpa donna", "women_clothing"),
    ("pantaloni donna", "women_clothing"),
    ("vestito donna", "women_clothing"),

    # ABBIGLIAMENTO OUTDOOR - alta priorità
    ("giacca trekking", "outdoor_clothing"),
    ("scarpe trekking", "outdoor_clothing"),
    ("pantaloni trekking", "outdoor_clothing"),
    ("pile uomo donna", "outdoor_clothing"),
    ("giacca impermeabile", "outdoor_clothing"),
    ("abbigliamento running", "outdoor_clothing"),

    # SPORT - media
    ("accessori fitness", "sports"),
    ("accessori running", "sports"),
    ("accessori ciclismo", "sports"),
    ("accessori palestra", "sports"),
    ("accessori trekking", "sports"),

    # AUTO - media
    ("accessori auto", "auto"),
    ("supporto smartphone auto", "auto"),
    ("caricatore auto usb", "auto"),
    ("compressore auto", "auto"),
    ("dash cam", "auto"),

    # TRAVEL - media
    ("accessori viaggio", "travel"),
    ("zaino viaggio", "travel"),
    ("valigia trolley", "travel"),
    ("organizer viaggio", "travel"),
    ("accessori valigia", "travel"),

    # HOBBY - media
    ("modellismo", "hobbies"),
    ("accessori fotografia", "hobbies"),
    ("giochi da tavolo", "hobbies"),
    ("accessori musica", "hobbies"),
    ("hobby creativi", "hobbies"),
]


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


def load_rotation_index():
    if not os.path.exists(ROTATION_FILE):
        return 0

    try:
        with open(ROTATION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return int(data.get("index", 0))

    except (json.JSONDecodeError, TypeError, ValueError):
        return 0


def save_rotation_index(index):
    with open(ROTATION_FILE, "w", encoding="utf-8") as file:
        json.dump(
            {"index": index},
            file,
            indent=2
        )


def get_next_searches():
    """
    Restituisce le prossime QUERIES_PER_RUN query della rotazione.

    La posizione viene salvata su disco, quindi la rotazione
    continua da una esecuzione all'altra e non ricomincia
    ogni giorno.
    """

    if not SEARCH_POOL:
        return []

    start_index = load_rotation_index()

    selected = []

    for offset in range(QUERIES_PER_RUN):
        index = (start_index + offset) % len(SEARCH_POOL)
        selected.append(SEARCH_POOL[index])

    next_index = (
        start_index + QUERIES_PER_RUN
    ) % len(SEARCH_POOL)

    save_rotation_index(next_index)

    return selected


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

    def find_products(value):
        # Lista di prodotti
        if isinstance(value, list):
            products = [
                item
                for item in value
                if isinstance(item, dict) and item.get("asin")
            ]

            if products:
                return products

            # Cerca anche dentro eventuali liste annidate
            for item in value:
                result = find_products(item)

                if result:
                    return result

        # Dizionario
        elif isinstance(value, dict):
            if value.get("asin"):
                return [value]

            for item in value.values():
                result = find_products(item)

                if result:
                    return result

        # A volte una risposta può contenere JSON
        # sotto forma di stringa.
        elif isinstance(value, str):
            try:
                decoded = json.loads(value)
                return find_products(decoded)

            except (json.JSONDecodeError, TypeError):
                pass

        return []

    products = find_products(data)

    return products


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

    searches = get_next_searches()

    print()
    print("=" * 70)
    print("ROTazione query")
    print("=" * 70)

    for query, category in searches:
        print(f"- {query} [{category}]")

    print("=" * 70)

    total_results = 0
    products_in_range = 0
    products_filtered = 0

    for query, category in searches:
        print()
        print("=" * 70)
        print(f"Ricerca: {query}")
        print(f"Categoria: {category}")

        products = search_parse(query)

        print(f"Risultati Parse: {len(products)}")

        total_results += len(products)

        for product in products:

            if not product_passes_filter(
                product,
                category
            ):
                continue

            products_in_range += 1

            if save_product(
                history,
                product,
                category
            ):
                products_filtered += 1

    save_history(history)

    print()
    print("=" * 70)
    print("AGGIORNAMENTO STORICO COMPLETATO")
    print(f"Query eseguite: {len(searches)}")
    print(f"Risultati totali Parse: {total_results}")
    print(
        "Prodotti validi nel range 10–50 €: "
        f"{products_in_range}"
    )
    print(
        "Prodotti salvati/aggiornati: "
        f"{products_filtered}"
    )
    print(
        "Totale prodotti nello storico: "
        f"{len(history)}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
