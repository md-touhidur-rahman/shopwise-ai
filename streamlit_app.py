import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import difflib
import streamlit as st
from io import StringIO
import csv


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
DATA_PATH = Path("data/common_products.json")  # put your JSON here

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
        "(Geben Sie den gewünschten Lebensmittelartikel ein, um den Preis vor dem Kauf zu vergleichen.)"
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
    """Split input smartly — commas/newlines first, else spaces."""
    if not text:
        return []
    if re.search(r"[,;\n]", text):
        parts = re.split(r"[,;\n]+", text)
    else:
        parts = text.split()
    return [p.strip() for p in parts if p.strip()]


def find_best_match(user_term: str, products: List[Dict[str, Any]], threshold: float = 0.5) -> Tuple[Dict[str, Any], float]:
    user_norm = normalize_text(user_term)
    best_score = 0.0
    best_product = None

    # substring
    for p in products:
        for name in p["__names_for_match"]:
            if user_norm and user_norm in normalize_text(name):
                return p, 0.99

    # fuzzy
    for p in products:
        for name in p["__names_for_match"]:
            score = difflib.SequenceMatcher(None, user_norm, normalize_text(name)).ratio()
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
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def build_csv(store_data: Dict[str, Dict[str, Any]]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["store", "item", "price_eur"])
    for store, data in store_data.items():
        for item, price in data["items"].items():
            writer.writerow([store, item, f"{price:.2f}"])
    return buffer.getvalue()


# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.title(TEXT["title"])
st.write(TEXT["subtitle"])

if not PRODUCTS:
    st.error(TEXT["file_missing"])
else:
    user_input = st.text_area(
        TEXT["input_label"],
        height=120,
        placeholder=TEXT["placeholder"],
    )

    if st.button("Compare / Vergleichen", type="primary"):
        items = split_user_input(user_input)
        if not items:
            st.warning(TEXT["no_items"])
        else:
            matched, not_found = [], []
            for term in items:
                product, score = find_best_match(term, PRODUCTS)
                if product is None:
                    not_found.append(term)
                else:
                    matched.append({"user_term": term, "product": product, "score": score})
            st.session_state["matched_items"] = matched
            st.session_state["not_found_items"] = not_found

    matched = st.session_state.get("matched_items", [])
    not_found = st.session_state.get("not_found_items", [])

    if matched or not_found:
        st.subheader(TEXT["results_header"])

        if matched:
            match_rows = []
            for m in matched:
                p = m["product"]
                match_rows.append({
                    "You typed / Eingegeben": m["user_term"],
                    "Matched product / Zugeordnet": p.get("canonical_name") or p.get("english_name"),
                    "Unit / Einheit": p.get("unit", ""),
                })
            st.dataframe(match_rows, hide_index=True, use_container_width=True)

            store_data = aggregate_by_store(matched)
            st.subheader(TEXT["per_store_header"])

            price_table = []
            for store, data in store_data.items():
                price_table.append({
                    "Store / Markt": store.capitalize(),
                    "Total (€)": round(data["total"], 2),
                    "Items counted / Artikel gezählt": len(data["items"]),
                })
            st.dataframe(price_table, hide_index=True, use_container_width=True)

            valid_stores = {s: d["total"] for s, d in store_data.items() if d["items"]}
            if valid_stores:
                cheapest = min(valid_stores, key=valid_stores.get)
                st.success(
                    f"Cheapest overall: **{cheapest.capitalize()}** with total {valid_stores[cheapest]:.2f} € "
                    f"(based on matched items). / "
                    f"Günstigster Markt: **{cheapest.capitalize()}** mit {valid_stores[cheapest]:.2f} €."
                )

            csv_text = build_csv(store_data)
            st.download_button(
                label="Download price comparison (CSV) / Preisvergleich herunterladen (CSV)",
                data=csv_text,
                file_name="shopwise_comparison.csv",
                mime="text/csv",
            )

            with st.expander("Details per store (Details je Markt)"):
                for store, data in store_data.items():
                    st.markdown(f"**{store.capitalize()}**")
                    rows = [{"Item entered / Eingegeben": k, "Price (€) / Preis (€)": v} for k, v in data["items"].items()]
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

        st.markdown("---")
        st.write(TEXT["add_more_label"])
        new_item = st.text_input("Item / Artikel", value="", key="add_item_input")

        if st.button("Add / Hinzufügen"):
            if new_item.strip():
                product, score = find_best_match(new_item, PRODUCTS)
                if product is None:
                    st.session_state["not_found_items"].append(new_item)
                else:
                    st.session_state["matched_items"].append({"user_term": new_item, "product": product, "score": score})
                safe_rerun()

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")
st.caption(
    "Demo: ShopWise AI — built by **Md. Touhidur Rahman** (M.Sc. Data Science, FAU Erlangen-Nürnberg). "
    "Bilingual Streamlit app for supermarket price comparison with fuzzy matching and JSON-backed data."
)
