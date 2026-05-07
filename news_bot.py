import requests
import time
import os
from textblob import TextBlob
from datetime import datetime

# -----------------------------
# CONFIG (GitHub Secrets)
# -----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

TICKERS = [
    "SPY",
    "SPYM",
    "QQQ",
    "^VIX",
    "HIMS",
    "HOOD",
    "SBET",
    "SOFI",
    "IREN"
]

# -----------------------------
# TICKER NEWS KEYWORDS
# -----------------------------
KEYWORDS_INCLUDE = [
    "earnings", "guidance", "forecast", "outlook",
    "downgrade", "upgrade", "beats", "miss",
    "inflows", "outflows", "etf",
    "rebalance", "rebalancing",
    "index", "holdings", "allocation",
    "merger", "acquisition", "buyout",
    "deal", "partnership",
    "regulation", "ban",
    "tariff", "sanctions", "stimulus"
]

# -----------------------------
# MACRO / MARKET KEYWORDS
# -----------------------------
MACRO_KEYWORDS = [
    "federal reserve", "fed",
    "interest rate", "rate cut", "rate hike",
    "inflation", "cpi", "ppi",
    "jobs report", "unemployment", "gdp",
    "treasury yield", "bond yields",
    "liquidity",

    "stock market", "markets plunge",
    "markets rally", "dow",
    "s&p 500", "nasdaq",
    "spy", "qqq",
    "volatility", "vix",
    "selloff", "rally",

    "bitcoin", "btc",
    "ethereum", "eth",
    "crypto", "crypto market",
    "etf inflows", "crypto regulation",

    "war", "iran",
    "china", "russia",
    "ukraine", "conflict",
    "oil prices",

    "sec", "policy change",
    "rule change", "etf approval"
]

# -----------------------------
# TELEGRAM
# -----------------------------
def send_telegram_message(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    requests.post(url, data=payload)

# -----------------------------
# FETCH NEWS
# -----------------------------
def fetch_news(ticker):

    now = int(time.time())

    # 🔥 2:30 minute lookback
    from_time = now - (60 * 150)

    from_date = time.strftime(
        '%Y-%m-%d',
        time.gmtime(from_time)
    )

    to_date = time.strftime(
        '%Y-%m-%d',
        time.gmtime(now)
    )

    url = (
        f"https://finnhub.io/api/v1/company-news"
        f"?symbol={ticker}"
        f"&from={from_date}"
        f"&to={to_date}"
        f"&token={FINNHUB_API_KEY}"
    )

    try:

        r = requests.get(url)

        data = r.json() if r.status_code == 200 else []

        # 🔥 Prevent duplicates
        filtered = [
            article for article in data
            if article.get("datetime", 0) >= from_time
        ]

        return filtered

    except:
        return []

# -----------------------------
# FETCH PRICE
# -----------------------------
def fetch_price(ticker):

    url = (
        f"https://finnhub.io/api/v1/quote"
        f"?symbol={ticker}"
        f"&token={FINNHUB_API_KEY}"
    )

    try:

        r = requests.get(url)

        data = r.json()

        return {
            "current": data.get("c"),
            "previous_close": data.get("pc")
        }

    except:
        return None

# -----------------------------
# MARKET REPORT
# -----------------------------
def send_market_report(report_type):

    message = f"📊 {report_type} MARKET REPORT\n\n"

    for ticker in TICKERS:

        price_data = fetch_price(ticker)

        if price_data:

            current = price_data["current"]
            previous = price_data["previous_close"]

            if current and previous:

                change_pct = (
                    ((current - previous) / previous) * 100
                )

                if change_pct > 0:
                    emoji = "📈"
                elif change_pct < 0:
                    emoji = "📉"
                else:
                    emoji = "⚪️"

                message += (
                    f"{emoji} {ticker}\n"
                    f"Price: ${current:.2f}\n"
                    f"Change: {change_pct:.2f}%\n\n"
                )

    send_telegram_message(message)

# -----------------------------
# SENTIMENT
# -----------------------------
def sentiment(text):

    polarity = TextBlob(text).sentiment.polarity

    if polarity > 0.05:
        return "📈 BULLISH"

    elif polarity < -0.05:
        return "📉 BEARISH"

    else:
        return "⚪️ NEUTRAL"

# -----------------------------
# RELEVANCE FILTER
# -----------------------------
def is_relevant(article):

    text = (
        article.get("headline", "") +
        " " +
        article.get("summary", "")
    ).lower()

    ticker_match = any(
        k in text for k in KEYWORDS_INCLUDE
    )

    macro_match = any(
        k in text for k in MACRO_KEYWORDS
    )

    return ticker_match or macro_match

# -----------------------------
# FORMAT MESSAGE
# -----------------------------
def format_message(ticker, article):

    head = article.get("headline", "")

    summ = (
        article.get("summary", "")[:300]
        + "..."
    )

    url = article.get("url", "")

    src = article.get("source", "")

    ts = time.strftime(
        '%Y-%m-%d %H:%M UTC',
        time.gmtime(article.get("datetime", 0))
    )

    text = (head + " " + summ).lower()

    # 🌍 Macro vs ticker
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
# MAIN BOT LOOP
# -----------------------------
def run_bot():

    print("Bot running...")

    now = datetime.utcnow()

    hour = now.hour
    minute = now.minute

    # ==========================================
# 🌅 PREMARKET REPORT
# Runs anytime between:
# 9:00 AM EST → 10:59 AM EST
# ==========================================
if hour == 13 or hour == 14:

    send_market_report("PREMARKET")

# ==========================================
# 🌙 AFTER CLOSE REPORT
# Runs anytime between:
# 4:15 PM EST → 5:59 PM EST
# ==========================================
elif hour == 20 or hour == 21:

    send_market_report("AFTER CLOSE")

    # ==========================================
    # 📰 NEWS SCANNING
    # ==========================================
    for ticker in TICKERS:

        news = fetch_news(ticker)

        print(
            f"{ticker}: "
            f"{len(news)} articles fetched"
        )

        for article in news:

            if is_relevant(article):

                message = format_message(
                    ticker,
                    article
                )

                send_telegram_message(message)

    print("Run complete.")

# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    run_bot()
