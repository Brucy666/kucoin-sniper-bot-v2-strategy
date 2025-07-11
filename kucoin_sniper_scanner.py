import requests
import time
from datetime import datetime
from sniper_executor import evaluate_and_execute

BASE_URL = "https://api.kucoin.com"

def fetch_symbols():
    url = f"{BASE_URL}/api/v1/market/allTickers"
    r = requests.get(url)
    if r.status_code == 200:
        return [x["symbol"] for x in r.json()["data"]["ticker"] if x["symbol"].endswith("USDT")]
    return []

def fetch_candles(symbol):
    url = f"{BASE_URL}/api/v1/market/candles?type=1min&symbol={symbol}&limit=10"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()["data"]
    return []

def fetch_orderbook(symbol):
    url = f"{BASE_URL}/api/v1/market/orderbook/level2_100?symbol={symbol}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()["data"]
        return data["bids"], data["asks"]
    return [], []

def calculate_vwap(candles):
    total_volume = 0
    total_price_volume = 0
    for candle in candles:
        high = float(candle[3])
        low = float(candle[4])
        close = float(candle[2])
        vol = float(candle[5])
        price = (high + low + close) / 3
        total_volume += vol
        total_price_volume += price * vol
    return total_price_volume / total_volume if total_volume else 0

def spoof_score(bids, asks):
    if not bids or not asks:
        return 0
    top_bid = float(bids[0][1])
    top_ask = float(asks[0][1])
    total_bid = sum(float(b[1]) for b in bids[:10])
    total_ask = sum(float(a[1]) for a in asks[:10])
    return round((top_bid / total_bid) - (top_ask / total_ask), 2)

def score_symbol(symbol):
    try:
        candles = fetch_candles(symbol)
        if not candles:
            return None
        vwap = calculate_vwap(candles)
        close = float(candles[0][2])
        bias = "BUY" if close > vwap else "SELL"

        bids, asks = fetch_orderbook(symbol)
        spoof = spoof_score(bids, asks)

        score = 1
        if bias == "BUY" and spoof > 0.1:
            score = 5
        elif bias == "SELL" and spoof < -0.1:
            score = 5

        return {
            "symbol": symbol,
            "bias": bias,
            "score": score,
            "spoof": spoof,
            "price": close,
            "vwap": round(vwap, 4),
            "time": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return None

def run_scan():
    symbols = fetch_symbols()[:30]
    for sym in symbols:
        result = score_symbol(sym)
        if result:
            evaluate_and_execute(result)

if __name__ == "__main__":
    while True:
        print("📈 KuCoin Strategy Bot scanning...")
        run_scan()
        time.sleep(60)
