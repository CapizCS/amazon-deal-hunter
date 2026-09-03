import os
import json
import statistics
import urllib.parse
import urllib.request


MIN_PRICE = 10
MAX_PRICE = 50
MIN_HISTORY_POINTS = 3
HISTORY_FILE = "price_history.json"


def load_price_history():
    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_real_products(history_data):
    products = []

    for asin, product in history_data.items():

        # I prodotti reali raccolti da Parse hanno un titolo.
        # I vecchi prodotti di test non lo hanno.
        if not product.get("title"):
            continue

        prices = [
            item["price"]
            for item in product.get("prices", [])
            if item.get("price", 0) > 0
        ]

        if not prices:
            continue

        products.append({
            "asin": asin,
            "title": product.get("title", ""),
            "url": product.get("url", ""),
            "category": product.get("category", "unknown"),
            "prices": prices
        })

    return products


def calculate_normal_price(prices):
    """
    Usa la mediana dello storico come stima
    del prezzo normale.
    """

    return statistics.median(prices)


def calculate_deal_score(
    current_price,
    normal_price,
    historical_low=None,
    history_points=0
):

    if current_price < MIN_PRICE or current_price > MAX_PRICE:
        return 0

    if normal_price <= 0:
        return 0

    if history_points < MIN_HISTORY_POINTS:
        return 0

    ratio = normal_price / current_price
    discount = 1 - (current_price / normal_price)

    score = 0

    # 1. Rapporto valore/prezzo
    if ratio >= 5:
        score += 45
    elif ratio >= 4:
        score += 40
    elif ratio >= 3:
        score += 35
    elif ratio >= 2.5:
        score += 28
    elif ratio >= 2:
        score += 20
    elif ratio >= 1.5:
        score += 10

    # 2. Sconto rispetto al prezzo normale
    if discount >= 0.80:
        score += 25
    elif discount >= 0.70:
        score += 22
    elif discount >= 0.60:
        score += 18
    elif discount >= 0.50:
        score += 14
    elif discount >= 0.40:
        score += 8

    # 3. Vicinanza al minimo storico
    if historical_low is not None and historical_low > 0:

        distance = current_price / historical_low

        if distance <= 1.02:
            score += 30
        elif distance <= 1.05:
            score += 25
        elif distance <= 1.10:
            score += 18
        elif distance <= 1.20:
            score += 10

    return min(score, 100)


def get_deal_level(score):

    if score >= 90:
        return "🚨 ECCEZIONALE"

    if score >= 80:
        return "🔥 SUPER DEAL"

    if score >= 65:
        return "🟢 AFFARE"

    return "⚪ IGNORA"


def send_telegram(message):

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message
    }).encode()

    request = urllib.request.Request(
        url,
        data=data
    )

    with urllib.request.urlopen(request, timeout=20) as response:

        if response.status == 200:
            print("Telegram: notifica inviata")


def analyze_product(product):

    prices = product["prices"]

    # Servono almeno 3 rilevazioni
    if len(prices) < MIN_HISTORY_POINTS:

        print()
        print(f"IN ATTESA STORICO: {product['title']}")
        print(f"Rilevazioni: {len(prices)}/{MIN_HISTORY_POINTS}")

        return

    current_price = prices[-1]

    # Prezzo normale = mediana dello storico
    normal_price = calculate_normal_price(prices)

    historical_low = min(prices)

    score = calculate_deal_score(
        current_price,
        normal_price,
        historical_low,
        len(prices)
    )

    print()
    print("=" * 70)
    print(product["title"])
    print(f"ASIN: {product['asin']}")
    print(f"Categoria: {product['category']}")
    print(f"Prezzo attuale: {current_price:.2f} €")
    print(f"Prezzo normale stimato: {normal_price:.2f} €")
    print(f"Minimo storico: {historical_low:.2f} €")
    print(f"Rilevazioni: {len(prices)}")

    if normal_price > 0:

        discount = (
            1 - current_price / normal_price
        ) * 100

        ratio = normal_price / current_price

        print(f"Sconto rispetto allo storico: {discount:.1f}%")
        print(f"Valore/prezzo: {ratio:.1f}x")

    print(f"DEAL SCORE: {score}/100")
    print(f"VALUTAZIONE: {get_deal_level(score)}")

    if score >= 65:

        message = (
            f"{get_deal_level(score)}\n\n"
            f"🛍 {product['title']}\n"
            f"💰 Ora: {current_price:.2f} €\n"
            f"📊 Prezzo normale stimato: {normal_price:.2f} €\n"
            f"📉 Sconto storico: {discount:.1f}%\n"
            f"💎 Valore/prezzo: {ratio:.1f}x\n"
            f"📈 Minimo storico: {historical_low:.2f} €\n"
            f"⭐ Deal Score: {score}/100\n\n"
            f"🔗 https://www.amazon.it/dp/{product['asin']}"
        )

        send_telegram(message)


def main():

    history_data = load_price_history()

    products = get_real_products(history_data)

    print()
    print("=" * 70)
    print("AMAZON DEAL HUNTER")
    print(f"Prodotti reali nello storico: {len(products)}")
    print("=" * 70)

    for product in products:

        analyze_product(product)


if __name__ == "__main__":
    main()
