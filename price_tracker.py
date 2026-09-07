import os
import json
import re
import requests
from datetime import datetime


# ============================================================
# CONFIGURAZIONE
# ============================================================

PARSE_URL = (
    "https://api.parse.bot/scraper/"
    "18564612-8aa3-47b4-a88b-4bc5ba70f945/"
    "get_search_results_csv"
)

HISTORY_FILE = "price_history.json"
ROTATION_FILE = "search_rotation.json"

# Storico: salviamo tutti i prezzi da 0,01 a 300 €
HISTORY_MIN_PRICE = 0.01
HISTORY_MAX_PRICE = 300.0

# Prezzo massimo considerato dal Deal Hunter
ALERT_MAX_PRICE = 30.0

# 2 query per ogni esecuzione
QUERIES_PER_RUN = 2

# Limite prudenziale mensile
MONTHLY_QUERY_LIMIT = 140


# ============================================================
# ROTAZIONE DELLE RICERCHE
# ============================================================

ROTATION = [
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
    {
        "category": "fashion_men",
        "query": "The North Face pile uomo",
    },
    {
        "category": "fashion_women",
        "query": "The North Face pile donna",
    },
    {
        "category": "fashion_men",
        "query": "The North Face giacca uomo",
    },
    {
        "category": "fashion_women",
        "query": "The North Face giacca donna",
    },
    {
        "category": "fashion_men",
        "query": "Columbia pile uomo",
    },
    {
        "category": "fashion_women",
        "query": "Columbia pile donna",
    },
    {
        "category": "fashion_unisex",
        "query": "Columbia giacca uomo donna",
    },
    {
        "category": "fashion_men",
        "query": "Calvin Klein t shirt uomo",
    },
    {
        "category": "fashion_women",
        "query": "Calvin Klein t shirt donna",
    },
    {
        "category": "fashion_men",
        "query": "Tommy Hilfiger t shirt uomo",
    },
    {
        "category": "fashion_women",
        "query": "Guess borsa donna",
    },
    {
        "category": "jewelry",
        "query": "Pandora anello",
    },
]


# ============================================================
# PREZZI
# ============================================================

def parse_price(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        price = float(value)

        if price > 0:
            return price

        return None

    text = str(value).strip()

    if not text:
        return None

    text = text.replace("€", "")
    text = text.replace("EUR", "")
    text = text.replace("eur", "")
    text = text.strip()

    # Formato italiano:
    # 1.299,99 -> 1299.99
    # 29,99 -> 29.99
    if "," in text and "." in text:

        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "")
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

    elif "," in text:
        text = text.replace(",", ".")

    text = re.sub(
        r"[^0-9.\-]",
        "",
        text
    )

    try:
        price = float(text)

        if price > 0:
            return price

    except (TypeError, ValueError):
        pass

    return None


# ============================================================
# PARSE
# ============================================================

def find_products(value):

    found = []

    if isinstance(value, list):

        for item in value:
            found.extend(
                find_products(item)
            )

        return found

    if isinstance(value, dict):

        if "asin" in value:
            found.append(value)

        for child in value.values():
            found.extend(
                find_products(child)
            )

        return found

    if isinstance(value, str):

        text = value.strip()

        if not text:
            return found

        try:

            parsed = json.loads(text)

            if parsed != value:
                found.extend(
                    find_products(parsed)
                )

        except Exception:
            pass

    return found


def search_parse(query):

    api_key = os.environ.get(
        "PARSE_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "PARSE_API_KEY non configurata."
        )

    response = requests.get(
        PARSE_URL,
        params={
            "query": query
        },
        headers={
            "X-API-Key": api_key
        },
        timeout=90
    )

    response.raise_for_status()

    try:
        data = response.json()

    except Exception:
        data = response.text

    products = find_products(data)

    # Elimina duplicati usando ASIN
    unique = {}

    for product in products:

        asin = str(
            product.get(
                "asin",
                ""
            )
        ).strip()

        if asin:
            unique[asin] = product

    return list(
        unique.values()
    )


# ============================================================
# STORICO
# ============================================================

def load_history():

    if not os.path.exists(
        HISTORY_FILE
    ):
        return {}

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

    except Exception:

        return {}

    if isinstance(data, dict):
        return data

    if isinstance(data, list):

        converted = {}

        for item in data:

            if not isinstance(
                item,
                dict
            ):
                continue

            asin = str(
                item.get(
                    "asin",
                    ""
                )
            ).strip()

            if asin:
                converted[asin] = item

        return converted

    return {}


def save_history(history):

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2
        )


def update_history(
    products,
    category,
    query
):

    history = load_history()

    saved = 0
    updated = 0
    skipped_price = 0
    skipped_other = 0

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    for product in products:

        asin = str(
            product.get(
                "asin",
                ""
            )
        ).strip()

        if not asin:

            skipped_other += 1
            continue

        # ----------------------------------------------------
        # PREZZO
        # ----------------------------------------------------

        price = None

        for key in [
            "price",
            "current_price",
            "buybox_price",
            "buy_box_price"
        ]:

            if key in product:

                price = parse_price(
                    product.get(key)
                )

                if price is not None:
                    break

        if price is None:

            skipped_other += 1
            continue

        # ----------------------------------------------------
        # FASCIA STORICO
        # ----------------------------------------------------

        if (
            price < HISTORY_MIN_PRICE
            or price > HISTORY_MAX_PRICE
        ):

            skipped_price += 1
            continue

        title = str(
            product.get(
                "title",
                "Prodotto senza titolo"
            )
        ).strip()

        product_url = str(
            product.get(
                "product_url",
                ""
            )
        ).strip()

        # ----------------------------------------------------
        # NUOVO PRODOTTO
        # ----------------------------------------------------

        if asin not in history:

            history[asin] = {
                "asin": asin,
                "title": title,
                "product_url": product_url,
                "category": category,
                "query": query,
                "prices": [
                    price
                ],
                "price_dates": [
                    today
                ]
            }

            saved += 1
            continue

        # ----------------------------------------------------
        # PRODOTTO ESISTENTE
        # ----------------------------------------------------

        item = history[asin]

        if not isinstance(
            item,
            dict
        ):
            item = {}

        item["asin"] = asin

        if title:
            item["title"] = title

        if product_url:
            item["product_url"] = (
                product_url
            )

        item["category"] = category
        item["query"] = query

        prices = item.get(
            "prices",
            []
        )

        dates = item.get(
            "price_dates",
            []
        )

        if not isinstance(
            prices,
            list
        ):
            prices = []

        if not isinstance(
            dates,
            list
        ):
            dates = []

        # ----------------------------------------------------
        # STESSO GIORNO:
        # aggiorniamo invece di aggiungere
        # ----------------------------------------------------

        if (
            dates
            and dates[-1] == today
        ):

            if prices:
                prices[-1] = price
            else:
                prices.append(price)

        else:

            prices.append(price)
            dates.append(today)

        item["prices"] = prices
        item["price_dates"] = dates

        history[asin] = item

        updated += 1

    save_history(history)

    return (
        saved,
        updated,
        skipped_price,
        skipped_other
    )


# ============================================================
# ROTAZIONE
# ============================================================

def load_rotation():

    if not os.path.exists(
        ROTATION_FILE
    ):

        return {
            "month": datetime.now().strftime(
                "%Y-%m"
            ),
            "queries_used": 0,
            "index": 0
        }

    try:

        with open(
            ROTATION_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

    except Exception:

        return {
            "month": datetime.now().strftime(
                "%Y-%m"
            ),
            "queries_used": 0,
            "index": 0
        }

    if not isinstance(
        data,
        dict
    ):

        return {
            "month": datetime.now().strftime(
                "%Y-%m"
            ),
            "queries_used": 0,
            "index": 0
        }

    return data


def save_rotation(rotation):

    with open(
        ROTATION_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            rotation,
            f,
            ensure_ascii=False,
            indent=2
        )


def prepare_rotation():

    rotation = load_rotation()

    current_month = datetime.now().strftime(
        "%Y-%m"
    )

    # Nuovo mese
    if rotation.get(
        "month"
    ) != current_month:

        rotation = {
            "month": current_month,
            "queries_used": 0,
            "index": 0
        }

    return rotation


def advance_rotation(
    rotation
):

    current_index = int(
        rotation.get(
            "index",
            0
        )
    )

    rotation["index"] = (
        current_index
        + QUERIES_PER_RUN
    ) % len(ROTATION)

    return rotation


# ============================================================
# MAIN
# ============================================================

def main():

    print("")
    print("==========================================")
    print("DEAL HUNTER - AGGIORNAMENTO STORICO")
    print("==========================================")

    rotation = prepare_rotation()

    queries_used = int(
        rotation.get(
            "queries_used",
            0
        )
    )

    index = int(
        rotation.get(
            "index",
            0
        )
    )

    print(
        f"Storico: "
        f"{HISTORY_MIN_PRICE:.2f}-"
        f"{HISTORY_MAX_PRICE:.0f} €"
    )

    print(
        f"Alert/acquisto: "
        f"max {ALERT_MAX_PRICE:.0f} €"
    )

    print(
        f"Query per esecuzione: "
        f"{QUERIES_PER_RUN}"
    )

    print(
        f"Query mensili utilizzate: "
        f"{queries_used}/"
        f"{MONTHLY_QUERY_LIMIT}"
    )

    # --------------------------------------------------------
    # CONTROLLO LIMITE
    # --------------------------------------------------------

    if (
        queries_used
        + QUERIES_PER_RUN
        > MONTHLY_QUERY_LIMIT
    ):

        print("")
        print(
            "LIMITE MENSILE RAGGIUNTO."
        )

        print(
            "Nessuna query eseguita."
        )

        save_rotation(
            rotation
        )

        return

    # --------------------------------------------------------
    # SELEZIONE DELLE 2 QUERY
    # --------------------------------------------------------

    selected = []

    for offset in range(
        QUERIES_PER_RUN
    ):

        position = (
            index
            + offset
        ) % len(ROTATION)

        selected.append(
            ROTATION[position]
        )

    total_saved = 0
    total_updated = 0
    total_price_skipped = 0
    total_other_skipped = 0
    successful_queries = 0

    # --------------------------------------------------------
    # ESECUZIONE
    # --------------------------------------------------------

    for number, slot in enumerate(
        selected,
        start=1
    ):

        category = slot[
            "category"
        ]

        query = slot[
            "query"
        ]

        print("")
        print(
            f"Query "
            f"{number}/"
            f"{QUERIES_PER_RUN}"
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

            successful_queries += 1

            (
                saved,
                updated,
                price_skipped,
                other_skipped
            ) = update_history(
                products,
                category,
                query
            )

            total_saved += saved
            total_updated += updated

            total_price_skipped += (
                price_skipped
            )

            total_other_skipped += (
                other_skipped
            )

        except Exception as e:

            print("")
            print(
                f"ERRORE query "
                f"'{query}':"
            )

            print(
                str(e)
            )

    # --------------------------------------------------------
    # AGGIORNA ROTAZIONE
    # --------------------------------------------------------

    rotation["queries_used"] = (
        queries_used
        + successful_queries
    )

    rotation = advance_rotation(
        rotation
    )

    save_rotation(
        rotation
    )

    # --------------------------------------------------------
    # RISULTATO
    # --------------------------------------------------------

    print("")
    print("==========================================")
    print("COMPLETATO")
    print("==========================================")

    print(
        f"Query riuscite: "
        f"{successful_queries}"
    )

    print(
        f"Query mensili utilizzate: "
        f"{rotation['queries_used']}/"
        f"{MONTHLY_QUERY_LIMIT}"
    )

    print(
        f"Prodotti nuovi salvati: "
        f"{total_saved}"
    )

    print(
        f"Prodotti aggiornati: "
        f"{total_updated}"
    )

    print(
        f"Scartati per prezzo: "
        f"{total_price_skipped}"
    )

    print(
        f"Scartati per altri motivi: "
        f"{total_other_skipped}"
    )

    print(
        f"Prossima posizione rotazione: "
        f"{rotation['index']}"
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":
    main()
