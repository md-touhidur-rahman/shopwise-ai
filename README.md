ShopWise AI – Grocery Price Comparison (Lebensmittel-Preisvergleich)

ShopWise AI is a bilingual Streamlit application that compares grocery prices across major German supermarkets — Kaufland, Lidl, and Aldi.
The app uses fuzzy matching to interpret user input (in English or German), aggregates prices for each store, and identifies the cheapest shopping option. It includes a rule-based reasoning system and optional integration with OpenAI’s API for AI-generated summaries.


Overview

ShopWise AI demonstrates the practical intersection of AI engineering, data processing, and full-stack development.
Users can input their grocery list — even with typos or mixed languages — and the system automatically:

Matches items against a local product dataset

Compares total and per-item prices across multiple retailers

Displays results interactively

Generates bilingual summaries (rule-based or LLM-powered)

Exports results as a CSV file for further analysis



Features

Fuzzy string matching for handling spelling variations and typos

English–German bilingual interface

Price comparison across multiple supermarkets

Downloadable price summary (CSV format)

Rule-based summary generation (free, no API needed)

Optional OpenAI API integration for natural language summaries

Clean and responsive user interface using Streamlit



| Component               | Technology                         |
| ----------------------- | ---------------------------------- |
| Framework               | Streamlit                          |
| Language                | Python                             |
| Data                    | JSON dataset of 200+ grocery items |
| Matching Algorithm      | `difflib` (fuzzy matching)         |
| Optional AI Integration | OpenAI GPT models                  |
| Output                  | Interactive UI and CSV export      |


shopwise-ai/
 ├── streamlit_app.py                     
 ├── data/
 │    └── common_products.json  # Local dataset of products
 ├── requirements.txt           # Dependencies
 └── README.md                  # Documentation



Deployment

The project is deployed on Streamlit Cloud:
https://shopwise-ai-qxiba6ugfmiuhqkmehsmpx.streamlit.app/

Author

Md. Touhidur Rahman
M.Sc. Data Science, Friedrich-Alexander-Universität Erlangen–Nürnberg
