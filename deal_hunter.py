def calculate_deal_score(current_price, normal_price):
    """
    Calcola un punteggio preliminare da 0 a 100.
    Più il prezzo attuale è basso rispetto al prezzo normale,
    maggiore è il punteggio.
    """

    if current_price <= 0 or normal_price <= 0:
        return 0

    ratio = normal_price / current_price
    discount = 1 - (current_price / normal_price)

    score = 0

    # Rapporto prezzo normale / prezzo attuale
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

    # Bonus se il prezzo è nel nostro range ideale
    if 10 <= current_price <= 50:
        score += 15

    return min(score, 100)


if __name__ == "__main__":
    examples = [
        ("Prodotto A", 39, 45),
        ("Prodotto B", 39, 179),
        ("Prodotto C", 25, 120),
        ("Prodotto D", 49, 199),
    ]

    for name, current, normal in examples:
        score = calculate_deal_score(current, normal)

        print(
            f"{name}: "
            f"{current:.2f}€ -> "
            f"normale {normal:.2f}€ | "
            f"Deal Score: {score}/100"
        )
