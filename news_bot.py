import requests
import json
import time
import os
from textblob import TextBlob


# -----------------------------
# CONFIG (from GitHub Secrets)
# -----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

TICKERS = ["SPY", "SPYM", "VIX", "HIMS", "HOOD", "SBET", "PINS", "SOFI", "IREN"]

# -----------------------------
# TICKER-SPECIFIC KEYWORDS
# -----------------------------
KEYWORDS_INCLUDE = [
    "earnings","guidance","forecast","outlook","downgrade","upgrade","beats","miss",
    "inflows","outflows","etf","rebalance","rebalancing","index","holdings","allocation",
    "merger","acquisition","buyout","deal","partnership",
    "regulation","ban","tariff","sanctions","stimulus"
]

# -----------------------------
# MACRO / MARKET KEYWORDS
# -----------------------------
MACRO_KEYWORDS = [
    # Fed / Economy
    "federal reserve","fed","interest rate","rate cut","rate hike",
    "inflation","cpi","ppi","jobs report","unemployment","gdp",
    "treasury yield","bond yields","liquidity",

    # Market moves
    "stock market","markets plunge","markets rally",
    "dow","s&p 500","nasdaq","spy","qqq",
    "volatility","vix","selloff","rally",

    # Crypto
    "bitcoin","btc","ethereum","eth","crypto",
    "crypto market","etf inflows","crypto regulation",

    # Geopolitics
    "war","iran","china","russia","ukraine",
    "conflict","oil prices",

    # Regulation
    "sec","policy change","rule change","etf approval"
]

# -----------------------------
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)

# -----------------------------
def fetch_news(ticker):
    now = int(time.time())

    # 🔥 45 MIN LOOKBACK (prevents missing news if GitHub delays)
    from_time = now - (60 * 120)

    from_date = time.strftime('%Y-%m-%d', time.gmtime(from_time))
    to_date = time.strftime('%Y-%m-%d', time.gmtime(now))

    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"

    try:
        r = requests.get(url)
        data = r.json() if r.status_code == 200 else []

        # 🔥 CRITICAL FILTER (prevents duplicates)
        filtered = [
            article for article in data
            if article.get("datetime", 0) >= from_time
        ]

        return filtered

    except:
        return []

# -----------------------------
def sentiment(text):
    p = TextBlob(text).sentiment.polarity
    if p > 0.05:
        return "📈 BULLISH"
    elif p < -0.05:
        return "📉 BEARISH"
    else:
        return "⚪️ NEUTRAL"

# -----------------------------
def is_relevant(article):
    text = (article.get("headline","") + " " + article.get("summary","")).lower()

    ticker_match = any(k in text for k in KEYWORDS_INCLUDE)
    macro_match = any(k in text for k in MACRO_KEYWORDS)

    return ticker_match or macro_match

# -----------------------------
def format_message(ticker, article):
    head = article.get("headline","")
    summ = article.get("summary","")[:300] + "..."
    url = article.get("url","")
    src = article.get("source","")
    ts = time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(article.get("datetime",0)))

    text = (head + " " + summ).lower()

    # Detect macro vs ticker
    if any(k in text for k in MACRO_KEYWORDS):
        header = "🌍 MACRO EVENT"
    else:
        header = f"📊 {ticker}"

    s = sentiment(head + summ)

    return f"""{header} | {s}

📰 {head}

🧾 {summ}

🕒 {ts}
🌐 {src}

🔗 {url}
"""

# -----------------------------
def run_bot():
    print("Bot running...")

    for ticker in TICKERS:
        news = fetch_news(ticker)
        print(f"{ticker}: {len(news)} articles fetched")

        for article in news:
            if is_relevant(article):
                message = format_message(ticker, article)
                send_telegram_message(message)

    print("Run complete.")

# -----------------------------
if __name__ == "__main__":
    run_bot()
