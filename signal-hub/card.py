"""Professional signal / result / track-record cards (SVG -> PNG). English labels only (cairo has no Persian shaping)."""
import datetime, html
try: import cairosvg
except Exception: cairosvg = None

F = "DejaVu Sans, Arial, sans-serif"
G, Rd, Y, B = "#22c55e", "#ef4444", "#f0b429", "#6aa9ff"
def fp(x): return f"{x:.6g}"
def utc(ts): return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
def png(svg, w=1000):
    if cairosvg is None: return None
    try: return cairosvg.svg2png(bytestring=svg.encode(), output_width=w)
    except Exception as e: print("card render failed:", e); return None
def head(title, sub, col):
    return (f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b1420"/><stop offset="1" stop-color="#121f31"/></linearGradient></defs><rect width="1000" height="1250" fill="url(#bg)"/>'
            f'<text x="40" y="58" font-family="{F}" font-size="26" fill="#8fa3b8" letter-spacing="3">WHALE PRO V3.10</text>'
            f'<text x="960" y="58" font-family="{F}" font-size="22" fill="#8fa3b8" text-anchor="end">{html.escape(sub)}</text>'
            f'<rect x="40" y="90" width="200" height="86" rx="18" fill="{col}"/><text x="140" y="150" font-family="{F}" font-size="46" font-weight="700" fill="#fff" text-anchor="middle">{title}</text>')
def chart(c, levels, x0=40, y0=250, w=920, h=520, n=60):
    seg = c[-n:]; PR = 150; pw = w - PR; lo = min(min(x[3] for x in seg), *[l[0] for l in levels]); hi = max(max(x[2] for x in seg), *[l[0] for l in levels])
    pad = (hi - lo) * .06 or hi * .01; lo -= pad; hi += pad; step = pw / len(seg); Y = lambda p: y0 + 10 + (hi - p) / (hi - lo) * (h - 20)
    s = f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="16" fill="#0b121a"/>'
    for k in range(5):
        p = lo + (hi - lo) * k / 4; near = any(abs(Y(p) - Y(l[0])) < 24 for l in levels)
        s += f'<line x1="{x0}" x2="{x0+pw}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="#fff" stroke-opacity=".07"/>' + ('' if near else f'<text x="{x0+pw+8}" y="{Y(p)+5:.1f}" font-family="{F}" font-size="16" fill="#8a96a3">{fp(p)}</text>')
    for i, k in enumerate(seg):
        up = k[4] >= k[1]; col = "#26a69a" if up else "#ef5350"; x = x0 + (i + .5) * step; yt, yb = Y(max(k[1], k[4])), Y(min(k[1], k[4]))
        s += f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{Y(k[2]):.1f}" y2="{Y(k[3]):.1f}" stroke="{col}" stroke-width="1.6"/><rect x="{x-step*.33:.1f}" y="{yt:.1f}" width="{step*.66:.1f}" height="{max(2,yb-yt):.1f}" fill="{col}"/>'
    labs = sorted([(Y(p), p, col, t) for p, col, t in levels]); fixed = []
    for y, p, col, t in labs:
        if fixed and y - fixed[-1] < 22: y = fixed[-1] + 22
        fixed.append(y)
    for (y0_, p, col, t), yy in zip(labs, fixed):
        s += f'<line x1="{x0}" x2="{x0+pw}" y1="{y0_:.1f}" y2="{y0_:.1f}" stroke="{col}" stroke-dasharray="9 6" stroke-width="2"/><rect x="{x0+pw+4}" y="{yy-14:.1f}" width="{PR-8}" height="26" rx="5" fill="{col}" opacity=".22"/><text x="{x0+pw+10}" y="{yy+5:.1f}" font-family="{F}" font-size="16" font-weight="700" fill="{col}">{t} {fp(p)}</text>'
    return s
def row(y, label, val, sub, col):
    return f'<rect x="40" y="{y}" width="920" height="70" rx="14" fill="#16222e"/><rect x="40" y="{y}" width="10" height="70" rx="5" fill="{col}"/><text x="76" y="{y+44}" font-family="{F}" font-size="26" fill="#cbd5e1">{label}</text><text x="560" y="{y+44}" font-family="{F}" font-size="32" font-weight="700" fill="#fff" text-anchor="end">{val}</text><text x="940" y="{y+44}" font-family="{F}" font-size="24" fill="{col}" text-anchor="end">{sub}</text>'
def foot(extra=""):
    return (f'<text x="40" y="1196" font-family="{F}" font-size="17" fill="#8a96a3">Entry at next candle open; levels come from the signal candle close. {extra}</text>'
            f'<text x="40" y="1224" font-family="{F}" font-size="17" fill="#8a96a3">Not financial advice. Risk max 1% per trade. Past results do not guarantee future results.</text>')

def signal_card(sym, tf, side, candles, entry, sl, t1, t2, src="Core", ts=0, uid=""):
    L = side == "long"; col = G if L else Rd; risk = abs(entry - sl); r1, r2 = abs(t1 - entry) / risk, abs(t2 - entry) / risk; wr = 0.6 * r1 + 0.4 * r2; be = 100 / (1 + wr)
    lv = [(entry, B, "ENTRY"), (sl, Y, "SL"), (t1, "#84cc16", "TP1"), (t2, G, "TP2")]
    s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1250">' + head("BUY" if L else "SELL", f"{tf} | {utc(ts)}", col)
    s += f'<text x="270" y="150" font-family="{F}" font-size="56" font-weight="700" fill="#fff">{html.escape(sym.replace("USDT",""))}/USDT</text><text x="270" y="190" font-family="{F}" font-size="22" fill="#8fa3b8">Signal type: {src} | Spot/Perp chart</text>'
    s += chart(candles, lv)
    pct = lambda p: f"{(p/entry-1)*100:+.2f}%"
    s += row(800, "ENTRY (signal close)", fp(entry), "market / next open", B) + row(880, "STOP LOSS", fp(sl), f"{pct(sl)}  (-1R)", Y) + row(960, "TP1  - close 60%", fp(t1), f"{pct(t1)}  (+{r1:.2f}R)", "#84cc16") + row(1040, "TP2  - close 40%", fp(t2), f"{pct(t2)}  (+{r2:.2f}R)", G)
    s += f'<text x="500" y="1142" font-family="{F}" font-size="21" fill="#cbd5e1" text-anchor="middle">After TP1 the stop moves to breakeven. Blended target {wr:.2f}R.</text><text x="500" y="1170" font-family="{F}" font-size="21" fill="#cbd5e1" text-anchor="middle">Break-even win rate {be:.0f}% (before fees)</text>'
    return png(s + foot(f"ID {uid}") + "</svg>")
def result_card(sym, side, entry, exits, pnl, uid="", ts=0):
    win = pnl > 0; col = G if win else Rd; L = side == "long"
    s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1250">' + head("WIN" if win else "LOSS", utc(ts), col)
    s += f'<text x="270" y="150" font-family="{F}" font-size="56" font-weight="700" fill="#fff">{html.escape(sym.replace("USDT",""))}/USDT</text><text x="270" y="190" font-family="{F}" font-size="24" fill="#8fa3b8">{"LONG" if L else "SHORT"} closed</text>'
    s += f'<text x="500" y="420" font-family="{F}" font-size="150" font-weight="700" fill="{col}" text-anchor="middle">{pnl*100:+.2f}%</text><text x="500" y="480" font-family="{F}" font-size="26" fill="#8fa3b8" text-anchor="middle">position result after fees (before sizing)</text>'
    y = 560
    for r, p, q in exits[:6]:
        s += row(y, f"{r}  ({int(q*100)}% of position)", fp(p), f"{((p/entry-1)*(1 if L else -1))*100:+.2f}%", G if r.startswith("TP") else (Y if r in ("BE", "TimeOut") else Rd)); y += 84
    return png(s + foot(f"ID {uid}") + "</svg>")
def record_card(st, trades, since):
    s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1250">' + head("RECORD", f"since {utc(since)}", B)
    s += f'<text x="270" y="140" font-family="{F}" font-size="44" font-weight="700" fill="#fff">LIVE TRACK RECORD</text><text x="270" y="180" font-family="{F}" font-size="22" fill="#8fa3b8">All closed trades, wins AND losses</text>'
    vals = [("Trades", st.get("positions")), ("Win rate", f'{st.get("pos_win")}%' if st.get("pos_win") is not None else "-"), ("Profit factor", st.get("pf") or "-"), ("Net", f'{st.get("net_pct",0):+.2f}%'), ("Max DD", f'{st.get("max_dd",0)}%')]
    for i, (k, v) in enumerate(vals):
        x = 40 + i * 188; s += f'<rect x="{x}" y="230" width="176" height="110" rx="14" fill="#16222e"/><text x="{x+88}" y="270" font-family="{F}" font-size="19" fill="#8fa3b8" text-anchor="middle">{k}</text><text x="{x+88}" y="322" font-family="{F}" font-size="34" font-weight="700" fill="#fff" text-anchor="middle">{v}</text>'
    y = 380
    for t in trades[-11:][::-1]:
        c = G if t["pct"] > 0 else Rd
        s += f'<rect x="40" y="{y}" width="920" height="58" rx="10" fill="#16222e"/><text x="64" y="{y+38}" font-family="{F}" font-size="24" fill="#fff">{html.escape(t["sym"].replace("USDT",""))} {"BUY" if t["side"]=="long" else "SELL"}</text><text x="500" y="{y+38}" font-family="{F}" font-size="21" fill="#8fa3b8">{"/".join(t["reasons"])}</text><text x="936" y="{y+38}" font-family="{F}" font-size="26" font-weight="700" fill="{c}" text-anchor="end">{t["pct"]:+.2f}%</text>'; y += 66
    return png(s + foot() + "</svg>")
