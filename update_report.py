import os
import requests
import google.generativeai as genai
from datetime import datetime

# 1. AUTH
ALPHA_KEY = os.getenv('ALPHA_VANTAGE_KEY')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def fetch_data(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_KEY}"
        data = requests.get(url).json().get("Global Quote", {})
        return {
            "price": float(data.get("05. price", 0)),
            "change": float(data.get("10. change percent", "0.0%").strip('%'))
        }
    except: return {"price": 0, "change": 0}

# 2. MARKET DATA SWEEP
ptf = {
    "EQCH": fetch_data("QQQ"),
    "SP500S": fetch_data("SPY"),
    "IWVD": fetch_data("IVW"),
    "SMHV": fetch_data("SOXX"),
    "AUUCH": fetch_data("GLD")
}

# 3. AI STRATEGIC ANALYSIS
prompt = f"""
Role: Dylan CIO (Geneva).
Data: {ptf}
Task: Return exactly 5 lines of text:
Line 1: REGIME_TITLE (e.g., 'Late-Cycle Rotation')
Line 2: EXECUTIVE_SUMMARY (2 sentences)
Line 3: PTF_STATUS (e.g., 'Defensive' or 'Aggressive')
Line 4: CIO_MARKET_COMMENTARY (2 sentences)
Line 5: ALGO_REASONING (1 sentence on rebalancing)
Do not use labels like 'Line 1'. Just the text.
"""
ai_out = model.generate_content(prompt).text.strip().split('\n')
ai_out = [line.strip() for line in ai_out if line.strip()]

# 4. TEMPLATE REPLACEMENT
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

reps = {
    "{{ DATE }}": datetime.now().strftime("%b %d, %Y"),
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
    "{{ REGIME_TITLE }}": ai_out[0] if len(ai_out) > 0 else "Market Update",
    "{{ EXECUTIVE_SUMMARY }}": ai_out[1] if len(ai_out) > 1 else "Stability is key.",
    "{{ PTF_STATUS }}": ai_out[2] if len(ai_out) > 2 else "Neutral",
    "{{ CIO_MARKET_COMMENTARY }}": ai_out[3] if len(ai_out) > 3 else "Focusing on core.",
    "{{ ALGO_REASONING }}": ai_out[4] if len(ai_out) > 4 else "Maintain target weights.",
    "{{ ORDER_TICKETS }}": "<div class='bg-emerald-900/50 p-4 rounded'>BUY 5 EQCH (Rebalance)</div>"
}

for k, v in reps.items():
    html = html.replace(k, v)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("System Synchronized.")
