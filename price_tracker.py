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

# ============================================================
# IMPORTANTE:
# questi NON sono limiti per gli alert.
#
# Servono soltanto a evitare prezzi palesemente anomali
# nello storico.
# ============================================================

HISTORY_MIN_PRICE = 0.01
HISTORY_MAX_PRICE = 300.0

# Prezzo massimo desiderato per l'acquisto/rivendita.
# Questo limite viene applicato dal DEAL HUNTER,
# non dal salvataggio dello storico.
MAX_CURRENT_PRICE = 30.0

# 2 query per esecuzione
QUERIES_PER_RUN = 2

# Budget normale
STANDARD_MONTHLY_QUERY_LIMIT = 180

# Settembre 2026: margine di sicurezza
CURRENT_MONTH_QUERY_LIMIT = 140

# Minimo storico tecnico
MIN_HISTORY_POINTS = 3


# ============================================================
# ROTAZIONE RICERCHE
# ============================================================

SEARCH_CYCLE = [

    # ========================================================
    # NIKE — 4/20
    # ========================================================

    {
        "category": "fashion_men",
        "query": "Nike t shirt uomo",
    },

    {
        "category": "fashion_women",
        "query": "Nike t shirt donna",
    },

    {
        "category": "fashion_men",
        "query": "Nike felpa uomo",
    },

    {
        "category": "fashion_women",
        "query": "Nike felpa donna",
    },


    # ========================================================
    # ADIDAS — 4/20
    # ========================================================

    {
        "category": "fashion_men",
        "query": "Adidas t shirt uomo",
    },

    {
        "category": "fashion_women",
        "query": "Adidas t shirt donna",
    },

    {
        "category": "fashion_men",
        "query": "Adidas felpa uomo",
    },

    {
        "category": "fashion_women",
        "query": "Adidas felpa donna",
    },


    # ========================================================
    # THE NORTH FACE — 4/20
    # ========================================================

    {
        "category": "outdoor_clothing",
        "query": "The North Face pile uomo",
    },

    {
        "category": "outdoor_clothing",
        "query": "The North Face pile donna",
    },

    {
        "category": "outdoor_clothing",
        "query": "The North Face giacca uomo",
    },

    {
        "category": "outdoor_clothing",
        "query": "The North Face giacca donna",
    },


    # ========================================================
    # COLUMBIA — 3/20
    # ========================================================

    {
        "category": "outdoor_clothing",
        "query": "Columbia pile uomo",
    },

    {
        "category": "outdoor_clothing",
        "query": "Columbia pile donna",
    },

    {
        "category": "outdoor_clothing",
        "query": "Columbia giacca uomo donna",
    },


    # ========================================================
    # CALVIN KLEIN — 2/20
    # ========================================================

    {
        "category": "fashion_men",
        "query": "Calvin Klein t shirt uomo",
    },

    {
        "category": "fashion_women",
        "query": "Calvin Klein t shirt donna",
    },


    # ========================================================
    # TOMMY HILFIGER — 1/20
    # ========================================================

    {
        "category": "fashion_men",
        "query": "Tommy Hilfiger t shirt uomo",
    },


    # ========================================================
    # GUESS — 1/20
    # ========================================================

    {
        "category": "fashion_accessories",
        "query": "Guess borsa donna",
    },


    # ========================================================
    # PANDORA — 1/20
    # ========================================================

    {
        "category": "jewelry",
        "query": "Pandora anello",
    },
]


# ============================================================
# JSON
# ============================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8",
        ) as f:

            return json.load(f)

    except Exception:

        return default


def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# TESTO
# ============================================================

def normalize_text(text):

    text = str(text or "").lower()

    text = (
        text
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
        .replace("\\", " ")
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def contains_keyword(text, keyword):

    text = normalize_text(text)
    keyword = normalize_text(keyword)

    if not keyword:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(keyword)
        + r"(?!\w)"
    )

    return re.search(
        pattern,
        text,
        flags=re.IGNORECASE,
    ) is not None


def contains_any(text, keywords):

    return any(
        contains_keyword(text, keyword)
        for keyword in keywords
    )


# ============================================================
# PREZZO
# ============================================================

def parse_price(value):

    if value is None:
        return None

    if isinstance(
        value,
        (int, float),
    ):

        return float(value)

    text = str(value).strip()

    if not text:
        return None

    text = (
        text
        .replace("€", "")
        .replace("EUR", "")
        .replace("\u00a0", " ")
        .strip()
    )

    # 1.234,56 -> 1234.56
    if "," in text:

        text = (
            text
            .replace(".", "")
            .replace(",", ".")
        )

    else:

        text = text.replace(",", "")

    try:

        return float(text)

    except ValueError:

        pass

    match = re.search(
        r"\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:

        return float(
            match.group(0)
        )

    except ValueError:

        return None


# ============================================================
# NORMALIZZAZIONE PARSE
# ============================================================

def find_products(obj):

    products = []

    if isinstance(obj, dict):

        if obj.get("asin"):

            products.append(obj)

        for value in obj.values():

            products.extend(
                find_products(value)
            )

    elif isinstance(obj, list):

        for item in obj:

            products.extend(
                find_products(item)
            )

    elif isinstance(obj, str):

        text = obj.strip()

        if (
            text.startswith("{")
            or text.startswith("[")
        ):

            try:

                parsed = json.loads(text)

                products.extend(
                    find_products(parsed)
                )

            except Exception:

                pass

    return products


# ============================================================
# PARSE
# ============================================================

def search_parse(query):

    if not PARSE_API_KEY:

        raise RuntimeError(
            "PARSE_API_KEY non configurata."
        )

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

        asin = str(
            product.get("asin", "")
        ).strip()

        if asin:

            unique[asin] = product

    return list(
        unique.values()
    )


# ============================================================
# FILTRO CATEGORIA
# ============================================================

def category_matches(
    product,
    category,
    query,
):

    title = normalize_text(
        product.get("title", "")
    )

    query_text = normalize_text(
        query
    )

    if not title:
        return False


    # ========================================================
    # UOMO
    # ========================================================

    if category == "fashion_men":

        clothing_keywords = [
            "t shirt",
            "t-shirt",
            "tshirt",
            "tee",
            "maglietta",
            "felpa",
            "hoodie",
            "sweatshirt",
            "sweater",
            "pullover",
            "maglia",
            "shirt",
            "camicia",
            "polo",
            "pantaloni",
            "trousers",
            "pants",
            "jeans",
            "shorts",
            "bermuda",
            "giacca",
            "jacket",
            "coat",
            "gilet",
            "vest",
        ]

        invalid_keywords = [
            "profumo",
            "parfum",
            "eau de toilette",
            "deodorante",
            "shampoo",
            "conditioner",
            "intimo",
            "underwear",
            "boxer",
            "slip",
            "calzino",
            "calze",
            "sock",
            "socks",
            "portafoglio",
            "wallet",
            "borsa",
            "handbag",
            "zaino",
            "backpack",
            "cintura",
            "belt",
            "orologio",
            "watch",
            "cover",
            "custodia",
            "case",
        ]

        if contains_any(
            title,
            invalid_keywords,
        ):

            return False

        return contains_any(
            title,
            clothing_keywords,
        )


    # ========================================================
    # DONNA
    # ========================================================

    if category == "fashion_women":

        clothing_keywords = [
            "t shirt",
            "t-shirt",
            "tshirt",
            "tee",
            "maglietta",
            "felpa",
            "hoodie",
            "sweatshirt",
            "sweater",
            "pullover",
            "maglia",
            "shirt",
            "camicia",
            "top",
            "polo",
            "pantaloni",
            "trousers",
            "pants",
            "jeans",
            "shorts",
            "bermuda",
            "leggings",
            "giacca",
            "jacket",
            "coat",
            "gilet",
            "vest",
            "vestito",
            "dress",
            "abito",
            "gonna",
            "skirt",
        ]

        invalid_keywords = [
            "profumo",
            "parfum",
            "eau de toilette",
            "deodorante",
            "shampoo",
            "conditioner",
            "intimo",
            "underwear",
            "reggiseno",
            "bra",
            "slip",
            "mutande",
            "calze",
            "sock",
            "socks",
            "borsa",
            "handbag",
            "portafoglio",
            "wallet",
            "cintura",
            "belt",
            "orologio",
            "watch",
            "cover",
            "custodia",
            "case",
        ]

        if contains_any(
            title,
            invalid_keywords,
        ):

            return False

        return contains_any(
            title,
            clothing_keywords,
        )


    # ========================================================
    # OUTDOOR
    # ========================================================

    if category == "outdoor_clothing":

        clothing_keywords = [
            "pile",
            "fleece",
            "polar",
            "giacca",
            "jacket",
            "coat",
            "softshell",
            "hardshell",
            "shell jacket",
            "impermeabile",
            "waterproof",
            "rain jacket",
            "raincoat",
            "antipioggia",
            "windbreaker",
            "windproof",
            "antivento",
            "parka",
            "gilet",
            "vest",
            "piumino",
            "down jacket",
            "trekking",
            "hiking",
            "outdoor",
            "mountain",
            "montagna",
        ]

        invalid_keywords = [
            "scarpe",
            "shoe",
            "shoes",
            "stivali",
            "boots",
            "zaino",
            "backpack",
            "bastoncini",
            "trekking poles",
            "tenda",
            "tent",
            "sacco a pelo",
            "sleeping bag",
            "borraccia",
            "water bottle",
            "accessorio",
            "accessories",
        ]

        if contains_any(
            title,
            invalid_keywords,
        ):

            return False

        return contains_any(
            title,
            clothing_keywords,
        )


    # ========================================================
    # GUESS / BORSE
    # ========================================================

    if category == "fashion_accessories":

        bag_keywords = [
            "borsa",
            "bag",
            "handbag",
            "shoulder bag",
            "crossbody",
            "tracolla",
            "pochette",
            "clutch",
            "tote",
            "shopper",
            "borsetta",
        ]

        invalid_keywords = [
            "cover",
            "custodia",
            "case",
            "portachiavi",
            "keychain",
            "profumo",
            "parfum",
            "deodorante",
        ]

        if contains_any(
            title,
            invalid_keywords,
        ):

            return False

        return contains_any(
            title,
            bag_keywords,
        )


    # ========================================================
    # PANDORA
    # ========================================================

    if category == "jewelry":

        jewelry_keywords = [
            "anello",
            "ring",
            "gioiello",
            "jewelry",
            "jewellery",
        ]

        invalid_keywords = [
            "custodia",
            "case",
            "scatola",
            "box",
            "espositore",
            "display",
            "supporto",
            "stand",
            "porta gioielli",
            "jewelry box",
        ]

        if contains_any(
            title,
            invalid_keywords,
        ):

            return False

        return contains_any(
            title,
            jewelry_keywords,
        )


    return False


# ============================================================
# STORICO
# ============================================================

def update_history(
    products,
    category,
    query,
):

    history = load_json(
        HISTORY_FILE,
        {},
    )

    today = date.today().isoformat()

    saved = 0
    skipped_price = 0
    skipped_category = 0
    skipped_other = 0

    for product in products:

        asin = str(
            product.get("asin", "")
        ).strip()

        if not asin:

            skipped_other += 1
            continue

        title = str(
            product.get("title", "")
        ).strip()

        if not title:

            skipped_other += 1
            continue

        # ====================================================
        # PREZZO ATTUALE
        # ====================================================

        price_value = product.get(
            "price"
        )

        if price_value is None:

            price_value = product.get(
                "current_price"
            )

        if price_value is None:

            price_value = product.get(
                "buybox_price"
            )

        if price_value is None:

            price_value = product.get(
                "buy_box_price"
            )

        price = parse_price(
            price_value
        )

        if price is None:

            skipped_price += 1
            continue

        # ====================================================
        # FILTRO TECNICO STORICO
        #
        # NON è il limite dell'alert.
        # Qui permettiamo anche prezzi > 30 €.
        # ====================================================

        if (
            price < HISTORY_MIN_PRICE
            or price > HISTORY_MAX_PRICE
        ):

            skipped_price += 1
            continue

        # ====================================================
        # CATEGORIA
        # ====================================================

        if not category_matches(
            product,
            category,
            query,
        ):

            skipped_category += 1
            continue

        # ====================================================
        # CREA PRODOTTO
        # ====================================================

        if asin not in history:

            history[asin] = {
                "title": title,
                "category": category,
                "query": query,
                "prices": [],
            }

        item = history[asin]

        item["title"] = title
        item["category"] = category
        item["query"] = query

        if (
            "prices" not in item
            or not isinstance(
                item["prices"],
                list,
            )
        ):

            item["prices"] = []

        # ====================================================
        # UNA SOLA RILEVAZIONE AL GIORNO
        # ====================================================

        existing = None

        for observation in item["prices"]:

            if (
                isinstance(
                    observation,
                    dict,
                )
                and observation.get("date")
                == today
            ):

                existing = observation
                break

        if existing:

            existing["price"] = round(
                price,
                2,
            )

        else:

            item["prices"].append(
                {
                    "date": today,
                    "price": round(
                        price,
                        2,
                    ),
                }
            )

        saved += 1

    save_json(
        HISTORY_FILE,
        history,
    )

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

    if (
        today.year == 2026
        and today.month == 9
    ):

        return CURRENT_MONTH_QUERY_LIMIT

    return STANDARD_MONTHLY_QUERY_LIMIT


# ============================================================
# ROTAZIONE
# ============================================================

def load_rotation(today):

    rotation = load_json(
        ROTATION_FILE,
        {
            "version": 4,
            "month": today.strftime(
                "%Y-%m"
            ),
            "queries_used": 0,
            "index": 0,
        },
    )

    current_month = today.strftime(
        "%Y-%m"
    )

    if (
        rotation.get("month")
        != current_month
    ):

        rotation = {
            "version": 4,
            "month": current_month,
            "queries_used": 0,
            "index": 0,
        }

    try:

        rotation["queries_used"] = int(
            rotation.get(
                "queries_used",
                0,
            )
        )

    except Exception:

        rotation["queries_used"] = 0

    try:

        rotation["index"] = int(
            rotation.get(
                "index",
                0,
            )
        )

    except Exception:

        rotation["index"] = 0

    rotation["index"] %= len(
        SEARCH_CYCLE
    )

    return rotation


def get_next_searches(
    rotation,
    monthly_limit,
):

    remaining = (
        monthly_limit
        - rotation["queries_used"]
    )

    if remaining <= 0:

        return []

    count = min(
        QUERIES_PER_RUN,
        remaining,
    )

    searches = []

    for offset in range(count):

        position = (
            rotation["index"]
            + offset
        ) % len(SEARCH_CYCLE)

        searches.append(
            SEARCH_CYCLE[position]
        )

    return searches


def register_successful_query(
    rotation,
):

    rotation["queries_used"] += 1

    rotation["index"] = (
        rotation["index"] + 1
    ) % len(SEARCH_CYCLE)


# ============================================================
# MAIN
# ============================================================

def main():

    today = date.today()

    monthly_limit = get_monthly_limit(
        today
    )

    rotation = load_rotation(
        today
    )

    print("=" * 60)
    print(
        "DEAL HUNTER - PRICE TRACKER"
    )
    print("=" * 60)

    print(
        f"Data: {today}"
    )

    print(
        f"Mese: {rotation['month']}"
    )

    print(
        f"Query utilizzate: "
        f"{rotation['queries_used']}"
        f"/{monthly_limit}"
    )

    print(
        f"Posizione rotazione: "
        f"{rotation['index']}"
    )

    print(
        f"Query per esecuzione: "
        f"{QUERIES_PER_RUN}"
    )

    print(
        "Storico: "
        f"{HISTORY_MIN_PRICE:.2f}-"
        f"{HISTORY_MAX_PRICE:.0f} €"
    )

    print(
        "Alert/acquisto: "
        f"max {MAX_CURRENT_PRICE:.0f} €"
    )

    searches = get_next_searches(
        rotation,
        monthly_limit,
    )

    if not searches:

        print()
        print(
            "LIMITE MENSILE RAGGIUNTO."
        )

        print(
            "Nessuna query Parse "
            "verrà eseguita."
        )

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

        category = search[
            "category"
        ]

        query = search[
            "query"
        ]

        print()

        print(
            f"Query "
            f"{number}/{len(searches)}"
        )

        print(
            f"Categoria: "
            f"{category}"
        )

        print(
            f"Ricerca: "
            f"{query}"
        )

        try:

            products = search_parse(
                query
            )

            print(
                f"Risultati ricevuti: "
                f"{len(products)}"
            )

            all_products.extend(
                [
                    (
                        product,
                        category,
                        query,
                    )
                    for product in products
                ]
            )

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

    for (
        product,
        category,
        query,
    ) in all_products:

        asin = str(
            product.get("asin", "")
        ).strip()

        if not asin:
            continue

        if asin not in unique_products:

            unique_products[asin] = (
                product,
                category,
                query,
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

    total_saved = 0
    total_price_skipped = 0
    total_category_skipped = 0
    total_other_skipped = 0

    for (
        product,
        category,
        query,
    ) in products_to_process:

        result = update_history(
            [product],
            category,
            query,
        )

        total_saved += result[
            "saved"
        ]

        total_price_skipped += result[
            "skipped_price"
        ]

        total_category_skipped += result[
            "skipped_category"
        ]

        total_other_skipped += result[
            "skipped_other"
        ]


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
        f"{rotation['queries_used']}"
        f"/{monthly_limit}"
    )

    print(
        f"Prodotti validi "
        f"salvati/aggiornati: "
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
        f"Prossima posizione "
        f"rotazione: "
        f"{rotation['index']}"
    )

    if (
        rotation["queries_used"]
        >= monthly_limit
    ):

        print()

        print(
            "⚠️ LIMITE MENSILE "
            "RAGGIUNTO."
        )

        print(
            "Il tracker resterà fermo "
            "fino al prossimo mese."
        )

    print("=" * 60)


# ============================================================
# AVVIO
# ============================================================

if __name__ == "__main__":

    main()
