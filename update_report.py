import os
import yfinance as yf
import google.generativeai as genai
import json
import re
from datetime import datetime

# 1. AUTH
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. CONFIGURATION & TICKERS
tickers = {
    "EQCH": {"sym": "EQCH.SW", "name": "Invesco Nasdaq 100", "color": "#ef4444"},
    "SP500S": {"sym": "SP500S.SW", "name": "UBS S&P 500", "color": "#f87171"},
    "IWVL": {"sym": "IWVL.L", "name": "iShares World Value", "color": "#10b981"},
    "SMHV": {"sym": "SMHV.SW", "name": "VanEck Semis", "color": "#fbbf24"},
    "AUCHAH": {"sym": "AUCHAH.SW", "name": "UBS Gold Hedged", "color": "#f59e0b"},
    "USDCHF": {"sym": "CHF=X", "name": "USD/CHF"},
    "VIX": {"sym": "^VIX", "name": "VIX"},
    "RATES": {"sym": "^IRX", "name": "Fed Rate (Proxy)"}
}

# 3. FETCH LIVE MARKET DATA
print("Fetching Live Data...")
def get_data(sym):
    try:
        t = yf.Ticker(sym)
        hist = t.history(period="1y")
        if hist.empty: return {"price": 0.0, "1w": 0.0, "ytd": 0.0, "1y": 0.0}
        
        curr = hist['Close'].iloc[-1]
        # 1 Week (5 trading days ago)
        try: p1w = hist['Close'].iloc[-6]; c1w = ((curr-p1w)/p1w)*100
        except: c1w = 0.0
        # YTD
        ytd_start = hist[hist.index.year == datetime.now().year]['Close'].iloc[0]
        cytd = ((curr-ytd_start)/ytd_start)*100
        # 1 Year
        p1y = hist['Close'].iloc[0]
        c1y = ((curr-p1y)/p1y)*100
        
        return {"price": round(curr, 2), "1w": round(c1w, 2), "ytd": round(cytd, 2), "1y": round(c1y, 2)}
    except:
        return {"price": 0.0, "1w": 0.0, "ytd": 0.0, "1y": 0.0}

market = {k: get_data(v["sym"]) for k, v in tickers.items()}

# 4. PERSISTENT LEDGER (The "Database")
# To add past transactions, edit this list inside the Python script.
# The script will inject this list into the HTML every week.
ledger_history = [
    {"date": "2026-01-01", "type": "DEPOSIT", "asset": "CASH", "qty": "-", "price": 1.00, "total": 100000},
    {"date": "2026-01-15", "type": "BUY", "asset": "EQCH", "qty": 150, "price": 420.50, "total": 63075},
    {"date": "2026-01-15", "type": "BUY", "asset": "SP500S", "qty": 80, "price": 680.00, "total": 54400}
]

# 5. AI ANALYSIS (Dynamic CPI & Macro)
# Note: We removed the hardcoded "3.1%" for CPI. We now ask Gemini to find it.
prompt = f"""
Act as Dylan CIO. Market Data: {market}.
Generate a valid JSON object.
CRITICAL: For 'macro', use your internal knowledge to fill in the latest 'US CPI' and 'Sahm Rule' values. Do not use placeholders.
Structure:
{{
  "meta": {{ "regime": "Title", "date": "{datetime.now().strftime('%b %d, %Y')}", "summary": "Summary", "status": "Defensive", "reasoning": "Reasoning" }},
  "algo": {{ "trend": "BULLISH" }},
  "macro": [
    {{ "name": "US CPI", "value": "FILL_LATEST_VALUE", "trend": "Trend?", "impact": "Impact?", "desc": "Latest print." }},
    {{ "name": "Fed Rate", "value": "{market['RATES']['price']}%", "trend": "High", "impact": "Neutral", "desc": "13-Wk T-Bill." }},
    {{ "name": "USD/CHF", "value": "{market['USDCHF']['price']}", "trend": "Live", "impact": "Neutral", "desc": "Real-time FX." }},
    {{ "name": "VIX", "value": "{market['VIX']['price']}", "trend": "Live", "impact": "Caution", "desc": "Fear Index." }},
    {{ "name": "Sahm Rule", "value": "FILL_LATEST_VALUE", "trend": "Trend?", "impact": "Impact?", "desc": "Recession indicator." }}
  ],
  "performance": {{ "commentary": "Short analysis." }},
  "breakers": [
    {{ "name": "VIX", "status": "SAFE", "level": "{market['VIX']['price']}", "color": "text-emerald-500", "dot": "bg-emerald-500" }},
    {{ "name": "FX Floor", "status": "SAFE", "level": "{market['USDCHF']['price']}", "color": "text-emerald-500", "dot": "bg-emerald-500" }}
  ],
  "orders": [
    {{ "action": "HOLD", "asset": "Nasdaq 100", "shares": "0", "reason": "Stable." }}
  ]
}}
"""

try:
    response = model.generate_content(prompt)
    # Regex to extract JSON safely
    match = re.search(r'\{.*\}', response.text, re.DOTALL)
    ai_data = json.loads(match.group()) if match else {}
except:
    ai_data = {"meta": {"regime": "Data Sync"}, "macro": []}

# 6. MERGE DATA
final_data = {
    "meta": ai_data.get("meta"),
    "algo": ai_data.get("algo", {"trend": "NEUTRAL"}),
    "macro": ai_data.get("macro", []),
    "performance": ai_data.get("performance", {"commentary": "No commentary."}),
    "breakers": ai_data.get("breakers", []),
    "orders": ai_data.get("orders", []),
    "assets": [],
    "ledger": ledger_history # Injecting the persistent ledger
}

# Populate Assets with Live Data
for k in ["EQCH", "SP500S", "IWVL", "SMHV", "AUCHAH"]:
    final_data["assets"].append({
        "id": k,
        "name": tickers[k]["name"],
        "color": tickers[k]["color"],
        "price": market[k]["price"],
        "change_1w": market[k]["1w"],
        "change_ytd": market[k]["ytd"],
        "change_1y": market[k]["1y"]
    })

# 7. INJECT INTO HTML
json_str = json.dumps(final_data)
with open('index.html', 'r', encoding='utf-8') as f: html = f.read()

# Replace the data object
html = html.replace("{{ REPORT_DATA_JSON }}", json_str)

with open('index.html', 'w', encoding='utf-8') as f: f.write(html)

print("✅ Live Data & Persistent Ledger Updated.")
