import os
import json
import statistics
import requests
from datetime import date


# ============================================================
# CONFIGURAZIONE
# ============================================================

HISTORY_FILE = "price_history.json"

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)

MAX_CURRENT_PRICE = 30.0

MIN_HISTORY_POINTS = 3

DEAL_ALERT_THRESHOLD = 65


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
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return default


# ============================================================
# TESTO
# ============================================================

def normalize_text(text):

    text = str(text or "").lower()

    replacements = {
        "-": " ",
        "_": " ",
        "/": " ",
        "\\": " ",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return " ".join(
        text.split()
    )


def contains_any(
    text,
    keywords
):

    text = normalize_text(
        text
    )

    return any(
        keyword in text
        for keyword in keywords
    )


# ============================================================
# RILEVANZA PRODOTTO
# ============================================================

def is_relevant_product(item):

    title = normalize_text(
        item.get("title", "")
    )

    category = normalize_text(
        item.get("category", "")
    )

    query = normalize_text(
        item.get("query", "")
    )


    if not title:

        return False


    # ========================================================
    # ESCLUSIONI GENERALI
    # ========================================================

    exclusions = [
        "scarpe",
        "scarpa",
        "shoes",
        "shoe",
        "sneaker",
        "stivali",
        "boots",
        "sandali",

        "calze",
        "calzini",
        "socks",
        "sock",

        "intimo",
        "underwear",
        "boxer",
        "slip",
        "reggiseno",
        "bra",

        "profumo",
        "parfum",
        "deodorante",

        "shampoo",
        "crema",
        "make up",

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


    if contains_any(
        title,
        exclusions
    ):

        return False


    # ========================================================
    # NIKE
    # ========================================================

    if "nike" in query:

        if "nike" not in title:

            return False


        if "t shirt" in query:

            return contains_any(
                title,
                [
                    "t shirt",
                    "t-shirt",
                    "tshirt",
                    "maglietta",
                    "tee",
                ]
            )


        if "felpa" in query:

            return contains_any(
                title,
                [
                    "felpa",
                    "hoodie",
                    "sweatshirt",
                    "sweater",
                    "pullover",
                ]
            )


    # ========================================================
    # ADIDAS
    # ========================================================

    if "adidas" in query:

        if "adidas" not in title:

            return False


        if "t shirt" in query:

            return contains_any(
                title,
                [
                    "t shirt",
                    "t-shirt",
                    "tshirt",
                    "maglietta",
                    "tee",
                ]
            )


        if "felpa" in query:

            return contains_any(
                title,
                [
                    "felpa",
                    "hoodie",
                    "sweatshirt",
                    "sweater",
                    "pullover",
                ]
            )


    # ========================================================
    # CALVIN KLEIN
    # ========================================================

    if "calvin klein" in query:

        if "calvin klein" not in title:

            return False


        if "t shirt" in query:

            return contains_any(
                title,
                [
                    "t shirt",
                    "t-shirt",
                    "tshirt",
                    "maglietta",
                    "tee",
                ]
            )


    # ========================================================
    # TOMMY HILFIGER
    # ========================================================

    if "tommy hilfiger" in query:

        if "tommy hilfiger" not in title:

            return False


        if "t shirt" in query:

            return contains_any(
                title,
                [
                    "t shirt",
                    "t-shirt",
                    "tshirt",
                    "maglietta",
                    "tee",
                ]
            )


    # ========================================================
    # THE NORTH FACE
    # ========================================================

    if "the north face" in query:

        if (
            "north face" not in title
            and "the north face" not in title
        ):

            return False


        if "pile" in query:

            return contains_any(
                title,
                [
                    "pile",
                    "fleece",
                ]
            )


        if "giacca" in query:

            return contains_any(
                title,
                [
                    "giacca",
                    "jacket",
                    "parka",
                    "softshell",
                    "hardshell",
                    "impermeabile",
                    "waterproof",
                    "antipioggia",
                    "windbreaker",
                    "piumino",
                    "down jacket",
                ]
            )


    # ========================================================
    # COLUMBIA
    # ========================================================

    if "columbia" in query:

        if "columbia" not in title:

            return False


        if "pile" in query:

            return contains_any(
                title,
                [
                    "pile",
                    "fleece",
                ]
            )


        if "giacca" in query:

            return contains_any(
                title,
                [
                    "giacca",
                    "jacket",
                    "parka",
                    "softshell",
                    "impermeabile",
                    "waterproof",
                    "antipioggia",
                    "windbreaker",
                    "piumino",
                ]
            )


    # ========================================================
    # GUESS
    # ========================================================

    if "guess" in query:

        if "guess" not in title:

            return False


        if "borsa" in query:

            return contains_any(
                title,
                [
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
            )


    # ========================================================
    # PANDORA
    # ========================================================

    if "pandora" in query:

        if "pandora" not in title:

            return False


        if "anello" in query:

            return contains_any(
                title,
                [
                    "anello",
                    "ring",
                ]
            )


    # ========================================================
    # COMPATIBILITÀ CON VECCHIO STORICO
    # ========================================================

    if not query:

        if category == "fashion_men":

            return contains_any(
                title,
                [
                    "t shirt",
                    "t-shirt",
                    "tshirt",
                    "maglietta",
                    "felpa",
                    "hoodie",
                ]
            )


        if category == "fashion_women":

            return contains_any(
                title,
                [
                    "t shirt",
                    "t-shirt",
                    "tshirt",
                    "maglietta",
                    "felpa",
                    "hoodie",
                    "vestito",
                    "abito",
                ]
            )


        if category == "outdoor_clothing":

            return contains_any(
                title,
                [
                    "pile",
                    "fleece",
                    "giacca",
                    "jacket",
                    "parka",
                    "softshell",
                    "impermeabile",
                ]
            )


        if category == "fashion_accessories":

            return (
                "guess" in title
                and contains_any(
                    title,
                    [
                        "borsa",
                        "bag",
                        "tracolla",
                        "crossbody",
                    ]
                )
            )


        if category == "jewelry":

            return (
                "pandora" in title
                and contains_any(
                    title,
                    [
                        "anello",
                        "ring",
                    ]
                )
            )


    return True


# ============================================================
# PREZZI STORICI
# ============================================================

def get_valid_prices(item):

    prices = []

    for observation in item.get(
        "prices",
        []
    ):

        if not isinstance(
            observation,
            dict
        ):

            continue

        value = observation.get(
            "price"
        )

        try:

            value = float(value)

        except (
            TypeError,
            ValueError
        ):

            continue

        if value > 0:

            prices.append(value)


    return prices


# ============================================================
# DEAL SCORE
# ============================================================

def calculate_deal_score(
    current_price,
    prices
):

    if not prices:

        return 0


    normal_price = statistics.median(
        prices
    )

    historical_low = min(
        prices
    )


    if current_price <= 0:

        return 0


    # ========================================================
    # RAPPORTO PREZZO NORMALE / PREZZO ATTUALE
    # ========================================================

    ratio = (
        normal_price
        / current_price
    )

    ratio_score = min(
        40,
        max(
            0,
            (ratio - 1) * 25
        )
    )


    # ========================================================
    # SCONTO REALE
    # ========================================================

    discount = (
        (
            normal_price
            - current_price
        )
        / normal_price
    ) * 100


    discount_score = min(
        30,
        max(
            0,
            discount * 0.40
        )
    )


    # ========================================================
    # VICINANZA AL MINIMO STORICO
    # ========================================================

    if current_price <= (
        historical_low * 1.10
    ):

        low_score = 20

    elif current_price <= (
        historical_low * 1.25
    ):

        low_score = 10

    else:

        low_score = 0


    # ========================================================
    # AFFIDABILITÀ STORICO
    # ========================================================

    history_score = min(
        10,
        len(prices) * 2
    )


    score = (
        ratio_score
        + discount_score
        + low_score
        + history_score
    )


    return round(
        min(
            100,
            score
        )
    )


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN:

        print(
            "TELEGRAM_BOT_TOKEN "
            "non configurato."
        )

        return False


    if not TELEGRAM_CHAT_ID:

        print(
            "TELEGRAM_CHAT_ID "
            "non configurato."
        )

        return False


    url = (
        "https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}"
        "/sendMessage"
    )


    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }


    response = requests.post(
        url,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    today = date.today()

    history = load_json(
        HISTORY_FILE,
        {}
    )


    deals = []

    analysed = 0

    ignored_price = 0

    ignored_history = 0

    ignored_relevance = 0


    # ========================================================
    # ANALISI
    # ========================================================

    for asin, item in history.items():

        prices = get_valid_prices(
            item
        )


        if not prices:

            continue


        analysed += 1


        # ----------------------------------------------------
        # PREZZO ATTUALE
        # ----------------------------------------------------

        current_price = prices[-1]


        # ----------------------------------------------------
        # LIMITE ACQUISTO / ALERT
        # ----------------------------------------------------

        if current_price > MAX_CURRENT_PRICE:

            ignored_price += 1

            continue


        # ----------------------------------------------------
        # STORICO MINIMO
        # ----------------------------------------------------

        if len(prices) < MIN_HISTORY_POINTS:

            ignored_history += 1

            continue


        # ----------------------------------------------------
        # RILEVANZA
        # ----------------------------------------------------

        if not is_relevant_product(
            item
        ):

            ignored_relevance += 1

            continue


        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        score = calculate_deal_score(
            current_price,
            prices
        )


        if score < DEAL_ALERT_THRESHOLD:

            continue


        normal_price = statistics.median(
            prices
        )

        historical_low = min(
            prices
        )


        discount = (
            (
                normal_price
                - current_price
            )
            / normal_price
        ) * 100


        ratio = (
            normal_price
            / current_price
        )


        if score >= 90:

            level = "🚨 ECCEZIONALE"

        elif score >= 80:

            level = "🔥 SUPER DEAL"

        else:

            level = "🟢 AFFARE"


        deals.append(
            {
                "asin": asin,
                "title": item.get(
                    "title",
                    "Prodotto"
                ),
                "current_price": current_price,
                "normal_price": normal_price,
                "historical_low": historical_low,
                "discount": discount,
                "ratio": ratio,
                "score": score,
                "level": level,
            }
        )


    # ========================================================
    # ORDINA PER SCORE
