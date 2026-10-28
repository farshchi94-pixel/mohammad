#!/usr/bin/env python3
"""Walk-forward robustness report for the Whale Pro strategy.
Fits nothing blindly: compares YOUR parameters with a grid, on TRAIN (first 60%) vs unseen TEST (last 40%),
checks neighbour-robustness and a Monte-Carlo drawdown estimate. Writes optimize.json.
Run: python optimize.py [--quick]
"""
import sys, json, time, random, itertools
import scan, whale_pro as W
from concurrent.futures import ThreadPoolExecutor

GRID = {"stop_pct": [0.4, 0.6, 0.8, 1.0], "tp1_pct": [0.25, 0.35, 0.5], "tp2_pct": [0.7, 0.9, 1.3], "min_adx_val": [18, 22, 26], "model": ["Hybrid", "Breakout"]}
QUICK = {"stop_pct": [0.6, 0.8], "tp1_pct": [0.35, 0.5], "tp2_pct": [0.9], "min_adx_val": [22], "model": ["Hybrid"]}
WARM = 250

def history(sym, tf, bars):
    """Long history via pagination (Gate 'to' parameter), newest last."""
    sec = scan.TFSEC[tf]; end = scan.NOW(); out = []
    while len(out) < bars:
        try:
            j = scan.jget("https://api.gateio.ws/api/v4/spot/candlesticks", {"currency_pair": sym[:-4] + "_USDT", "interval": tf, "limit": 1000, "to": end})
        except Exception as e: print("history error", sym, e); break
        if not j: break
        rows = [[int(a[0]) * 1000, float(a[5]), float(a[3]), float(a[4]), float(a[2]), float(a[1])] for a in j]
        out = rows + out
        end = min(int(a[0]) for a in j) - sec
        if len(j) < 900: break
    unique = {row[0]: row for row in out}
    out = [unique[t] for t in sorted(unique)]
    return out[-bars:] if len(out) >= 600 else None

def split_stats(trades, P, split_i):
    tr = [t for t in trades if t["entry_i"] >= WARM and t["entry_i"] < split_i]; te = [t for t in trades if t["entry_i"] >= split_i]
    return tr, te

def pooled(rows, P):
    rows = sorted(rows, key=lambda x: x["entry_t"]); return W.stats(rows, P)

def monte_carlo(rows, P, runs=1000):
    if len(rows) < 10: return None
    pn = [sum(e["q"] * e["pct"] for e in t["exits"]) for t in rows]; dds = []; rnd = random.Random(7)
    for _ in range(runs):
        rnd.shuffle(pn); eq = peak = 1.0; dd = 0.0
        for p in pn: eq *= 1 + P["alloc"] * p; peak = max(peak, eq); dd = max(dd, (peak - eq) / peak)
        dds.append(dd)
    dds.sort(); return {"dd_median": round(dds[len(dds) // 2] * 100, 2), "dd_p95": round(dds[int(len(dds) * .95)] * 100, 2), "trades": len(pn)}

def main():
    quick = "--quick" in sys.argv; grid = QUICK if quick else GRID; tf = scan.CFG.get("whale_tf", "15m")
    bars = 1500 if quick else 3000; base = dict(W.DEFAULT); base.update(scan.CFG.get("whale_params", {}))
    syms = scan.CFG.get("whale_symbols") or scan.CFG["majors"][:10]
    data = {}
    def load_history(sym):
        try: return sym, history(sym, tf, bars)
        except Exception as exc: print("history error", sym, exc); return sym, None
    with ThreadPoolExecutor(max_workers=min(4, max(2, len(syms)))) as ex:
        for sym, h in ex.map(load_history, syms):
            if h: data[sym] = h
    print("history loaded:", {k: len(v) for k, v in data.items()})
    if not data: print("no data"); return False
    keys = list(grid); combos = [dict(zip(keys, v)) for v in itertools.product(*grid.values())]
    cur_key = {k: base.get(k) for k in keys}
    if cur_key not in combos: combos.append(cur_key)
    results = []; current_trades = []; t0 = time.time()
    for ci, c in enumerate(combos):
        P = dict(base); P.update(c); tr_all, te_all = [], []
        for s, cs in data.items():
            split = int(len(cs) * .6); r = W.run(cs, P); a, b = split_stats(r["trades"], P, split); tr_all += a; te_all += b
            if c == cur_key: current_trades += [t for t in r["trades"] if t["entry_i"] >= WARM]
        results.append({"params": c, "train": pooled(tr_all, P), "test": pooled(te_all, P), "key": c})
        if ci % 20 == 0: print(f"{ci}/{len(combos)} {time.time()-t0:.0f}s")
    def key_of(c): return tuple(c[k] for k in keys)
    byk = {key_of(r["params"]): r for r in results}; cur = byk[key_of(cur_key)]
    def good(r): return r["test"]["positions"] >= 15 and (r["test"]["pf"] or 0) > 1.0 and r["test"]["net_pct"] > 0
    nb = []
    for k in keys:
        for v in grid[k]:
            if v != cur_key[k]:
                c2 = dict(cur_key); c2[k] = v
                if key_of(c2) in byk: nb.append(good(byk[key_of(c2)]))
    robust = round(sum(nb) / len(nb), 2) if nb else None
    ranked = sorted([r for r in results if r["train"]["positions"] >= 25 and good(r)], key=lambda r: -((r["train"]["pf"] or 0) * min(1, r["train"]["positions"] / 60) ** .5 * (r["test"]["pf"] or 0)))[:5]
    # Monte Carlo for current params on all data
    P = dict(base); allt = current_trades
    allst = pooled(allt, P); mc = monte_carlo(allt, P)
    tpf = cur["test"]["pf"] or 0
    verdict = ("پایدار: روی داده دیده‌نشده هم سودده بود و همسایه‌های پارامترها هم تا حد خوبی سودده‌اند." if tpf > 1.1 and cur["test"]["positions"] >= 20 and (robust or 0) >= .6 else
               "مرزی: روی داده دیده‌نشده سودده یا نزدیک سربه‌سر است ولی پایداری کافی ندارد." if tpf > 1.0 else
               "ناپایدار: روی داده دیده‌نشده سود نداد؛ احتمال بیش‌برازش یا شرایط بازار خاص. با پول واقعی استفاده نکنید.")
    if cur["test"]["positions"] < 20: verdict = "داده کافی نیست (کمتر از ۲۰ معاملهٔ آزمون)؛ نتیجه قابل‌اتکا نیست. بازهٔ بیشتر یا نمادهای بیشتر لازم است."
    scan.save("optimize.json", {"updated": scan.NOW(), "tf": tf, "bars": {k: len(v) for k, v in data.items()}, "grid_size": len(combos), "split": "60/40", "warm": WARM,
        "current": {"params": cur_key, "train": cur["train"], "test": cur["test"], "robust": robust, "all": allst, "mc": mc}, "top": [{"params": r["params"], "train": r["train"], "test": r["test"]} for r in ranked],
        "verdict": verdict, "note": "نتیجهٔ بهینه‌سازی روی گذشته است. پارامتر بهتر فقط وقتی معتبر است که در آزمون دیده‌نشده هم بماند. پیشنهادهای بالا را فقط با رکورد زنده تأیید کنید."})
    print("optimize ok:", verdict)
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
