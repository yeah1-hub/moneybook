# 네이버 증권에서 국내 주식·ETF, 미국 주식 시세를 받아 prices.json 으로 저장
import json, time, urllib.request, datetime

UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
      "Referer": "https://m.stock.naver.com/"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    for enc in ("utf-8", "euc-kr"):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            pass
    raise ValueError("JSON 아님: " + url)

def num(v):
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None

items = {}   # code -> [name, price, currency]

def add(code, name, price, cur):
    p = num(price)
    if code and name and p:
        items[code] = [name, p, cur]

# 국내 주식 (코스피·코스닥 전체)
for market in ("KOSPI", "KOSDAQ"):
    page = 1
    while page <= 40:
        try:
            d = get(f"https://m.stock.naver.com/api/stocks/marketValue/{market}?page={page}&pageSize=100")
        except Exception as e:
            print(market, page, "실패", e); break
        stocks = d.get("stocks") or []
        for s in stocks:
            add(s.get("itemCode"), s.get("stockName"), s.get("closePrice"), "KRW")
        if len(stocks) < 100: break
        page += 1; time.sleep(0.2)
    print(market, "누적", len(items))

# 국내 ETF
try:
    d = get("https://finance.naver.com/api/sise/etfItemList.nhn")
    for s in d["result"]["etfItemList"]:
        add(s.get("itemcode"), s.get("itemname"), s.get("nowVal"), "KRW")
except Exception as e:
    print("ETF 실패", e)
print("ETF 포함", len(items))

# 미국 주식 (시가총액 상위)
for ex in ("NASDAQ", "NYSE", "AMEX"):
    for page in range(1, 6):
        try:
            d = get(f"https://api.stock.naver.com/stock/exchange/{ex}/marketValue?page={page}&pageSize=100")
        except Exception as e:
            print(ex, page, "실패", e); break
        stocks = d.get("stocks") or []
        for s in stocks:
            code = s.get("symbolCode") or s.get("reutersCode")
            name = s.get("stockName") or s.get("stockNameEng")
            add(code, name, s.get("closePrice"), "USD")
        if len(stocks) < 100: break
        time.sleep(0.2)
    print(ex, "누적", len(items))

# 원달러 환율
usd = None
for url in ("https://m.stock.naver.com/front-api/marketIndex/productDetail?category=exchange&reutersCode=FX_USDKRW",
            "https://api.stock.naver.com/marketindex/exchange/FX_USDKRW"):
    try:
        d = get(url)
        r = d.get("result") or d
        usd = num(r.get("closePrice") or (r.get("exchangeInfo") or {}).get("closePrice"))
        if usd: break
    except Exception as e:
        print("환율 실패", url, e)
print("환율", usd)

kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
if len(items) < 500:
    raise SystemExit("받아온 종목이 너무 적어서 저장하지 않아요: %d" % len(items))
with open("prices.json", "w", encoding="utf-8") as f:
    json.dump({"updated": kst.strftime("%Y-%m-%d %H:%M"), "usdkrw": usd, "items": items}, f, ensure_ascii=False, separators=(",", ":"))
print("저장", len(items))
