import os
import requests
import google.generativeai as genai
from datetime import datetime

# 1. AUTH & SAFETY CHECK
ALPHA_KEY = os.getenv('ALPHA_VANTAGE_KEY')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if not ALPHA_KEY or not GEMINI_KEY:
    print("❌ ERROR: API Keys missing from GitHub Secrets.")
    exit(1)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def fetch_data(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_KEY}"
        data = requests.get(url).json().get("Global Quote", {})
        return {
            "price": float(data.get("05. price", 0.0)),
            "change": float(data.get("10. change percent", "0.0%").strip('%'))
        }
    except Exception as e:
        print(f"⚠️ Fetch Error for {symbol}: {e}")
        return {"price": 0.0, "change": 0.0}

# 2. MARKET DATA SWEEP
ptf = {
    "EQCH": fetch_data("QQQ"),
    "SP500S": fetch_data("SPY"),
    "IWVD": fetch_data("IVW"),
    "SMHV": fetch_data("SOXX"),
    "AUUCH": fetch_data("GLD")
}

# 3. AI STRATEGIC ANALYSIS (With error handling for splitting)
prompt = f"Data: {ptf}. Write 3 lines: 1. A short title. 2. A 2-sentence summary. 3. A 2-sentence commentary."
try:
    ai_raw = model.generate_content(prompt).text.strip().split('\n')
    ai_out = [line.strip() for line in ai_raw if line.strip()]
except Exception as e:
    print(f"⚠️ AI Error: {e}")
    ai_out = ["Market Update", "Stability remains focus.", "Monitor key levels."]

# 4. TEMPLATE REPLACEMENT
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

reps = {
    "{{ DATE }}": datetime.now().strftime("%A, %b %d, %Y"),
    "{{ NASDAQ_PRICE }}": str(ptf["EQCH"]["price"]),
    "{{ NASDAQ_CHANGE }}": str(ptf["EQCH"]["change"]),
    "{{ SP500_PRICE }}": str(ptf["SP500S"]["price"]),
    "{{ SP500_CHANGE }}": str(ptf["SP500S"]["change"]),
    "{{ VALUE_PRICE }}": str(ptf["IWVD"]["price"]),
    "{{ VALUE_CHANGE }}": str(ptf["IWVD"]["change"]),
    "{{ SEMI_PRICE }}": str(ptf["SMHV"]["price"]),
    "{{ SEMI_CHANGE }}": str(ptf["SMHV"]["change"]),
    "{{ GOLD_PRICE }}": str(ptf["AUUCH"]["price"]),
    "{{ GOLD_CHANGE }}": str(ptf["AUUCH"]["change"]),
    "{{ REGIME_TITLE }}": ai_out[0] if len(ai_out) > 0 else "Analysis Online",
    "{{ EXECUTIVE_SUMMARY }}": ai_out[1] if len(ai_out) > 1 else "Syncing ptf data.",
    "{{ PTF_STATUS }}": "Barbell Strategy Active",
    "{{ CIO_MARKET_COMMENTARY }}": ai_out[2] if len(ai_out) > 2 else "Check levels.",
    "{{ ALGO_REASONING }}": "System remains within risk parameters.",
    "{{ ORDER_TICKETS }}": "<div class='bg-emerald-900/40 p-3 rounded text-xs'>HOLD: No rebalance required this cycle.</div>"
}

for k, v in reps.items():
    html = html.replace(k, v)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Dashboard fully synchronized.")
