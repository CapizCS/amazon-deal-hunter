import os
import json
import statistics
from datetime import date
import requests


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

# ============================================================
# PREZZO MASSIMO PER L'ALERT
# ============================================================

MAX_CURRENT_PRICE = 30.0

# Minimo storico necessario
MIN_HISTORY_POINTS = 3


# ============================================================
# SOGLIE DEAL SCORE
# ============================================================

EXCEPTIONAL_SCORE = 90
SUPER_DEAL_SCORE = 80
DEAL_SCORE = 65


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

        return None


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN:
        print(
            "TELEGRAM_BOT_TOKEN non configurato."
        )
        return False

    if not TELEGRAM_CHAT_ID:
        print(
            "TELEGRAM_CHAT_ID non configurato."
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

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        return True

    except Exception as e:

        print(
            f"Errore Telegram: {e}"
        )

        return False


# ============================================================
# SCORE
# ============================================================

def calculate_score(
    current_price,
    historical_prices,
):

    if not historical_prices:
        return 0

    normal_price = statistics.median(
        historical_prices
    )

    historical_low = min(
        historical_prices
    )

    if current_price <= 0:
        return 0

    # ========================================================
    # RAPPORTO VALORE / PREZZO
    # ========================================================

    ratio = (
        normal_price
        / current_price
    )

    # ========================================================
    # SCONTO REALE
    # ========================================================

    discount = (
        1
        - (
            current_price
            / normal_price
        )
    )

    # ========================================================
    # DISTANZA DAL MINIMO STORICO
    # ========================================================

    if normal_price > historical_low:

        distance_from_low = (
            current_price
            - historical_low
        ) / (
            normal_price
            - historical_low
        )

    else:

        distance_from_low = 0.0

    distance_from_low = max(
        0.0,
        min(
            1.0,
            distance_from_low,
        ),
    )

    # ========================================================
    # SCORE RAPPORTO
    # ========================================================

    if ratio >= 6:
        ratio_score = 100

    elif ratio >= 5:
        ratio_score = 95

    elif ratio >= 4:
        ratio_score = 90

    elif ratio >= 3:
        ratio_score = 80

    elif ratio >= 2.5:
        ratio_score = 70

    elif ratio >= 2:
        ratio_score = 55

    elif ratio >= 1.5:
        ratio_score = 35

    else:
        ratio_score = 10


    # ========================================================
    # SCORE SCONTO
    # ========================================================

    if discount >= 0.80:
        discount_score = 100

    elif discount >= 0.70:
        discount_score = 90

    elif discount >= 0.60:
        discount_score = 80

    elif discount >= 0.50:
        discount_score = 65

    elif discount >= 0.40:
        discount_score = 50

    elif discount >= 0.30:
        discount_score = 35

    else:
        discount_score = 10


    # ========================================================
    # SCORE VICINANZA AL MINIMO
    # ========================================================

    low_score = (
        100
        * (
            1
            - distance_from_low
        )
    )

    # ========================================================
    # SCORE FINALE
    # ========================================================
    #
    # Il rapporto valore/prezzo pesa di più.
    # Questo evita di segnalare semplicemente
    # qualsiasi prodotto con una grossa percentuale
    # di sconto.
    # ========================================================

    score = (
        ratio_score * 0.50
        + discount_score * 0.30
        + low_score * 0.20
    )

    return round(
        max(
            0,
            min(
                100,
                score,
            ),
        )
    )


# ============================================================
# LIVELLO DEAL
# ============================================================

def get_deal_level(score):

    if score >= EXCEPTIONAL_SCORE:

        return "🚨 ECCEZIONALE"

    if score >= SUPER_DEAL_SCORE:

        return "🔥 SUPER DEAL"

    if score >= DEAL_SCORE:

        return "🟢 AFFARE"

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    today = date.today()

    history = load_json(
        HISTORY_FILE,
        {},
    )

    print("=" * 60)
    print(
        "DEAL HUNTER"
    )
    print("=" * 60)

    print(
        f"Data: {today}"
    )

    print(
        f"Prezzo massimo alert: "
        f"{MAX_CURRENT_PRICE:.0f} €"
    )

    print(
        f"Minimo storico richiesto: "
        f"{MIN_HISTORY_POINTS}"
    )

    print()

    deals = []

    analyzed = 0

    insufficient_history = 0

    over_budget = 0

    invalid_products = 0


    # ========================================================
    # ANALISI PRODOTTI
    # ========================================================

    for asin, item in history.items():

        if not isinstance(
            item,
            dict,
        ):

            invalid_products += 1
            continue

        prices = item.get(
            "prices",
            [],
        )

        if not isinstance(
            prices,
            list,
        ):

            invalid_products += 1
            continue


        # ====================================================
        # ESTRAI PREZZI STORICI
        # ====================================================

        historical_prices = []

        for observation in prices:

            if not isinstance(
                observation,
                dict,
            ):

                continue

            price = parse_price(
                observation.get(
                    "price"
                )
            )

            if (
                price is not None
                and price > 0
            ):

                historical_prices.append(
                    price
                )


        if len(
            historical_prices
        ) < MIN_HISTORY_POINTS:

            insufficient_history += 1
            continue


        # ====================================================
        # PREZZO ATTUALE
        # ====================================================

        latest_observations = []

        for observation in prices:

            if not isinstance(
                observation,
                dict,
            ):

                continue

            observation_price = parse_price(
                observation.get(
                    "price"
                )
            )

            observation_date = observation.get(
                "date",
                "",
            )

            if (
                observation_price is not None
                and observation_date
            ):

                latest_observations.append(
                    (
                        observation_date,
                        observation_price,
                    )
                )


        if not latest_observations:

            invalid_products += 1
            continue


        latest_observations.sort(
            key=lambda x: x[0]
        )

        current_price = (
            latest_observations[-1][1]
        )


        # ====================================================
        # NUMERO PRODOTTI ANALIZZATI
        # ====================================================

        analyzed += 1


        # ====================================================
        # LIMITE DI ACQUISTO
        # ====================================================
        #
        # QUESTO È IL SOLO PUNTO IN CUI
        # applichiamo il limite dei 30 €.
        #
        # Un prodotto da 60 € rimane nello storico.
        # Un prodotto da 60 € semplicemente non genera alert.
        # ====================================================

        if current_price > MAX_CURRENT_PRICE:

            over_budget += 1
            continue


        # ====================================================
        # SCORE
        # ====================================================

        score = calculate_score(
            current_price,
            historical_prices,
        )

        level = get_deal_level(
            score
        )

        if not level:
            continue


        # ====================================================
        # DATI STORICI
        # ====================================================

        normal_price = statistics.median(
            historical_prices
        )

        historical_low = min(
            historical_prices
        )

        discount = (
            1
            - (
                current_price
                / normal_price
            )
        )

        ratio = (
            normal_price
            / current_price
        )


        # ====================================================
        # PRODOTTO
        # ====================================================

        title = item.get(
            "title",
            "Prodotto Amazon",
        )

        category = item.get(
            "category",
            "",
        )

        query = item.get(
            "query",
            "",
        )


        # ====================================================
        # LINK AMAZON
        # ====================================================

        product_url = (
            "https://www.amazon.it/dp/"
            f"{asin}"
        )


        # ====================================================
        # DEAL
        # ====================================================

        deals.append(
            {
                "asin": asin,
                "title": title,
                "category": category,
                "query": query,
                "current_price": current_price,
                "normal_price": normal_price,
                "historical_low": historical_low,
                "discount": discount,
                "ratio": ratio,
                "score": score,
                "level": level,
                "url": product_url,
                "history_points": len(
                    historical_prices
                ),
            }
        )


    # ========================================================
    # ORDINA PER SCORE
    # ========================================================

    deals.sort(
        key=lambda deal: (
            deal["score"],
            deal["ratio"],
        ),
        reverse=True,
    )


    # ========================================================
    # TELEGRAM
    # ========================================================

    if deals:

        print(
            f"Deal trovati: "
            f"{len(deals)}"
        )

        print()

        for deal in deals:

            discount_percent = round(
                deal["discount"] * 100
            )

            message = (
                f"{deal['level']}\n\n"
                f"🛍️ {deal['title']}\n\n"
                f"💰 Prezzo attuale: "
                f"€{deal['current_price']:.2f}\n"
                f"📊 Prezzo normale: "
                f"€{deal['normal_price']:.2f}\n"
                f"📉 Minimo storico: "
                f"€{deal['historical_low']:.2f}\n"
                f"🔥 Sconto reale: "
                f"{discount_percent}%\n"
                f"💎 Rapporto valore/prezzo: "
                f"{deal['ratio']:.2f}x\n"
                f"🎯 Deal Score: "
                f"{deal['score']}/100\n"
                f"📚 Rilevazioni: "
                f"{deal['history_points']}\n\n"
                f"🏷️ Categoria: "
                f"{deal['category']}\n"
                f"🔎 Query: "
                f"{deal['query']}\n\n"
                f"🔗 {deal['url']}"
            )

            print(
                message
            )

            print()

            send_telegram(
                message
            )


    else:

        print(
            "Deal trovati: 0"
        )

        message = (
            "🤖 Deal Hunter — "
            "Controllo completato\n\n"
            f"📅 {today.strftime('%d/%m/%Y')}\n"
            f"📦 Prodotti analizzati: "
            f"{analyzed}\n"
            f"💰 Fascia acquisto: "
            f"0–{MAX_CURRENT_PRICE:.0f} €\n"
            f"🔥 Deal trovati: 0\n\n"
            "Nessun affare abbastanza "
            "interessante oggi."
        )

        send_telegram(
            message
        )


    # ========================================================
    # RIEPILOGO
    # ========================================================

    print()

    print("=" * 60)
    print("RIEPILOGO")
    print("=" * 60)

    print(
        f"Prodotti analizzati: "
        f"{analyzed}"
    )

    print(
        f"Storico insufficiente: "
        f"{insufficient_history}"
    )

    print(
        f"Oltre €{MAX_CURRENT_PRICE:.0f}: "
        f"{over_budget}"
    )

    print(
        f"Prodotti non validi: "
        f"{invalid_products}"
    )

    print(
        f"Deal trovati: "
        f"{len(deals)}"
    )

    print("=" * 60)


# ============================================================
# AVVIO
# ============================================================

if __name__ == "__main__":

    main()
