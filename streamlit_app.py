import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import difflib
import streamlit as st
from io import StringIO
import csv

# optional OpenAI: only used if a key is provided
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
DATA_PATH = Path("data/common_products.json")

st.set_page_config(
    page_title="ShopWise AI – Grocery Price Comparator",
    layout="wide",
)

TEXT = {
    "title": "ShopWise AI – Grocery Price Comparison (Lebensmittel-Preisvergleich)",
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
# SIDEBAR: optional real AI
# ---------------------------------------------------------
st.sidebar.header("AI Settings")
user_api_key = st.sidebar.text_input(
    "Optional: paste your OpenAI API key to use real LLM",
    type="password",
    help="If empty, the app will use a rule-based summary.",
)

client = None
if OpenAI and user_api_key:
    client = OpenAI(api_key=user_api_key)

# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------
if "matched_items" not in st.session_state:
    st.session_state["matched_items"] = []
if "not_found_items" not in st.session_state:
    st.session_state["not_found_items"] = []

# ---------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_products(path: Path):
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
# HELPERS
# ---------------------------------------------------------
def normalize_text(s: str) -> str:
    s = s.lower().strip()
    repl = {"ä": "a", "ö": "o", "ü": "u", "ß": "ss"}
    for k, v in repl.items():
        s = s.replace(k, v)
    return s


def split_user_input(text: str) -> List[str]:
    if not text:
        return []
    if re.search(r"[,;\n]", text):
        parts = re.split(r"[,;\n]+", text)
    else:
        parts = text.split()
    return [p.strip() for p in parts if p.strip()]


def find_best_match(user_term: str, products, threshold: float = 0.5):
    user_norm = normalize_text(user_term)
    best_score = 0.0
    best_product = None

    # substring first
    for p in products:
        for name in p["__names_for_match"]:
            if user_norm and user_norm in normalize_text(name):
                return p, 0.99

    # fuzzy
    for p in products:
        for name in p["__names_for_match"]:
            score = difflib.SequenceMatcher(
                None, user_norm, normalize_text(name)
            ).ratio()
            if score > best_score:
                best_score = score
                best_product = p

    if best_score >= threshold:
        return best_product, best_score
    return None, 0.0


def aggregate_by_store(matched_items):
    stores = ["kaufland", "lidl", "aldi"]
    result = {s: {"total": 0.0, "items": {}} for s in stores}
    for entry in matched_items:
        product = entry["product"]
        user_term = entry["user_term"]
        for store, price in product.get("prices", {}).items():
            result[store]["total"] += float(price)
            result[store]["items"][user_term] = float(price)
    return result


def build_csv(store_data):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["store", "item", "price_eur"])
    for store, data in store_data.items():
        for item, price in data["items"].items():
            writer.writerow([store, item, f"{price:.2f}"])
    return buffer.getvalue()


def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def rule_based_summary(store_data: Dict[str, Dict[str, Any]], matched_items):
    valid = {s: d["total"] for s, d in store_data.items() if d["items"]}
    if not valid:
        return (
            "No valid prices to compare. Please check your items.\n"
            "Keine gültigen Preise zum Vergleichen. Bitte prüfen Sie Ihre Artikel."
        )

    cheapest = min(valid, key=valid.get)

    lines = []
    lines.append(
        f"Cheapest store (based on matched items): {cheapest.capitalize()} with {valid[cheapest]:.2f} €."
    )

    for s, total in valid.items():
        if s != cheapest:
            diff = total - valid[cheapest]
            lines.append(f"{s.capitalize()} is {diff:.2f} € more expensive for this basket.")

    item_list = ", ".join([m["user_term"] for m in matched_items])
    lines.append(f"Items compared: {item_list}")

    # German part without mixing f-string and format
    german_line = (
        "Deutsch: Günstigster Markt auf Basis dieser Artikel: "
        + f"{cheapest.capitalize()} mit {valid[cheapest]:.2f} €."
    )
    lines.append(german_line)

    return "\n".join(lines)

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.markdown(
    f"<h1 style='color:#1E3A8A'>{TEXT['title']}</h1>",
    unsafe_allow_html=True,
)
st.write(TEXT["subtitle"])

if not PRODUCTS:
    st.error(TEXT["file_missing"])
else:
    user_input = st.text_area(
        TEXT["input_label"],
        height=120,
        placeholder=TEXT["placeholder"],
    )

    # button style
    st.markdown(
        """
        <style>
        div.stButton > button:first-child {
            background-color:#2563EB;
            color:white;
            border-radius:8px;
            height:3em;
            width:100%;
            border:none;
        }
        div.stButton > button:first-child:hover {
            background-color:#1E40AF;
            color:white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Compare / Vergleichen"):
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
                    matched.append(
                        {"user_term": term, "product": product, "score": score}
                    )
            st.session_state["matched_items"] = matched
            st.session_state["not_found_items"] = not_found

    matched = st.session_state.get("matched_items", [])
    not_found = st.session_state.get("not_found_items", [])

    if matched or not_found:
        st.subheader(TEXT["results_header"])

        if matched:
            match_rows = [
                {
                    "You typed / Eingegeben": m["user_term"],
                    "Matched product / Zugeordnet": m["product"].get(
                        "canonical_name"
                    )
                    or m["product"].get("english_name"),
                    "Unit / Einheit": m["product"].get("unit", ""),
                }
                for m in matched
            ]
            st.dataframe(match_rows, hide_index=True, use_container_width=True)

            store_data = aggregate_by_store(matched)
            st.subheader(TEXT["per_store_header"])
            price_table = [
                {
                    "Store / Markt": s.capitalize(),
                    "Total (€)": round(d["total"], 2),
                    "Items counted / Artikel gezählt": len(d["items"]),
                }
                for s, d in store_data.items()
            ]
            st.dataframe(price_table, hide_index=True, use_container_width=True)

            valid_stores = {s: d["total"] for s, d in store_data.items() if d["items"]}
            if valid_stores:
                cheapest = min(valid_stores, key=valid_stores.get)
                st.success(
                    f"Cheapest overall: {cheapest.capitalize()} with total {valid_stores[cheapest]:.2f} € "
                    f"(based on matched items). / "
                    f"Günstigster Markt: {cheapest.capitalize()} mit {valid_stores[cheapest]:.2f} €."
                )

            csv_text = build_csv(store_data)
            st.download_button(
                label="Download price comparison (CSV) / Preisvergleich herunterladen (CSV)",
                data=csv_text,
                file_name="shopwise_comparison.csv",
                mime="text/csv",
            )

            with st.expander("Details per store (Details je Markt)"):
                for s, d in store_data.items():
                    st.markdown(f"**{s.capitalize()}**")
                    rows = [
                        {
                            "Item entered / Eingegeben": k,
                            "Price (€) / Preis (€)": v,
                        }
                        for k, v in d["items"].items()
                    ]
                    st.dataframe(rows, hide_index=True, use_container_width=True)

            # AI-like section
            st.markdown("### AI Summary (realistic) / KI-Zusammenfassung")

            if client:
                if st.button("Generate with OpenAI / Mit OpenAI erzeugen"):
                    try:
                        context_text = "Price comparison results:\n"
                        for store, data in store_data.items():
                            context_text += (
                                f"- {store}: total {data['total']:.2f} € "
                                f"({len(data['items'])} items)\n"
                            )
                        context_text += "\nUser items:\n" + ", ".join(
                            [m["user_term"] for m in matched]
                        )

                        system_prompt = (
                            "You are an assistant helping a shopper in Germany compare grocery prices "
                            "between Lidl, Kaufland and Aldi. Summarize in English and then in German. "
                            "Be concise and refer only to the provided numbers."
                        )

                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": context_text},
                            ],
                            temperature=0.3,
                        )
                        ai_text = response.choices[0].message.content.strip()
                        st.markdown(ai_text)
                    except Exception as e:
                        st.error(f"Error calling OpenAI: {e}")
            else:
                summary_text = rule_based_summary(store_data, matched)
                st.code(summary_text)

        if not_found:
            st.subheader(TEXT["not_found_header"])
            st.write(
                "These items could not be matched to our list. Try spelling them differently or use German names.\n"
                "Diese Artikel konnten nicht zugeordnet werden. Bitte andere Schreibweise oder deutsche Bezeichnung versuchen."
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
                    st.session_state["matched_items"].append(
                        {"user_term": new_item, "product": product, "score": score}
                    )
                safe_rerun()

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")
st.caption(
    "ShopWise AI — built by Md. Touhidur Rahman. Bilingual Streamlit prototype for price comparison with optional LLM integration."
)
