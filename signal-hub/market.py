"""Market module: economic calendar (news blackout windows), crypto headlines (RSS), altcoin-season index."""
import time, datetime, re, html, email.utils
import xml.etree.ElementTree as ET
import scan

CAL_URLS = ["https://nfs.faireconomy.media/ff_calendar_thisweek.json", "https://nfs.faireconomy.media/ff_calendar_nextweek.json"]
RSS = [("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"), ("Cointelegraph", "https://cointelegraph.com/rss")]

def calendar():
    out = []
    for u in CAL_URLS:
        try:
            for e in scan.jget(u):
                t = int(datetime.datetime.fromisoformat(e["date"]).timestamp())
                out.append({"t": t, "title": e.get("title", ""), "cur": e.get("country", ""), "impact": e.get("impact", ""), "fc": e.get("forecast", ""), "prev": e.get("previous", "")})
        except Exception as ex: print("calendar failed:", u.split("/")[-1], ex)
    now = scan.NOW()
    return sorted([e for e in out if now - 86400 <= e["t"] <= now + 7 * 86400 and e["impact"] in ("High", "Medium") and e["cur"] in ("USD", "EUR", "CNY", "JPY", "GBP", "ALL")], key=lambda x: x["t"])

def blackouts(events, minutes):
    """High-impact USD events -> [[start_ms, end_ms], ...] (pause new entries around them)."""
    return [[(e["t"] - minutes * 60) * 1000, (e["t"] + minutes * 60) * 1000] for e in events if e["impact"] == "High" and e["cur"] == "USD"]

def news(limit=14):
    items = []
    for name, u in RSS:
        try:
            r = scan.requests.get(u, headers=scan.H, timeout=25); r.raise_for_status()
            for it in ET.fromstring(r.content).iter("item"):
                t = email.utils.parsedate_to_datetime(it.findtext("pubDate")).timestamp()
                items.append({"t": int(t), "title": html.unescape(re.sub(r"<[^>]+>", "", it.findtext("title") or "")).strip(), "url": it.findtext("link") or "", "src": name})
        except Exception as ex: print("rss failed:", name, ex)
    return sorted(items, key=lambda x: -x["t"])[:limit]

def alt_season(cfg):
    """Own 'altcoin season' gauge: share of watchlist alts that beat BTC over 90 days (>=75% = altcoin season)."""
    btc = scan.klines("BTCUSDT", "1d", 120)
    if not btc or len(btc) < 95: return None
    b90 = btc[-1][4] / btc[-91][4] - 1; b30 = btc[-1][4] / btc[-31][4] - 1; rows = []
    for s in [x for x in cfg["majors"] if x != "BTCUSDT"]:
        c = scan.klines(s, "1d", 120)
        if c and len(c) >= 95: rows.append((s.replace("USDT", ""), c[-1][4] / c[-91][4] - 1, c[-1][4] / c[-31][4] - 1))
    if not rows: return None
    n90 = sum(1 for _, r, _ in rows if r > b90); n30 = sum(1 for _, _, r in rows if r > b30)
    top = sorted(rows, key=lambda x: -(x[1] - b90))[:5]
    return {"idx90": round(100 * n90 / len(rows)), "idx30": round(100 * n30 / len(rows)), "n": len(rows), "btc90": round(b90 * 100, 1), "btc30": round(b30 * 100, 1),
            "top": [{"s": s, "r90": round(r * 100, 1)} for s, r, _ in top]}

def run_market():
    cfg = scan.CFG; ev = calendar(); bl = blackouts(ev, cfg.get("news_blackout_min", 30))
    scan.save("market.json", {"updated": scan.NOW(), "events": ev, "blackouts": bl, "news": news(), "alt": alt_season(cfg), "blackout_min": cfg.get("news_blackout_min", 30)})
    print("market ok:", len(ev), "events,", len(bl), "blackout windows")
    return True
