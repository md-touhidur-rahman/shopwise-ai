import json
import streamlit as st
from utils.normalize import normalize_item

st.set_page_config(page_title="ShopWise AI", page_icon="🛒")

st.title("🛒 ShopWise AI — Smart Grocery Price Assistant")
st.write("Type your shopping list naturally — I'll clean it, correct typos, and compare prices across Lidl, Kaufland, REWE, and Penny.")

# load price database
with open("data/prices.json", "r", encoding="utf-8") as f:
    PRICE_DB = json.load(f)

STORES = ["lidl", "kaufland", "rewe", "penny"]

def parse_list(text):
    # simple split by comma or newline
    return [p.strip() for p in text.replace("\n", ",").split(",") if p.strip()]

def build_cart(items):
    cart = []
    unknown = []
    for item in items:
        norm = normalize_item(item)
        if norm:
            cart.append(norm)
        else:
            unknown.append(item)
    return cart, unknown

def compute_totals(cart):
    totals = {s: 0 for s in STORES}
    breakdown = {s: [] for s in STORES}
    for ci in cart:
        if ci not in PRICE_DB:
            continue
        for s in STORES:
            price = PRICE_DB[ci][s]
            totals[s] += price
            breakdown[s].append((ci, price))
    return totals, breakdown

def make_summary(totals):
    cheapest = min(totals, key=totals.get)
    return f"✅ **{cheapest.title()}** is cheapest right now in our dataset: **{totals[cheapest]:.2f} €**."

user_input = st.text_area(
    "🗣️ Your shopping list (e.g. '2l milk, bred, choclet, eggs')",
    height=120
)

if st.button("Compare prices"):
    if not user_input.strip():
        st.warning("Please enter something first.")
    else:
        items = parse_list(user_input)
        cart, unknown = build_cart(items)
        totals, breakdown = compute_totals(cart)

        st.subheader("🧾 Cleaned list")
        if cart:
            for c in cart:
                st.write(f"- {c}")
        else:
            st.write("_No recognized items_")

        if unknown:
            st.warning("I couldn't recognize these:")
            for u in unknown:
                st.write(f"- {u}")

        st.subheader("💰 Price comparison")
        for store, total in totals.items():
            st.write(f"- **{store.title()}**: {total:.2f} €")

        if totals:
            st.markdown(make_summary(totals))

        st.subheader("📦 Item-wise breakdown")
        for store in STORES:
            st.write(f"**{store.title()}**")
            for name, price in breakdown[store]:
                st.write(f"- {name}: {price:.2f} €")

st.caption("Demo data only — educational, non-commercial use.")
