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

# 2. TICKER MAP
tickers = {
    "EQCH": {"sym": "EQCH.SW", "name": "Invesco Nasdaq 100", "color": "#ef4444"},
    "SP500S": {"sym": "SP500S.SW", "name": "UBS S&P 500", "color": "#f87171"},
    "IWVL": {"sym": "IWVL.L", "name": "iShares World Value", "color": "#10b981"},
    "SMHV": {"sym": "SMHV.SW", "name": "VanEck Semis", "color": "#fbbf24"},
    "AUCHAH": {"sym": "AUCHAH.SW", "name": "UBS Gold Hedged", "color": "#f59e0b"},
    "USDCHF": {"sym": "CHF=X", "name": "USD/CHF"},
    "VIX": {"sym": "^VIX", "name": "VIX"},
    "RATES": {"sym": "^IRX", "name": "Fed Rate"}
}

def get_data(sym):
    try:
        t = yf.Ticker(sym)
        hist = t.history(period="1y")
        if hist.empty: return {"price": 0.0, "1w": 0.0, "ytd": 0.0, "1y": 0.0}
        
        curr = hist['Close'].iloc[-1]
        # 1 Week (5 days ago)
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

print("Fetching Market Data...")
market = {k: get_data(v["sym"]) for k, v in tickers.items()}

# 3. CONSTRUCT ROBUST DATA OBJECT
# This structure exists BEFORE calling AI, guaranteeing the site works even if AI fails.
final_data = {
    "meta": {
        "regime": "Market Data Synced",
        "date": datetime.now().strftime('%A, %b %d, %Y'),
        "summary": "Live prices updated from SIX Swiss Exchange.",
        "status": "Active",
        "reasoning": "Monitoring volatility levels."
    },
    "algo": {"trend": "NEUTRAL"},
    "macro": [
        {"name": "USD/CHF", "value": f"{market['USDCHF']['price']}", "trend": "Live", "impact": "Neutral", "desc": "Real-time FX."},
        {"name": "VIX", "value": f"{market['VIX']['price']}", "trend": "Live", "impact": "Caution", "desc": "Volatility Index."},
        {"name": "Fed Rate", "value": f"{market['RATES']['price']}%", "trend": "High", "impact": "Neutral", "desc": "13-Wk T-Bill."}
    ],
    "assets": [],
    "performance": {"commentary": "Click bars to view details."},
    "breakers": [
        {"name": "VIX", "status": "SAFE" if market['VIX']['price'] < 20 else "CAUTION", "level": f"{market['VIX']['price']}", "color": "text-emerald-500", "dot": "bg-emerald-500"},
        {"name": "FX Floor", "status": "SAFE", "level": f"{market['USDCHF']['price']}", "color": "text-emerald-500", "dot": "bg-emerald-500"}
    ],
    "orders": [
        {"action": "HOLD", "asset": "Portfolio", "shares": "-", "reason": "Standard monitoring."}
    ]
}

# Populate Assets immediately with Real Data
for k in ["EQCH", "SP500S", "IWVL", "SMHV", "AUCHAH"]:
    final_data["assets"].append({
        "id": k,
        "name": tickers[k]["name"],
        "color": tickers[k]["color"],
        "price": market[k]["price"],
        "change_1w": market[k]["1w"],
        "change_ytd": market[k]["ytd"],
        "change_1y": market[k]["1y"],
        "commentary": f"Weekly change: {market[k]['1w']}%"
    })

# 4. AI ENRICHMENT (Try to make it smarter, but don't break it)
prompt = f"""
Act as Dylan CIO. Market Data: {market}.
Return ONLY a valid JSON object with these keys: "regime_title", "summary", "status", "algo_trend", "asset_commentary" (object with keys EQCH, SP500S etc).
"""
try:
    response = model.generate_content(prompt)
    text = response.text
    # Extract JSON using Regex to avoid Markdown errors
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        ai_json = json.loads(match.group())
        # Update Master Data safely
        final_data["meta"]["regime"] = ai_json.get("regime_title", final_data["meta"]["regime"])
        final_data["meta"]["summary"] = ai_json.get("summary", final_data["meta"]["summary"])
        final_data["meta"]["status"] = ai_json.get("status", final_data["meta"]["status"])
        final_data["algo"]["trend"] = ai_json.get("algo_trend", "NEUTRAL")
        
        # Update Asset Commentary
        comments = ai_json.get("asset_commentary", {})
        for asset in final_data["assets"]:
            if asset["id"] in comments:
                asset["commentary"] = comments[asset["id"]]
except Exception as e:
    print(f"⚠️ AI Enrichment Failed: {e}. Using Standard Data.")

# 5. WRITE HTML
json_str = json.dumps(final_data)
with open('index.html', 'r', encoding='utf-8') as f: html = f.read()
html = html.replace("{{ REPORT_DATA_JSON }}", json_str)
with open('index.html', 'w', encoding='utf-8') as f: f.write(html)

print("✅ Dashboard Updated Successfully.")
