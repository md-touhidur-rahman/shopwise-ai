import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import difflib
import streamlit as st


# =========================================================
# CONFIG
# =========================================================

DATA_PATH = Path("data/common_products.json")  # adjust if needed

st.set_page_config(
    page_title="Grocery Price Comparator",
    layout="centered",
)


# =========================================================
# TEXTS (EN + DE)
# =========================================================

TEXT = {
    "title": "Grocery Price Comparison (Lebensmittel-Preisvergleich)",
    "subtitle": (
        "Type grocery item to compare price before you going to buy it.\n"
        "Geben Sie den gewünschten Lebensmittelartikel ein, um den Preis vor dem Kauf zu vergleichen."
    ),
    "input_label": (
        "Your items (comma or line separated)\n"
        "Ihre Artikel (durch Komma oder Zeilenumbruch getrennt)"
    ),
    "placeholder": "e.g. milk, bread, bananas, toilet paper / z.B. Milch, Brot, Bananen, Toilettenpapier",
    "results_header": "Comparison Result (Vergleichsergebnis)",
    "not_found_header": "Not found (Nicht gefunden)",
    "per_store_header": "Prices per store (Preise je Markt)",
    "no_items": "Enter at least one item. / Bitte mindestens einen Artikel eingeben.",
    "file_missing": (
        "Product data file not found. Please make sure `data/common_products.json` exists.\n"
        "Produktdatei nicht gefunden. Bitte stellen Sie sicher, dass `data/common_products.json` existiert."
    ),
}


# =========================================================
# DATA LOADING
# =========================================================

@st.cache_data(show_spinner=False)
def load_products(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # normalize names for faster lookups
    for item in data:
        item["__names_for_match"] = [
            item.get("canonical_name", ""),
            item.get("english_name", ""),
        ]
    return data


PRODUCTS = load_products(DATA_PATH)


# =========================================================
# MATCHING
# =========================================================

def normalize_text(s: str) -> str:
    s = s.lower().strip()
    # replace german umlauts for more robust english typing
    replacements = {
        "ä": "a",
        "ö": "o",
        "ü": "u",
        "ß": "ss"
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s


def split_user_input(text: str) -> List[str]:
    """
    Split on commas, semicolons, newlines.
    Also handle users writing everything in one line.
    """
    if not text:
        return []
    parts = re.split(r"[,;\n]+", text)
    # filter empties
    parts = [p.strip() for p in parts if p.strip()]
    return parts


def find_best_match(user_term: str, products: List[Dict[str, Any]], threshold: float = 0.55) -> Tuple[Dict[str, Any], float]:
    """
    Use difflib to find a decent match among canonical_name and english_name.
    Returns (product, score) or (None, 0.0) if no good match.
    """
    user_norm = normalize_text(user_term)
    best_score = 0.0
    best_product = None

    for p in products:
        for name in p["__names_for_match"]:
            candidate = normalize_text(name)
            score = difflib.SequenceMatcher(None, user_norm, candidate).ratio()
            if score > best_score:
                best_score = score
                best_product = p

    if best_score >= threshold:
        return best_product, best_score
    return None, 0.0


# =========================================================
# PRICE AGGREGATION
# =========================================================

def aggregate_by_store(matched_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Return structure:
    {
      "kaufland": {"total": x, "items": {name: price}},
      "lidl": {...},
      "aldi": {...}
    }
    """
    stores = ["kaufland", "lidl", "aldi"]
    result = {s: {"total": 0.0, "items": {}} for s in stores}

    for entry in matched_items:
        product = entry["product"]
        user_term = entry["user_term"]
        prices = product.get("prices", {})
        for store in stores:
            price = float(prices.get(store, 0.0))
            result[store]["total"] += price
            # show product name, not user term, but we can keep user term for context
            result[store]["items"][user_term] = price

    return result


# =========================================================
# UI
# =========================================================

st.title(TEXT["title"])
st.write(TEXT["subtitle"])

if not PRODUCTS:
    st.error(TEXT["file_missing"])
else:
    user_input = st.text_area(
        TEXT["input_label"],
        height=120,
        placeholder=TEXT["placeholder"]
    )

    if st.button("Compare / Vergleichen", type="primary"):
        items = split_user_input(user_input)
        if not items:
            st.warning(TEXT["no_items"])
        else:
            matched = []
            not_found = []

            for term in items:
                product, score = find_best_match(term, PRODUCTS)
                if product is None:
                    not_found.append(term)
                else:
                    matched.append({
                        "user_term": term,
                        "product": product,
                        "score": score
                    })

            st.subheader(TEXT["results_header"])

            if matched:
                # show a simple table of what we matched to what
                st.write("Matched items (Zuordnungen):")
                match_rows = []
                for m in matched:
                    p = m["product"]
                    match_rows.append({
                        "You typed / Eingegeben": m["user_term"],
                        "Matched product / Zugeordnet": p.get("canonical_name") or p.get("english_name"),
                        "Unit / Einheit": p.get("unit", ""),
                        "Category / Kategorie": p.get("category", ""),
                    })
                st.dataframe(match_rows, hide_index=True, use_container_width=True)

                # aggregate prices
                store_data = aggregate_by_store(matched)

                st.subheader(TEXT["per_store_header"])

                # make a nice, professional table
                price_table = []
                for store, data in store_data.items():
                    price_table.append({
                        "Store / Markt": store.capitalize(),
                        "Total (€)": round(data["total"], 2),
                        "Items counted / Artikel gezählt": len(data["items"]),
                    })
                st.dataframe(price_table, hide_index=True, use_container_width=True)

                with st.expander("Details per store (Details je Markt)"):
                    for store, data in store_data.items():
                        st.markdown(f"**{store.capitalize()}**")
                        detail_rows = []
                        for user_term, price in data["items"].items():
                            detail_rows.append({
                                "Item entered / Eingegeben": user_term,
                                "Price (€) / Preis (€)": price
                            })
                        st.dataframe(detail_rows, hide_index=True, use_container_width=True)

            else:
                st.info("No items could be matched. / Es konnten keine Artikel zugeordnet werden.")

            if not_found:
                st.subheader(TEXT["not_found_header"])
                st.write(
                    "These items could not be matched to our list. "
                    "Try spelling them differently or use German names.\n"
                    "Diese Artikel konnten nicht zugeordnet werden. "
                    "Bitte andere Schreibweise oder deutsche Bezeichnung versuchen."
                )
                st.write(", ".join(not_found))
