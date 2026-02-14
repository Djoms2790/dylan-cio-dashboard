import os
import yfinance as yf
import google.generativeai as genai
import json
from datetime import datetime

# 1. SETUP
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_KEY:
    print("❌ API Key Missing")
    exit(1)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. TICKERS
# Mapping user IDs to Yahoo Finance Tickers
# NOTE: 'EQCH.SW' etc are the correct Swiss tickers.
tickers = {
    "EQCH": {"sym": "EQCH.SW", "name": "Invesco Nasdaq 100", "color": "#ef4444"},
    "SP500S": {"sym": "SP500S.SW", "name": "UBS S&P 500", "color": "#f87171"},
    "IWVD": {"sym": "IWVD.L", "name": "iShares World Value", "color": "#10b981"}, # London proxy for Value
    "SMHV": {"sym": "SMHV.SW", "name": "VanEck Semis", "color": "#fbbf24"},
    "AUUCH": {"sym": "AUUCH.SW", "name": "UBS Gold", "color": "#f59e0b"},
    "USDCHF": {"sym": "CHF=X", "name": "USD/CHF"},
    "VIX": {"sym": "^VIX", "name": "VIX"}
}

def get_data(ticker_info):
    try:
        t = yf.Ticker(ticker_info["sym"])
        hist = t.history(period="ytd") # Get YTD data
        if hist.empty: return {"price": 0.0, "change_1w": 0.0, "change_ytd": 0.0}
        
        curr = hist['Close'].iloc[-1]
        
        # 1 Week Change (5 trading days ago)
        try:
            prev_1w = hist['Close'].iloc[-6]
            change_1w = ((curr - prev_1w) / prev_1w) * 100
        except:
            change_1w = 0.0

        # YTD Change (First day of year)
        start_ytd = hist['Close'].iloc[0]
        change_ytd = ((curr - start_ytd) / start_ytd) * 100

        return {
            "price": round(curr, 2),
            "change_1w": round(change_1w, 2),
            "change_ytd": round(change_ytd, 2)
        }
    except:
        return {"price": 0.0, "change_1w": 0.0, "change_ytd": 0.0}

# 3. FETCH ALL DATA
market_data = {k: get_data(v) for k, v in tickers.items()}

# 4. AI ANALYSIS (Constructing the Report)
# We ask Gemini to populate the subjective parts of the JSON
prompt = f"""
You are Dylan CIO (Geneva). Market Data: {market_data}.
Generate a valid JSON string matching this structure exactly (no markdown):
{{
  "meta": {{
    "regime": "Short phrase (e.g. Stagflation Risk)",
    "date": "{datetime.now().strftime('%A, %b %d, %Y')}",
    "summary": "2 sentences executive summary.",
    "status": "Defensive / Aggressive / Neutral",
    "reasoning": "1 sentence on rebalancing logic."
  }},
  "algo": {{ "trend": "BULLISH" or "BEARISH" }},
  "macro": [
    {{ "name": "US CPI", "value": "2.4%", "trend": "Cooling", "impact": "Bullish", "desc": "Fed room to cut." }},
    {{ "name": "Fed Rate", "value": "3.75%", "trend": "Pause", "impact": "Neutral", "desc": "Cuts priced in." }}
  ],
  "assets_commentary": {{
    "EQCH": "Short comment on Nasdaq.",
    "SP500S": "Short comment on S&P.",
    "IWVD": "Short comment on Value.",
    "SMHV": "Short comment on Semis.",
    "AUUCH": "Short comment on Gold."
  }},
  "breakers": [
    {{ "name": "Sahm Rule", "status": "SAFE", "level": "0.35%", "color": "text-emerald-500", "dot": "bg-emerald-500" }},
    {{ "name": "VIX", "status": "CAUTION", "level": "{market_data['VIX']['price']}", "color": "text-yellow-500", "dot": "bg-yellow-500" }},
    {{ "name": "FX Floor", "status": "SAFE", "level": "{market_data['USDCHF']['price']}", "color": "text-emerald-500", "dot": "bg-emerald-500" }}
  ],
  "orders": [
    {{ "action": "HOLD", "asset": "Nasdaq 100", "shares": "0", "reason": "No drift." }},
    {{ "action": "BUY", "asset": "Gold", "shares": "5", "reason": "Hedge increase." }}
  ]
}}
"""

try:
    response = model.generate_content(prompt)
    json_text = response.text.strip()
    if "```json" in json_text:
        json_text = json_text.split("```json")[1].split("```")[0]
    ai_data = json.loads(json_text)
except Exception as e:
    print(f"AI Error: {e}")
    # Fallback Data if AI fails
    ai_data = {
        "meta": {"regime": "System Update", "date": datetime.now().strftime('%A, %b %d, %Y'), "summary": "Data sync only.", "status": "Neutral", "reasoning": "Hold."},
        "algo": {"trend": "NEUTRAL"},
        "macro": [],
        "assets_commentary": {},
        "breakers": [],
        "orders": []
    }

# 5. ASSEMBLE FINAL REPORT OBJECT
# Merging Python Data (Objective) with AI Data (Subjective)
report_object = {
    "meta": ai_data.get("meta"),
    "algo": ai_data.get("algo"),
    "macro": ai_data.get("macro", []) + [
        {"name": "USD/CHF", "value": str(market_data["USDCHF"]["price"]), "trend": "Live", "impact": "Neutral", "desc": "Real-time FX."}
    ],
    "assets": [],
    "performance": {"commentary": []},
    "breakers": ai_data.get("breakers", []),
    "orders": ai_data.get("orders", [])
}

# Populate Assets List
for key in ["EQCH", "SP500S", "IWVD", "SMHV", "AUUCH"]:
    report_object["assets"].append({
        "id": key,
        "name": tickers[key]["name"],
        "price": market_data[key]["price"],
        "change": market_data[key]["change_1w"],
        "color": tickers[key]["color"],
        "commentary": ai_data.get("assets_commentary", {}).get(key, "No data.")
    })

# 6. INJECT INTO HTML
json_str = json.dumps(report_object)

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the specific placeholder {{ REPORT_DATA_JSON }}
html = html.replace("{{ REPORT_DATA_JSON }}", json_str)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Full Suite Update Complete.")
