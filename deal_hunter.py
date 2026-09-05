import os
import json
import statistics
import requests
from datetime import datetime


HISTORY_FILE = "price_history.json"

MAX_CURRENT_PRICE = 30.0
MIN_HISTORY_POINTS = 3
DEAL_ALERT_THRESHOLD = 65


def normalize_text(text):
    return " ".join(str(text or "").lower().split())


def contains_any(text, words):
    text = normalize_text(text)
    return any(word in text for word in words)


def is_relevant_product(item):
    title = normalize_text(item.get("title", ""))
    category = normalize_text(item.get("category", ""))
    query = normalize_text(item.get("query", ""))

    text = f"{title} {category} {query}"

    excluded = [
        "scarpe", "scarpa", "shoes", "shoe", "sneaker",
        "stivali", "boots", "sandali",
        "calze", "calzini", "socks",
        "intimo", "underwear", "boxer", "slip",
        "reggiseno", "bra",
        "profumo", "parfum", "deodorante",
        "shampoo", "crema", "make up",
        "zaino", "backpack",
        "portafoglio", "wallet",
        "cintura", "belt",
        "cover", "custodia", "case"
    ]

    if contains_any(text, excluded):
        return False

    # NIKE
    if "nike" in text:
        if "t shirt" in query or "t-shirt" in query or "tshirt" in query:
            return "nike" in title and contains_any(
                title,
                ["t shirt", "t-shirt", "tshirt", "maglietta", "tee"]
            )

        if "felpa" in query:
            return "nike" in title and contains_any(
                title,
                ["felpa", "hoodie", "sweatshirt", "sweater", "pullover"]
            )

        return "nike" in title

    # ADIDAS
    if "adidas" in text:
        if "t shirt" in query or "t-shirt" in query or "tshirt" in query:
            return "adidas" in title and contains_any(
                title,
                ["t shirt", "t-shirt", "tshirt", "maglietta", "tee"]
            )

        if "felpa" in query:
            return "adidas" in title and contains_any(
                title,
                ["felpa", "hoodie", "sweatshirt", "sweater", "pullover"]
            )

        return "adidas" in title

    # CALVIN KLEIN
    if "calvin klein" in text:
        if "t shirt" in query or "t-shirt" in query or "tshirt" in query:
            return "calvin klein" in title and contains_any(
                title,
                ["t shirt", "t-shirt", "tshirt", "maglietta", "tee"]
            )

        return "calvin klein" in title

    # TOMMY HILFIGER
    if "tommy hilfiger" in text:
        if "t shirt" in query or "t-shirt" in query or "tshirt" in query:
            return "tommy hilfiger" in title and contains_any(
                title,
                ["t shirt", "t-shirt", "tshirt", "maglietta", "tee"]
            )

        return "tommy hilfiger" in title

    # THE NORTH FACE
    if "the north face" in text or "north face" in text:
        if "pile" in query:
            return contains_any(
                title,
                ["the north face", "north face"]
            ) and contains_any(title, ["pile", "fleece"])

        if "giacca" in query:
            return contains_any(
                title,
                ["the north face", "north face"]
            ) and contains_any(
                title,
                [
                    "giacca", "jacket", "parka",
                    "softshell", "hardshell",
                    "impermeabile", "waterproof",
                    "antipioggia", "windbreaker",
                    "piumino", "down jacket"
                ]
            )

        return contains_any(title, ["the north face", "north face"])

    # COLUMBIA
    if "columbia" in text:
        if "pile" in query:
            return "columbia" in title and contains_any(
                title,
                ["pile", "fleece"]
            )

        if "giacca" in query:
            return "columbia" in title and contains_any(
                title,
                [
                    "giacca", "jacket", "parka",
                    "softshell", "hardshell",
                    "impermeabile", "waterproof",
                    "antipioggia", "windbreaker",
                    "piumino", "down jacket"
                ]
            )

        return "columbia" in title

    # GUESS
    if "guess" in text:
        if "borsa" in query:
            return "guess" in title and contains_any(
                title,
                [
                    "borsa", "bag", "handbag",
                    "shoulder bag", "crossbody",
                    "tracolla", "pochette",
                    "clutch", "tote",
                    "shopper", "borsetta"
                ]
            )

        return "guess" in title

    # PANDORA
    if "pandora" in text:
        if "anello" in query:
            return "pandora" in title and contains_any(
                title,
                ["anello", "ring"]
            )

        return "pandora" in title

    return False


def get_valid_prices(item):
    prices = item.get("prices", [])

    if not isinstance(prices, list):
        return []

    valid = []

    for value in prices:
        try:
            price = float(value)
            if price > 0:
                valid.append(price)
        except (TypeError, ValueError):
            pass

    return valid


def calculate_deal_score(prices):
    current_price = prices[-1]
    normal_price = statistics.median(prices)
    historical_low = min(prices)

    if normal_price <= 0 or current_price <= 0:
        return 0, normal_price, historical_low, 0, 0

    discount = max(
        0,
        (normal_price - current_price) / normal_price
    )

    ratio = normal_price / current_price

    ratio_score = min(
        40,
        max(0, (ratio - 1) * 25)
    )

    discount_score = min(
        30,
        max(0, discount * 40)
    )

    if current_price <= historical_low * 1.10:
        low_score = 20
    elif current_price <= historical_low * 1.25:
        low_score = 10
    else:
        low_score = 0

    history_score = min(
        10,
        len(prices) * 2
    )

    score = round(
        ratio_score +
        discount_score +
        low_score +
        history_score
    )

    return (
        min(100, score),
        normal_price,
        historical_low,
        discount,
        ratio
    )


def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token:
        print("ERRORE: TELEGRAM_BOT_TOKEN mancante.")
        return False

    if not chat_id:
        print("ERRORE: TELEGRAM_CHAT_ID mancante.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": False
            },
            timeout=30
        )

        print(f"Telegram HTTP: {response.status_code}")

        if response.ok:
            print("Messaggio Telegram inviato correttamente.")
            return True

        print(f"Errore Telegram: {response.text}")
        return False

    except Exception as e:
        print(f"Errore connessione Telegram: {e}")
        return False


def load_history():
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Il tracker salva lo storico come dizionario:
    # { "ASIN": { ...dati prodotto... } }
    if isinstance(data, dict):
        # Supporto anche nel caso esista una chiave "products"
        if isinstance(data.get("products"), list):
            return data["products"]

        products = []

        for value in data.values():
            if isinstance(value, dict):
                products.append(value)

        return products

    # Supporto anche per un eventuale storico già in formato lista
    if isinstance(data, list):
        return data

    raise ValueError(
        "Formato di price_history.json non riconosciuto."
    )


def main():
    print("==========================================")
    print("DEAL HUNTER")
    print("==========================================")

    if not os.path.exists(HISTORY_FILE):
        print(f"ERRORE: {HISTORY_FILE} non trovato.")
        return

    try:
        history = load_history()
    except Exception as e:
        print(f"ERRORE lettura storico: {e}")
        return

    print(f"Prodotti nello storico: {len(history)}")
    print(f"Fascia acquisto: 0-{MAX_CURRENT_PRICE:.0f} €")
    print(f"Storico minimo richiesto: {MIN_HISTORY_POINTS} prezzi")
    print("")

    analysed = 0
    skipped_price = 0
    skipped_history = 0
    skipped_relevance = 0
    deals = []

    for item in history:
        if not isinstance(item, dict):
            continue

        prices = get_valid_prices(item)

        if not prices:
            continue

        current_price = prices[-1]

        if current_price > MAX_CURRENT_PRICE:
            skipped_price += 1
            continue

        if len(prices) < MIN_HISTORY_POINTS:
            skipped_history += 1
            continue

        analysed += 1

        if not is_relevant_product(item):
            skipped_relevance += 1
            continue

        (
            score,
            normal_price,
            historical_low,
            discount,
            ratio
        ) = calculate_deal_score(prices)

        title = item.get("title", "Prodotto senza titolo")

        print(
            f"Analizzato: {title[:80]} | "
            f"Attuale: €{current_price:.2f} | "
            f"Normale: €{normal_price:.2f} | "
            f"Score: {score}"
        )

        if score >= DEAL_ALERT_THRESHOLD:
            deals.append({
                "item": item,
                "current": current_price,
                "normal": normal_price,
                "low": historical_low,
                "discount": discount,
                "ratio": ratio,
                "score": score
            })

    deals.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    print("")
    print("==========================================")
    print("RISULTATO")
    print("==========================================")
    print(f"Prodotti analizzati: {analysed}")
    print(f"Scartati per prezzo > 30 €: {skipped_price}")
    print(f"Scartati per storico insufficiente: {skipped_history}")
    print(f"Scartati per rilevanza: {skipped_relevance}")
    print(f"Deal trovati: {len(deals)}")
    print("")

    if deals:
        for deal in deals:
            item = deal["item"]

            title = item.get("title", "Prodotto")
            asin = item.get("asin", "")

            product_url = item.get("product_url", "")

            if not product_url and asin:
                product_url = f"https://www.amazon.it/dp/{asin}"

            score = deal["score"]

            if score >= 90:
                level = "🚨 ECCEZIONALE"
            elif score >= 80:
                level = "🔥 SUPER DEAL"
            else:
                level = "🟢 AFFARE"

            message = (
                f"{level}\n\n"
                f"📦 {title}\n\n"
                f"💰 Prezzo attuale: €{deal['current']:.2f}\n"
                f"📊 Prezzo normale storico: €{deal['normal']:.2f}\n"
                f"📉 Minimo storico: €{deal['low']:.2f}\n"
                f"💥 Sconto reale: {deal['discount'] * 100:.0f}%\n"
                f"📈 Rapporto normale/prezzo: {deal['ratio']:.2f}x\n"
                f"🎯 Deal Score: {score}/100\n\n"
                f"🛒 {product_url}"
            )

            print("Invio deal Telegram...")
            send_telegram(message)

    else:
        today = datetime.now().strftime("%d/%m/%Y")

        heartbeat = (
            "🤖 Deal Hunter — Controllo completato\n\n"
            f"📅 {today}\n"
            f"📦 Prodotti analizzati: {analysed}\n"
            "💰 Fascia acquisto: 0–30 €\n"
            "🔥 Deal trovati: 0\n\n"
            "Nessun affare abbastanza interessante oggi."
        )

        print("Nessun deal trovato.")
        print("Invio messaggio Telegram di controllo...")

        send_telegram(heartbeat)

    print("")
    print("==========================================")
    print("DEAL HUNTER TERMINATO")
    print("==========================================")


if __name__ == "__main__":
    main()
