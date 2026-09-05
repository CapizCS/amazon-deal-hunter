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
# STORICO
# ============================================================
#
# IMPORTANTE:
# Il prezzo massimo NON è 30 €.
#
# Salviamo nello storico anche prodotti da 50, 100, 200,
# 300 € perché ci servono per capire il prezzo normale.
#
# Il limite di 30 € viene applicato successivamente
# dal Deal Hunter quando decide se mandare l'alert.
# ============================================================

HISTORY_MIN_PRICE = 0.01
HISTORY_MAX_PRICE = 300.0

# Solo informativo: il vero limite viene applicato
# da deal_hunter.py.
MAX_CURRENT_PRICE = 30.0


# ============================================================
# QUERY / BUDGET
# ============================================================

QUERIES_PER_RUN = 2

STANDARD_MONTHLY_QUERY_LIMIT = 180

# Settembre 2026
CURRENT_MONTH_QUERY_LIMIT = 140

MIN_HISTORY_POINTS = 3


# ============================================================
# ROTAZIONE
# ============================================================
#
# 20 query:
#
# Nike                 4
# Adidas               4
# The North Face       4
# Columbia             3
# Calvin Klein         2
# Tommy Hilfiger       1
# Guess                1
# Pandora              1
#
# 9 cicli completi = 180 query
# ============================================================

SEARCH_CYCLE = [

    # --------------------------------------------------------
    # NIKE
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # ADIDAS
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # THE NORTH FACE
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # COLUMBIA
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # CALVIN KLEIN
    # --------------------------------------------------------

    {
        "category": "fashion_men",
        "query": "Calvin Klein t shirt uomo",
    },

    {
        "category": "fashion_women",
        "query": "Calvin Klein t shirt donna",
    },


    # --------------------------------------------------------
    # TOMMY HILFIGER
    # --------------------------------------------------------

    {
        "category": "fashion_men",
        "query": "Tommy Hilfiger t shirt uomo",
    },


    # --------------------------------------------------------
    # GUESS
    # --------------------------------------------------------

    {
        "category": "fashion_accessories",
        "query": "Guess borsa donna",
    },


    # --------------------------------------------------------
    # PANDORA
    # --------------------------------------------------------

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

    # Formato italiano:
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
# NORMALIZZAZIONE RISPOSTA PARSE
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
#
# PRINCIPIO:
#
# La query è già molto specifica.
#
# Non dobbiamo pretendere che il titolo Amazon contenga
# esattamente tutte le parole della query.
#
# Usiamo quindi:
#
# 1. marca richiesta
# 2. tipo di prodotto richiesto
# 3. sesso quando riconoscibile
# 4. esclusioni evidenti
#
# In questo modo non perdiamo prodotti buoni solo perché
# Amazon ha restituito un titolo particolare.
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
    # ESCLUSIONI GENERALI
    # ========================================================
    #
    # Questi prodotti non ci interessano praticamente mai
    # nelle categorie attuali.
    # ========================================================

    universal_exclusions = [
        "profumo",
        "parfum",
        "eau de toilette",
        "deodorante",
        "shampoo",
        "conditioner",
        "balsamo capelli",
        "dentifricio",
        "crema",
        "make up",
        "fondotinta",
        "rossetto",

        "scarpe",
        "scarpa",
        "shoe",
        "shoes",
        "sneaker",
        "sneakers",
        "stivali",
        "boots",
        "sandali",
        "sandal",

        "calze",
        "calzini",
        "sock",
        "socks",

        "intimo",
        "underwear",
        "boxer",
        "slip",
        "reggiseno",
        "bra",

        "zaino",
        "backpack",

        "portafoglio",
        "wallet",

        "cintura",
        "belt",

        "cover",
        "custodia",
        "case",
    ]


    # ========================================================
    # UOMO
    # ========================================================

    if category == "fashion_men":

        # ----------------------------------------------------
        # MARCA
        # ----------------------------------------------------

        brands = []

        if contains_keyword(
            query_text,
            "nike",
        ):

            brands.append("nike")

        if contains_keyword(
            query_text,
            "adidas",
        ):

            brands.append("adidas")

        if contains_keyword(
            query_text,
            "calvin klein",
        ):

            brands.append(
                "calvin klein"
            )

        if contains_keyword(
            query_text,
            "tommy hilfiger",
        ):

            brands.append(
                "tommy hilfiger"
            )

        if brands and not contains_any(
            title,
            brands,
        ):

            return False


        # ----------------------------------------------------
        # ESCLUSIONI
        # ----------------------------------------------------

        if contains_any(
            title,
            universal_exclusions,
        ):

            return False


        # ----------------------------------------------------
        # T-SHIRT
        # ----------------------------------------------------

        if contains_keyword(
            query_text,
            "t shirt",
        ):

            tshirt_keywords = [
                "t shirt",
                "t-shirt",
                "tshirt",
                "tee",
                "maglietta",
            ]

            return contains_any(
                title,
                tshirt_keywords,
            )


        # ----------------------------------------------------
        # FELPA
        # ----------------------------------------------------

        if contains_keyword(
            query_text,
            "felpa",
        ):

            sweatshirt_keywords = [
                "felpa",
                "hoodie",
                "sweatshirt",
                "sweater",
                "pullover",
                "crewneck",
            ]

            return contains_any(
                title,
                sweatshirt_keywords,
            )


        # ----------------------------------------------------
        # PANTALONI
        # ----------------------------------------------------

        if contains_keyword(
            query_text,
            "pantaloni",
        ):

            pants_keywords = [
                "pantaloni",
                "pants",
                "trousers",
                "jeans",
                "shorts",
                "bermuda",
            ]

            return contains_any(
                title,
                pants_keywords,
            )


        return False


    # ========================================================
    # DONNA
    # ========================================================

    if category == "fashion_women":

        brands = []

        if contains_keyword(
            query_text,
            "nike",
        ):

            brands.append("nike")

        if contains_keyword(
            query_text,
            "adidas",
        ):

            brands.append("adidas")

        if contains_keyword(
            query_text,
            "calvin klein",
        ):

            brands.append(
                "calvin klein"
            )

        if brands and not contains_any(
            title,
            brands,
        ):

            return False


        # ----------------------------------------------------
        # ESCLUSIONI
        # ----------------------------------------------------

        if contains_any(
            title,
            universal_exclusions,
        ):

            return False


        # ----------------------------------------------------
        # T-SHIRT
        # ----------------------------------------------------

        if contains_keyword(
            query_text,
            "t shirt",
        ):

            tshirt_keywords = [
                "t shirt",
                "t-shirt",
                "tshirt",
                "tee",
                "maglietta",
            ]

            return contains_any(
                title,
                tshirt_keywords,
            )


        # ----------------------------------------------------
        # FELPA
        # ----------------------------------------------------

        if contains_keyword(
            query_text,
            "felpa",
        ):

            sweatshirt_keywords = [
                "felpa",
                "hoodie",
                "sweatshirt",
                "sweater",
                "pullover",
                "crewneck",
            ]

            return contains_any(
                title,
                sweatshirt_keywords,
            )


        return False


    # ========================================================
    # OUTDOOR
    # ========================================================

    if category == "outdoor_clothing":

        # ----------------------------------------------------
        # MARCA
        # ----------------------------------------------------

        outdoor_brands = [
            "the north face",
            "columbia",
        ]

        if not contains_any(
            title,
            outdoor_brands,
        ):

            return False


        # ----------------------------------------------------
        # ESCLUSIONI
        # ----------------------------------------------------

        outdoor_exclusions = [
            "scarpe",
            "scarpa",
            "shoe",
            "shoes",
            "sneaker",
            "stivali",
            "boots",
            "zaino",
            "backpack",
            "borraccia",
            "water bottle",
            "tenda",
            "tent",
            "sacco a pelo",
            "sleeping bag",
            "bastoncini",
            "trekking poles",
        ]

        if contains_any(
            title,
            outdoor_exclusions,
        ):

            return False


        # ----------------------------------------------------
        # PILE
        # ----------------------------------------------------

        if contains_keyword(
            query_text,
            "pile",
        ):

            pile_keywords = [
                "pile",
                "fleece",
                "polar",
            ]

            return contains_any(
                title,
                pile_keywords,
            )


        # ----------------------------------------------------
        # GIACCA
        # ----------------------------------------------------

        if contains_keyword(
            query_text,
            "giacca",
        ):

            jacket_keywords = [
                "giacca",
                "jacket",
                "coat",
                "parka",
                "softshell",
                "hardshell",
                "shell",
                "impermeabile",
                "waterproof",
                "rain jacket",
                "raincoat",
                "antipioggia",
                "windbreaker",
                "windproof",
                "antivento",
                "piumino",
                "down jacket",
            ]

            return contains_any(
                title,
                jacket_keywords,
            )


        return False


    # ========================================================
    # GUESS — BORSE DONNA
    # ========================================================

    if category == "fashion_accessories":

        if not contains_keyword(
            title,
            "guess",
        ):

            return False


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

        if not contains_any(
            title,
            bag_keywords,
        ):

            return False


        accessory_exclusions = [
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
            accessory_exclusions,
        ):

            return False


        return True


    # ========================================================
    # PANDORA — ANELLI
    # ========================================================

    if category == "jewelry":

        if not contains_keyword(
            title,
            "pandora",
        ):

            return False


        ring_keywords = [
            "anello",
            "ring",
        ]

        if not contains_any(
            title,
            ring_keywords,
        ):

            return False


        jewelry_exclusions = [
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
            jewelry_exclusions,
        ):

            return False


        return True


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
        # PREZZO
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
        # FILTRO PREZZO DELLO STORICO
        #
        # NON è il limite dell'alert.
        #
        # Esempio:
        #
        # €25  -> salvato
        # €60  -> salvato
        # €150 -> salvato
        # €250 -> salvato
        #
        # Solo oltre €300 viene escluso.
        # ====================================================

        if (
            price < HISTORY_MIN_PRICE
            or price > HISTORY_MAX_PRICE
        ):

            skipped_price += 1
            continue


        # ====================================================
        # FILTRO CATEGORIA
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
        # UNA RILEVAZIONE AL GIORNO
        # ====================================================

        existing = None

        for observation in item["prices"]:

            if (
                isinstance(
                    observation,
                    dict,
                )
                and observation.get(
                    "date"
                ) == today
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
            "version": 5,
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
            "version": 5,
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
        f"Storico: "
        f"{HISTORY_MIN_PRICE:.2f}-"
        f"{HISTORY_MAX_PRICE:.0f} €"
    )

    print(
        f"Alert/acquisto: max "
        f"{MAX_CURRENT_PRICE:.0f} €"
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
