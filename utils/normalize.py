from rapidfuzz import process

CANONICAL_ITEMS = {
    "milk": "milk_1l",
    "milk 1l": "milk_1l",
    "1l milk": "milk_1l",
    "bread": "bread",
    "brot": "bread",
    "eggs": "eggs_10",
    "egg": "eggs_10",
    "10 eggs": "eggs_10",
    "chocolate": "chocolate_bar",
    "choclet": "chocolate_bar",
    "schokolade": "chocolate_bar",
    "tomato": "tomato_1kg",
    "tomato 1kg": "tomato_1kg",
    "tomaten": "tomato_1kg"
}

def normalize_item(raw: str):
    low = raw.lower().strip()
    if low in CANONICAL_ITEMS:
        return CANONICAL_ITEMS[low]
    best_match, score, _ = process.extractOne(low, CANONICAL_ITEMS.keys())
    if score > 70:
        return CANONICAL_ITEMS[best_match]
    return None
