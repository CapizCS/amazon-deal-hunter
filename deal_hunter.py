def calculate_deal_score(current_price, normal_price):
    if current_price <= 0 or normal_price <= 0:
        return 0

    ratio = normal_price / current_price
    discount = 1 - (current_price / normal_price)

    score = 0

    # Rapporto tra prezzo normale e prezzo attuale
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

    # Sconto reale
    if discount >= 0.80:
        score += 35
    elif discount >= 0.70:
        score += 30
    elif discount >= 0.60:
        score += 25
    elif discount >= 0.50:
        score += 18
    elif discount >= 0.40:
        score += 10

    # Prezzo nel nostro range
    if 10 <= current_price <= 50:
        score += 15

    return min(score, 100)


def analyze_product(name, current_price, normal_price):
    score = calculate_deal_score(current_price, normal_price)

    ratio = normal_price / current_price
    discount = (1 - current_price / normal_price) * 100

    print()
    print("=" * 50)
    print(name)
    print(f"Prezzo attuale: {current_price:.2f} €")
    print(f"Prezzo normale: {normal_price:.2f} €")
    print(f"Valore/prezzo:  {ratio:.1f}x")
    print(f"Sconto reale:   {discount:.1f}%")
    print(f"DEAL SCORE:     {score}/100")

    if score >= 80:
        print("🔥 SUPER DEAL")
    elif score >= 65:
        print("🟢 AFFARE")
    else:
        print("⚪ IGNORA")


if __name__ == "__main__":

    products = [
        ("Cuffie economiche", 39, 45),
        ("Smartwatch", 39, 179),
        ("SSD", 29, 119),
        ("Monitor gaming", 49, 199),
        ("Prodotto troppo economico", 5, 100),
        ("Prodotto troppo costoso", 89, 300),
    ]

    for product in products:
        analyze_product(*product)
