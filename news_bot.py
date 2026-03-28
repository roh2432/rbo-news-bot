import requests
import json
import time
import os
from textblob import TextBlob

# -----------------------------
# CONFIG (FILLED VIA SECRETS)
# -----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

TICKERS = ["SPY", "QQQ", "IWM", "IJH", "TLT", "VXUS", "XLF", "TQQQ", "UPRO",
           "HIMS", "HOOD", "SBET", "PINS", "SOFI", "IREN"]

KEYWORDS_INCLUDE = [
    "earnings","guidance","forecast","outlook","downgrade","upgrade","beats","miss",
    "inflows","outflows","etf","rebalance","rebalancing","index","holdings","allocation","sector rotation",
    "fed","interest rates","rate hike","rate cut","inflation","cpi","ppi","jobs report","unemployment","gdp",
    "merger","acquisition","buyout","deal","partnership",
    "regulation","ban","tariff","sanctions","stimulus","crisis"
]

# -----------------------------
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)

# -----------------------------
def fetch_news(ticker):
    now = int(time.time())

    # 🔥 Look back only 30 minutes
    from_time = now - (60 * 30)

    from_date = time.strftime('%Y-%m-%d', time.gmtime(from_time))
    to_date = time.strftime('%Y-%m-%d', time.gmtime(now))

    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"

    try:
        r = requests.get(url)
        data = r.json() if r.status_code == 200 else []

        # 🔥 CRITICAL FILTER (this is what actually fixes duplicates)
        filtered = [
            article for article in data
            if article.get("datetime", 0) >= from_time
        ]

        return filtered

    except:
        return []

# -----------------------------
def load_sent():
    if os.path.exists("sent.json"):
        with open("sent.json","r") as f:
            return set(json.load(f))
    return set()

def save_sent(sent):
    with open("sent.json","w") as f:
        json.dump(list(sent), f)

# -----------------------------
def filter_keywords(article):
    text = (article.get("headline","") + " " + article.get("summary","")).lower()
    return any(k in text for k in KEYWORDS_INCLUDE)

def sentiment(text):
    p = TextBlob(text).sentiment.polarity
    if p > 0.05: return "📈 BULLISH"
    if p < -0.05: return "📉 BEARISH"
    return "⚪️ NEUTRAL"

# -----------------------------
def format_msg(ticker, a):
    head = a.get("headline","")
    summ = a.get("summary","")[:300] + "..."
    url = a.get("url","")
    src = a.get("source","")
    ts = time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(a.get("datetime",0)))

    s = sentiment(head + summ)

    if ticker in ["SPY","QQQ"]:
        macro = f"🧠 {s} MARKET"
    else:
        macro = f"🧠 {s}"

    return f"""📊 {ticker} | {s}

{macro}

📰 {head}

🧾 {summ}

🕒 {ts}
🌐 {src}

🔗 {url}
"""

# -----------------------------
def run():
    sent = load_sent()

    for t in TICKERS:
        news = fetch_news(t)

        for a in news:
            aid = str(a.get("id"))

            if aid not in sent:
                if filter_keywords(a):
                    send_telegram_message(format_msg(t, a))

                sent.add(aid)

    save_sent(sent)

# -----------------------------
if __name__ == "__main__":
    run()
