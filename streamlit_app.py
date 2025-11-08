import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import difflib
import streamlit as st


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
DATA_PATH = Path("data/common_products.json")  # adjust if needed

st.set_page_config(
    page_title="Grocery Price Comparator",
    layout="centered",
)

# ---------------------------------------------------------
# TEXTS (EN + DE)
# ---------------------------------------------------------
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
    "placeholder": "e.g. milk, bread, bananas / z.B. Milch, Brot, Bananen",
    "results_header": "Comparison Result (Vergleichsergebnis)",
    "not_found_header": "Not found (Nicht gefunden)",
    "per_store_header": "Prices per store (Preise je Markt)",
    "no_items": "Enter at least one item. / Bitte mindestens einen Artikel eingeben.",
    "file_missing": (
        "Product data file not found. Please make sure `data/common_products.json` exists.\n"
        "Produktdatei nicht gefunden. Bitte stellen Sie sicher, dass `data/common_products.json` existiert."
    ),
    "add_more_label": "Add another item (Weiteren Artikel hinzufügen)",
}


# ---------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------
if "matched_items" not in st.session_state:
    st.session_state["matched_items"] = []
if "not_found_items" not in st.session_state:
    st.session_state["not_found_items"] = []


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_products(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # add helper field for matching
    for item in data:
        item["__names_for_match"] = [
            item.get("canonical_name", "") or "",
            item.get("english_name", "") or "",
        ]
    return data


PRODUCTS = load_products(DATA_PATH)


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def normalize_text(s: str) -> str:
    s = s.lower().strip()
    repl = {"ä": "a", "ö": "o", "ü": "u", "ß": "ss"}
    for k, v in repl.items():
        s = s.replace(k, v)
    return s


def split_user_input(text: str) -> List[str]:
    """
    1. If user used commas/semicolons/newlines -> split on those.
    2. Else -> fall back to splitting on spaces (for 'milch brot banane').
    """
    if not text:
        return []

    if re.search(r"[,;\n]", text):
        parts = re.split(r"[,;\n]+", text)
    else:
        parts = text.split()

    parts = [p.strip() for p in parts if p.strip()]
    return parts


def find_best_match(
    user_term: str,
    products: List[Dict[str, Any]],
    threshold: float = 0.5,
) -> Tuple[Dict[str, Any], float]:
    """
    1. try substring match first (for partials)
    2. fallback to fuzzy
    """
    user_norm = normalize_text(user_term)
    best_score = 0.0
    best_product = None

    # substring pass
    for p in products:
        for name in p["__names_for_match"]:
            name_norm = normalize_text(name)
            if user_norm and user_norm in name_norm:
                return p, 0.99

    # fuzzy pass
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


def aggregate_by_store(matched_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    stores = ["kaufland", "lidl", "aldi"]
    result = {s: {"total": 0.0, "items": {}} for s in stores}

    for entry in matched_items:
        product = entry["product"]
        user_term = entry["user_term"]
        prices = product.get("prices", {})
        for store in stores:
            price = float(prices.get(store, 0.0))
            result[store]["total"] += price
            result[store]["items"][user_term] = price

    return result


def safe_rerun():
    """Use st.rerun if available, else silently ignore."""
    if hasattr(st, "rerun"):
        st.rerun()
    # older versions had st.experimental_rerun
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    # else: do nothing


# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.title(TEXT["title"])
st.write(TEXT["subtitle"])

if not PRODUCTS:
    st.error(TEXT["file_missing"])
else:
    # main input
    user_input = st.text_area(
        TEXT["input_label"],
        height=120,
        placeholder=TEXT["placeholder"],
    )

    # MAIN COMPARE BUTTON
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
                    matched.append(
                        {
                            "user_term": term,
                            "product": product,
                            "score": score,
                        }
                    )

            # store in session, so we can add more later
            st.session_state["matched_items"] = matched
            st.session_state["not_found_items"] = not_found

    # RENDER RESULTS FROM SESSION
    matched = st.session_state.get("matched_items", [])
    not_found = st.session_state.get("not_found_items", [])

    if matched or not_found:
        st.subheader(TEXT["results_header"])

        if matched:
            # show matched items
            match_rows = []
            for m in matched:
                p = m["product"]
                match_rows.append(
                    {
                        "You typed / Eingegeben": m["user_term"],
                        "Matched product / Zugeordnet": p.get("canonical_name") or p.get("english_name"),
                        "Unit / Einheit": p.get("unit", ""),
                        "Category / Kategorie": p.get("category", ""),
                    }
                )
            st.dataframe(match_rows, hide_index=True, use_container_width=True)

            # aggregate per store
            store_data = aggregate_by_store(matched)
            st.subheader(TEXT["per_store_header"])

            price_table = []
            for store, data in store_data.items():
                price_table.append(
                    {
                        "Store / Markt": store.capitalize(),
                        "Total (€)": round(data["total"], 2),
                        "Items counted / Artikel gezählt": len(data["items"]),
                    }
                )
            st.dataframe(price_table, hide_index=True, use_container_width=True)

            with st.expander("Details per store (Details je Markt)"):
                for store, data in store_data.items():
                    st.markdown(f"**{store.capitalize()}**")
                    rows = []
                    for user_term, price in data["items"].items():
                        rows.append(
                            {
                                "Item entered / Eingegeben": user_term,
                                "Price (€) / Preis (€)": price,
                            }
                        )
                    st.dataframe(rows, hide_index=True, use_container_width=True)

        if not_found:
            st.subheader(TEXT["not_found_header"])
            st.write(
                "These items could not be matched to our list. "
                "Try spelling them differently or use German names.\n"
                "Diese Artikel konnten nicht zugeordnet werden. "
                "Bitte andere Schreibweise oder deutsche Bezeichnung versuchen."
            )
            st.write(", ".join(not_found))

        # -------------------------------------------------
        # ADD ANOTHER ITEM
        # -------------------------------------------------
        st.markdown("---")
        st.write(TEXT["add_more_label"])
        new_item = st.text_input("Item / Artikel", value="", key="add_item_input")

        if st.button("Add / Hinzufügen"):
            if new_item.strip():
                product, score = find_best_match(new_item, PRODUCTS)
                if product is None:
                    st.session_state["not_found_items"].append(new_item)
                else:
                    st.session_state["matched_items"].append(
                        {
                            "user_term": new_item,
                            "product": product,
                            "score": score,
                        }
                    )
                # refresh UI
                safe_rerun()
