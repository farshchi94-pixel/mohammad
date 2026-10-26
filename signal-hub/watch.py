"""Competitor audit: reads PUBLIC Telegram channel previews (t.me/s/<channel>), extracts signals with levels,
and measures what REALLY happened afterwards using real candles. Analysis only - nothing is republished."""
import re, html, time, datetime, statistics
import scan

PD = str.maketrans("۰۱۲۳۴۵۶۷۸۹٫٬٠١٢٣٤٥٦٧٨٩", "0123456789.,0123456789")
def clean(t):
    t = re.sub(r"<br\s*/?>", "\n", t); t = html.unescape(re.sub(r"<[^>]+>", "", t)); return t.translate(PD)
def nums(sec): return [float(x.replace(",", "")) for x in re.findall(r"(?<![\d.])\d[\d,]*(?:\.\d+)?(?![\d)])", sec)]

def fetch(channel):
    r = scan.requests.get(f"https://t.me/s/{channel}", headers=scan.H, timeout=25); r.raise_for_status(); posts = []
    for blk in re.split(r'<div class="tgme_widget_message_wrap', r.text)[1:]:
        m = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', blk, re.S); d = re.search(r'<time[^>]*datetime="([^"]+)"', blk); u = re.search(r'href="(https://t\.me/[^"]+/\d+)"', blk)
        if m and d: posts.append({"text": clean(m.group(1)), "t": int(datetime.datetime.fromisoformat(d.group(1)).timestamp()), "url": u.group(1) if u else ""})
    return posts

def parse(text):
    T = text; U = T.upper()
    pm = re.search(r"#?([A-Z0-9]{2,12})\s*/\s*USDT", U) or re.search(r"\b([A-Z0-9]{2,12})USDT\b", U)
    side = re.search(r"\b(LONG|SHORT|BUY|SELL)\b", U); fa = re.search(r"(لانگ|خرید)", T); fs = re.search(r"(شورت|فروش)", T)
    if not pm: return None
    s = ("long" if side.group(1) in ("LONG", "BUY") else "short") if side else ("long" if fa and not fs else "short" if fs and not fa else None)
    if not s: return None
    def sec(pat, stop):
        m = re.search(pat, T, re.I)
        if not m: return []
        rest = T[m.end():]; st = re.search(stop, rest, re.I); seg = rest[:st.start()] if st else rest
        seg = re.sub(r"(?i)(TARGETS?|TP)\s*\d+\s*[:)\-]?", " ", seg); seg = re.sub(r"(?i)\b(T|E)\s*\d+\s*[:)\-]", " ", seg); seg = re.sub(r"(هدف|تارگت)\s*\d+\s*[:)\-]?", " ", seg)
        return nums(seg)
    ent = sec(r"(ENTRY|ENTER|ورود|قیمت ورود)", r"TARGET|TP|STOP|SL|هدف|تارگت|حد ضرر|استاپ")
    tgt = sec(r"(TARGETS?|TP\s*\d*|هدف\s*\d*|تارگت\s*\d*)", r"STOP|SL|حد ضرر|استاپ")
    sl = re.search(r"(STOP\s*LOSS|STOP|SL|حد ضرر|استاپ)[^0-9]*(\d[\d,]*(?:\.\d+)?)", T, re.I); lv = re.search(r"(?:LEVERAGE|لوریج|اهرم)[^0-9]*(\d+)|\((\d+)\s*[Xx]\)", T, re.I)
    if not ent: return None
    return {"sym": pm.group(1) + "USDT", "side": s, "entry": ent[0], "t": tgt[:4], "sl": float(sl.group(2).replace(",", "")) if sl else None, "lev": int((lv.group(1) or lv.group(2))) if lv else 1}

def candles_from(sym, t0, tf="15m"):
    sec = scan.TFSEC[tf]; end = min(scan.NOW(), t0 + 1000 * sec)
    try:
        j = scan.jget("https://api.gateio.ws/api/v4/spot/candlesticks", {"currency_pair": sym[:-4] + "_USDT", "interval": tf, "from": t0 - 2 * sec, "to": end})
        return [[int(a[0]) * 1000, float(a[5]), float(a[3]), float(a[4]), float(a[2])] for a in j]
    except Exception: return None

def evaluate(sig, c, t_post):
    L = sig["side"] == "long"; d = 1 if L else -1; e = sig["entry"]; sl = sig["sl"]; T = sig["t"]; px0 = c[0][4]
    res = {"late": bool(T) and ((px0 >= T[0]) if L else (px0 <= T[0])), "post_px": px0}
    mfe = max((x[2] / e - 1) * d if L else (1 - x[3] / e) for x in c) * 100; mae = min((x[3] / e - 1) if L else (1 - x[2] / e) for x in c) * 100
    res.update(mfe=round(mfe, 2), mae=round(mae, 2), now=round(((c[-1][4] / e - 1) * d) * 100, 2))
    if not (sl and T): res["status"] = "entry-only"; return res
    risk = abs(e - sl); liq = e * (1 - .9 / sig["lev"]) if L else e * (1 + .9 / sig["lev"]); filled = False
    for x in c:
        h, l = x[2], x[3]
        if not filled:
            if (h >= T[0]) if L else (l <= T[0]):
                if not ((l <= e) if L else (h >= e)): res["status"] = "missed"; return res
            if (l <= e) if L else (h >= e): filled = True
            else: continue
        if (l <= liq) if L else (h >= liq):
            if not ((l <= sl) if L else (h >= sl)) or (liq >= sl if L else liq <= sl): res.update(status="liquidated", R=-1.0); return res
        if (l <= sl) if L else (h >= sl): res.update(status="sl", R=-1.0); return res
        if (h >= T[0]) if L else (l <= T[0]): res.update(status="win", R=round(abs(T[0] - e) / risk, 2)); return res
    res["status"] = "open" if filled else "nofill"; return res

def audit_channel(name, limit=40):
    posts = fetch(name); sigs = []
    for p in posts[-limit:]:
        s = parse(p["text"])
        if s: sigs.append({**s, "post_t": p["t"], "url": p["url"]})
    out = []
    for s in sigs:
        c = candles_from(s["sym"], s["post_t"])
        if c and len(c) > 3: out.append({**{k: s[k] for k in ("sym", "side", "entry", "t", "sl", "lev", "post_t", "url")}, **evaluate(s, c, s["post_t"])})
        time.sleep(.3)
    full = [x for x in out if x["status"] in ("win", "sl", "liquidated")]; wins = [x for x in full if x["status"] == "win"]
    st = {"posts": len(posts), "signals": len(sigs), "evaluated": len(out), "closed": len(full), "win": round(100 * len(wins) / len(full), 1) if full else None,
          "avgR": round(sum(x["R"] for x in full) / len(full), 2) if full else None, "late": sum(1 for x in out if x.get("late")), "liq": sum(1 for x in out if x["status"] == "liquidated"),
          "entry_only": sum(1 for x in out if x["status"] == "entry-only"), "med_mae": round(statistics.median([x["mae"] for x in out]), 2) if out else None}
    return {"stats": st, "recent": sorted(out, key=lambda x: -x["post_t"])[:12]}

def run_watch():
    ch = scan.CFG.get("watch_channels", [])
    if not ch: print("watch: no channels configured"); return False
    res = {}
    for name in ch:
        try: res[name] = audit_channel(name)
        except Exception as e: print("watch failed", name, e)
    scan.save("competitors.json", {"updated": scan.NOW(), "channels": res}); print("watch ok:", list(res)); return True
