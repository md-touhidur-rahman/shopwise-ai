import json
import os
from pathlib import Path

import streamlit as st
from rapidfuzz import process, fuzz

st.set_page_config(page_title="ShopWise AI", page_icon="🛒", layout="wide")
st.title("🛒 ShopWise AI")
st.write("Compare grocery items across Kaufland, Lidl and Aldi from your prepared JSON files.")

# --- 1. load data -----------------------------------------------------------
DATA_DIR = Path("data")

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

# adapt these to your actual filenames
KAUFLAND = load_json(DATA_DIR / "kaufland.json")
LIDL = load_json(DATA_DIR / "lidl_products.json")
ALDI = load_json(DATA_DIR / "aldi_products.json")

stores = {
    "kaufland": KAUFLAND,
    "lidl": LIDL,
    "aldi": ALDI,
}

st.sidebar.subheader("📦 Data loaded")
for name, data in stores.items():
    st.sidebar.write(f"{name.title()}: {len(data)} products")

# --- 2. helper: get display name / price from different schemas ------------
def extract_name(item: dict):
    # try common keys from the files you uploaded
    for key in ["product_name", "name", "title", "Product", "article"]:
        if key in item and item[key]:
            return str(item[key])
    return "Unknown item"

def extract_price_now(item: dict):
    # some files had strings like "1.00" or "0,99"
    for key in ["price_now", "price", "current_price", "priceCurrent"]:
        if key in item and item[key] not in (None, ""):
            val = str(item[key]).replace("€", "").replace(",", ".").strip()
            try:
                return float(val)
            except ValueError:
                pass
    return None

def extract_unit(item: dict):
    for key in ["weight_or_unit", "unit", "packaging", "size"]:
        if key in item and item[key]:
            return str(item[key])
    return ""

# --- 3. fuzzy finder per store ---------------------------------------------
def find_best_match(query: str, products: list, score_cutoff: int = 70):
    # build choices of names
    names = [extract_name(p) for p in products]
    best = process.extractOne(
        query,
        names,
        scorer=fuzz.WRatio,
        score_cutoff=score_cutoff
    )
    if not best:
        return None, None
    name, score, idx = best
    return products[idx], score

# --- 4. parse user input ---------------------------------------------------
user_text = st.text_area(
    "📝 Your shopping list",
    placeholder="e.g. milka chocolate, bananas, sliced cheese, potatoes",
    height=120
)

col_run, col_info = st.columns([1, 3])
with col_run:
    run = st.button("Compare")

with col_info:
    st.caption("Tip: we'll try to correct typos like *choclet* → *chocolate* per store.")

# --- 5. main logic ----------------------------------------------------------
if run:
    if not user_text.strip():
        st.warning("Please enter at least one product.")
    else:
        # split by comma or newline
        raw_items = [p.strip() for p in user_text.replace("\n", ",").split(",") if p.strip()]
        st.subheader("🧾 Cleaned items")
        st.write(", ".join(raw_items))

        # table results
        results = []  # will hold dicts for building a dataframe-like output

        for item in raw_items:
            row = {"query": item}
            for store_name, data in stores.items():
                match, score = find_best_match(item, data)
                if match:
                    price = extract_price_now(match)
                    unit = extract_unit(match)
                    row[f"{store_name}_name"] = extract_name(match)
                    row[f"{store_name}_price"] = price
                    row[f"{store_name}_unit"] = unit
                    row[f"{store_name}_score"] = score
                else:
                    row[f"{store_name}_name"] = "— not available —"
                    row[f"{store_name}_price"] = None
                    row[f"{store_name}_unit"] = ""
                    row[f"{store_name}_score"] = 0
            results.append(row)

        # --- 6. show per item ------------------------------------------------
        st.subheader("💰 Price comparison")
        for row in results:
            st.markdown(f"### {row['query']}")
            c1, c2, c3 = st.columns(3)
            for col, store_name in zip([c1, c2, c3], ["kaufland", "lidl", "aldi"]):
                with col:
                    name = row[f"{store_name}_name"]
                    price = row[f"{store_name}_price"]
                    unit = row[f"{store_name}_unit"]
                    if price is not None:
                        st.write(f"**{store_name.title()}**")
                        st.write(name)
                        st.write(f"**{price:.2f} €**")
                        if unit:
                            st.caption(unit)
                    else:
                        st.write(f"**{store_name.title()}**")
                        st.write("❌ not available")

        # --- 7. find overall cheapest store for this basket ------------------
        st.subheader("🧮 Basket total per store")
        totals = {s: 0.0 for s in stores.keys()}
        for row in results:
            for store_name in stores.keys():
                price = row.get(f"{store_name}_price")
                if price is not None:
                    totals[store_name] += price

        for store_name, total in totals.items():
            st.write(f"- **{store_name.title()}**: {total:.2f} €")

        cheapest_store = min(totals, key=totals.get)
        st.success(f"✅ Cheapest overall: **{cheapest_store.title()}** with {totals[cheapest_store]:.2f} € (based on matched items).")

st.caption("Demo app for recruiter: compares three supermarkets from uploaded JSONs, handles fuzzy names, and shows unavailable items clearly.")
