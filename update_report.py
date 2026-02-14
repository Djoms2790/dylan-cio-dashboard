import os
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

# 1. AUTH
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_KEY:
    print("❌ API Key Missing")
    exit(1)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. TICKER MAPPING (Yahoo Finance Symbols)
# Ensure these match the markets you want. 
# EQCH.SW = Invesco Nasdaq (Swiss), SP500S.SW = UBS S&P (Swiss)
tickers = {
    "EQCH": "EQCH.SW",
    "SP500S": "SP500S.SW", 
    "IWVD": "IWVD.L",    # iShares World Value (London) - Common proxy
    "SMHV": "SMHV.SW",   
    "AUUCH": "AUUCH.SW" 
}

def get_data(symbol):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if hist.empty: return {"price": 0.0, "change": 0.0}
        
        curr = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[0]
        change = ((curr - prev) / prev) * 100
        return {"price": round(curr, 2), "change": round(change, 2)}
    except:
        return {"price": 0.0, "change": 0.0}

# 3. FETCH DATA
ptf = {k: get_data(v) for k, v in tickers.items()}

# 4. AI ANALYSIS
prompt = f"""
Act as Dylan CIO. Portfolio Data: {ptf}.
Write 5 distinct parts separated by '|':
1. Short Title (e.g. Bullish Trend)
2. Executive Summary (2 sentences)
3. Status (e.g. Defensive)
4. Market Commentary (2 sentences)
5. Algo Logic (1 sentence)
"""
try:
    ai_raw = model.generate_content(prompt).text.strip().split('|')
    ai_out = [x.strip() for x in ai_raw]
    # Fallback if split fails
    if len(ai_out) < 5: ai_out = ["Update", "Data synced.", "Neutral", "Check levels.", "Hold."]
except:
    ai_out = ["System Update", "Prices refreshed.", "Active", "Monitoring volatility.", "Standard rebalance check."]

# 5. UPDATE HTML
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
    "{{ REGIME_TITLE }}": ai_out[0],
    "{{ EXECUTIVE_SUMMARY }}": ai_out[1],
    "{{ PTF_STATUS }}": ai_out[2],
    "{{ CIO_MARKET_COMMENTARY }}": ai_out[3],
    "{{ ALGO_REASONING }}": ai_out[4]
}

for k, v in reps.items():
    html = html.replace(k, v)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Update Success")
