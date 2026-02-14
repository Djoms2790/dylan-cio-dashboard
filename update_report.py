import os
import requests
import google.generativeai as genai
from datetime import datetime

# RETRIEVE KEYS
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# SAFETY CHECK: Stop if keys are missing
if not ALPHA_VANTAGE_KEY or not GEMINI_API_KEY:
    print("❌ ERROR: Missing API Keys in GitHub Secrets.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_market_data(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
        r = requests.get(url).json()
        quote = r.get("Global Quote", {})
        # If API fails or limit is hit, return 0 instead of crashing
        price = float(quote.get("05. price", 0))
        change = float(quote.get("10. change percent", "0.0%").strip('%'))
        return {"price": price, "change": change}
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch {symbol}. Error: {e}")
        return {"price": 0, "change": 0.0}

# 1. DATA SWEEP
nasdaq = get_market_data("QQQ")
sp500 = get_market_data("SPY")
value = get_market_data("IVW")
semis = get_market_data("SOXX")
gold = get_market_data("GLD")

# 2. ASK GEMINI FOR THE ANALYST VIEW
prompt = f"""
You are Dylan CIO. Based on these 1-week changes:
Nasdaq: {nasdaq['change']}%, S&P 500: {sp500['change']}%, World Value: {value['change']}%, Semis: {semis['change']}%, Gold: {gold['change']}%
Write exactly 4 things:
1. REGIME_TITLE: Short title.
2. EXECUTIVE_SUMMARY: 2 concise sentences.
3. CIO_MARKET_COMMENTARY: 2 sentences.
4. ALGO_REASONING: 1 sentence on why we should hold or rebalance.
"""

try:
    response = model.generate_content(prompt)
    ai_text = response.text
except Exception as e:
    ai_text = "Analysis temporarily unavailable due to AI sync issues."
    print(f"❌ Gemini Error: {e}")

# 3. UPDATE THE HTML FILE (Strict Replace)
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

now = datetime.now().strftime("%Y-%m-%d %H:%M")
replacements = {
    "{{ NASDAQ_CHANGE }}": str(nasdaq['change']),
    "{{ SP500_CHANGE }}": str(sp500['change']),
    "{{ VALUE_CHANGE }}": str(value['change']),
    "{{ SEMI_CHANGE }}": str(semis['change']),
    "{{ GOLD_CHANGE }}": str(gold['change']),
    "{{ DATE }}": datetime.now().strftime("%A, %b %d, %Y"),
    "{{ SYNC_TIME }}": now,
    "{{ EXECUTIVE_SUMMARY }}": ai_text.split('\n')[1] if '\n' in ai_text else ai_text,
    "{{ REGIME_TITLE }}": ai_text.split('\n')[0],
}

for key, val in replacements.items():
    html = html.replace(key, val)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Deployment successful at {now}")
