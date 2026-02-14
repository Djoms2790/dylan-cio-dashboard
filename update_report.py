import os
import yfinance as yf
import google.generativeai as genai
import json
from datetime import datetime

GEMINI_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_KEY: exit(1)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# TICKER MAP (Corrected)
tickers = {
    "EQCH": {"sym": "EQCH.SW", "name": "Nasdaq 100", "color": "#ef4444"},
    "SP500S": {"sym": "SP500S.SW", "name": "S&P 500", "color": "#f87171"},
    "IWVL": {"sym": "IWVL.L", "name": "World Value", "color": "#10b981"}, 
    "SMHV": {"sym": "SMHV.SW", "name": "Semiconductors", "color": "#fbbf24"},
    "AUCHAH": {"sym": "AUCHAH.SW", "name": "Gold Hedged", "color": "#f59e0b"},
    "USDCHF": {"sym": "CHF=X", "name": "USD/CHF"},
    "VIX": {"sym": "^VIX", "name": "VIX"},
    "RATES": {"sym": "^IRX", "name": "Fed Rate (Proxy)"}
}

def get_data(sym):
    try:
        t = yf.Ticker(sym)
        hist = t.history(period="1y")
        if hist.empty: return {k: 0.0 for k in ["price", "1w", "ytd", "1y"]}
        
        curr = hist['Close'].iloc[-1]
        
        # 1 Week
        try: p1w = hist['Close'].iloc[-6]; c1w = ((curr-p1w)/p1w)*100
        except: c1w = 0.0
        
        # YTD
        ytd_start = hist[hist.index.year == datetime.now().year]['Close'].iloc[0]
        cytd = ((curr-ytd_start)/ytd_start)*100
        
        # 1 Year
        p1y = hist['Close'].iloc[0]
        c1y = ((curr-p1y)/p1y)*100
        
        return {"price": round(curr, 2), "1w": round(c1w, 2), "ytd": round(cytd, 2), "1y": round(c1y, 2)}
    except: return {k: 0.0 for k in ["price", "1w", "ytd", "1y"]}

market = {k: get_data(v["sym"]) for k, v in tickers.items()}

# AI PROMPT
prompt = f"""
Act as Dylan CIO. Market Data: {market}.
Construct a JSON object exactly like this:
{{
  "meta": {{ "regime": "Title", "date": "Date", "summary": "Summary", "status": "Defensive", "reasoning": "Reasoning" }},
  "algo": {{ "trend": "BULLISH" }},
  "macro": [
    {{ "name": "US CPI", "value": "3.1%", "trend": "Stable", "impact": "Neutral", "desc": "Latest print." }},
    {{ "name": "USD/CHF", "value": "{market['USDCHF']['price']}", "trend": "Live", "impact": "Neutral", "desc": "FX Rate." }},
    {{ "name": "Fed Rate", "value": "{market['RATES']['price']}%", "trend": "High", "impact": "Caution", "desc": "13-Wk T-Bill." }},
    {{ "name": "VIX", "value": "{market['VIX']['price']}", "trend": "Volatile", "impact": "Caution", "desc": "Fear Index." }},
    {{ "name": "Sahm Rule", "value": "0.40%", "trend": "Safe", "impact": "Safe", "desc": "Recession indicator." }}
  ],
  "performance": {{ "commentary": "Short market analysis." }},
  "breakers": [
    {{ "name": "Sahm Rule", "status": "SAFE", "level": "0.40%", "color": "text-emerald-500", "dot": "bg-emerald-500" }},
    {{ "name": "VIX", "status": "CAUTION", "level": "{market['VIX']['price']}", "color": "text-yellow-500", "dot": "bg-yellow-500" }},
    {{ "name": "FX Floor", "status": "SAFE", "level": "{market['USDCHF']['price']}", "color": "text-emerald-500", "dot": "bg-emerald-500" }}
  ],
  "orders": [
    {{ "action": "HOLD", "asset": "Nasdaq 100", "shares": "0", "reason": "Stable." }}
  ]
}}
"""

try:
    raw = model.generate_content(prompt).text
    json_str = raw[raw.find('{'):raw.rfind('}')+1]
    final_json = json.loads(json_str)
except:
    final_json = {"meta": {"regime": "Update Failed"}, "assets": []} # Fallback

# Merge Python Data into AI JSON
final_json["assets"] = []
for k in ["EQCH", "SP500S", "IWVL", "SMHV", "AUCHAH"]:
    final_json["assets"].append({
        "id": k, "name": tickers[k]["name"], "color": tickers[k]["color"],
        "price": market[k]["price"], "change_1w": market[k]["1w"],
        "change_ytd": market[k]["ytd"], "change_1y": market[k]["1y"]
    })

# WRITE FILE
with open('index.html', 'r', encoding='utf-8') as f: html = f.read()
html = html.replace("{{ REPORT_DATA_JSON }}", json.dumps(final_json))
with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
