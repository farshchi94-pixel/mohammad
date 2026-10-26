"""Auto-trader (PAPER account) + webhook forwarder. Takes fresh signals, sizes them by risk %, manages SL/TPs on real candles,
and keeps an honest virtual account (fees + slippage). Optionally forwards every new signal to YOUR OWN webhook bot.
No direct exchange orders are placed by this file."""
import json, time
import scan

D = dict(mode="paper", start_equity=1000.0, risk_pct=0.5, max_open=3, max_leverage=3.0, fee_pct=0.05, slip_pct=0.03, daily_loss_pct=2.0, kill_switch=False,
         sources=["whalepro", "consensus"], min_votes=4, be_after_tp1=True, webhook_url="", webhook_headers={}, webhook_body='{"id":"{id}","action":"{action}","symbol":"{symbol}","entry":{entry},"sl":{sl},"tp1":{tp1},"tp2":{tp2},"risk_pct":{risk_pct},"source":"{source}"}')
def cfg(): c = dict(D); c.update(scan.CFG.get("trading", {})); return c

def collect():
    """Fresh signals from the other modules -> normalized dicts."""
    out = []; wp = scan.load("whalepro.json", {}); sg = scan.load("signals.json", {})
    for sym, d in (wp.get("symbols") or {}).items():
        s = d.get("signal")
        if s: out.append({"id": f"WP-{sym}-{s['t']}", "src": "whalepro", "sym": sym, "side": s["side"], "sl": s["sl"], "tps": [(s["t1"], .6), (s["t2"], .4)]})
    for s in sg.get("open", []):
        if s.get("tier") == "consensus" and s.get("okn", 0) >= cfg()["min_votes"] and not s.get("hits"):
            out.append({"id": "C-" + s["id"], "src": "consensus", "sym": s["sym"], "side": s["side"], "sl": s["sl"], "tps": [(s["T"][0], .4), (s["T"][1], .3), (s["T"][2], .3)]})
    return [x for x in out if x["src"] in cfg()["sources"]]

def webhook(sig, risk_pct):
    c = cfg(); u = c["webhook_url"]
    if not u: return False
    L = sig["side"] == "long"; tp = [t for t, _ in sig["tps"]]
    body = c["webhook_body"]
    for k, v in {"id": sig["id"], "action": "buy" if L else "sell", "symbol": sig["sym"], "entry": "null", "sl": sig["sl"], "tp1": tp[0], "tp2": tp[1] if len(tp) > 1 else tp[0], "risk_pct": risk_pct, "source": sig["src"]}.items():
        body = body.replace("{" + k + "}", str(v))
    try:
        r = scan.requests.post(u, data=body.encode(), headers={"Content-Type": "application/json", **c["webhook_headers"]}, timeout=20); print("webhook", sig["id"], r.status_code); return r.ok
    except Exception as e: print("webhook failed", e); return False

def _px(sym, cache):
    if sym not in cache: cache[sym] = scan.klines(sym, "15m", 100)
    return cache[sym]

def manage(p, c, st, cf):
    """advance one open position on candles after p['last_t']; returns True when fully closed."""
    L = p["side"] == "long"; d = 1 if L else -1; fee = cf["fee_pct"] / 100; slip = cf["slip_pct"] / 100
    def realize(q, px, why):
        pnl = (px - p["entry"]) * d * q - fee * px * q; st["equity"] += pnl; p["pnl"] += pnl; p["qty_open"] -= q; p["exits"].append({"t": scan.NOW(), "p": scan.fp(px), "q": round(q, 8), "r": why})
    for row in c:
        t, h, l = row[0], row[2], row[3]
        if t <= p["last_t"]: continue
        p["last_t"] = t
        if (l <= p["stop"]) if L else (h >= p["stop"]):
            realize(p["qty_open"], p["stop"] * (1 - slip * d), "BE" if p["stop"] == p["entry"] else "SL"); return True
        for i, (tp, w) in enumerate(p["tps"]):
            if i not in p["hits"] and ((h >= tp) if L else (l <= tp)) and p["qty_open"] > 1e-12:
                q = min(p["qty_open"], p["qty0"] * w) if i < len(p["tps"]) - 1 else p["qty_open"]; realize(q, tp, f"TP{i+1}"); p["hits"].append(i)
        if p["qty_open"] <= 1e-12: return True
        if cf["be_after_tp1"] and p["hits"] and p["stop"] != p["entry"]: p["stop"] = p["entry"]
    if scan.NOW() - p["t_open"] > 48 * 3600 and c:
        realize(p["qty_open"], c[-1][4], "TimeOut"); return True
    return False

def run_trader():
    cf = cfg()
    if cf["mode"] == "off": print("trader: off"); return False
    st = scan.load("paper.json", {"equity": cf["start_equity"], "start_equity": cf["start_equity"], "start": scan.NOW(), "positions": [], "closed": [], "curve": [], "seen": [], "day": {}, "webhooked": []})
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if st["day"].get("d") != today: st["day"] = {"d": today, "eq0": st["equity"]}
    cache = {}; still = []
    for p in st["positions"]:
        c = _px(p["sym"], cache)
        if c and manage(p, c, st, cf):
            tot = round(p["pnl"], 2); p["R"] = round(p["pnl"] / p["risk_amt"], 2); p["closed_at"] = scan.NOW(); st["closed"].append(p)
            scan.tg(f"{'✅' if p['pnl'] > 0 else '❌'} حساب کاغذی: {p['sym']} {p['side']} بسته شد | {tot:+.2f}$ ({p['R']:+.2f}R) | {'، '.join(e['r'] for e in p['exits'])}")
        else: still.append(p)
    st["positions"] = still
    halted = cf["kill_switch"] or st["equity"] <= st["day"]["eq0"] * (1 - cf["daily_loss_pct"] / 100)
    for s in collect():
        if s["id"] in st["seen"]: continue
        st["seen"].append(s["id"])
        if cf["mode"] in ("webhook", "both") and s["id"] not in st["webhooked"]:
            if webhook(s, cf["risk_pct"]): st["webhooked"].append(s["id"])
        if cf["mode"] not in ("paper", "both"): continue
        if halted: print("trader: halted (kill switch / daily loss) -", s["id"]); continue
        if len(st["positions"]) >= cf["max_open"] or any(p["sym"] == s["sym"] for p in st["positions"]): print("trader: skip", s["id"]); continue
        c = _px(s["sym"], cache)
        if not c: continue
        L = s["side"] == "long"; d = 1 if L else -1; slip = cf["slip_pct"] / 100; ep = c[-1][4] * (1 + slip * d); dist = abs(ep - s["sl"])
        if dist / ep < 0.001 or ((ep - s["sl"]) * d) <= 0: print("trader: bad stop", s["id"]); continue
        risk_amt = st["equity"] * cf["risk_pct"] / 100; qty = risk_amt / dist; qty = min(qty, st["equity"] * cf["max_leverage"] / ep)
        if qty * ep < 10: continue
        st["equity"] -= cf["fee_pct"] / 100 * ep * qty
        pos = {"id": s["id"], "sym": s["sym"], "side": s["side"], "src": s["src"], "entry": scan.fp(ep), "sl": s["sl"], "stop": s["sl"], "tps": s["tps"], "qty0": qty, "qty_open": qty, "risk_amt": risk_amt, "t_open": scan.NOW(), "last_t": c[-1][0],
               "hits": [], "exits": [], "pnl": -cf["fee_pct"] / 100 * ep * qty}
        st["positions"].append(pos); scan.tg(f"📒 حساب کاغذی: {s['sym']} {'خرید' if L else 'فروش'} | ورود {pos['entry']} | SL {s['sl']} | ریسک {cf['risk_pct']}٪ ≈ {risk_amt:.2f}$")
    mtm = 0.0
    for p in st["positions"]:
        c = _px(p["sym"], cache)
        if c: p["now"] = scan.fp(c[-1][4]); mtm += ((c[-1][4] - p["entry"]) * (1 if p["side"] == "long" else -1)) * p["qty_open"]
    eq = st["equity"] + mtm
    if not st["curve"] or abs(st["curve"][-1][1] - eq) > 1e-9 and scan.NOW() - st["curve"][-1][0] > 600: st["curve"].append([scan.NOW(), round(eq, 2)])
    st["curve"] = st["curve"][-500:]; st["seen"] = st["seen"][-400:]; st["webhooked"] = st["webhooked"][-400:]; st["closed"] = st["closed"][-200:]
    cl = st["closed"]; wins = [x for x in cl if x["pnl"] > 0]; gp = sum(x["pnl"] for x in wins); gl = -sum(x["pnl"] for x in cl if x["pnl"] < 0); peak = dd = 0.0
    for _, v in st["curve"]: peak = max(peak, v); dd = max(dd, (peak - v) / peak * 100 if peak else 0)
    out = {k: st[k] for k in ("equity", "start_equity", "start", "positions", "closed", "curve", "seen", "day", "webhooked")}
    out.update(updated=scan.NOW(), equity_mtm=round(eq, 2), halted=bool(halted), mode=cf["mode"], cfg={k: cf[k] for k in ("risk_pct", "max_open", "max_leverage", "fee_pct", "slip_pct", "daily_loss_pct", "sources")},
               stats={"n": len(cl), "win": round(100 * len(wins) / len(cl), 1) if cl else None, "pf": round(gp / gl, 2) if gl else None, "ret_pct": round((eq / st["start_equity"] - 1) * 100, 2), "max_dd": round(dd, 2)})
    scan.save("paper.json", out); print(f"trader ok: equity {eq:.2f}, open {len(st['positions'])}, closed {len(cl)}"); return True
