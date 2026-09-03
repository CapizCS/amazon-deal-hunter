import os
import json
import urllib.parse
import urllib.request


MIN_PRICE = 10
MAX_PRICE = 50
HISTORY_FILE = "price_history.json"


def load_price_history():
    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_historical_low(history_data, product_id):
    product = history_data.get(product_id)

    if not product:
        return None

    prices = [
        item["price"]
        for item in product.get("prices", [])
        if item.get("price", 0) > 0
    ]

    if not prices:
        return None

    return min(prices)


def calculate_deal_score(current_price, normal_price, historical_low=None):

    # Prezzo di acquisto consentito
    if current_price < MIN_PRICE or current_price > MAX_PRICE:
        return 0

    if normal_price <= 0:
        return 0

    ratio = normal_price / current_price
    discount = 1 - (current_price / normal_price)

    score = 0

    # 1. Rapporto tra valore normale e prezzo attuale
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

    # 2. Sconto reale
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

    # 3. Quanto siamo vicini al minimo storico
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

    elif score >= 80:
        return "🔥 SUPER DEAL"

    elif score >= 65:
        return "🟢 AFFARE"

    else:
        return "⚪ IGNORA"


def send_telegram(message):

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message
    }).encode()

    request = urllib.request.Request(url, data=data)

    with urllib.request.urlopen(request) as response:

        if response.status == 200:
            print("Telegram: notifica inviata")

        else:
            print(f"Telegram: errore HTTP {response.status}")


def analyze_product(
    product_id,
    name,
    current_price,
    normal_price,
    history_data
):

    historical_low = get_historical_low(
        history_data,
        product_id
    )

    score = calculate_deal_score(
        current_price,
        normal_price,
        historical_low
    )

    # Fuori dal range
    if score == 0:

        print()
        print(f"IGNORATO: {name}")
        print(f"Prezzo: {current_price:.2f} €")

        return

    ratio = normal_price / current_price
    discount = (1 - current_price / normal_price) * 100
    saving = normal_price - current_price

    level = get_deal_level(score)

    print()
    print("=" * 60)
    print(name)
    print(f"Prezzo attuale: {current_price:.2f} €")
    print(f"Prezzo normale: {normal_price:.2f} €")
    print(f"Risparmio: {saving:.2f} €")
    print(f"Sconto reale: {discount:.1f}%")
    print(f"Valore/prezzo: {ratio:.1f}x")

    if historical_low is not None:
        print(f"Minimo storico: {historical_low:.2f} €")

    print(f"DEAL SCORE: {score}/100")
    print(f"VALUTAZIONE: {level}")

    if score >= 65:

        message = (
            f"{level}\n\n"
            f"🛍 {name}\n"
            f"💰 Ora: {current_price:.2f} €\n"
            f"📊 Prezzo normale: {normal_price:.2f} €\n"
            f"💶 Risparmio: {saving:.2f} €\n"
            f"📉 Sconto reale: {discount:.1f}%\n"
            f"💎 Valore/prezzo: {ratio:.1f}x\n"
        )

        if historical_low is not None:
            message += (
                f"📈 Minimo storico: "
                f"{historical_low:.2f} €\n"
            )

        message += f"⭐ Deal Score: {score}/100"

        send_telegram(message)


if __name__ == "__main__":

    history_data = load_price_history()

    products = [

        {
            "id": "smartwatch",
            "name": "Smartwatch",
            "current_price": 39,
            "normal_price": 179
        },

        {
            "id": "ssd",
            "name": "SSD",
            "current_price": 29,
            "normal_price": 119
        },

        {
            "id": "monitor-gaming",
            "name": "Monitor gaming",
            "current_price": 49,
            "normal_price": 199
        },

        {
            "id": "fake-deal",
            "name": "Falso affare",
            "current_price": 39,
            "normal_price": 45
        }
    ]

    for product in products:

        analyze_product(
            product["id"],
            product["name"],
            product["current_price"],
            product["normal_price"],
            history_data
        )
