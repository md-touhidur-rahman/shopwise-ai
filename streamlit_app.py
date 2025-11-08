import json
from pathlib import Path

import streamlit as st
from rapidfuzz import process, fuzz

st.set_page_config(page_title="ShopWise AI", page_icon="🛒", layout="wide")
st.title("🛒 ShopWise AI — Save your Money (Sparen Sie Ihr Geld)")
st.write("Type  grocery items  to compare price before going to buy it.")
st.write("Geben Sie den gewünschten Lebensmittelartikel ein, um den Preis vor dem Kauf zu vergleichen.")
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------
# 1) 50 common items in Germany with dummy prices
# ---------------------------------------------------------------------
BASE_ITEMS = [
    # name, unit, kaufland, lidl, aldi
    ("milch 1l", "1 l", 1.05, 0.99, 1.09),
    ("butter 250g", "250 g", 2.19, 2.09, 2.05),
    ("eier 10er", "10 stk", 2.29, 2.19, 2.25),
    ("kartoffeln 2,5kg", "2,5 kg", 3.49, 3.39, 3.29),
    ("zwiebeln 1kg", "1 kg", 0.99, 0.95, 0.89),
    ("bananen", "per kg", 0.85, 0.88, 0.89),
    ("äpfel 1kg", "1 kg", 1.49, 1.59, 1.39),
    ("paprika mix 500g", "500 g", 1.99, 1.89, 1.95),
    ("tomaten 1kg", "1 kg", 2.49, 2.39, 2.29),
    ("gurke", "stk", 0.79, 0.69, 0.75),
    ("brot", "750 g", 1.49, 1.39, 1.29),
    ("brötchen 5stk", "5 stk", 1.49, 1.39, 1.29),
    ("joghurt natur 500g", "500 g", 0.99, 0.95, 0.89),
    ("quark 250g", "250 g", 0.79, 0.69, 0.75),
    ("käse scheiben 150g", "150 g", 1.49, 1.39, 1.45),
    ("frischkäse 200g", "200 g", 1.19, 1.09, 1.15),
    ("schnittkäse 250g", "250 g", 2.19, 2.09, 2.05),
    ("wurstaufschnitt 200g", "200 g", 1.99, 1.79, 1.89),
    ("schinken gekocht 200g", "200 g", 2.29, 2.19, 2.15),
    ("hackfleisch gemischt 500g", "500 g", 4.49, 4.29, 4.39),
    ("hähnchenbrust 1kg", "1 kg", 7.99, 7.79, 7.49),
    ("lachsfilet tk 300g", "300 g", 4.49, 4.29, 4.39),
    ("fischstäbchen 15stk", "390-450 g", 2.99, 2.79, 2.89),
    ("tiefkühl pizza", "stk", 2.49, 2.29, 2.39),
    ("nudeln 500g", "500 g", 0.99, 0.95, 0.89),
    ("reis 1kg", "1 kg", 1.99, 1.89, 1.79),
    ("mehl 1kg", "1 kg", 0.89, 0.85, 0.79),
    ("zucker 1kg", "1 kg", 0.99, 0.95, 0.89),
    ("salz 500g", "500 g", 0.39, 0.35, 0.39),
    ("sonnenblumenöl 1l", "1 l", 2.59, 2.49, 2.39),
    ("olivenöl 1l", "1 l", 5.99, 5.79, 5.49),
    ("kaffee 500g", "500 g", 5.49, 5.29, 5.19),
    ("tee schwarz 25 beutel", "25 beutel", 1.29, 1.19, 1.25),
    ("mineralwasser still 1,5l", "1,5 l", 0.45, 0.39, 0.39),
    ("cola 1,25l", "1,25 l", 1.29, 1.25, 1.19),
    ("saft orange 1l", "1 l", 1.49, 1.39, 1.29),
    ("schokolade tafel 100g", "100 g", 0.99, 0.89, 0.95),
    ("müsli 500g", "500 g", 2.29, 2.09, 1.99),
    ("haferflocken 500g", "500 g", 0.99, 0.89, 0.85),
    ("tomatenmark 200g", "200 g", 0.89, 0.79, 0.79),
    ("passierte tomaten 500g", "500 g", 0.99, 0.89, 0.85),
    ("dosentomaten 400g", "400 g", 0.89, 0.79, 0.75),
    ("mais dose 340g", "340 g", 0.99, 0.89, 0.85),
    ("erbsen dose 400g", "400 g", 0.99, 0.89, 0.85),
    ("spinat tk 450g", "450 g", 1.29, 1.19, 1.15),
    ("pommes tk 1kg", "1 kg", 2.19, 1.99, 1.95),
    ("waschmittel 20 wäschen", "1 stk", 3.99, 3.79, 3.69),
    ("toilettenpapier 8 rollen", "8 rollen", 3.49, 3.29, 3.19),
    ("pampers feuchttücher", "pkt", 1.99, 1.89, 1.79),
    ("brotaufstrich nutella 450g", "450 g", 3.29, 3.19, 3.09),
    ("biskuit / kekse 200g", "200 g", 1.19, 1.09, 1.05)
]


def base_store_data():
    kaufland, lidl, aldi = [], [], []
    for name, unit, k_price, l_price, a_price in BASE_ITEMS:
        kaufland.append({"product_name": name, "unit": unit, "price_now": k_price})
        lidl.append({"product_name": name, "unit": unit, "price_now": l_price})
        aldi.append({"product_name": name, "unit": unit, "price_now": a_price})
    return kaufland, lidl, aldi


# ---------------------------------------------------------------------
# 2) try to load your real JSONs (if present) and extend with base data
# ---------------------------------------------------------------------
def load_if_exists(path: Path):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []

# user-provided files (optional)
kaufland_user = load_if_exists(DATA_DIR / "kaufland.json")
lidl_user = load_if_exists(DATA_DIR / "lidl_products.json")
aldi_user = load_if_exists(DATA_DIR / "aldi_products.json")

# base dummy data
kaufland_base, lidl_base, aldi_base = base_store_data()

KAUFLAND = kaufland_user + kaufland_base
LIDL = lidl_user + lidl_base
ALDI = aldi_user + aldi_base

stores = {
    "kaufland": KAUFLAND,
    "lidl": LIDL,
    "aldi": ALDI,
}

st.sidebar.subheader(" Data sources")
st.sidebar.write(f"Kaufland: {len(KAUFLAND)} items")
st.sidebar.write(f"Lidl: {len(LIDL)} items")
st.sidebar.write(f"Aldi: {len(ALDI)} items")
st.sidebar.caption("If your own JSONs exist in /data, they are used first, then 50 dummy staples are added.")


# ---------------------------------------------------------------------
# helpers to standardize fields
# ---------------------------------------------------------------------
def extract_name(item: dict):
    for key in ["product_name", "name", "title", "article"]:
        if key in item and item[key]:
            return str(item[key])
    return "Unknown item"


def extract_price_now(item: dict):
    for key in ["price_now", "price", "current_price"]:
        if key in item and item[key] not in ("", None):
            val = str(item[key]).replace("€", "").replace(",", ".").strip()
            try:
                return float(val)
            except ValueError:
                return None
    return None


def extract_unit(item: dict):
    for key in ["unit", "weight_or_unit", "packaging", "size"]:
        if key in item and item[key]:
            return str(item[key])
    return ""


def find_best_match(query: str, products: list, score_cutoff: int = 80):
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


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------
user_text = st.text_area(
    "Your shopping list",
    placeholder="e.g. milch, eier, paprika, nutella, waschmittel",
    height=130
)

if st.button("Compare prices"):
    if not user_text.strip():
        st.warning("Please enter at least one product.")
    else:
        raw_items = [p.strip() for p in user_text.replace("\n", ",").split(",") if p.strip()]
        st.subheader(" Items I will look for")
        st.write(", ".join(raw_items))

        results = []
        for item in raw_items:
            row = {"query": item}
            for store_name, data in stores.items():
                match, score = find_best_match(item, data)
                if match:
                    row[f"{store_name}_name"] = extract_name(match)
                    row[f"{store_name}_price"] = extract_price_now(match)
                    row[f"{store_name}_unit"] = extract_unit(match)
                    row[f"{store_name}_score"] = score
                else:
                    row[f"{store_name}_name"] = "— not available —"
                    row[f"{store_name}_price"] = None
                    row[f"{store_name}_unit"] = ""
                    row[f"{store_name}_score"] = 0
            results.append(row)

        st.subheader(" Price comparison")
        for row in results:
            st.markdown(f"### {row['query']}")
            c1, c2, c3 = st.columns(3)
            for col, store_name in zip([c1, c2, c3], ["kaufland", "lidl", "aldi"]):
                with col:
                    price = row[f"{store_name}_price"]
                    name = row[f"{store_name}_name"]
                    unit = row[f"{store_name}_unit"]
                    st.write(f"**{store_name.title()}**")
                    if price is not None:
                        st.write(name)
                        st.write(f"**{price:.2f} €**")
                        if unit:
                            st.caption(unit)
                    else:
                        st.write(" not available")

        # --------------------------------------------------
        # basket totals: only count stores with >=1 matches
        # --------------------------------------------------
        st.subheader("Basket total per store")
        totals = {s: 0.0 for s in stores.keys()}
        matches = {s: 0 for s in stores.keys()}

        for row in results:
            for store_name in stores.keys():
                price = row.get(f"{store_name}_price")
                if price is not None:
                    totals[store_name] += price
                    matches[store_name] += 1

        for store_name in stores.keys():
            if matches[store_name] == 0:
                st.write(f"- **{store_name.title()}**:  no matching items")
            else:
                st.write(f"- **{store_name.title()}**: {totals[store_name]:.2f} € ({matches[store_name]} items)")

        valid_stores = {s: totals[s] for s in stores.keys() if matches[s] > 0}
        if valid_stores:
            cheapest = min(valid_stores, key=valid_stores.get)
            st.success(
                f" Cheapest overall: **{cheapest.title()}** with {valid_stores[cheapest]:.2f} € "
                f"(based on {matches[cheapest]} matched items)."
            )
        else:
            st.warning("Could not match any item in any store.")

st.caption("Demo for recruiters: loads real JSON if present, falls back to 50 German staples with dummy prices, fuzzy-matches user input, compares 3 stores, and handles unavailable items.")
