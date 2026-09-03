import os
import urllib.parse
import urllib.request


MIN_PRICE = 10
MAX_PRICE = 50


def calculate_deal_score(current_price, normal_price, historical_low=None):
    # Filtro obbligatorio: compriamo solo tra 10 € e 50 €
    if current_price < MIN_PRICE or current_price > MAX_PRICE:
        return 0

    if normal_price <= 0:
        return 0

    ratio = normal_price / current_price
    discount = 1 - (current_price / normal_price)

    score = 0

    # Quanto valore riceviamo per ogni euro speso
    if ratio >= 5:
        score += 50
    elif ratio >= 4:
        score += 45
    elif ratio >= 3:
        score += 38
    elif ratio >= 2.5:
        score += 30
    elif ratio >= 2:
        score += 20
    elif ratio >= 1.5:
        score += 10

    # Sconto rispetto al prezzo normale
    if discount >= 0.80:
        score += 30
    elif discount >= 0.70:
        score += 25
    elif discount >= 0.60:
        score += 20
    elif discount >= 0.50:
        score += 15
    elif discount >= 0.40:
        score += 8

    # Bonus se il prezzo attuale è vicino al minimo storico
    if historical_low is not None and historical_low > 0:
        distance_from_low = current_price / historical_low

        if distance_from_low <= 1.05:
            score += 20
        elif distance_from_low <= 1.10:
            score += 15
        elif distance_from_low <= 1.20:
            score += 8

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
    name,
    current_price,
    normal_price,
    historical_low=None
):
    score = calculate_deal_score(
        current_price,
        normal_price,
        historical_low
    )

    # Fuori dal nostro range: ignoriamo completamente
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
    print(f"Prezzo attuale:   {current_price:.2f} €")
    print(f"Prezzo normale:    {normal_price:.2f} €")
    print(f"Risparmio:         {saving:.2f} €")
    print(f"Sconto reale:      {discount:.1f}%")
    print(f"Valore/prezzo:     {ratio:.1f}x")

    if historical_low:
        print(f"Minimo storico:    {historical_low:.2f} €")

    print(f"DEAL SCORE:        {score}/100")
    print(f"VALUTAZIONE:       {level}")

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

        if historical_low:
            message += f"📈 Minimo storico: {historical_low:.2f} €\n"

        message += f"⭐ Deal Score: {score}/100"

        send_telegram(message)


if __name__ == "__main__":

    products = [
        # nome, prezzo attuale, prezzo normale, minimo storico

        ("Smartwatch", 39, 179, 35),

        ("SSD", 29, 119, 27),

        ("Monitor gaming", 49, 199, 45),

        # Questo NON deve generare una notifica
        ("Prodotto troppo economico", 5, 100, 4),

        # Questo NON deve generare una notifica
        ("Prodotto troppo costoso", 89, 300, 80),

        # Questo serve a testare un falso affare
        ("Falso affare", 39, 45, 38),
    ]

    for product in products:
        analyze_product(*product)
