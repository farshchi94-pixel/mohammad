#!/usr/bin/env python3
"""Signal Hub: scans markets (4h bias + 15m trigger), tracks a live track record,
follows Hyperliquid whales and (optionally) Solana wallets. Writes signals.json / whales.json.
Run:  python scan.py            (all)     python scan.py --signals | --whales
"""
import os, sys, json, time, statistics, requests, gzip, tempfile
from pathlib import Path
import whale_pro
from concurrent.futures import ThreadPoolExecutor

CFG = json.load(open("config.json", encoding="utf-8"))
TG_TOKEN, TG_CHAT = os.getenv("TELEGRAM_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")
HELIUS = os.getenv("HELIUS_API_KEY", "")
NOW = lambda: int(time.time())
H = {"User-Agent": "Mozilla/5.0"}
HTTP = requests.Session()
HTTP.headers.update(H)
RETRYABLE = {408, 425, 429, 500, 502, 503, 504}

def jget(url, params=None, headers=None):
    for i in range(3):
        try:
            r = HTTP.get(url, params=params, headers=headers, timeout=25)
            if r.status_code in RETRYABLE:
                wait = r.headers.get("Retry-After")
                time.sleep(float(wait) if wait and wait.replace('.', '', 1).isdigit() else 1.5 * (i + 1))
                continue
            r.raise_for_status(); return r.json()
        except Exception:
            if i == 2: raise
            time.sleep(1.5 * (i + 1))
def jpost(url, body):
    r = HTTP.post(url, json=body, timeout=25); r.raise_for_status(); return r.json()
def fp(x): return float(f"{x:.6g}")
def tg(text):
    if not TG_TOKEN or not TG_CHAT: print("[telegram off]", text.replace("\n", " | ")[:140]); return
    try: HTTP.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT, "text": text, "disable_web_page_preview": True}, timeout=25)
    except Exception as e: print("telegram error", e)
def tg_photo(png, caption):
    if not png: tg(caption); return
    if not TG_TOKEN or not TG_CHAT: print("[telegram off] card", len(png), "bytes |", caption.replace("\n", " | ")[:100]); return
    try: HTTP.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto", data={"chat_id": TG_CHAT, "caption": caption[:1000]}, files={"photo": ("card.png", png)}, timeout=40)
    except Exception as e: print("telegram photo error", e); tg(caption)
def load(path, default):
    try: return json.load(open(path, encoding="utf-8"))
    except Exception: return default
def save(path, obj): json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---------------- candle sources (work from US servers) ----------------
def kl_mexc(sym, tf, n, start_ms=None):
    params = {"symbol": sym, "interval": {"1h": "60m"}.get(tf, tf), "limit": min(n, 500)}
    if start_ms: params["startTime"] = int(start_ms)
    j = jget("https://api.mexc.com/api/v3/klines", params)
    return [[int(a[0]), float(a[1]), float(a[2]), float(a[3]), float(a[4]), float(a[5])] for a in j]
def kl_gate(sym, tf, n, start_ms=None):
    params = {"currency_pair": sym[:-4] + "_USDT", "interval": tf, "limit": min(n, 1000)}
    if start_ms: params["from"] = int(start_ms // 1000)
    j = jget("https://api.gateio.ws/api/v4/spot/candlesticks", params)
    return [[int(a[0]) * 1000, float(a[5]), float(a[3]), float(a[4]), float(a[2]), float(a[1])] for a in j]
SRC = {"mexc": kl_mexc, "gate": kl_gate}
KLINE_CACHE = {}
CACHE_FILE = Path(os.getenv("SIGNAL_HUB_CACHE", "cache/candles.json.gz"))
CACHE_STATS = {"requests": 0, "incremental_requests": 0, "bootstrap_requests": 0, "cache_hits": 0, "cache_misses": 0, "candles_merged": 0}

def _load_kline_cache():
    try:
        with gzip.open(CACHE_FILE, "rt", encoding="utf-8") as f: raw = json.load(f)
        for key, rows in raw.get("series", {}).items():
            sym, tf = key.split("|", 1)
            clean = normalize_candles(rows, tf)
            if clean: KLINE_CACHE[(sym, tf)] = clean
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return

def save_kline_cache():
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "updated": NOW(), "series": {f"{sym}|{tf}": rows[-1000:] for (sym, tf), rows in KLINE_CACHE.items()}}
    fd, tmp = tempfile.mkstemp(prefix="candles-", suffix=".json.gz", dir=str(CACHE_FILE.parent))
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
                gz.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        os.replace(tmp, CACHE_FILE)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def cache_status():
    return {**CACHE_STATS, "series": len(KLINE_CACHE), "file": str(CACHE_FILE)}

def normalize_candles(rows, tf, closed_only=True):
    """Sort, deduplicate and discard malformed or still-forming candles."""
    clean = {}
    for row in rows or []:
        if len(row) < 6: continue
        try:
            t, o, h, l, c, v = int(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])
        except (TypeError, ValueError): continue
        if min(o, h, l, c, v) < 0 or h < max(o, c) or l > min(o, c) or h < l: continue
        clean[t] = [t, o, h, l, c, v]
    out = [clean[t] for t in sorted(clean)]
    if closed_only and out and out[-1][0] + TFSEC.get(tf, 900) * 1000 > NOW() * 1000:
        out.pop()
    return out

def klines(sym, tf, n=500, min_n=60):
    cached = KLINE_CACHE.get((sym, tf))
    sec = TFSEC.get(tf, 900)
    for s in CFG.get("sources", ["mexc", "gate"]):
        try:
            CACHE_STATS["requests"] += 1
            if cached:
                start_ms = cached[-1][0] + sec * 1000
                delta = normalize_candles(SRC[s](sym, tf, min(max(20, n - len(cached) + 8), 500), start_ms), tf)
                merged = normalize_candles(cached + delta, tf)
                CACHE_STATS["incremental_requests"] += 1
                CACHE_STATS["candles_merged"] += len(delta)
                if len(merged) >= min_n:
                    KLINE_CACHE[(sym, tf)] = merged[-1000:]
                    CACHE_STATS["cache_hits"] += 1
                    return KLINE_CACHE[(sym, tf)][-n:]
            c = normalize_candles(SRC[s](sym, tf, n), tf)
            CACHE_STATS["bootstrap_requests"] += 1
            if len(c) > min_n:
                KLINE_CACHE[(sym, tf)] = normalize_candles((cached or []) + c, tf)[-1000:]
                CACHE_STATS["cache_misses"] += 1
                return KLINE_CACHE[(sym, tf)][-n:]
        except Exception: pass
    if cached and len(cached) >= min_n:
        CACHE_STATS["cache_hits"] += 1
        return cached[-n:]
    return None
TFSEC = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}
CANDLES = {}
_load_kline_cache()

# ---------------- indicators ----------------
def ema(a, n):
    k = 2 / (n + 1); e = a[0]
    for x in a[1:]: e = x * k + e * (1 - k)
    return e
def rsi(a, n=14):
    if len(a) < n + 2: return 50.0
    g = l = 0.0
    for i in range(1, n + 1):
        d = a[i] - a[i - 1]; g += max(d, 0); l += max(-d, 0)
    g /= n; l /= n
    for i in range(n + 1, len(a)):
        d = a[i] - a[i - 1]; g = (g * (n - 1) + max(d, 0)) / n; l = (l * (n - 1) + max(-d, 0)) / n
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)
def atr(cs, n=14):
    s = 0.0
    for k in range(len(cs) - n, len(cs)):
        p = cs[k - 1][4]; s += max(cs[k][2] - cs[k][3], abs(cs[k][2] - p), abs(cs[k][3] - p))
    return s / n
def piv(cs, k, hi):
    r = []
    for i in range(k, len(cs) - k):
        v = cs[i][2 if hi else 3]; ok = True
        for q in range(i - k, i + k + 1):
            if q == i: continue
            w = cs[q][2 if hi else 3]
            if (w > v) if hi else (w < v): ok = False; break
        if ok: r.append(v)
    return r
cl = lambda x, a, b: max(a, min(b, x))

# ---------------- model: 4h bias + 15m trigger ----------------
def mk_bias(c4, ctx, is_btc):
    cc = [x[4] for x in c4]; c = cc[-1]
    e20, e50 = ema(cc[-100:], 20), ema(cc[-200:], 50)
    e200 = ema(cc[-400:], 200) if len(cc) >= 200 else None
    r4, at = rsi(cc[-150:]), atr(c4)
    vols = [x[5] for x in c4]; vx = vols[-1] / ((sum(vols[-21:-1]) / 20) or 1); up = c4[-1][4] >= c4[-1][1]
    seg = c4[-160:]; ph, pl = piv(seg, 3, True), piv(seg, 3, False); why = []; P = {}
    P["a"] = 1 if c > e50 else -1; why.append("۴ساعته: قیمت " + ("بالای" if P["a"] > 0 else "زیر") + " EMA50")
    P["b"] = 1 if e20 > e50 else -1; why.append("۴ساعته: EMA20 " + ("بالای" if P["b"] > 0 else "زیر") + " EMA50")
    P["c"] = 0 if e200 is None else (1 if e50 > e200 else -1)
    if e200 is not None: why.append("۴ساعته: روند بزرگ " + ("صعودی" if P["c"] > 0 else "نزولی") + " (EMA50 در برابر EMA200)")
    P["s"] = 0
    if len(ph) >= 2 and len(pl) >= 2:
        hh, hl = ph[-1] > ph[-2], pl[-1] > pl[-2]; P["s"] = 1 if hh and hl else (-1 if (not hh and not hl) else 0)
        why.append("ساختار: " + ("سقف و کف بالاتر" if P["s"] > 0 else "سقف و کف پایین‌تر" if P["s"] < 0 else "مختلط"))
    P["r"] = 1 if 50 <= r4 <= 70 else (-1 if r4 < 50 else 0); why.append(f"RSI ۴ساعته {r4:.0f}")
    P["v"] = (1 if up else -1) if vx >= 1.3 else 0
    if vx >= 1.3: why.append(f"حجم ۴ساعته {vx:.1f}× میانگین")
    P["x"] = 0
    if not is_btc and "btcUp" in ctx: P["x"] = 1 if ctx["btcUp"] else -1; why.append("بیت‌کوین " + ("صعودی" if ctx["btcUp"] else "نزولی"))
    total = float(sum(P.values()))
    fng = ctx.get("fng")
    if fng is not None:
        if fng > 80 and total > 0: total -= .5; why.append(f"ترس و طمع {fng}: بازار داغ")
        elif fng < 20 and total < 0: total += .5; why.append(f"ترس و طمع {fng}: ترس شدید")
    rs = ctx.get("rs")
    if rs is not None and not is_btc:
        if rs > 5 and total > 0: total += .5; why.append("قدرت نسبی نسبت به BTC مثبت")
        elif rs < -5 and total < 0: total -= .5; why.append("ضعیف‌تر از BTC")
    d = "long" if total >= 3 else "short" if total <= -3 else "neutral"
    return {"dir": d, "total": total, "why": why, "c": c, "at": at,
            "sup": sorted([p for p in pl if p < c * .997], reverse=True), "res": sorted([p for p in ph if p > c * 1.003])}

def trig15(c15, B):
    n = len(c15); cc = [x[4] for x in c15]; c = cc[-1]
    e20, e50, r, at = ema(cc[-80:], 20), ema(cc[-160:], 50), rsi(cc[-120:]), atr(c15); L = B["dir"] == "long"
    hit = -1
    for k in range(n - 1, n - 4, -1):
        pv = c15[k - 8:k]; lv = max(x[2] for x in pv) if L else min(x[3] for x in pv)
        if (cc[k] > lv) if L else (cc[k] < lv): hit = k; break
    p8 = c15[n - 9:n - 1]; lvl = max(x[2] for x in p8) if L else min(x[3] for x in p8)
    vk = hit if hit >= 0 else n - 1; vv = c15[vk][5] / ((sum(x[5] for x in c15[vk - 20:vk]) / 20) or 1)
    checks = [(("EMA/قیمت ۱۵دقیقه هم‌جهت"), (c > e20 > e50) if L else (c < e20 < e50)),
              (f"RSI ۱۵دقیقه {r:.0f}", (50 <= r <= 72) if L else (28 <= r <= 50)),
              ("شکست " + ("سقف" if L else "کف") + " ۸ کندل", hit >= 0),
              (f"حجم شکست {vv:.1f}×", vv >= 1.3),
              ("فاصلهٔ کم از EMA20", abs(c - e20) <= 2 * at)]
    okn = sum(1 for _, ok in checks if ok); fired = hit >= 0 and okn >= 4
    out = {"B": B, "checks": [{"t": t, "ok": ok} for t, ok in checks], "okn": okn, "state": "fired" if fired else "ready", "trig": lvl, "c": c}
    if not fired: return out
    d = 1 if L else -1
    lows = [p for p in piv(c15[-60:], 3, not L) if (p < c if L else p > c)]
    sw = lows[-1] if lows else None
    sl = min(sw * .999 if sw else c - at, c - at) if L else max(sw * 1.001 if sw else c + at, c + at)
    risk = cl(abs(c - sl), at, 2.5 * at); sl = c - d * risk
    lv = [p for p in (B["res"] if L else B["sup"]) if abs(p - c) >= risk]; T = []
    for p in lv:
        if len(T) < 4 and (not T or abs(p - T[-1]) > .3 * risk): T.append(p)
    for m in (1.5, 2.5, 3.5, 5):
        if len(T) < 4:
            p = c + d * risk * m
            if not T or ((p > T[-1] + .3 * risk) if L else (p < T[-1] - .3 * risk)): T.append(p)
    T = sorted(T, reverse=not L)[:4]
    e2 = max(e20 if e20 < c else c - .5 * risk, c - .5 * risk) if L else min(e20 if e20 > c else c + .5 * risk, c + .5 * risk)
    out["plan"] = {"side": "long" if L else "short", "entry": c, "e2": e2, "sl": sl, "risk": risk, "T": T, "R": [abs(t - c) / risk for t in T]}
    return out

def model(c4, c15, ctx, is_btc):
    B = mk_bias(c4, ctx, is_btc)
    if B["dir"] == "neutral": return {"B": B, "state": "none", "checks": [], "okn": 0}
    return trig15(c15, B)

# ---------------- track record ----------------
FEE = .05
def evaluate(sig, c15):
    L = sig["side"] == "long"; d = 1 if L else -1; e, risk, T = sig["entry"], sig["risk"], sig["T"]
    stop = sig.get("stop", sig["sl"]); hits = sig.setdefault("hits", [])
    def realized(exit_px):
        part = sum(.25 * abs(T[i] - e) / risk for i in hits); rest = 1 - .25 * len(hits)
        return part + rest * d * (exit_px - e) / risk - FEE
    for row in c15:
        t = row[0]
        if t <= sig["last_t"]: continue
        sig["last_t"] = t; h, l = row[2], row[3]
        if (l <= stop) if L else (h >= stop):
            sig.update(status="closed", R=round(realized(stop), 3), closed_at=t // 1000, reason="be" if stop == e else "stop"); return sig
        for i, tg in enumerate(T):
            if i not in hits and ((h >= tg) if L else (l <= tg)): hits.append(i)
        if 0 in hits and stop != e: stop = e; sig["stop"] = e
        if len(hits) == len(T):
            sig.update(status="closed", R=round(realized(T[-1]), 3), closed_at=t // 1000, reason="targets"); return sig
    if NOW() - sig["t_open"] > 48 * 3600 and c15:
        sig.update(status="closed", R=round(realized(c15[-1][4]), 3), closed_at=NOW(), reason="timeout")
    return sig
def stats(closed):
    def agg(rows):
        if not rows: return {"n": 0}
        rs = [x["R"] for x in rows]; cum = peak = dd = 0.0
        for r in rs: cum += r; peak = max(peak, cum); dd = max(dd, peak - cum)
        return {"n": len(rs), "win": round(100 * sum(1 for r in rs if r > 0) / len(rs), 1), "avgR": round(sum(rs) / len(rs), 2), "totalR": round(sum(rs), 2), "maxDD": round(dd, 2)}
    live = [x for x in closed if x.get("tier") == "live"]; n = NOW(); cons = [x for x in closed if x.get("tier") == "consensus"]
    return {"all": agg(live), "d30": agg([x for x in live if x["closed_at"] > n - 30 * 86400]), "d7": agg([x for x in live if x["closed_at"] > n - 7 * 86400]), "practice": agg([x for x in closed if x.get("tier") not in ("live", "consensus")]), "consensus": agg(cons)}

def sig_text(s, title):
    L = s["side"] == "long"
    return (f"{title} {'🟢 لانگ' if L else '🔴 شورت'} {s['sym']} ({'زنده' if s['tier']=='live' else 'تمرینی'})\nورود: {fp(s['entry'])} / پله‌ای {fp(s['e2'])}\nحد ضرر: {fp(s['sl'])}\nاهداف: {' / '.join(str(fp(t)) for t in s['T'])}\n"
            f"تأیید ۱۵دقیقه: {s['okn']} از ۵ | قدرت جهت ۴ساعته: {abs(s['bias']):.1f}\n⚠️ توصیهٔ مالی نیست؛ حداکثر ۱٪ سرمایه ریسک کنید.")

def run_signals():
    prev = load("signals.json", {"open": [], "closed": []}); op, closed = prev.get("open", []), prev.get("closed", [])
    syms = [s for s in CFG["majors"] + CFG.get("memes", []) if s != "BTCUSDT"]; memes = set(CFG.get("memes", []))
    ctx = {}
    try: ctx["fng"] = int(jget("https://api.alternative.me/fng/")["data"][0]["value"])
    except Exception: pass
    b4, b15 = klines("BTCUSDT", "4h"), klines("BTCUSDT", "15m")
    if not b4 or not b15: print("BTC data unavailable from all sources:", CFG.get("sources")); return False
    btc_total = mk_bias(b4, ctx, True)["total"]; ctx["btcUp"] = btc_total > 0
    data = {"BTCUSDT": (b4, b15)}
    def get(s):
        c4, c15 = klines(s, "4h"), klines(s, "15m")
        return s, (c4, c15) if c4 and c15 and len(c4) > 200 else None
    with ThreadPoolExecutor(max_workers=min(8, max(2, len(syms)))) as ex:
        for sym, pair in ex.map(get, syms):
            if pair: data[sym] = pair
    print(f"data ok for {len(data)} of {len(syms)+1} symbols")
    stillopen = []
    for s in op:
        if s["sym"] in data: s = evaluate(s, data[s["sym"]][1])
        if s["status"] == "closed":
            closed.append(s)
            if s["tier"] == "live": tg(f"{'✅' if s['R']>0 else '❌'} بسته شد: {s['sym']} {s['side']} | نتیجه {s['R']:+.2f}R | علت: {s['reason']}")
        else: stillopen.append(s)
    op = stillopen; analysis = {}
    for sym, (c4, c15) in data.items():
        c = dict(ctx)
        if sym != "BTCUSDT": c["rs"] = ((c4[-1][4] / c4[-181][4]) - (b4[-1][4] / b4[-181][4])) * 100 if len(c4) > 181 else 0
        CANDLES[sym] = [[x[0] // 1000, fp(x[1]), fp(x[2]), fp(x[3]), fp(x[4])] for x in c15[-120:]]
        r = model(c4, c15, c, sym == "BTCUSDT"); B = r["B"]
        analysis[sym] = {"price": fp(c15[-1][4]), "dir": B["dir"], "score": round(B["total"], 1), "state": r["state"], "okn": r["okn"], "why": B["why"][:5],
                         "checks": r["checks"], "trig": fp(r["trig"]) if "trig" in r else None, "sup": [fp(x) for x in B["sup"][:2]], "res": [fp(x) for x in B["res"][:2]],
                         "spark": [fp(x[4]) for x in c15[-96:]], "t": c15[-1][0] // 1000}
        if r["state"] == "fired" and not any(o["sym"] == sym for o in op) and not any(x["sym"] == sym and NOW() - x["closed_at"] < 2 * 3600 for x in closed[-60:]):
            p = r["plan"]; tier = "live" if (sym not in memes and abs(B["total"]) >= 4 and r["okn"] >= 4) else "practice"
            s = {"id": f"{sym}-{NOW()}", "sym": sym, "side": p["side"], "tier": tier, "entry": fp(p["entry"]), "e2": fp(p["e2"]), "sl": fp(p["sl"]), "risk": p["risk"],
                 "T": [fp(t) for t in p["T"]], "R": [round(x, 2) for x in p["R"]], "okn": r["okn"], "bias": round(B["total"], 1), "t_open": NOW(), "last_t": c15[-1][0], "status": "open", "hits": []}
            op.append(s); print("NEW", tier, sym, p["side"])
            if tier == "live": tg(sig_text(s, "🔔 سیگنال جدید"))
    save("signals.json", {"updated": NOW(), "open": op, "closed": closed[-300:], "stats": stats(closed), "analysis": analysis, "ctx": {"fng": ctx.get("fng"), "btcDir": "long" if btc_total >= 3 else "short" if btc_total <= -3 else "neutral"}, "cache": cache_status()})
    save("candles.json", {"updated": NOW(), "tf": "15m", "c": CANDLES})
    return True

# ---------------- Whale Pro strategy (user's Pine script, ported) ----------------
def rnd_c(rows, k=200): return [[x[0] // 1000, fp(x[1]), fp(x[2]), fp(x[3]), fp(x[4])] for x in rows[-k:]]
def trade_json(tr):
    return {"side": tr["side"], "t": tr["entry_t"] // 1000, "entry": fp(tr["fill"]), "sig": fp(tr["sig_px"]), "sl": fp(tr["sl"]), "t1": fp(tr["t1"]), "t2": fp(tr["t2"]), "src": tr["src"],
            "exits": [{"t": e["t"] // 1000, "p": fp(e["p"]), "q": e["q"], "r": e["r"]} for e in tr["exits"]], "pct": round(tr.get("pct", 0) * 100, 3), "res": tr.get("result", "open")}
def run_whalepro():
    prev = load("whalepro.json", {}); start = prev.get("start") or NOW(); tf = CFG.get("whale_tf", "15m"); P = dict(CFG.get("whale_params", {}))
    mk = load("market.json", {}); P["blackouts"] = P.get("blackouts") or mk.get("blackouts", []); htf_tf = CFG.get("whale_htf", "4h")
    import card
    alerted = prev.get("alerted", {}); notified = set(prev.get("notified", [])); out = {}; all_tr = []; sec = TFSEC.get(tf, 900)
    syms = CFG.get("whale_symbols") or CFG["majors"][:10]
    def get(sym):
        c = klines(sym, tf, 1000, min_n=600); h = klines(sym, htf_tf, 500, min_n=250) if P.get("htf_filter") else None
        return sym, (c, h)
    with ThreadPoolExecutor(max_workers=min(8, max(2, len(syms)))) as ex: res = list(ex.map(get, syms))
    sent_res = [0]
    for sym, (c, htf) in res:
        if not c: print("whale: no data", sym); continue
        if c[-1][0] / 1000 + sec > NOW(): c = c[:-1]          # drop the still-forming candle
        r = whale_pro.run(c, P, htf=htf, htf_sec=TFSEC.get(htf_tf, 14400)); trs = [dict(t) for t in r["trades"]]
        n = len(c); k = min(200, n); off = n - k
        mk = [{"i": m["i"] - off, "k": m["k"], "s": m["side"], "p": fp(m["p"]), "src": m.get("src", "")} for m in r["markers"] if m["i"] >= off][-80:]
        pos = r["open"]
        rec = whale_pro.stats(trs, whale_pro.DEFAULT | P, since_t=start * 1000)
        out[sym] = {"price": fp(c[-1][4]), "t": c[-1][0] // 1000, "candles": rnd_c(c, k),
                    "ema": {key: [None if v is None else fp(v) for v in r["series"][key][-k:]] for key in ("ema8", "ema21", "ema55", "ema200")}, "markers": mk,
                    "trades": [trade_json(t) for t in trs[-15:]], "stats": r["stats"], "live": rec, "diag": r["diag"],
                    "open": ({"side": pos["side"], "t": pos["entry_t"] // 1000, "entry": fp(pos["fill"]), "sl": fp(pos["be_px"] if pos.get("be") else pos["sl"]), "t1": fp(pos["t1"]), "t2": fp(pos["t2"]), "be": bool(pos.get("be")),
                              "tp1_done": pos["rem_tp1"] == 0, "src": pos["src"]} if pos else None),
                    "signal": ({"side": r["signal"]["side"], "px": fp(r["signal"]["sig_px"]), "sl": fp(r["signal"]["sl"]), "t1": fp(r["signal"]["t1"]), "t2": fp(r["signal"]["t2"]), "src": r["signal"]["src"], "t": c[-1][0] // 1000} if r["signal"] else None),
                    "pending": ({"side": r["pending_confirm"]["side"], "level": fp(r["pending_confirm"]["level"])} if r["pending_confirm"] else None)}
        for t in trs:
            t["sym"] = sym
            if t["entry_t"] >= start * 1000: all_tr.append(t)
        sg = out[sym]["signal"]
        if sg and alerted.get(sym) != sg["t"]:
            alerted[sym] = sg["t"]; L = sg["side"] == "long"
            cap = (f"{'🟢 BUY' if L else '🔴 SELL'} {sym} | Whale Pro V3.10 ({sg['src']}) | {tf}\nقیمت سیگنال: {sg['px']}\nحد ضرر: {sg['sl']}\nTP1 (۶۰٪): {sg['t1']}\nTP2 (۴۰٪): {sg['t2']}\n"
                   f"ADX {r['diag']['adx']:.0f} | RSI {r['diag']['rsi']:.0f}\n⚠️ ورود در بازشدن کندل بعد؛ توصیهٔ مالی نیست.")
            tg_photo(card.signal_card(sym, tf, sg["side"], [[x[0] // 1000, x[1], x[2], x[3], x[4]] for x in c[-60:]], sg["px"], sg["sl"], sg["t1"], sg["t2"], sg["src"], sg["t"], f"{sym[:3]}-{sg['t']}"), cap)
        for t in trs:
            if t["entry_t"] >= start * 1000:
                tid = f"{sym}-{t['entry_t']}"
                if tid not in notified:
                    notified.add(tid); pnl = sum(e["q"] * e["pct"] for e in t["exits"]) * 100; sent_res[0] += 1
                    if sent_res[0] <= 8: tg_photo(card.result_card(sym, t["side"], t["fill"], [(e["r"], e["p"], e["q"]) for e in t["exits"]], pnl / 100, f"{sym[:3]}-{t['entry_t']//1000}", t["exits"][-1]["t"] // 1000),
                             f"{'✅' if pnl > 0 else '❌'} Whale Pro {sym} {t['side']} بسته شد: {pnl:+.2f}٪ ({'، '.join(e['r'] for e in t['exits'])})")
    all_tr.sort(key=lambda x: x["entry_t"])
    today = time.strftime("%Y-%m-%d", time.gmtime()); rec = whale_pro.stats(all_tr, whale_pro.DEFAULT | P); rs = prev.get("record_sent")
    if time.gmtime().tm_wday == 6 and rs != today and rec["positions"]:
        tg_photo(card.record_card(rec, [{"sym": x["sym"], "side": x["side"], "pct": x.get("pct", 0) * 100, "reasons": [e["r"] for e in x["exits"]]} for x in all_tr], start), f"📊 رکورد زندهٔ Whale Pro: {rec['positions']} معامله | برد {rec['pos_win']}٪ | PF {rec['pf']} | خالص {rec['net_pct']:+.2f}٪\nهمهٔ معاملات بسته‌شده، با باخت‌ها."); rs = today
    save("whalepro.json", {"updated": NOW(), "start": start, "tf": tf, "params": {k: v for k, v in (whale_pro.DEFAULT | P).items()}, "symbols": out, "record": whale_pro.stats(all_tr, whale_pro.DEFAULT | P),
                           "alerted": alerted, "notified": sorted(notified)[-500:], "record_sent": rs, "cache": cache_status()})
    print("whalepro ok:", len(out), "symbols")
    return True

# ---------------- phase 2: whales ----------------
def hl_wallets():
    ws = []
    try:
        j = jget("https://stats-data.hyperliquid.xyz/Mainnet/leaderboard")
        rows = []
        for r in j.get("leaderboardRows", []):
            perf = dict((k, v) for k, v in r.get("windowPerformances", []))
            rows.append((float((perf.get("month") or {}).get("pnl", 0)), float(r.get("accountValue", 0)), r["ethAddress"]))
        rows = [x for x in rows if x[1] >= CFG.get("hl_min_account", 500000)]
        ws = [a for _, _, a in sorted(rows, reverse=True)[:CFG.get("hyperliquid_top", 25)]]
    except Exception as e: print("leaderboard failed:", e)
    return list(dict.fromkeys(ws + CFG.get("hyperliquid_wallets", [])))
def hl_positions(addr):
    j = jpost("https://api.hyperliquid.xyz/info", {"type": "clearinghouseState", "user": addr}); out = []
    for ap in j.get("assetPositions", []):
        p = ap["position"]; sz = float(p["szi"])
        if sz == 0: continue
        out.append({"coin": p["coin"], "side": "long" if sz > 0 else "short", "usd": abs(float(p["positionValue"])), "entry": float(p.get("entryPx") or 0), "pnl": float(p.get("unrealizedPnl", 0)), "lev": (p.get("leverage") or {}).get("value")})
    return out
SOLP = None
def sol_price():
    global SOLP
    if SOLP is None:
        try: SOLP = float(jget("https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112")["pairs"][0]["priceUsd"])
        except Exception: SOLP = 0
    return SOLP
STABLE_MINTS = {"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"}
def sol_events(wallet, since):
    ev = []; j = jget(f"https://api.helius.xyz/v0/addresses/{wallet}/transactions", {"api-key": HELIUS, "type": "SWAP", "limit": 20}, {})
    for tx in j:
        ts = int(tx.get("timestamp", 0))
        if ts <= since: continue
        recv = [t for t in tx.get("tokenTransfers", []) if t.get("toUserAccount") == wallet and t["mint"] not in STABLE_MINTS]
        sent = [t for t in tx.get("tokenTransfers", []) if t.get("fromUserAccount") == wallet and t["mint"] not in STABLE_MINTS]
        usd_out = sum(float(t["tokenAmount"]) for t in tx.get("tokenTransfers", []) if t.get("fromUserAccount") == wallet and t["mint"] in STABLE_MINTS)
        usd_in = sum(float(t["tokenAmount"]) for t in tx.get("tokenTransfers", []) if t.get("toUserAccount") == wallet and t["mint"] in STABLE_MINTS)
        sol_out = sum(n["amount"] for n in tx.get("nativeTransfers", []) if n.get("fromUserAccount") == wallet) / 1e9
        sol_in = sum(n["amount"] for n in tx.get("nativeTransfers", []) if n.get("toUserAccount") == wallet) / 1e9
        if recv and not sent: side, mint, usd = "buy", recv[0]["mint"], usd_out + sol_out * sol_price()
        elif sent and not recv: side, mint, usd = "sell", sent[0]["mint"], usd_in + sol_in * sol_price()
        else: continue
        if usd >= CFG.get("sol_min_usd", 2000): ev.append({"wallet": wallet, "side": side, "mint": mint, "usd": round(usd), "ts": ts, "sig": tx.get("signature", "")})
    return ev
def sol_token(mint):
    try:
        ps = jget(f"https://api.dexscreener.com/latest/dex/tokens/{mint}").get("pairs") or []
        if not ps: return {}
        p = max(ps, key=lambda x: (x.get("liquidity") or {}).get("usd", 0))
        return {"symbol": p["baseToken"]["symbol"], "liq": (p.get("liquidity") or {}).get("usd", 0), "h1": (p.get("priceChange") or {}).get("h1"), "h24": (p.get("priceChange") or {}).get("h24"), "url": p.get("url")}
    except Exception: return {}
def run_whales():
    prev = load("whales.json", {}); pp = prev.get("_pos", {}); first = not pp; new_pos, events, tops = {}, [], []
    ws = hl_wallets(); print("hyperliquid wallets:", len(ws))
    def one(a):
        try: return a, hl_positions(a)
        except Exception as e: print("hl error", a[:8], e); return a, None
    with ThreadPoolExecutor(max_workers=min(8, max(2, len(ws)))) as ex: res = list(ex.map(one, ws))
    net = {}
    for a, ps in res:
        if ps is None: continue
        new_pos[a] = {f"{p['coin']}": p for p in ps}
        for p in ps:
            n = net.setdefault(p["coin"], {"coin": p["coin"], "long": 0, "short": 0, "w": set(), "nl": 0, "ns": 0}); n[p["side"]] += p["usd"]; n["w"].add(a); n["nl" if p["side"] == "long" else "ns"] += 1
            tops.append({**p, "wallet": a[:6] + "…" + a[-4:]})
        if not first:
            old = pp.get(a, {})
            for coin, p in new_pos[a].items():
                o = old.get(coin)
                if (not o or o["side"] != p["side"]) and p["usd"] >= CFG.get("hl_event_min_usd", 500000):
                    events.append({"t": NOW(), "wallet": a[:6] + "…" + a[-4:], "coin": coin, "side": p["side"], "usd": round(p["usd"]), "entry": p["entry"], "kind": "flip" if o else "open"})
            for coin, o in old.items():
                if coin not in new_pos[a] and o["usd"] >= CFG.get("hl_event_min_usd", 500000):
                    events.append({"t": NOW(), "wallet": a[:6] + "…" + a[-4:], "coin": coin, "side": o["side"], "usd": round(o["usd"]), "kind": "close"})
    for e in events:
        k = {"open": "باز کرد", "flip": "جهت را برعکس کرد", "close": "بست"}[e["kind"]]
        tg(f"🐋 کیف پول هوشمند Hyperliquid {e['wallet']} پوزیشن {'لانگ' if e['side']=='long' else 'شورت'} {e['coin']} به ارزش ${e['usd']:,} را {k}.\n⚠️ کپی‌کردن کورکورانه خطرناک است.")
    netl = sorted(({"coin": n["coin"], "long": round(n["long"]), "short": round(n["short"]), "wallets": len(n["w"]), "nl": n["nl"], "ns": n["ns"]} for n in net.values()), key=lambda x: -(x["long"] + x["short"]))[:15]
    sol = prev.get("sol", {"events": [], "last": {}})
    if HELIUS and CFG.get("solana_wallets"):
        for w in CFG["solana_wallets"]:
            try:
                since = sol["last"].get(w)
                if since is None: sol["last"][w] = NOW(); continue
                evs = sol_events(w, since)
                if evs: sol["last"][w] = max(e["ts"] for e in evs)
                for e in sorted(evs, key=lambda x: x["ts"]):
                    e.update(sol_token(e["mint"])); sol["events"].insert(0, e)
                    tg(f"🐋 سولانا {w[:4]}…{w[-4:]} {'خرید' if e['side']=='buy' else 'فروش'} {e.get('symbol','?')} ≈ ${e['usd']:,}\nنقدشوندگی: ${e.get('liq',0):,.0f}\n{e.get('url','')}\n⚠️ قبل از هر کاری RugCheck را ببینید.")
            except Exception as ex: print("helius error", w[:6], ex)
        sol["events"] = sol["events"][:40]
    elif CFG.get("solana_wallets"): print("HELIUS_API_KEY not set: Solana part skipped")
    evs_all = (events + prev.get("hl", {}).get("events", []))[:40]
    save("whales.json", {"updated": NOW(), "_pos": new_pos, "hl": {"net": netl, "top": sorted(tops, key=lambda x: -x["usd"])[:25], "events": evs_all, "wallets": len(ws)}, "sol": sol})
    return True

if __name__ == "__main__":
    a = sys.argv[1:]; ok = True
    try:
        if not a or "--market" in a:
            try: import market; market.run_market()
            except Exception as e: print("market failed:", repr(e))
        if not a or "--signals" in a:
            try: ok = run_signals() and ok
            except Exception as e: print("signals failed:", repr(e)); ok = False
        if not a or "--whalepro" in a:
            try: run_whalepro()
            except Exception as e: print("whalepro failed:", repr(e))
        if not a or "--consensus" in a:
            try:
                import consensus; consensus.run_consensus(); consensus.run_dex_consensus()
            except Exception as e: print("consensus failed:", repr(e))
        if not a or "--trader" in a:
            try: import trader; trader.run_trader()
            except Exception as e: print("trader failed:", repr(e))
        if "--watch" in a or (not a and CFG.get("watch_channels")):
            try: import watch; watch.run_watch()
            except Exception as e: print("watch failed:", repr(e))
        if not a or "--whales" in a:
            try: run_whales()
            except Exception as e: print("whales failed:", repr(e))
    finally:
        save_kline_cache()
    sys.exit(0 if ok else 1)
