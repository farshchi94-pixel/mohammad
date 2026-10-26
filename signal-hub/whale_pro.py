"""Whale Pro V3.10 - faithful Python port of the user's Pine strategy (same inputs, same bar-by-bar state machine).
Execution model mimics TradingView: orders placed at bar close fill at NEXT bar open; exits are evaluated inside the bar
along the OHLC path (O-H-L-C if high is closer to open, else O-L-H-C); BE stop moves from the next bar.
"""
import datetime, math

DEFAULT = dict(enable=True, stop_pct=0.6, tp1_pct=0.35, tp2_pct=0.9, use_timeout=True, max_bars_open=100, session_filter="Always",
    use_adx=True, min_adx_val=22, trend_mode="Soft", use_volume=True, vol_ratio=1.3, min_confluence=2, model="Hybrid", sr_len=18,
    pullback_bars=4, max_trades=50, use_confirm_candle=True, use_avoid_hours=False, avoid_start_hour=0, avoid_end_hour=4,
    use_breakeven=True, use_cooldown=True, cooldown_after_losses=2, cooldown_bars=4,
    use_mw_pattern=False, mw_pivot_len=5, mw_tolerance_pct=0.3, mw_as_filter_only=False, commission=0.04, alloc=0.30,
    # ---- optional professional upgrades (all OFF by default = identical to the Pine script) ----
    stop_mode="pct", atr_mult_stop=1.5, atr_mult_tp1=0.8, atr_mult_tp2=2.0, htf_filter=False, htf_ema=50, daily_loss_pct=0.0, blackouts=None)

# ---------- Pine-exact indicators (None = na) ----------
def sma_s(a, n):
    out = [None] * len(a); run = 0.0; cnt = 0
    for i, x in enumerate(a):
        if x is None: run = 0.0; cnt = 0; continue
        run += x; cnt += 1
        if cnt > n: run -= a[i - n]; cnt = n
        if cnt == n: out[i] = run / n
    return out
def _seeded(a, n, alpha):
    out = [None] * len(a); prev = None; buf = []
    for i, x in enumerate(a):
        if x is None: prev = None; buf = []; continue
        if prev is None:
            buf.append(x)
            if len(buf) == n: prev = sum(buf) / n; out[i] = prev
        else:
            prev = alpha * x + (1 - alpha) * prev; out[i] = prev
    return out
def ema_s(a, n): return _seeded(a, n, 2 / (n + 1))
def rma_s(a, n): return _seeded(a, n, 1 / n)
def tr_s(h, l, c):
    return [None] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(h))]
def rsi_s(c, n=14):
    up = [None] + [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    dn = [None] + [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    u, d = rma_s(up, n), rma_s(dn, n); out = []
    for a, b in zip(u, d):
        out.append(None if a is None else (100.0 if b == 0 else (0.0 if a == 0 else 100 - 100 / (1 + a / b))))
    return out
def adx_s(h, l, c, n=14):
    N = len(h); tr = tr_s(h, l, c); pdm = [None] * N; mdm = [None] * N
    for i in range(1, N):
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm[i] = up if (up > dn and up > 0) else 0.0; mdm[i] = dn if (dn > up and dn > 0) else 0.0
    trr, pr, mr = rma_s(tr, n), rma_s(pdm, n), rma_s(mdm, n); dx = [None] * N
    for i in range(N):
        if trr[i] is None or pr[i] is None or mr[i] is None: continue
        p, m = 100 * pr[i] / trr[i], 100 * mr[i] / trr[i]; s = p + m
        dx[i] = abs(p - m) / (1 if s == 0 else s)
    return [None if v is None else 100 * v for v in rma_s(dx, n)]
def highest_s(a, n):
    return [None if i < n - 1 else max(a[i - n + 1:i + 1]) for i in range(len(a))]
def lowest_s(a, n):
    return [None if i < n - 1 else min(a[i - n + 1:i + 1]) for i in range(len(a))]

def _gt(a, b): return a is not None and b is not None and a > b
def _lt(a, b): return a is not None and b is not None and a < b
def _ge(a, b): return a is not None and b is not None and a >= b

def run(candles, params=None, htf=None, htf_sec=14400):
    P = dict(DEFAULT); P.update(params or {}); n = len(candles)
    T = [x[0] for x in candles]; O = [x[1] for x in candles]; Hh = [x[2] for x in candles]; Lw = [x[3] for x in candles]; C = [x[4] for x in candles]; V = [x[5] for x in candles]
    ema8, ema21, ema55, ema200 = ema_s(C, 8), ema_s(C, 21), ema_s(C, 55), ema_s(C, 200)
    rsi = rsi_s(C, 14); adx = adx_s(Hh, Lw, C, 14)
    e12, e26 = ema_s(C, 12), ema_s(C, 26)
    macd = [None if a is None or b is None else a - b for a, b in zip(e12, e26)]; sig = ema_s(macd, 9)
    vma = sma_s(V, 20); res = highest_s(Hh, P["sr_len"]); sup = lowest_s(Lw, P["sr_len"])
    atr14 = rma_s(tr_s(Hh, Lw, C), 14)
    # higher-timeframe trend state per bar (uses only HTF candles that are already CLOSED at the bar's open)
    htf_state = [0] * n
    if P["htf_filter"] and htf:
        hc = [x[4] for x in htf]; he = ema_s(hc, P["htf_ema"]); closes_t = [x[0] + htf_sec * 1000 for x in htf]; j = -1
        for i in range(n):
            while j + 1 < len(htf) and closes_t[j + 1] <= T[i]: j += 1
            if j >= 0 and he[j] is not None: htf_state[i] = 1 if hc[j] > he[j] else -1 if hc[j] < he[j] else 0
    bl = P["blackouts"] or []; day_pnl = 0.0
    stop, tp1p, tp2p, comm = P["stop_pct"] / 100, P["tp1_pct"] / 100, P["tp2_pct"] / 100, P["commission"] / 100
    # state
    pos = None; pend_entry = None; pend_close = False; closed_cnt = 0; prev_closed = 0; last_profit = 0.0
    loss_streak = 0; cooldown_until = 0; bsc = 999; lcu = False
    sp_long = sp_short = False; sl_level = ss_level = None; sl_mw = ss_mw = False
    bars_in = 0; entry_qty = None; entry_price = None; be_moved = False; day_trades = 0
    last_day = datetime.datetime.utcfromtimestamp(T[0] / 1000).weekday() if n else 0
    ph1 = ph2 = pl1 = pl2 = neck_top = neck_bot = run_low = run_high = None
    trades = []; markers = []; fills = []
    L = P["mw_pivot_len"]; diag = {}
    def fill(side, qty, px, t, reason, cur):
        nonlocal closed_cnt, last_profit, day_pnl
        d = 1 if side == "long" else -1; e = cur["fill"]
        pct = d * (px - e) / e - comm * (1 + px / e)
        closed_cnt += 1; last_profit = pct; day_pnl += P["alloc"] * qty * pct
        cur["exits"].append({"t": t, "p": px, "q": qty, "r": reason, "pct": pct}); cur["rem"] -= qty
    for i in range(n):
        t, o, h, l, c = T[i], O[i], Hh[i], Lw[i], C[i]
        # ===== A) order fills inside this bar =====
        if pend_close and pos:
            for q, kind in ((pos["rem_tp1"], "tp1"), (pos["rem_tp2"], "tp2")):
                if q > 1e-9: fill(pos["side"], q, o, t, "TimeOut", pos)
            pos["closed_i"] = i; trades.append(pos); pos = None
        pend_close = False
        if pend_entry and pos is None:
            pe = pend_entry; pos = {"side": pe["side"], "sig_i": pe["sig_i"], "entry_i": i, "entry_t": t, "fill": o, "sig_px": pe["sig_px"], "sl": pe["sl"], "t1": pe["t1"], "t2": pe["t2"],
                                    "src": pe["src"], "exits": [], "rem": 1.0, "rem_tp1": 0.6, "rem_tp2": 0.4, "be": False}
            markers.append({"t": t, "side": pe["side"], "k": "entry", "p": o, "i": i, "src": pe["src"]})
        pend_entry = None
        if pos:
            long_ = pos["side"] == "long"; stop_px = pos["be_px"] if pos["be"] else pos["sl"]
            path = [o, h, l, c] if abs(h - o) <= abs(l - o) else [o, l, h, c]
            for a, b in zip(path[:-1], path[1:]):
                if pos is None: break
                up = b > a
                if long_ == up:      # profit direction: limits (TP) trigger
                    for lvl, key, nm in sorted([(pos["t1"], "rem_tp1", "TP1"), (pos["t2"], "rem_tp2", "TP2")], key=lambda x: x[0] if long_ else -x[0]):
                        if pos[key] > 1e-9 and ((max(a, b) >= lvl) if long_ else (min(a, b) <= lvl)):
                            px = lvl if ((a < lvl) if long_ else (a > lvl)) else a
                            fill(pos["side"], pos[key], px, t, nm, pos); markers.append({"t": t, "side": pos["side"], "k": "tp", "p": px, "i": i, "r": nm}); pos[key] = 0.0
                else:                # adverse direction: stop triggers
                    if (min(a, b) <= stop_px) if long_ else (max(a, b) >= stop_px):
                        px = stop_px if ((a > stop_px) if long_ else (a < stop_px)) else a
                        for key in ("rem_tp1", "rem_tp2"):
                            if pos[key] > 1e-9: fill(pos["side"], pos[key], px, t, "BE" if pos["be"] else "SL", pos); pos[key] = 0.0
                        markers.append({"t": t, "side": pos["side"], "k": "sl", "p": px, "i": i})
                if pos["rem_tp1"] + pos["rem_tp2"] <= 1e-9:
                    pos["closed_i"] = i; trades.append(pos); pos = None
        # ===== B) script logic at bar close =====
        dow = datetime.datetime.utcfromtimestamp(t / 1000).weekday()
        if dow != last_day: day_trades = 0; last_day = dow; day_pnl = 0.0
        if closed_cnt > prev_closed:
            if last_profit < 0: loss_streak += 1
            else: loss_streak = 0
            if P["use_cooldown"] and loss_streak >= P["cooldown_after_losses"]: cooldown_until = i + P["cooldown_bars"]; loss_streak = 0
        cooldown_ok = i >= cooldown_until
        hour = datetime.datetime.utcfromtimestamp(t / 1000).hour; minute = datetime.datetime.utcfromtimestamp(t / 1000).minute
        if not P["use_avoid_hours"]: hours_ok = True
        elif P["avoid_start_hour"] <= P["avoid_end_hour"]: hours_ok = not (P["avoid_start_hour"] <= hour < P["avoid_end_hour"])
        else: hours_ok = not (hour >= P["avoid_start_hour"] or hour < P["avoid_end_hour"])
        sf = P["session_filter"]
        session_ok = (13 <= hour <= 21 or (hour == 22 and minute == 0)) if sf == "America" else (7 <= hour <= 15) if sf == "Europe" else (0 <= hour <= 8) if sf == "Asia" else (12 <= hour <= 15) if sf == "London+NewYork" else True
        in_bl = any(a <= t <= b for a, b in bl)
        loss_ok = P["daily_loss_pct"] <= 0 or day_pnl * 100 > -P["daily_loss_pct"]
        trades_ok = day_trades < P["max_trades"] and cooldown_ok and hours_ok and not in_bl and loss_ok
        vol_ok = (not P["use_volume"]) or _gt(V[i], None if vma[i] is None else vma[i] * P["vol_ratio"])
        adx_ok = (not P["use_adx"]) or _ge(adx[i], P["min_adx_val"])
        macd_up, macd_dn = _gt(macd[i], sig[i]), _lt(macd[i], sig[i])
        tm = P["trend_mode"]
        bull_hard = _gt(c, ema200[i]) and _gt(ema21[i], ema200[i]); bear_hard = _lt(c, ema200[i]) and _lt(ema21[i], ema200[i])
        bull_soft, bear_soft = _gt(c, ema55[i]), _lt(c, ema55[i])
        tok_l = bull_hard if tm == "Hard" else bull_soft if tm == "Soft" else True
        tok_s = bear_hard if tm == "Hard" else bear_soft if tm == "Soft" else True
        bias_l = bull_soft if tm == "Soft" else True; bias_s = bear_soft if tm == "Soft" else True
        r1, s1 = (res[i - 1] if i > 0 else None), (sup[i - 1] if i > 0 else None)
        brk_l = _gt(c, r1) and _gt(c, ema21[i]) and macd_up and vol_ok
        brk_s = _lt(c, s1) and _lt(c, ema21[i]) and macd_dn and vol_ok
        cross_up = i > 0 and ema21[i] is not None and ema55[i] is not None and ema21[i - 1] is not None and ema55[i - 1] is not None and ema21[i] > ema55[i] and ema21[i - 1] <= ema55[i - 1]
        cross_dn = i > 0 and ema21[i] is not None and ema55[i] is not None and ema21[i - 1] is not None and ema55[i - 1] is not None and ema21[i] < ema55[i] and ema21[i - 1] >= ema55[i - 1]
        if cross_up: bsc = 0; lcu = True
        if cross_dn: bsc = 0; lcu = False
        if not (cross_up or cross_dn): bsc += 1
        pull_l = bsc <= P["pullback_bars"] and (ema21[i] is not None and l <= ema21[i]) and _gt(c, ema21[i]) and lcu and macd_up and vol_ok
        pull_s = bsc <= P["pullback_bars"] and (ema21[i] is not None and h >= ema21[i]) and _lt(c, ema21[i]) and (not lcu) and macd_dn and vol_ok
        def xo(a, b): return i > 0 and a[i] is not None and b[i] is not None and a[i - 1] is not None and b[i - 1] is not None and a[i] > b[i] and a[i - 1] <= b[i - 1]
        def xu(a, b): return i > 0 and a[i] is not None and b[i] is not None and a[i - 1] is not None and b[i - 1] is not None and a[i] < b[i] and a[i - 1] >= b[i - 1]
        ec_l = xo(ema8, ema21) and _gt(c, ema55[i]); ec_s = xu(ema8, ema21) and _lt(c, ema55[i])
        mc_l = xo(macd, sig) and _gt(c, ema21[i]); mc_s = xu(macd, sig) and _lt(c, ema21[i])
        # M & W pattern
        mw_l = mw_s = False
        if i >= 2 * L:
            j = i - L; run_low = Lw[j] if run_low is None else min(run_low, Lw[j]); run_high = Hh[j] if run_high is None else max(run_high, Hh[j])
            win_h, win_l = Hh[j - L:j + L + 1], Lw[j - L:j + L + 1]
            if Hh[j] == max(win_h) and all(Hh[j] > x for x in Hh[j - L:j]):
                ph2, ph1 = ph1, Hh[j]; neck_top = run_low; run_low = None
            if Lw[j] == min(win_l) and all(Lw[j] < x for x in Lw[j - L:j]):
                pl2, pl1 = pl1, Lw[j]; neck_bot = run_high; run_high = None
            tol = P["mw_tolerance_pct"] / 100
            m_pat = ph1 is not None and ph2 is not None and abs(ph1 - ph2) / ph2 <= tol; w_pat = pl1 is not None and pl2 is not None and abs(pl1 - pl2) / pl2 <= tol
            mw_s = P["use_mw_pattern"] and m_pat and neck_top is not None and i > 0 and C[i - 1] >= neck_top and c < neck_top
            mw_l = P["use_mw_pattern"] and w_pat and neck_bot is not None and i > 0 and C[i - 1] <= neck_bot and c > neck_bot
        mdl = P["model"]; score_l = score_s = 0
        if mdl == "Breakout": long_raw, short_raw = brk_l, brk_s
        elif mdl == "Pullback": long_raw, short_raw = pull_l, pull_s
        elif mdl == "EMA_Cross": long_raw, short_raw = ec_l, ec_s
        elif mdl == "MACD": long_raw, short_raw = mc_l, mc_s
        else:
            score_l = sum(map(int, [brk_l, pull_l, ec_l, mc_l, bool(bias_l), bool(vol_ok), P["use_mw_pattern"] and mw_l]))
            score_s = sum(map(int, [brk_s, pull_s, ec_s, mc_s, bool(bias_s), bool(vol_ok), P["use_mw_pattern"] and mw_s]))
            long_raw = score_l >= P["min_confluence"] and (brk_l or pull_l or ec_l or mc_l or (P["use_mw_pattern"] and mw_l))
            short_raw = score_s >= P["min_confluence"] and (brk_s or pull_s or ec_s or mc_s or (P["use_mw_pattern"] and mw_s))
        if P["use_mw_pattern"]:
            if P["mw_as_filter_only"]: long_raw = long_raw or (mw_l and (brk_l or pull_l or ec_l or mc_l)); short_raw = short_raw or (mw_s and (brk_s or pull_s or ec_s or mc_s))
            else: long_raw = long_raw or mw_l; short_raw = short_raw or mw_s
        rs = rsi[i]
        hf_l = (not P["htf_filter"]) or htf_state[i] >= 0; hf_s = (not P["htf_filter"]) or htf_state[i] <= 0
        long_sig = P["enable"] and long_raw and adx_ok and tok_l and (rs is not None and rs < 78) and session_ok and trades_ok and hf_l
        short_sig = P["enable"] and short_raw and adx_ok and tok_s and (rs is not None and rs > 22) and session_ok and trades_ok and hf_s
        fin_l, fin_s = long_sig and not short_sig, short_sig and not long_sig
        if P["use_confirm_candle"]:
            conf_l = sp_long and sl_level is not None and c > sl_level; conf_s = sp_short and ss_level is not None and c < ss_level; conf_l_mw, conf_s_mw = sl_mw, ss_mw
        else: conf_l, conf_s, conf_l_mw, conf_s_mw = fin_l, fin_s, mw_l, mw_s
        sp_long = sp_short = False
        if fin_l: sp_long = True; sl_level = h; sl_mw = mw_l
        if fin_s: sp_short = True; ss_level = l; ss_mw = mw_s
        # timeout / state resets
        if pos is None: be_moved = False; bars_in = 0
        if P["use_timeout"] and pos is not None:
            bars_in += 1
            if bars_in >= P["max_bars_open"]: pend_close = True; bars_in = 0; entry_qty = None; entry_price = None; be_moved = False
        entered = None
        if (conf_l or conf_s) and pos is None:
            day_trades += 1; bars_in = 0; entry_qty = 1.0; entry_price = c; be_moved = False
            if P["stop_mode"] == "atr" and atr14[i] is not None:
                a = atr14[i]; ds, d1, d2 = a * P["atr_mult_stop"], a * P["atr_mult_tp1"], a * P["atr_mult_tp2"]
            else: ds, d1, d2 = c * stop, c * tp1p, c * tp2p
            if conf_l: pend_entry = {"side": "long", "sig_i": i, "sig_px": c, "sl": c - ds, "t1": c + d1, "t2": c + d2, "src": "MW" if conf_l_mw else "Core"}
            else: pend_entry = {"side": "short", "sig_i": i, "sig_px": c, "sl": c + ds, "t1": c - d1, "t2": c - d2, "src": "MW" if conf_s_mw else "Core"}
            entered = pend_entry
        if P["use_breakeven"] and pos is not None and not be_moved and entry_qty is not None and (pos["rem_tp1"] + pos["rem_tp2"]) < entry_qty * 0.99:
            be_moved = True; pos["be"] = True; pos["be_px"] = entry_price
        prev_closed = closed_cnt
        if i == n - 1:
            diag = {"adx": adx[i], "rsi": rs, "score_l": score_l, "score_s": score_s, "vol_ok": bool(vol_ok), "adx_ok": bool(adx_ok), "trend_ok_l": bool(tok_l), "trend_ok_s": bool(tok_s),
                    "cooldown": not cooldown_ok, "day_trades": day_trades, "brk": [bool(brk_l), bool(brk_s)], "pull": [bool(pull_l), bool(pull_s)], "ec": [bool(ec_l), bool(ec_s)], "mc": [bool(mc_l), bool(mc_s)],
                    "raw": [bool(fin_l), bool(fin_s)], "bars_in": bars_in}
            last_signal = entered
            pending_confirm = ({"side": "long", "level": sl_level} if sp_long else {"side": "short", "level": ss_level} if sp_short else None)
    out = {"trades": trades, "markers": markers, "open": pos, "signal": last_signal if n else None, "pending_confirm": pending_confirm if n else None, "diag": diag, "params": P,
           "series": {"ema8": ema8, "ema21": ema21, "ema55": ema55, "ema200": ema200}}
    out["stats"] = stats(trades, P)
    return out

def stats(trades, P, since_t=None):
    rows = [x for x in trades if since_t is None or x["entry_t"] >= since_t]
    eq = 100.0; peak = 100.0; mdd = 0.0; gp = gl = 0.0; wins = losses = 0; pw = pl = 0
    for tr in rows:
        pnl = sum(e["q"] * e["pct"] for e in tr["exits"]); tr["pct"] = pnl; tr["result"] = ("win" if pnl > 0 else "loss")
        eq *= 1 + P["alloc"] * pnl; peak = max(peak, eq); mdd = max(mdd, (peak - eq) / peak * 100)
        for e in tr["exits"]:
            v = P["alloc"] * e["q"] * e["pct"] * 100
            if v > 0: gp += v; wins += 1
            elif v < 0: gl += -v; losses += 1
        if pnl > 0: pw += 1
        else: pl += 1
    n = len(rows)
    return {"positions": n, "pos_win": round(100 * pw / n, 1) if n else None, "tv_trades": wins + losses, "tv_win": round(100 * wins / (wins + losses), 1) if wins + losses else None,
            "pf": round(gp / gl, 2) if gl else None, "net_pct": round(eq - 100, 2), "max_dd": round(mdd, 2)}
