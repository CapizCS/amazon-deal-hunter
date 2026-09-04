import os
import json
from datetime import date
from statistics import median
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

# 2 query Parse per ogni esecuzione
QUERIES_PER_RUN = 2

# Limite normale: 180 query/mese
STANDARD_MONTHLY_QUERY_LIMIT = 180

# Settembre 2026: lasciamo un margine di sicurezza
CURRENT_MONTH_QUERY_LIMIT = 140

# Minimo storico necessario per considerare un prodotto
MIN_HISTORY_POINTS = 3


# ============================================================
# ROTAZIONE CATEGORIE
# ============================================================
#
# 20 query complessive:
#
# Tecnologia       5/20 = 25%
# Gaming           4/20 = 20%
# Donna sera       4/20 = 20%
# Outdoor          3/20 = 15%
# T-shirt uomo     3/20 = 15%
# Sportivo         1/20 =  5%
#
# Il ciclo viene ripetuto automaticamente.
# 9 cicli = 180 query esatte.
# ============================================================

SEARCH_CYCLE = [
    {
        "category": "technology",
        "query": "tecnologia elettronica",
    },
    {
        "category": "gaming",
        "query": "gaming",
    },
    {
        "category": "women_evening",
        "query": "vestito da sera donna",
    },
    {
        "category": "outdoor_clothing",
        "query": "abbigliamento outdoor",
    },
    {
        "category": "men_tshirts",
        "query": "t-shirt uomo",
    },
    {
        "category": "technology",
        "query": "smartwatch cuffie auricolari",
    },
    {
        "category": "gaming",
        "query": "accessori gaming",
    },
    {
        "category": "women_evening",
        "query": "abito elegante donna",
    },
    {
        "category": "outdoor_clothing",
        "query": "giacca outdoor uomo donna",
    },
    {
        "category": "men_tshirts",
        "query": "magliette uomo",
    },
    {
        "category": "technology",
        "query": "computer accessori elettronica",
    },
    {
        "category": "gaming",
        "query": "mouse tastiera gaming",
    },
    {
        "category": "women_evening",
        "query": "vestito elegante donna",
    },
    {
        "category": "outdoor_clothing",
        "query": "pile giacca trekking",
    },
    {
        "category": "men_tshirts",
        "query": "t shirt uomo cotone",
    },
    {
        "category": "technology",
        "query": "tablet elettronica",
    },
    {
        "category": "gaming",
        "query": "controller gaming cuffie gaming",
    },
    {
        "category": "women_evening",
        "query": "abito cerimonia donna",
    },
    {
        "category": "outdoor_clothing",
        "query": "abbigliamento trekking",
    },
    {
        "category": "technology",
        "query": "monitor elettronica",
    },
]


# ============================================================
# FUNZIONI GENERALI
# ============================================================

def load_json(filename, default):
    """Carica un JSON. Se non esiste o è corrotto, restituisce default."""
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    """Salva un JSON in modo leggibile."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_price(value):
    """Converte vari formati di prezzo in float."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    # Rimuove simboli comuni
    text = (
        text.replace("€", "")
        .replace("EUR", "")
        .replace("\u00a0", " ")
        .strip()
    )

    # Gestione formato italiano: 1.234,56
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        # Gestione eventuali prezzi con testo extra
        text = text.replace(",", "")

    # Tenta conversione diretta
    try:
        return float(text)
    except ValueError:
        pass

    # Estrae il primo numero trovato
    import re

    match = re.search(r"\d+(?:\.\d+)?", text)

    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None

    return None


# ============================================================
# NORMALIZZAZIONE RISPOSTA PARSE
# ============================================================

def find_products(obj):
    """
    Cerca ricorsivamente liste/dizionari contenenti prodotti con ASIN.
    Gestisce anche JSON annidato dentro stringhe.
    """

    products = []

    if isinstance(obj, dict):

        # Caso: dizionario che è direttamente un prodotto
        if obj.get("asin"):
            products.append(obj)

        # Cerca ricorsivamente nei valori
        for value in obj.values():
            products.extend(find_products(value))

    elif isinstance(obj, list):

        for item in obj:
            products.extend(find_products(item))

    elif isinstance(obj, str):

        text = obj.strip()

        # Prova a interpretare stringhe JSON
        if text.startswith("{") or text.startswith("["):
            try:
                parsed = json.loads(text)
                products.extend(find_products(parsed))
            except Exception:
                pass

    return products


# ============================================================
# QUERY PARSE
# ============================================================

def search_parse(query):
    """Esegue una singola query Parse."""

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

    # Elimina duplicati per ASIN
    unique = {}

    for product in products:
        asin = product.get("asin")

        if asin:
            unique[str(asin)] = product

    return list(unique.values())


# ============================================================
# FILTRI CATEGORIE
# ============================================================

def category_matches(product, category):
    """
    Filtro aggiuntivo per evitare che i risultati delle query
    finiscano troppo facilmente in categorie sbagliate.
    """

    title = str(product.get("title", "")).lower()

    if not title:
        return False

    if category == "technology":
        keywords = [
            "smartphone",
            "tablet",
            "monitor",
            "computer",
            "pc",
            "laptop",
            "notebook",
            "smartwatch",
            "cuffie",
            "auricolari",
            "mouse",
            "tastiera",
            "webcam",
            "router",
            "ssd",
            "hard disk",
            "elettronica",
        ]
        return any(k in title for k in keywords)

    if category == "gaming":
        keywords = [
            "gaming",
            "videogioco",
            "controller",
            "console",
            "playstation",
            "xbox",
            "nintendo",
            "steam deck",
            "mouse gaming",
            "tastiera gaming",
            "cuffie gaming",
        ]
        return any(k in title for k in keywords)

    if category == "women_evening":
        keywords = [
            "vestito donna",
            "abito donna",
            "vestito elegante",
            "abito elegante",
            "abito cerimonia",
            "vestito cerimonia",
            "dress donna",
            "evening dress",
        ]
        return any(k in title for k in keywords)

    if category == "outdoor_clothing":
        keywords = [
            "outdoor",
            "trekking",
            "escursionismo",
            "hiking",
            "montagna",
            "softshell",
            "hardshell",
            "giacca impermeabile",
            "giacca trekking",
            "pile",
            "fleece",
        ]
        return any(k in title for k in keywords)

    if category == "men_tshirts":
        generic_keywords = [
            "t-shirt",
            "t shirt",
            "maglietta",
            "maglietta",
        ]

        men_keywords = [
            "uomo",
            "men",
            "mens",
            "male",
            "maschile",
        ]

        has_product_type = any(k in title for k in generic_keywords)
        has_men_marker = any(k in title for k in men_keywords)

        return has_product_type and has_men_marker

    if category == "sports_clothing":
        keywords = [
            "abbigliamento sportivo",
            "tuta sportiva",
            "pantaloni sportivi",
            "giacca sportiva",
            "running",
            "fitness",
            "training",
            "sport",
        ]
        return any(k in title for k in keywords)

    return True


# ============================================================
# STORICO
# ============================================================

def update_history(products, category):
    """
    Aggiorna lo storico.

    Se lo stesso ASIN viene rilevato più volte nello stesso giorno,
    aggiorna il prezzo della giornata invece di creare duplicati.
    """

    history = load_json(HISTORY_FILE, {})

    today = date.today().isoformat()

    saved = 0
    skipped = 0

    for product in products:

        asin = str(product.get("asin", "")).strip()

        if not asin:
            skipped += 1
            continue

        price = parse_price(
            product.get("price")
            or product.get("current_price")
            or product.get("buybox_price")
        )

        if price is None:
            skipped += 1
            continue

        # Fascia di prezzo richiesta
        if price < MIN_PRICE or price > MAX_PRICE:
            skipped += 1
            continue

        # Filtro categoria
        if not category_matches(product, category):
            skipped += 1
            continue

        title = str(product.get("title", "")).strip()

        if not title:
            skipped += 1
            continue

        # Struttura iniziale prodotto
        if asin not in history:
            history[asin] = {
                "title": title,
                "category": category,
                "prices": [],
            }

        item = history[asin]

        # Aggiorna informazioni che possono cambiare
        item["title"] = title
        item["category"] = category

        # Compatibilità con eventuali vecchi dati
        if "prices" not in item or not isinstance(item["prices"], list):
            item["prices"] = []

        # Cerca se esiste già una rilevazione oggi
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

    return saved, skipped, history


# ============================================================
# ROTAZIONE
# ============================================================

def get_monthly_limit(today):
    """
    Settembre 2026: 140 query.
    Dal mese successivo: 180 query.
    """

    if today.year == 2026 and today.month == 9:
        return CURRENT_MONTH_QUERY_LIMIT

    return STANDARD_MONTHLY_QUERY_LIMIT


def load_rotation(today):
    """
    Carica lo stato della rotazione.

    Se cambia mese:
    - azzera le query utilizzate
    - riparte dalla posizione successiva coerente
      con il ciclo.
    """

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

    saved_month = rotation.get("month")

    if saved_month != current_month:
        rotation = {
            "version": 1,
            "month": current_month,
            "queries_used": 0,
            "index": 0,
        }

    # Protezione da dati corrotti
    try:
        rotation["queries_used"] = int(rotation.get("queries_used", 0))
    except Exception:
        rotation["queries_used"] = 0

    try:
        rotation["index"] = int(rotation.get("index", 0))
    except Exception:
        rotation["index"] = 0

    rotation["index"] %= len(SEARCH_CYCLE)

    return rotation


def get_next_searches(rotation, monthly_limit):
    """
    Determina le prossime query senza modificare ancora lo stato.

    Questo è importante:
    se Parse fallisce, la query NON viene considerata consumata.
    """

    remaining = monthly_limit - rotation["queries_used"]

    if remaining <= 0:
        return []

    count = min(QUERIES_PER_RUN, remaining)

    searches = []

    index = rotation["index"]

    for offset in range(count):
        position = (index + offset) % len(SEARCH_CYCLE)
        searches.append(SEARCH_CYCLE[position])

    return searches


def register_successful_query(rotation):
    """Avanza la rotazione dopo una query Parse riuscita."""

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
    print(f"Query utilizzate: {rotation['queries_used']}/{monthly_limit}")
    print(f"Posizione rotazione: {rotation['index']}")
    print(f"Query per esecuzione: {QUERIES_PER_RUN}")

    # Controllo budget
    searches = get_next_searches(
        rotation,
        monthly_limit,
    )

    if not searches:
        print()
        print("LIMITE MENSILE RAGGIUNTO.")
        print("Nessuna query Parse verrà eseguita.")
        print("=" * 60)

        save_json(ROTATION_FILE, rotation)

        return

    all_products = []

    successful_queries = 0

    # ========================================================
    # ESECUZIONE QUERY
    # ========================================================

    for search in searches:

        category = search["category"]
        query = search["query"]

        print()
        print(f"Query {successful_queries + 1}/{len(searches)}")
        print(f"Categoria: {category}")
        print(f"Ricerca: {query}")

        try:

            products = search_parse(query)

            print(f"Risultati ricevuti: {len(products)}")

            all_products.extend(
                [
                    (product, category)
                    for product in products
                ]
            )

            # SOLO QUI consumiamo una posizione della rotazione
            register_successful_query(rotation)

            successful_queries += 1

        except Exception as e:

            print(f"ERRORE Parse: {e}")
            print("Query non conteggiata nella rotazione.")

    # ========================================================
    # DEDUPLICAZIONE
    # ========================================================

    unique_products = {}

    for product, category in all_products:

        asin = str(product.get("asin", "")).strip()

        if not asin:
            continue

        # Manteniamo la prima categoria associata
        if asin not in unique_products:
            unique_products[asin] = (
                product,
                category,
            )

    products_to_save = [
        item
        for item in unique_products.values()
    ]

    print()
    print(f"Prodotti unici ricevuti: {len(products_to_save)}")

    # ========================================================
    # SALVATAGGIO STORICO
    # ========================================================

    total_saved = 0
    total_skipped = 0

    # Aggiorniamo per categoria così conserviamo
    # la categoria della query che ha trovato il prodotto.
    grouped = {}

    for product, category in products_to_save:
        grouped.setdefault(category, []).append(product)

    for category, products in grouped.items():

        saved, skipped, _ = update_history(
            products,
            category,
        )

        total_saved += saved
        total_skipped += skipped

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

    print(f"Query riuscite: {successful_queries}")
    print(
        f"Query mensili utilizzate: "
        f"{rotation['queries_used']}/{monthly_limit}"
    )

    print(f"Prodotti validi salvati/aggiornati: {total_saved}")
    print(f"Prodotti scartati: {total_skipped}")

    print()
    print("Prossima posizione rotazione:", rotation["index"])

    if rotation["queries_used"] >= monthly_limit:
        print()
        print("⚠️ LIMITE MENSILE RAGGIUNTO.")
        print("Il tracker resterà fermo fino al prossimo mese.")

    print("=" * 60)


if __name__ == "__main__":
    main()
