import os
import json
import re
from datetime import date
import requests


# ============================================================
# CONFIGURAZIONE
# ============================================================

PARSE_API_KEY = os.getenv("PARSE_API_KEY")

PARSE_URL = (
    "https://api.parse.bot/scraper/"
    "18564612-8aa3-47b4-a88b-4bc5ba70f945/"
    "get_search_results_csv"
)

HISTORY_FILE = "price_history.json"
ROTATION_FILE = "search_rotation.json"

MIN_PRICE = 10.0
MAX_PRICE = 50.0

# 2 query per ogni esecuzione
QUERIES_PER_RUN = 2

# Budget normale
STANDARD_MONTHLY_QUERY_LIMIT = 180

# Settembre 2026: margine di sicurezza
CURRENT_MONTH_QUERY_LIMIT = 140

# Non consideriamo un deal "storicamente valutabile"
# finché non abbiamo almeno 3 osservazioni.
MIN_HISTORY_POINTS = 3


# ============================================================
# ROTAZIONE
# ============================================================
#
# 20 posizioni:
#
# Tecnologia       5 = 25%
# Gaming           4 = 20%
# Donna sera       4 = 20%
# Outdoor          3 = 15%
# T-shirt uomo     3 = 15%
# Sportivo         1 =  5%
#
# 9 cicli completi = 180 query
# ============================================================

SEARCH_CYCLE = [
    # 🔴 TECNOLOGIA — 5/20
    {"category": "technology", "query": "cuffie bluetooth"},
    {"category": "technology", "query": "smartwatch"},
    {"category": "technology", "query": "mouse wireless"},
    {"category": "technology", "query": "tastiera meccanica"},
    {"category": "technology", "query": "webcam full hd"},

    # 🔴 GAMING — 4/20
    {"category": "gaming", "query": "mouse gaming"},
    {"category": "gaming", "query": "tastiera gaming"},
    {"category": "gaming", "query": "cuffie gaming"},
    {"category": "gaming", "query": "controller pc gaming"},

    # 🔴 VESTITI DA SERA DONNA — 4/20
    {"category": "women_evening", "query": "vestito elegante donna"},
    {"category": "women_evening", "query": "abito cerimonia donna"},
    {"category": "women_evening", "query": "vestito cocktail donna"},
    {"category": "women_evening", "query": "abito lungo elegante donna"},

    # 🔴 OUTDOOR — 3/20
    {"category": "outdoor_clothing", "query": "pile trekking"},
    {"category": "outdoor_clothing", "query": "giacca softshell"},
    {"category": "outdoor_clothing", "query": "giacca impermeabile trekking"},

    # 🔴 MAGLIETTE UOMO — 3/20
    {"category": "men_tshirts", "query": "t shirt uomo confezione"},
    {"category": "men_tshirts", "query": "t shirt uomo 2 pezzi"},
    {"category": "men_tshirts", "query": "t shirt uomo 3 pezzi"},

    # 🟡 ABBIGLIAMENTO SPORTIVO — 1/20
    {"category": "sportswear", "query": "t shirt running"},
]


# ============================================================
# FUNZIONI JSON
# ============================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# PREZZO
# ============================================================

def parse_price(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    text = (
        text.replace("€", "")
        .replace("EUR", "")
        .replace("\u00a0", " ")
        .strip()
    )

    # Formato italiano: 1.234,56
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")

    try:
        return float(text)
    except ValueError:
        pass

    match = re.search(r"\d+(?:\.\d+)?", text)

    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None

    return None


# ============================================================
# NORMALIZZAZIONE PARSE
# ============================================================

def find_products(obj):
    """
    Cerca ricorsivamente prodotti con ASIN.
    Gestisce anche JSON contenuto dentro stringhe.
    """

    products = []

    if isinstance(obj, dict):

        if obj.get("asin"):
            products.append(obj)

        for value in obj.values():
            products.extend(find_products(value))

    elif isinstance(obj, list):

        for item in obj:
            products.extend(find_products(item))

    elif isinstance(obj, str):

        text = obj.strip()

        if text.startswith("{") or text.startswith("["):
            try:
                parsed = json.loads(text)
                products.extend(find_products(parsed))
            except Exception:
                pass

    return products


# ============================================================
# PARSE
# ============================================================

def search_parse(query):
    if not PARSE_API_KEY:
        raise RuntimeError("PARSE_API_KEY non configurata.")

    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "query": query,
    }

    response = requests.get(
        PARSE_URL,
        headers=headers,
        params=params,
        timeout=60,
    )

    response.raise_for_status()

    try:
        data = response.json()
    except Exception:
        data = response.text

    products = find_products(data)

    unique = {}

    for product in products:
        asin = product.get("asin")

        if asin:
            unique[str(asin)] = product

    return list(unique.values())


# ============================================================
# FILTRO CATEGORIA
# ============================================================
#
# IMPORTANTE:
# Non usiamo più filtri rigidi.
# Le query sono già mirate.
#
# Qui controlliamo solamente che il prodotto abbia
# almeno qualche indicatore compatibile con la categoria.
# ============================================================

def category_matches(product, category):

    title = str(product.get("title", "")).lower().strip()

    if not title:
        return False

    # --------------------------------------------------------
    # TECNOLOGIA
    # --------------------------------------------------------

    if category == "technology":

        keywords = [
            "smartphone",
            "telefono",
            "tablet",
            "ipad",
            "computer",
            "pc",
            "laptop",
            "notebook",
            "monitor",
            "smartwatch",
            "orologio smart",
            "cuffie",
            "auricolari",
            "earbuds",
            "mouse",
            "tastiera",
            "webcam",
            "router",
            "ssd",
            "hard disk",
            "disco esterno",
            "elettronica",
            "caricatore",
            "power bank",
            "hub usb",
            "usb",
            "bluetooth",
        ]

        return any(k in title for k in keywords)

    # --------------------------------------------------------
    # GAMING
    # --------------------------------------------------------

    if category == "gaming":

        keywords = [
            "gaming",
            "videogioco",
            "videogame",
            "playstation",
            "ps5",
            "ps4",
            "xbox",
            "nintendo",
            "switch",
            "controller",
            "joystick",
            "gamepad",
            "steam deck",
            "cuffie gaming",
            "mouse gaming",
            "tastiera gaming",
            "volante gaming",
        ]

        return any(k in title for k in keywords)

    # --------------------------------------------------------
    # DONNA - VESTITI DA SERA
    # --------------------------------------------------------

    if category == "women_evening":

        keywords = [
            "vestito",
            "abito",
            "dress",
            "gonna",
            "cerimonia",
            "elegante",
            "sera",
            "cocktail",
            "party",
            "ballo",
            "midi",
            "maxi dress",
            "abito lungo",
        ]

        # Deve esserci un indicatore di abbigliamento
        return any(k in title for k in keywords)

    # --------------------------------------------------------
    # OUTDOOR
    # --------------------------------------------------------

    if category == "outdoor_clothing":

        keywords = [
            "outdoor",
            "trekking",
            "hiking",
            "escursionismo",
            "montagna",
            "softshell",
            "hardshell",
            "impermeabile",
            "antipioggia",
            "giacca",
            "pile",
            "fleece",
            "windbreaker",
            "parka",
            "gilet",
        ]

        return any(k in title for k in keywords)

    # --------------------------------------------------------
    # T-SHIRT UOMO
    # --------------------------------------------------------

    if category == "men_tshirts":

        product_keywords = [
            "t-shirt",
            "t shirt",
            "tshirt",
            "maglietta",
            "maglia",
        ]

        men_keywords = [
            "uomo",
            "men",
            "mens",
            "male",
            "maschile",
        ]

        has_product = any(k in title for k in product_keywords)
        has_men = any(k in title for k in men_keywords)

        # Se il titolo dice chiaramente uomo/men,
        # accettiamo il prodotto.
        if has_product and has_men:
            return True

        # Alcuni risultati Amazon possono non riportare
        # "uomo" nel titolo. In quel caso accettiamo comunque
        # una T-shirt se la query era specificamente uomo.
        return has_product

    # --------------------------------------------------------
    # ABBIGLIAMENTO SPORTIVO
    # --------------------------------------------------------

    if category == "sports_clothing":

        keywords = [
            "sport",
            "sportivo",
            "running",
            "fitness",
            "training",
            "palestra",
            "workout",
            "jogging",
            "tuta",
            "pantaloni sportivi",
            "giacca sportiva",
            "abbigliamento sportivo",
        ]

        return any(k in title for k in keywords)

    return True


# ============================================================
# STORICO
# ============================================================

def update_history(products, category):

    history = load_json(HISTORY_FILE, {})

    today = date.today().isoformat()

    saved = 0
    skipped_price = 0
    skipped_category = 0
    skipped_other = 0

    for product in products:

        asin = str(product.get("asin", "")).strip()

        if not asin:
            skipped_other += 1
            continue

        title = str(product.get("title", "")).strip()

        if not title:
            skipped_other += 1
            continue

        # Prova diversi possibili campi prezzo
        price_value = (
            product.get("price")
            or product.get("current_price")
            or product.get("buybox_price")
            or product.get("buy_box_price")
        )

        price = parse_price(price_value)

        if price is None:
            skipped_price += 1
            continue

        # Fascia richiesta
        if price < MIN_PRICE or price > MAX_PRICE:
            skipped_price += 1
            continue

        # Filtro categoria
        if not category_matches(product, category):
            skipped_category += 1
            continue

        # Crea prodotto se nuovo
        if asin not in history:

            history[asin] = {
                "title": title,
                "category": category,
                "prices": [],
            }

        item = history[asin]

        item["title"] = title
        item["category"] = category

        if "prices" not in item or not isinstance(item["prices"], list):
            item["prices"] = []

        # Aggiorna la rilevazione odierna se già presente
        existing = None

        for observation in item["prices"]:

            if (
                isinstance(observation, dict)
                and observation.get("date") == today
            ):
                existing = observation
                break

        if existing:

            existing["price"] = round(price, 2)

        else:

            item["prices"].append(
                {
                    "date": today,
                    "price": round(price, 2),
                }
            )

        saved += 1

    save_json(HISTORY_FILE, history)

    return {
        "saved": saved,
        "skipped_price": skipped_price,
        "skipped_category": skipped_category,
        "skipped_other": skipped_other,
    }


# ============================================================
# LIMITE MENSILE
# ============================================================

def get_monthly_limit(today):

    if today.year == 2026 and today.month == 9:
        return CURRENT_MONTH_QUERY_LIMIT

    return STANDARD_MONTHLY_QUERY_LIMIT


# ============================================================
# ROTAZIONE
# ============================================================

def load_rotation(today):

    rotation = load_json(
        ROTATION_FILE,
        {
            "version": 1,
            "month": today.strftime("%Y-%m"),
            "queries_used": 0,
            "index": 0,
        },
    )

    current_month = today.strftime("%Y-%m")

    if rotation.get("month") != current_month:

        rotation = {
            "version": 1,
            "month": current_month,
            "queries_used": 0,
            "index": 0,
        }

    try:
        rotation["queries_used"] = int(
            rotation.get("queries_used", 0)
        )
    except Exception:
        rotation["queries_used"] = 0

    try:
        rotation["index"] = int(
            rotation.get("index", 0)
        )
    except Exception:
        rotation["index"] = 0

    rotation["index"] %= len(SEARCH_CYCLE)

    return rotation


def get_next_searches(rotation, monthly_limit):

    remaining = monthly_limit - rotation["queries_used"]

    if remaining <= 0:
        return []

    count = min(
        QUERIES_PER_RUN,
        remaining,
    )

    searches = []

    for offset in range(count):

        position = (
            rotation["index"] + offset
        ) % len(SEARCH_CYCLE)

        searches.append(
            SEARCH_CYCLE[position]
        )

    return searches


def register_successful_query(rotation):

    rotation["queries_used"] += 1

    rotation["index"] = (
        rotation["index"] + 1
    ) % len(SEARCH_CYCLE)


# ============================================================
# MAIN
# ============================================================

def main():

    today = date.today()

    monthly_limit = get_monthly_limit(today)

    rotation = load_rotation(today)

    print("=" * 60)
    print("DEAL HUNTER - PRICE TRACKER")
    print("=" * 60)

    print(f"Data: {today}")
    print(f"Mese: {rotation['month']}")
    print(
        f"Query utilizzate: "
        f"{rotation['queries_used']}/{monthly_limit}"
    )
    print(
        f"Posizione rotazione: "
        f"{rotation['index']}"
    )
    print(
        f"Query per esecuzione: "
        f"{QUERIES_PER_RUN}"
    )

    searches = get_next_searches(
        rotation,
        monthly_limit,
    )

    if not searches:

        print()
        print("LIMITE MENSILE RAGGIUNTO.")
        print("Nessuna query Parse verrà eseguita.")

        save_json(
            ROTATION_FILE,
            rotation,
        )

        return

    all_products = []

    successful_queries = 0

    # ========================================================
    # QUERY
    # ========================================================

    for number, search in enumerate(
        searches,
        start=1,
    ):

        category = search["category"]
        query = search["query"]

        print()
        print(
            f"Query {number}/{len(searches)}"
        )
        print(
            f"Categoria: {category}"
        )
        print(
            f"Ricerca: {query}"
        )

        try:

            products = search_parse(query)

            print(
                f"Risultati ricevuti: "
                f"{len(products)}"
            )

            all_products.extend(
                [
                    (product, category)
                    for product in products
                ]
            )

            # La query viene conteggiata SOLO
            # se Parse ha risposto correttamente.
            register_successful_query(
                rotation
            )

            successful_queries += 1

        except Exception as e:

            print(
                f"ERRORE Parse: {e}"
            )

            print(
                "Query NON conteggiata."
            )

    # ========================================================
    # DEDUPLICAZIONE
    # ========================================================

    unique_products = {}

    for product, category in all_products:

        asin = str(
            product.get("asin", "")
        ).strip()

        if not asin:
            continue

        if asin not in unique_products:

            unique_products[asin] = (
                product,
                category,
            )

    products_to_process = list(
        unique_products.values()
    )

    print()
    print(
        f"Prodotti unici ricevuti: "
        f"{len(products_to_process)}"
    )

    # ========================================================
    # AGGIORNAMENTO STORICO
    # ========================================================

    grouped = {}

    for product, category in products_to_process:

        grouped.setdefault(
            category,
            []
        ).append(product)

    total_saved = 0
    total_price_skipped = 0
    total_category_skipped = 0
    total_other_skipped = 0

    for category, products in grouped.items():

        result = update_history(
            products,
            category,
        )

        total_saved += result["saved"]
        total_price_skipped += (
            result["skipped_price"]
        )
        total_category_skipped += (
            result["skipped_category"]
        )
        total_other_skipped += (
            result["skipped_other"]
        )

    # ========================================================
    # SALVA ROTAZIONE
    # ========================================================

    save_json(
        ROTATION_FILE,
        rotation,
    )

    # ========================================================
    # RIEPILOGO
    # ========================================================

    print()
    print("=" * 60)
    print("COMPLETATO")
    print("=" * 60)

    print(
        f"Query riuscite: "
        f"{successful_queries}"
    )

    print(
        f"Query mensili utilizzate: "
        f"{rotation['queries_used']}/{monthly_limit}"
    )

    print(
        f"Prodotti validi salvati/aggiornati: "
        f"{total_saved}"
    )

    print(
        f"Scartati per prezzo: "
        f"{total_price_skipped}"
    )

    print(
        f"Scartati per categoria: "
        f"{total_category_skipped}"
    )

    print(
        f"Scartati per altri motivi: "
        f"{total_other_skipped}"
    )

    print()
    print(
        f"Prossima posizione rotazione: "
        f"{rotation['index']}"
    )

    if rotation["queries_used"] >= monthly_limit:

        print()
        print(
            "⚠️ LIMITE MENSILE RAGGIUNTO."
        )
        print(
            "Il tracker resterà fermo "
            "fino al prossimo mese."
        )

    print("=" * 60)


if __name__ == "__main__":
    main()
