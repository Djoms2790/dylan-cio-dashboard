import os
import requests
import google.generativeai as genai
from datetime import datetime

ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_market_data(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
        r = requests.get(url).json()
        quote = r.get("Global Quote", {})
        return {"price": float(quote.get("05. price", 0)), "change": float(quote.get("10. change percent", "0.0%").strip('%'))}
    except:
        return {"price": 0, "change": 0.0}

nasdaq = get_market_data("QQQ")
sp500 = get_market_data("SPY")
value = get_market_data("IVW")
semis = get_market_data("SOXX")
gold = get_market_data("GLD")

prompt = f"Nasdaq: {nasdaq['change']}%, SP500: {sp500['change']}%. Write a 1-sentence REGIME_TITLE, 2-sentence EXECUTIVE_SUMMARY, and 2-sentence CIO_MARKET_COMMENTARY."
ai = model.generate_content(prompt).text.split('\n')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

replacements = {
    "{{ NASDAQ_CHANGE }}": str(nasdaq['change']),
    "{{ SP500_CHANGE }}": str(sp500['change']),
    "{{ VALUE_CHANGE }}": str(value['change']),
    "{{ SEMI_CHANGE }}": str(semis['change']),
    "{{ GOLD_CHANGE }}": str(gold['change']),
    "{{ DATE }}": datetime.now().strftime("%A, %b %d, %Y"),
    "{{ REGIME_TITLE }}": ai[0] if len(ai) > 0 else "Market Update",
    "{{ EXECUTIVE_SUMMARY }}": ai[1] if len(ai) > 1 else "Analysis pending.",
    "{{ CIO_MARKET_COMMENTARY }}": ai[2] if len(ai) > 2 else "Check back shortly."
}

for key, val in replacements.items():
    html = html.replace(key, val)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
