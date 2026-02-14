import os
import requests
import google.generativeai as genai
from datetime import datetime

# 1. SETUP & KEY CHECK
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not ALPHA_VANTAGE_KEY or not GEMINI_API_KEY:
    print("❌ ERROR: API Keys missing.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_market_data(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
        r = requests.get(url).json()
        quote = r.get("Global Quote", {})
        return {"change": float(quote.get("10. change percent", "0.0%").strip('%'))}
    except:
        return {"change": 0.0}

# 2. DATA COLLECTION
nasdaq = get_market_data("QQQ")
sp500 = get_market_data("SPY")
value = get_market_data("IVW")
semis = get_market_data("SOXX")
gold = get_market_data("GLD")

# 3. AI ANALYSIS (With Safety Net)
try:
    prompt = f"Nasdaq: {nasdaq['change']}%, S&P 500: {sp500['change']}%. Write: 1. A short title. 2. A 2-sentence summary. 3. A 2-sentence market analysis."
    ai_response = model.generate_content(prompt).text.split('\n')
    # Clean up empty strings from response
    ai_response = [line for line in ai_response if line.strip()]
except:
    ai_response = ["Market Update", "Stability remains the core focus.", "Monitor key levels."]

# 4. DATA-DRIVEN REPLACEMENTS
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# We use a dictionary to safely map placeholders to values
replacements = {
    "{{ NASDAQ_CHANGE }}": str(nasdaq['change']),
    "{{ SP500_CHANGE }}": str(sp500['change']),
    "{{ VALUE_CHANGE }}": str(value['change']),
    "{{ SEMI_CHANGE }}": str(semis['change']),
    "{{ GOLD_CHANGE }}": str(gold['change']),
    "{{ DATE }}": datetime.now().strftime("%A, %b %d, %Y"),
    "{{ REGIME_TITLE }}": ai_response[0] if len(ai_response) > 0 else "Dylan CIO Report",
    "{{ EXECUTIVE_SUMMARY }}": ai_response[1] if len(ai_response) > 1 else "Market analysis ongoing.",
    "{{ CIO_MARKET_COMMENTARY }}": ai_response[2] if len(ai_response) > 2 else "Focusing on core barbell assets."
}

for key, val in replacements.items():
    html = html.replace(key, val)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Update Complete.")
