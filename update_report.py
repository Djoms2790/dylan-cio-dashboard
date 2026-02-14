import os
import requests
import google.generativeai as genai

# 1. SETUP KEYS (Retrieved from GitHub Secrets)
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_market_data(symbol):
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
    r = requests.get(url).json()
    quote = r.get("Global Quote", {})
    return {
        "price": float(quote.get("05. price", 0)),
        "change": float(quote.get("10. change percent", "0").strip('%'))
    }

# 2. DATA SWEEP
# Note: For free Alpha Vantage, we track the US equivalents (QQQ, SPY, IVW, SOXX, GLD)
nasdaq = get_market_data("QQQ")
sp500 = get_market_data("SPY")
value = get_market_data("IVW")
semis = get_market_data("SOXX")
gold = get_market_data("GLD")

# 3. ASK DYLAN CIO FOR ANALYSIS
prompt = f"""
You are Dylan CIO. Based on these 1-week changes:
Nasdaq: {nasdaq['change']}%
S&P 500: {sp500['change']}%
World Value: {value['change']}%
Semis: {semis['change']}%
Gold: {gold['change']}%

Write a brief, professional CIO report. 
- A 1-sentence 'REGIME_TITLE' (e.g. 'Tech Pullback' or 'Bull Market Charging')
- A 2-sentence 'EXECUTIVE_SUMMARY'
- A 2-sentence 'CIO_MARKET_COMMENTARY'
- Actionable 'ORDER_TICKETS' in HTML format (e.g. <div>...</div>)
- A short 'ALGO_REASONING' for the orders.
Return ONLY valid Python-style dictionary format.
"""

response = model.generate_content(prompt)
# (Simplified for this example: In a real script, you'd parse this response carefully)
analysis = response.text 

# 4. UPDATE THE HTML FILE
with open('index.html', 'r') as f:
    html = f.read()

# Finding and replacing placeholders
replacements = {
    "{{ NASDAQ_CHANGE }}": str(nasdaq['change']),
    "{{ SP500_CHANGE }}": str(sp500['change']),
    "{{ VALUE_CHANGE }}": str(value['change']),
    "{{ SEMI_CHANGE }}": str(semis['change']),
    "{{ GOLD_CHANGE }}": str(gold['change']),
    "{{ DATE }}": "Monday Morning Update",
    "{{ SYNC_TIME }}": "Just Now",
}

for key, value in replacements.items():
    html = html.replace(key, value)

with open('index.html', 'w') as f:
    f.write(html)

print("Report updated successfully.")
