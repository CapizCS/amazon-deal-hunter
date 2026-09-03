import json
from datetime import date


HISTORY_FILE = "price_history.json"


def load_history():
    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=2, ensure_ascii=False)


def update_price(history, product_id, price):
    today = str(date.today())

    if product_id not in history:
        history[product_id] = {
            "category": "unknown",
            "prices": []
        }

    prices = history[product_id]["prices"]

    # Se abbiamo già registrato il prodotto oggi,
    # aggiorniamo il prezzo invece di creare un duplicato.
    for item in prices:
        if item["date"] == today:
            item["price"] = price
            return

    prices.append({
        "date": today,
        "price": price
    })


def main():

    history = load_history()

    # Prezzi di test attuali.
    # In seguito questi valori arriveranno dalla fonte dati reale.
    products = {
        "smartwatch": 39.00,
        "ssd": 29.00,
        "monitor-gaming": 49.00
    }

    for product_id, price in products.items():
        update_price(history, product_id, price)

    save_history(history)

    print("Storico prezzi aggiornato correttamente.")

    for product_id, price in products.items():
        print(f"{product_id}: {price:.2f} €")


if __name__ == "__main__":
    main()
