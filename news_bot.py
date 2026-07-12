import requests
import time
import os
from textblob import TextBlob
from datetime import datetime

# =========================================================
# CONFIG (GitHub Secrets)
# =========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# =========================================================
# TICKERS
# =========================================================

TICKERS = [
    "SPY",
    "SPYM",
    "QQQ",
    "^VIX",
    "HIMS",
    "SBET",
    "SOFI",
    "XBI",
    "XLK",
    "XLE",
    "XLF",
    "XLY",
    "XLI",
    "XLV",
    "XLP",
]

# =========================================================
# DEDUPLICATION
# =========================================================

SEEN_URLS = set()

# =========================================================
# KEYWORDS
# =========================================================

KEYWORDS_INCLUDE = [
    "earnings",
    "guidance",
    "forecast",
    "outlook",
    "downgrade",
    "upgrade",
    "beats",
    "miss",
    "inflows",
    "outflows",
    "etf",
    "rebalance",
    "rebalancing",
    "index",
    "holdings",
    "allocation",
    "merger",
    "acquisition",
    "buyout",
    "deal",
    "partnership",
    "regulation",
    "ban",
    "tariff",
    "sanctions",
    "stimulus",
]

MACRO_KEYWORDS = [
    "federal reserve",
    "fed",
    "interest rate",
    "rate cut",
    "rate hike",
    "inflation",
    "cpi",
    "ppi",
    "jobs report",
    "unemployment",
    "gdp",
    "treasury yield",
    "bond yields",
    "liquidity",
    "stock market",
    "markets plunge",
    "markets rally",
    "dow",
    "s&p 500",
    "nasdaq",
    "spy",
    "qqq",
    "volatility",
    "vix",
    "selloff",
    "rally",
    "bitcoin",
    "btc",
    "ethereum",
    "eth",
    "crypto",
    "crypto market",
    "etf inflows",
    "crypto regulation",
    "war",
    "iran",
    "china",
    "russia",
    "ukraine",
    "conflict",
    "oil prices",
    "sec",
    "policy change",
    "rule change",
    "etf approval",
    "lawsuit",
    "settlement",
    "court",
    "judge",
    "supreme court",
    "trade talks",
    "trade deal",
    "negotiations",
    "diplomacy",
    "white house",
    "treasury",
    "commerce department",
    "recession",
    "consumer spending",
    "retail sales",
    "manufacturing",
    "opec",
    "middle east",
    "israel",
    "taiwan",
    "shipping",
    "supply chain",
    "banking crisis",
    "debt ceiling",
    "government shutdown",
]

# =========================================================
# TELEGRAM
# =========================================================

def send_telegram_message(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload, timeout=10)

    except Exception as e:
        print(f"Telegram error: {e}")

# =========================================================
# FETCH TICKER NEWS
# =========================================================

def fetch_company_news(ticker):

    now = int(time.time())
    from_time = now - (60 * 150)

    from_date = time.strftime('%Y-%m-%d', time.gmtime(from_time))
    to_date = time.strftime('%Y-%m-%d', time.gmtime(now))

    url = (
        f"https://finnhub.io/api/v1/company-news"
        f"?symbol={ticker}"
        f"&from={from_date}"
        f"&to={to_date}"
        f"&token={FINNHUB_API_KEY}"
    )

    try:

        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return []

        data = r.json()

        filtered = [
            article for article in data
            if article.get("datetime", 0) >= from_time
        ]

        return filtered

    except Exception as e:

        print(f"Company news error ({ticker}): {e}")
        return []

# =========================================================
# FETCH GENERAL MACRO NEWS
# =========================================================

def fetch_general_news():

    url = (
        f"https://finnhub.io/api/v1/news"
        f"?category=general"
        f"&token={FINNHUB_API_KEY}"
    )

    try:

        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return []

        data = r.json()

        now = int(time.time())
        from_time = now - (60 * 150)

        filtered = [
            article for article in data
            if article.get("datetime", 0) >= from_time
        ]

        return filtered

    except Exception as e:

        print(f"General news error: {e}")
        return []

# =========================================================
# SENTIMENT
# =========================================================

def sentiment(text):

    polarity = TextBlob(text).sentiment.polarity

    if polarity > 0.05:
        return "📈 BULLISH"

    elif polarity < -0.05:
        return "📉 BEARISH"

    else:
        return "⚪️ NEUTRAL"

# =========================================================
# RELEVANCE FILTER
# =========================================================

def is_relevant(article):

    text = (
        article.get("headline", "") +
        " " +
        article.get("summary", "")
    ).lower()

    return (
        any(k in text for k in KEYWORDS_INCLUDE)
        or
        any(k in text for k in MACRO_KEYWORDS)
    )

# =========================================================
# DUPLICATE FILTER
# =========================================================

def already_seen(article):

    url = article.get("url", "")

    if not url:
        return True

    if url in SEEN_URLS:
        return True

    SEEN_URLS.add(url)

    return False

# =========================================================
# FORMAT MESSAGE
# =========================================================

def format_message(ticker, article):

    head = article.get("headline", "")

    summary_raw = article.get("summary", "")

    if len(summary_raw) > 300:
        summ = summary_raw[:300] + "..."
    else:
        summ = summary_raw

    url = article.get("url", "")
    src = article.get("source", "")

    ts = time.strftime(
        '%Y-%m-%d %H:%M UTC',
        time.gmtime(article.get("datetime", 0))
    )

    text = (head + " " + summ).lower()

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

# =========================================================
# PROCESS ARTICLES
# =========================================================

def process_articles(ticker, articles):

    sent_count = 0

    for article in articles:

        if already_seen(article):
            continue

        if not is_relevant(article):
            continue

        message = format_message(ticker, article)

        send_telegram_message(message)

        sent_count += 1

        time.sleep(1)

    return sent_count

# =========================================================
# MAIN BOT LOOP
# =========================================================

def run_bot():

    print("Bot running...")

    # =====================================================
    # GENERAL MACRO NEWS
    # =====================================================

    print("Scanning general macro news...")

    general_news = fetch_general_news()

    macro_sent = process_articles("MACRO", general_news)

    print(f"Macro articles sent: {macro_sent}")

    # =====================================================
    # TICKER NEWS
    # =====================================================

    total_sent = 0

    for ticker in TICKERS:

        news = fetch_company_news(ticker)

        print(f"{ticker}: {len(news)} articles fetched")

        sent = process_articles(ticker, news)

        total_sent += sent

        time.sleep(1)

    print(f"Ticker articles sent: {total_sent}")

    print("Run complete.")

# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    run_bot()
