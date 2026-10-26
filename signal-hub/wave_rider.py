#!/usr/bin/env python3
"""Wave Rider - 1-minute momentum-wave scalper (PAPER account) with fully configurable parameters.
Setups: 'base' (price holds a floor/ceiling in a squeeze, then breaks with volume) and 'level' (break of the N-minute high/low).
Exits: 50% at half of the target, stop moves to break-even (risk-free), rest at the final target (or trailing 'ride'), time-out for dead waves.
Risk: position size comes from risk % and stop distance; leverage only sets the margin and is checked against the liquidation distance.
Needs an always-on machine:  python wave_rider.py --serve 8080   (set WAVE_TOKEN to allow editing settings from the web UI)"""
import os, sys, json, time, math, re, threading
import scan

DEF = dict(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "PAXGUSDT"], poll_sec=10, setups=["base", "level"], base_bars=15, max_base_pct=0.45, base_atr_mult=7.0, floor_touches=2, level_bars=60,
           vol_mult=1.8, close_strength=0.6, max_chase_pct=0.15, trend_filter=True, adaptive=True, atr_stop_mult=1.3, min_stop_pct=0.12, max_stop_pct=0.5, stop_pct=0.3, rr=2.0, target_pct=1.0,
           tp1_dist=0.5, tp1_close=0.5, risk_free=True, ride_mode="target", trail_atr=1.0, max_minutes=15, leverage=25, risk_pct=0.5, max_margin_pct=40, liq_buffer=0.5, min_target_cost_mult=3.0,
           fee_pct=0.05, slip_pct=0.02, max_trades_hour=4, cooldown_min=5, loss_streak_pause=3, pause_min=30, daily_loss_pct=3.0, kill_switch=False, start_equity=1000.0)
BOUNDS = dict(poll_sec=(3, 120), base_bars=(5, 60), max_base_pct=(0.05, 3), base_atr_mult=(2, 20), floor_touches=(1, 6), level_bars=(20, 240), vol_mult=(1, 6), close_strength=(0.3, 0.95), max_chase_pct=(0.02, 1),
              atr_stop_mult=(0.5, 4), min_stop_pct=(0.03, 1), max_stop_pct=(0.1, 3), stop_pct=(0.05, 3), rr=(1, 8), target_pct=(0.2, 10), tp1_dist=(0.2, 0.9), tp1_close=(0.1, 0.9), trail_atr=(0.3, 4),
              max_minutes=(3, 120), leverage=(1, 50), risk_pct=(0.05, 2), max_margin_pct=(5, 90), liq_buffer=(0.1, 0.9), min_target_cost_mult=(1, 10), fee_pct=(0, 0.3), slip_pct=(0, 0.3),
              max_trades_hour=(1, 30), cooldown_min=(0, 120), loss_streak_pause=(1, 10), pause_min=(1, 240), daily_loss_pct=(0.5, 20), start_equity=(10, 1e7))
BOOLS = ("trend_filter", "adaptive", "risk_free", "kill_switch"); ENUMS = {"ride_mode": ("target", "trail")}; SETUPS = ("base", "level")
cl = lambda x, a, b: max(a, min(b, x))

def params():
    P = dict(DEF); P.update(scan.CFG.get("wave", {})); return P
def sanitize(inp):
    out = {}
    for k, v in inp.items():
        if k in BOUNDS and isinstance(v, (int, float)) and not isinstance(v, bool): out[k] = cl(float(v), *BOUNDS[k])
        elif k in BOOLS and isinstance(v, bool): out[k] = v
        elif k in ENUMS and v in ENUMS[k]: out[k] = v
        elif k == "setups" and isinstance(v, list): out[k] = [x for x in v if x in SETUPS] or ["base"]
        elif k == "symbols" and isinstance(v, list): out[k] = [x.upper() for x in v if isinstance(x, str) and re.fullmatch(r"[A-Za-z0-9]{2,12}USDT", x)][:20] or DEF["symbols"]
    return out
def ema(a, n):
    k = 2 / (n + 1); e = a[0]
    for x in a[1:]: e = x * k + e * (1 - k)
    return e
def atr(c, n=14):
    s = 0.0
    for k in range(len(c) - n, len(c)):
        p = c[k - 1][4]; s += max(c[k][2] - c[k][3], abs(c[k][2] - p), abs(c[k][3] - p))
    return s / n
def agg5(c):
    out = []
    for i in range(len(c) % 5, len(c) - 4, 5): out.append(c[i + 4][4])
    return out

class Acct:
    def __init__(s, P): s.P = P; s.eq = P["start_equity"]; s.start = s.eq; s.closed = []; s.curve = []; s.day = None; s.eq0 = s.eq; s.entries = []; s.pause = 0; s.streak = 0; s.day_pnl = 0.0
    def tick(s, t):
        d = int(t // 86400)
        if d != s.day: s.day = d; s.eq0 = s.eq; s.day_pnl = 0.0
    def halted(s, t): return s.P["kill_switch"] or s.eq <= s.eq0 * (1 - s.P["daily_loss_pct"] / 100) or t < s.pause

class Rider:
    def __init__(s, sym, P, acct, notify=None): s.sym = sym; s.P = P; s.a = acct; s.c = []; s.pos = None; s.cool = 0; s.notify = notify or (lambda m: None); s.info = {}
    def on_candle(s, row, live=True):
        s.c.append(row); s.c = s.c[-700:]; t = row[0] / 1000; s.a.tick(t)
        if s.pos: s.manage(row)
        if live and not s.pos: s.scan(row)
        elif not s.pos: s.info = s.info or {}
    # ---------- entry logic ----------
    def scan(s, row):
        P, c = s.P, s.c; n = len(c); t = row[0] / 1000
        if n < max(P["level_bars"], P["base_bars"]) + 25: return
        close, h, l = row[4], row[2], row[3]; at = atr(c); atp = at / close * 100
        va = sum(x[5] for x in c[-21:-1]) / 20 or 1; vm = row[5] / va; rng = (h - l) or 1e-12
        ema9 = ema([x[4] for x in c[-30:]], 9); c5 = agg5(c[-130:]); e5 = ema(c5, 20) if len(c5) >= 20 else close
        B = c[-1 - P["base_bars"]:-1]; hi = max(x[2] for x in B); lo = min(x[3] for x in B); rp = (hi - lo) / lo * 100
        squeeze = rp <= P["max_base_pct"] or (hi - lo) / at <= P["base_atr_mult"]
        tl = sum(1 for x in B if x[3] <= lo + .25 * at); th = sum(1 for x in B if x[2] >= hi - .25 * at)
        LB = c[-1 - P["level_bars"]:-1]; hh = max(x[2] for x in LB); ll = min(x[3] for x in LB)
        s.info = {"price": close, "rng": round(rp, 3), "floor": tl, "ceil": th, "vm": round(vm, 2), "atrp": round(atp, 3), "squeeze": bool(squeeze), "trend": "up" if close >= e5 else "down",
                  "state": "ARMED" if squeeze and max(tl, th) >= P["floor_touches"] else "SQUEEZE" if squeeze else "IDLE", "to_hi": round((hi / close - 1) * 100, 3), "to_lo": round((close / lo - 1) * 100, 3)}
        if s.a.halted(t) or t < s.cool or len([x for x in s.a.entries if x > t - 3600]) >= P["max_trades_hour"]: return
        strength_l = (close - l) / rng; strength_s = (h - close) / rng
        for setup in P["setups"]:
            for side in ("long", "short"):
                L = side == "long"
                if P["trend_filter"] and ((L and close < e5) or ((not L) and close > e5)): continue
                if (L and close < ema9) or ((not L) and close > ema9): continue
                if vm < P["vol_mult"] or (strength_l if L else strength_s) < P["close_strength"]: continue
                if setup == "base":
                    if not squeeze or (tl if L else th) < P["floor_touches"]: continue
                    ok = close > hi if L else close < lo; ref = hi if L else lo
                else:
                    ok = close > hh if L else close < ll; ref = hh if L else ll
                if not ok or abs(close - ref) / close * 100 > P["max_chase_pct"]: continue
                p, why = s.plan(side, setup, close, at, lo, hi)
                if p: s.open(p, row); return
                s.info["skip"] = why
    def plan(s, side, setup, close, at, lo, hi):
        P = s.P; L = side == "long"; d = 1 if L else -1; slip = P["slip_pct"] / 100; ep = close * (1 + slip * d)
        sp = cl(P["atr_stop_mult"] * at / close * 100, P["min_stop_pct"], P["max_stop_pct"]) if P["adaptive"] else P["stop_pct"]
        sl = ep * (1 - d * sp / 100)
        if setup == "base": st = lo - .1 * at if L else hi + .1 * at; sl = min(sl, st) if L else max(sl, st)
        dist = abs(ep - sl); spct = dist / ep * 100
        if spct > max(P["max_stop_pct"], P["stop_pct"]) * 1.0 + 1e-9 and P["adaptive"]: return None, "stop wide"
        if spct > 90 / P["leverage"] * P["liq_buffer"]: return None, "stop too close to liquidation for this leverage"
        tdist = dist * P["rr"] if P["adaptive"] else ep * P["target_pct"] / 100
        cost = 2 * (P["fee_pct"] + P["slip_pct"]); tpct = tdist / ep * 100
        if tpct < P["min_target_cost_mult"] * cost: return None, f"target {tpct:.2f}% too small vs costs {cost:.2f}%"
        tgt = ep + d * tdist; tp1 = ep + d * tdist * P["tp1_dist"]
        risk_amt = s.a.eq * P["risk_pct"] / 100; notional = risk_amt / (dist / ep); margin = notional / P["leverage"]; mm = s.a.eq * P["max_margin_pct"] / 100
        if margin > mm: notional = mm * P["leverage"]; margin = mm
        if notional < 10: return None, "size too small"
        qty = notional / ep; liq = ep * (1 - d * 0.9 / P["leverage"])
        return {"side": side, "setup": setup, "entry": ep, "sl": sl, "stop": sl, "tp1": tp1, "tgt": tgt, "qty0": qty, "qty": qty, "margin": margin, "risk_amt": risk_amt, "liq": liq, "hi": ep, "lo": ep}, ""
    def open(s, p, row):
        P = s.P; t = row[0] / 1000; fee = P["fee_pct"] / 100 * p["entry"] * p["qty0"]; s.a.eq -= fee
        p.update(sym=s.sym, t_open=row[0], pnl=-fee, fees=fee, exits=[], tp1_hit=False, lev=P["leverage"]); s.pos = p; s.a.entries.append(t)
        s.notify(f"🌊 موج‌سوار (کاغذی) {'BUY' if p['side']=='long' else 'SELL'} {s.sym} [{p['setup']}]\nورود {scan.fp(p['entry'])} | SL {scan.fp(p['sl'])} ({abs(p['entry']-p['sl'])/p['entry']*100:.2f}٪)\nTP1 {scan.fp(p['tp1'])} (۵۰٪) | هدف {scan.fp(p['tgt'])}\nمارجین {p['margin']:.1f}$ با اهرم {P['leverage']}× | ریسک {P['risk_pct']}٪ ≈ {p['risk_amt']:.2f}$")
    # ---------- management ----------
    def realize(s, q, px, why, row):
        p = s.pos; d = 1 if p["side"] == "long" else -1; fee = s.P["fee_pct"] / 100 * px * q
        pnl = (px - p["entry"]) * d * q - fee
        if why == "LIQ": pnl = -p["margin"] * (q / p["qty0"]) - fee
        s.a.eq += pnl; s.a.day_pnl += pnl; p["pnl"] += pnl; p["fees"] += fee; p["qty"] -= q; p["exits"].append({"t": int(row[0] / 1000), "p": scan.fp(px), "q": round(q / p["qty0"], 3), "r": why})
    def manage(s, row):
        P, p = s.P, s.pos; L = p["side"] == "long"; d = 1 if L else -1; t, h, l, c = row[0], row[2], row[3], row[4]; slip = P["slip_pct"] / 100
        if t <= p["t_open"]: return
        done = False
        if (l <= p["liq"]) if L else (h >= p["liq"]): s.realize(p["qty"], p["liq"], "LIQ", row); done = True
        elif (l <= p["stop"]) if L else (h >= p["stop"]):
            s.realize(p["qty"], p["stop"] * (1 - slip * d), "TRAIL" if p.get("trailing") else "BE" if p["tp1_hit"] else "SL", row); done = True
        else:
            if not p["tp1_hit"] and ((h >= p["tp1"]) if L else (l <= p["tp1"])):
                s.realize(p["qty0"] * P["tp1_close"], p["tp1"], "TP1", row); p["tp1_hit"] = True
                if P["risk_free"]: p["stop"] = p["entry"] * (1 + d * (2 * P["fee_pct"] + P["slip_pct"]) / 100)
                s.notify(f"🛡️ {s.sym}: TP1 خورد ({int(P['tp1_close']*100)}٪ بسته شد)" + (" و حد ضرر به نقطهٔ ورود رفت (ریسک‌فری)" if P["risk_free"] else ""))
            if p["tp1_hit"] and P["ride_mode"] == "trail":
                p["trailing"] = True; ext = max(p["hi"], h) if L else min(p["lo"], l); p["hi"], p["lo"] = (ext, p["lo"]) if L else (p["hi"], ext); tr = ext - d * P["trail_atr"] * atr(s.c)
                p["stop"] = max(p["stop"], tr) if L else min(p["stop"], tr)
            elif p["tp1_hit"] and ((h >= p["tgt"]) if L else (l <= p["tgt"])): s.realize(p["qty"], p["tgt"], "TP2", row); done = True
            if not done and (t - p["t_open"]) / 60000 >= P["max_minutes"]: s.realize(p["qty"], c, "TIME", row); done = True
        if done or p["qty"] <= 1e-12:
            p["t_close"] = int(t / 1000); p["R"] = round(p["pnl"] / p["risk_amt"], 2); s.a.closed.append(p); s.a.curve.append([int(t / 1000), round(s.a.eq, 2)]); s.pos = None
            if p["pnl"] < 0: s.cool = t / 1000 + P["cooldown_min"] * 60; s.a.streak += 1
            else: s.a.streak = 0
            if s.a.streak >= P["loss_streak_pause"]: s.a.pause = t / 1000 + P["pause_min"] * 60; s.a.streak = 0
            s.notify(f"{'✅' if p['pnl']>0 else '❌'} {s.sym} {p['side']} بسته شد: {p['pnl']:+.2f}$ ({p['R']:+.2f}R) | {'، '.join(e['r'] for e in p['exits'])} | کارمزد {p['fees']:.2f}$")

def stats(closed, start):
    rs = [x["pnl"] for x in closed]; w = [x for x in rs if x > 0]; gp = sum(w); gl = -sum(x for x in rs if x < 0); eq = peak = start; dd = 0.0
    for x in rs: eq += x; peak = max(peak, eq); dd = max(dd, (peak - eq) / peak * 100)
    return {"n": len(rs), "win": round(100 * len(w) / len(rs), 1) if rs else None, "pf": round(gp / gl, 2) if gl else None, "net": round(sum(rs), 2), "avgR": round(sum(x["R"] for x in closed) / len(rs), 2) if rs else None,
            "fees": round(sum(x["fees"] for x in closed), 2), "max_dd": round(dd, 2), "liq": sum(1 for x in closed if any(e["r"] == "LIQ" for e in x["exits"])), "avg_min": round(sum((x["t_close"] - x["t_open"] / 1000) for x in closed) / len(rs) / 60, 1) if rs else None}
def costs(P):
    rt = 2 * (P["fee_pct"] + P["slip_pct"]); return {"rt_cost_pct": round(rt, 3), "rt_cost_on_margin_pct": round(rt * P["leverage"], 2), "liq_move_pct": round(90 / P["leverage"], 2), "move_1pct_on_margin": round(P["leverage"], 1)}

def backtest(candles, P):
    a = Acct(P); r = Rider("BT", P, a)
    for row in candles: r.on_candle(row, True)
    return {"stats": stats(a.closed, a.start), "closed": a.closed, "curve": a.curve, "eq": a.eq}

# ---------------- live daemon ----------------
def write_state(P, a, riders, halted_note=""):
    mt = 0.0; pos = []
    for r in riders.values():
        if r.pos and r.c:
            p = r.pos; d = 1 if p["side"] == "long" else -1; mt += (r.c[-1][4] - p["entry"]) * d * p["qty"]; pos.append({**{k: p[k] for k in ("sym", "side", "setup", "entry", "sl", "stop", "tp1", "tgt", "margin", "tp1_hit", "risk_amt", "pnl")}, "now": r.c[-1][4], "mins": round((r.c[-1][0] - p["t_open"]) / 60000, 1)})
    P = riders[next(iter(riders))].P if riders else params()
    scan.save("wave.json", {"updated": scan.NOW(), "config": P, "costs": costs(P), "equity": round(a.eq, 2), "eq_mtm": round(a.eq + mt, 2), "start_equity": a.start, "day_pnl": round(a.day_pnl, 2), "halted": a.halted(time.time()), "paused_until": a.pause,
                            "symbols": {s: r.info for s, r in riders.items() if r.info}, "positions": pos, "closed": a.closed[-60:], "curve": a.curve[-300:], "stats": stats(a.closed, a.start)})
def daemon(serve=None):
    P = params(); a = Acct(P); riders = {s: Rider(s, P, a, scan.tg) for s in P["symbols"]}; last = {}
    st = scan.load("wave_state.json", None)
    if st: a.eq, a.start, a.closed, a.curve = st["eq"], st["start"], st["closed"][-200:], st["curve"][-300:]
    if serve: threading.Thread(target=serve_http, args=(serve,), daemon=True).start()
    print("wave daemon: symbols", list(riders), "| paper account", round(a.eq, 2))
    while True:
        try:
            P = params(); a.P = P
            for s in P["symbols"]:
                if s not in riders: riders[s] = Rider(s, P, a, scan.tg)
            for s in list(riders):
                r = riders[s]; r.P = P; warm = s not in last
                c = scan.klines(s, "1m", 500 if warm else 120, min_n=30)
                if not c: continue
                if c[-1][0] / 1000 + 60 > time.time(): c = c[:-1]
                for row in c:
                    if row[0] > last.get(s, 0): r.on_candle(row, live=(not warm) and time.time() - row[0] / 1000 < 120); last[s] = row[0]
            write_state(P, a, riders); scan.save("wave_state.json", {"eq": a.eq, "start": a.start, "closed": a.closed[-200:], "curve": a.curve[-300:]})
        except Exception as e: print("loop error:", repr(e))
        time.sleep(P["poll_sec"])

def serve_http(port):
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    token = os.getenv("WAVE_TOKEN", "")
    class H(SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
        def _j(self, code, obj): b = json.dumps(obj, ensure_ascii=False).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            if self.path.startswith("/api/config"): return self._j(200, {"wave": params(), "bounds": BOUNDS, "editable": bool(token)})
            return super().do_GET()
        def do_POST(self):
            if not token or self.headers.get("X-Token") != token: return self._j(403, {"ok": False, "error": "token"})
            try: inp = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except Exception: return self._j(400, {"ok": False})
            if self.path.startswith("/api/config"):
                cfg = json.load(open("config.json", encoding="utf-8")); cfg.setdefault("wave", {}).update(sanitize(inp)); json.dump(cfg, open("config.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1); scan.CFG.update(cfg); return self._j(200, {"ok": True, "wave": params()})
            if self.path.startswith("/api/kill"):
                cfg = json.load(open("config.json", encoding="utf-8")); cfg.setdefault("wave", {})["kill_switch"] = bool(inp.get("on")); json.dump(cfg, open("config.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1); scan.CFG.update(cfg); return self._j(200, {"ok": True})
            self._j(404, {"ok": False})
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()

if __name__ == "__main__":
    a = sys.argv[1:]; daemon(int(a[a.index("--serve") + 1]) if "--serve" in a else None)
