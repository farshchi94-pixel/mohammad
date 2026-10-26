"""Consensus engine: six independent agents vote; a signal fires only when >= N agree and nothing vetoes.
Branch 1: exchange coins. Branch 2: Solana/DEX tokens (from tracked wallets). Results are PAPER-traded and recorded honestly."""
import time
import scan

AGENTS = ["TECH", "TREND", "MARKET", "SMART$", "DERIV", "RISK"]
FA = {"TECH": "تکنیکال (ویل پرو)", "TREND": "روند ۴ساعته", "MARKET": "بازار (BTC و ترس/طمع)", "SMART$": "پول هوشمند Hyperliquid", "DERIV": "مشتقات (فاندینگ و لانگ/شورت)", "RISK": "ریسک رویداد و آنلاک"}

def _atr(c, n=14):
    s = 0.0
    for k in range(len(c) - n, len(c)):
        p = c[k - 1][4]; s += max(c[k][2] - c[k][3], abs(c[k][2] - p), abs(c[k][3] - p))
    return s / n

def deriv(sym):
    """Gate futures: funding rate + long/short account ratio (best effort; tolerant to missing fields)."""
    base = sym[:-4] + "_USDT"
    f = float(scan.jget(f"https://api.gateio.ws/api/v4/futures/usdt/contracts/{base}").get("funding_rate", 0) or 0)
    lsr = 1.0; oi = None
    try:
        st = scan.jget("https://api.gateio.ws/api/v4/futures/usdt/contract_stats", {"contract": base, "interval": "1h", "limit": 6})
        if st:
            lsr = float(st[-1].get("lsr_account") or st[-1].get("lsr_taker") or 1.0)
            o = [float(x.get("open_interest_usd") or x.get("open_interest") or 0) for x in st]
            oi = (o[-1] / o[0] - 1) * 100 if o[0] else None
    except Exception: pass
    return {"funding": f, "lsr": lsr, "oi_chg": oi}

def agent_votes(sym, side, d, dv):
    """d: dict with inputs. Returns list of {n, ok, t} in AGENTS order."""
    L = side == "long"; coin = sym.replace("USDT", ""); out = []
    a = d["analysis"].get(sym) or {}; wp = (d["wp"].get(sym) or {})
    s_wp = wp.get("signal") or wp.get("open")
    if s_wp and s_wp.get("side") == side: ok, t = True, "ویل پرو: " + ("سیگنال تازه" if wp.get("signal") else "پوزیشن باز هم‌جهت")
    elif a.get("state") == "fired" and a.get("dir") == side: ok, t = True, "مدل ۴ساعته+۱۵دقیقه تأیید کامل"
    else: ok, t = False, f"تأیید ۱۵دقیقه کامل نیست ({a.get('okn', 0)} از ۵)" if a else "داده تکنیکال نیست"
    out.append({"n": "TECH", "ok": ok, "t": t})
    sc = a.get("score", 0); ok = a.get("dir") == side and abs(sc) >= 3
    out.append({"n": "TREND", "ok": ok, "t": f"جهت ۴ساعته {'صعودی' if a.get('dir')=='long' else 'نزولی' if a.get('dir')=='short' else 'خنثی'} (امتیاز {sc})" if a else "داده نیست"})
    bd = d["btcDir"]; fng = d.get("fng"); ok = (bd == side) if sym == "BTCUSDT" else (bd in (side, "neutral"))
    if fng is not None and ((L and fng > 80) or ((not L) and fng < 20)): ok = False
    out.append({"n": "MARKET", "ok": ok, "t": f"BTC {'صعودی' if bd=='long' else 'نزولی' if bd=='short' else 'خنثی'} | ترس و طمع {fng}"})
    n = d["hl"].get(coin)
    if n and n["wallets"] >= 2 and n["long"] + n["short"] > 0:
        imb = (n["long"] - n["short"]) / (n["long"] + n["short"]); ok = (imb >= .25) if L else (imb <= -.25)
        out.append({"n": "SMART$", "ok": ok, "t": f"{n['wallets']} کیف پول: لانگ ${n['long']:,} | شورت ${n['short']:,}"})
    else: out.append({"n": "SMART$", "ok": False, "t": "داده Hyperliquid برای این ارز کافی نیست"})
    if dv is None: out.append({"n": "DERIV", "ok": False, "t": "بررسی نشد (رأی‌های دیگر کافی نبود) یا داده فیوچرز نیست"})
    else:
        f, lsr = dv["funding"], dv["lsr"]
        ok = (f < .0003 and lsr < 1.25 and (f <= .0001 or lsr <= 1.05)) if L else (f > -.0001 and lsr > .8 and (f >= .0001 or lsr >= 1.2))
        out.append({"n": "DERIV", "ok": ok, "t": f"فاندینگ {f*100:.3f}٪ | نسبت لانگ/شورت {lsr:.2f}" + (f" | OI {dv['oi_chg']:+.1f}٪" if dv.get("oi_chg") is not None else "")})
    now = scan.NOW(); veto = any(b[0] <= now * 1000 <= b[1] + 30 * 60 * 1000 for b in d["blackouts"]); unl = [u for u in d["unlocks"] if u["sym"] == coin and 0 <= (u["t"] - now) < 3 * 86400]
    out.append({"n": "RISK", "ok": not veto and not unl, "t": "بلک‌اوت خبر فعال است" if veto else (f"آنلاک توکن تا {int((unl[0]['t']-now)/3600)} ساعت دیگر" if unl else "رویداد پرریسک نزدیک نیست")})
    return out, veto

def _load_inputs():
    sg = scan.load("signals.json", {}); wp = scan.load("whalepro.json", {}); wh = scan.load("whales.json", {}); mk = scan.load("market.json", {}); cd = scan.load("candles.json", {})
    unl = []
    for u in scan.CFG.get("unlocks", []):
        try: unl.append({"sym": u["sym"], "t": int(time.mktime(time.strptime(u["date"], "%Y-%m-%d")))})
        except Exception: pass
    return {"analysis": sg.get("analysis", {}), "btcDir": (sg.get("ctx") or {}).get("btcDir", "neutral"), "fng": (sg.get("ctx") or {}).get("fng"), "wp": wp.get("symbols", {}),
            "hl": {n["coin"]: n for n in ((wh.get("hl") or {}).get("net") or [])}, "blackouts": mk.get("blackouts", []), "unlocks": unl, "candles": cd.get("c", {}), "sg": sg, "wh": wh}

def plan(sym, side, d):
    c = d["candles"].get(sym); a = d["analysis"].get(sym) or {}
    if not c or len(c) < 20: return None
    px = c[-1][4]; at = _atr(c); L = side == "long"; dd = 1 if L else -1; risk = max(1.5 * at, px * .006)
    T = [px + dd * risk * m for m in (1, 2, 3)]
    return {"entry": scan.fp(px), "e2": scan.fp(px - dd * .3 * risk), "sl": scan.fp(px - dd * risk), "risk": risk, "T": [scan.fp(t) for t in T], "R": [1.0, 2.0, 3.0]}

def run_consensus():
    d = _load_inputs(); cfg = scan.CFG; need = cfg.get("consensus_min", 4); prev = scan.load("consensus.json", {"funnel": {"scans": 0, "considered": 0, "ge3": 0, "fired": 0}})
    sg = d["sg"]; op = sg.get("open", []); closed = sg.get("closed", []); syms = sorted(d["analysis"].keys()); res = {}; fired_now = []; ge3 = 0; considered = 0
    for sym in syms:
        sides = {}
        for side in ("long", "short"):
            votes, veto = agent_votes(sym, side, d, None); pre = sum(v["ok"] for v in votes)
            if pre >= 2 and not veto:
                try: dv = deriv(sym)
                except Exception: dv = None
                if dv: votes, veto = agent_votes(sym, side, d, dv)
            n = sum(v["ok"] for v in votes); considered += 1; ge3 += n >= 3
            sides[side] = {"n": n, "veto": veto, "agents": votes}
        res[sym] = sides
        side = max(("long", "short"), key=lambda s: sides[s]["n"]); sd = sides[side]
        busy = any(o["sym"] == sym for o in op) or any(x["sym"] == sym and x.get("tier") == "consensus" and scan.NOW() - x.get("closed_at", 0) < 4 * 3600 for x in closed[-80:])
        req_ok = all(any(v["n"] == r and v["ok"] for v in sd["agents"]) for r in cfg.get("consensus_required", ["TECH"]))
        if sd["n"] >= need and req_ok and not sd["veto"] and sides["long"]["n"] != sides["short"]["n"] and not busy:
            p = plan(sym, side, d)
            if p:
                s = {"id": f"{sym}-C{scan.NOW()}", "sym": sym, "side": side, "tier": "consensus", "entry": p["entry"], "e2": p["e2"], "sl": p["sl"], "risk": p["risk"], "T": p["T"], "R": p["R"],
                     "okn": sd["n"], "bias": (d["analysis"].get(sym) or {}).get("score", 0), "t_open": scan.NOW(), "last_t": d["candles"][sym][-1][0] * 1000, "status": "open", "hits": [],
                     "agents": [{"n": v["n"], "ok": v["ok"]} for v in sd["agents"]]}
                op.append(s); fired_now.append(s); print("CONSENSUS", sym, side, f"{sd['n']}/6")
    f = prev.get("funnel", {}); f = {"scans": f.get("scans", 0) + 1, "considered": f.get("considered", 0) + considered, "ge3": f.get("ge3", 0) + ge3, "fired": f.get("fired", 0) + len(fired_now)}
    if fired_now:
        sg["open"] = op; sg["stats"] = scan.stats(closed); scan.save("signals.json", sg)
    import card
    for s in fired_now:
        L = s["side"] == "long"; ag = "\n".join(f"{'✅' if v['ok'] else '⬜'} {FA[v['n']]}: {v['t']}" for v in res[s["sym"]][s["side"]]["agents"])
        cap = f"{'🟢 BUY' if L else '🔴 SELL'} {s['sym']} | اجماع {s['okn']} از ۶ (کاغذی)\nورود: {s['entry']} | SL: {s['sl']}\nاهداف: {' / '.join(str(t) for t in s['T'])}\n{ag}\n⚠️ توصیهٔ مالی نیست."
        rows = d["candles"].get(s["sym"], [])[-60:]
        scan.tg_photo(card.signal_card(s["sym"], "15m", s["side"], rows, s["entry"], s["sl"], s["T"][0], s["T"][1], f"Consensus {s['okn']}/6", scan.NOW(), s["id"][-8:]) if rows else None, cap)
    top = sorted(res.items(), key=lambda kv: -max(kv[1]["long"]["n"], kv[1]["short"]["n"]))[:30]
    scan.save("consensus.json", {"updated": scan.NOW(), "need": need, "funnel": f, "last": {"considered": considered, "ge3": ge3, "fired": len(fired_now)}, "symbols": dict(top), "agents": FA,
                                 "fired_now": [s["id"] for s in fired_now]})
    print(f"consensus ok: {considered} pairs, {ge3} with >=3 votes, {len(fired_now)} fired")
    return True

# ---------------- Branch 2: Solana / DEX tokens ----------------
def run_dex_consensus():
    cfg = scan.CFG; wh = scan.load("whales.json", {}); evs = [e for e in ((wh.get("sol") or {}).get("events") or []) if e["side"] == "buy" and scan.NOW() - e["ts"] < 86400]
    prev = scan.load("dex_consensus.json", {"tokens": {}}); tok = prev.get("tokens", {}); by = {}
    for e in evs: b = by.setdefault(e["mint"], {"w": set(), "usd": 0, "sym": e.get("symbol", "?")}); b["w"].add(e["wallet"]); b["usd"] += e["usd"]
    min_liq = cfg.get("dex_min_liq", 100000); need = cfg.get("dex_min_votes", 4); fired = []
    for mint, b in by.items():
        try:
            ps = scan.jget(f"https://api.dexscreener.com/latest/dex/tokens/{mint}").get("pairs") or []
            if not ps: continue
            p = max(ps, key=lambda x: (x.get("liquidity") or {}).get("usd", 0)); liq = (p.get("liquidity") or {}).get("usd", 0); v24 = (p.get("volume") or {}).get("h24", 0); pc = p.get("priceChange") or {}; px = float(p.get("priceUsd") or 0)
        except Exception as ex: print("dex info failed", mint[:6], ex); continue
        risks = []; known = False
        try:
            j = scan.jget(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary"); known = True; risks = j.get("risks") or []
        except Exception: pass
        danger = [r for r in risks if r.get("level") == "danger"]; conc = [r for r in risks if any(k in (r.get("name", "") + r.get("description", "")).lower() for k in ("holder", "concentrat", "creator", "top "))]
        votes = [("نهنگ", b["usd"] >= cfg.get("sol_min_usd", 2000), f"خرید خالص ≈ ${b['usd']:,}"), ("چند کیف پول", len(b["w"]) >= 2, f"{len(b['w'])} کیف پول رصدشده"),
                 ("امنیت", known and not danger, "RugCheck: " + ("خطرناک: " + ", ".join(r.get("name", "") for r in danger) if danger else "مورد خطرناک نیست" if known else "در دسترس نیست")),
                 ("نقدشوندگی", liq >= min_liq and (not liq or v24 / liq <= 20), f"نقدشوندگی ${liq:,.0f} | حجم ۲۴س/نقدشوندگی {(v24/liq if liq else 0):.1f}"),
                 ("مومنتوم", (pc.get("h1") or 0) >= 0 and (pc.get("h24") or 0) <= 200, f"۱س {pc.get('h1')}٪ | ۲۴س {pc.get('h24')}٪ (دیر نشده باشد)"),
                 ("توزیع", known and not conc, "تمرکز دارندگان/سازنده: " + ("هشدار" if conc else "هشدار مشخصی نیست" if known else "نامشخص"))]
        n = sum(1 for _, ok, _ in votes if ok); t = tok.get(mint)
        rec = {"mint": mint, "symbol": b["sym"], "n": n, "veto": bool(danger), "votes": [{"n": a, "ok": ok, "t": s} for a, ok, s in votes], "px": px, "liq": liq, "url": p.get("url"), "last_t": scan.NOW()}
        if t: rec.update({k: t[k] for k in ("first_t", "entry_px", "mfe", "mae", "fired") if k in t})
        if n >= need and not danger and not rec.get("fired"):
            rec.update(fired=True, first_t=scan.NOW(), entry_px=px, mfe=0.0, mae=0.0); fired.append(rec)
        elif rec.get("fired") and rec.get("entry_px") and px:
            ch = (px / rec["entry_px"] - 1) * 100; rec["mfe"] = max(rec.get("mfe", 0), ch); rec["mae"] = min(rec.get("mae", 0), ch); rec["now"] = round(ch, 1)
        tok[mint] = rec
    for r in fired:
        ag = "\n".join(f"{'✅' if v['ok'] else '⬜'} {v['n']}: {v['t']}" for v in r["votes"])
        scan.tg(f"🧪 اجماع DEX {r['n']} از ۶ (پایش کاغذی): {r['symbol']}\n{ag}\n{r.get('url','')}\n⚠️ توکن تازه؛ ریسک رج‌پول. توصیهٔ مالی نیست.")
    keep = sorted(tok.values(), key=lambda x: -x["last_t"])[:40]
    scan.save("dex_consensus.json", {"updated": scan.NOW(), "need": need, "tokens": {r["mint"]: r for r in keep}, "note": "نیاز به کیف پول‌های سولانا در config.json و کلید Helius"})
    print(f"dex consensus ok: {len(by)} tokens, {len(fired)} fired"); return True
