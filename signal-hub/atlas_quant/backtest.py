"""Historical-data backtester. Long-only spot simulation; never places exchange orders."""
from __future__ import annotations
import json, urllib.parse, urllib.request
from datetime import datetime, timezone
from typing import Any

BASE = 'https://api.lbkex.com/v2/kline.do'
INTERVALS = {'1m':'minute1','3m':'minute3','5m':'minute5','15m':'minute15','30m':'minute30','1h':'hour1','4h':'hour4','1d':'day1'}

class BacktestError(ValueError): pass

def fetch_candles(symbol: str, timeframe: str, limit: int = 500) -> list[dict[str, float]]:
    if timeframe not in INTERVALS: raise BacktestError('تایم‌فریم پشتیبانی نمی‌شود.')
    if not (100 <= limit <= 2000): raise BacktestError('تعداد کندل باید بین ۱۰۰ تا ۲۰۰۰ باشد.')
    params = urllib.parse.urlencode({'symbol': symbol.lower().replace('/', '_'), 'type': INTERVALS[timeframe], 'size': limit})
    req = urllib.request.Request(BASE + '?' + params, headers={'User-Agent':'ATLAS-QUANT-PAPER-BACKTEST/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response: payload = json.loads(response.read().decode('utf-8'))
    except Exception as e: raise BacktestError(f'دریافت داده تاریخی از LBank ناموفق بود: {type(e).__name__}') from e
    if not isinstance(payload, list):
        data = payload.get('data') if isinstance(payload, dict) else None
        if isinstance(data, list): payload = data
        else: raise BacktestError('پاسخ API کندل معتبر نیست؛ اتصال یا قالب API را بررسی کنید.')
    candles=[]
    for row in payload:
        try:
            # LBank v2 kline rows: [timestamp, open, high, low, close, volume, ...]
            if isinstance(row, dict):
                ts = row.get('timestamp', row.get('time', row.get('t')))
                o,h,l,c,v = [float(row[k]) for k in ('open','high','low','close','volume')]
            else:
                ts = row[0]; o,h,l,c,v = map(float,row[1:6])
            ts=float(ts); ts=ts/1000 if ts>10_000_000_000 else ts
            if min(o,h,l,c) <= 0 or h < max(o,c,l) or l > min(o,c,h): continue
            candles.append({'time':ts,'open':o,'high':h,'low':l,'close':c,'volume':v})
        except (TypeError, ValueError, KeyError, IndexError): continue
    candles.sort(key=lambda x:x['time'])
    # Remove duplicate timestamps, keep latest occurrence.
    unique={c['time']:c for c in candles}
    candles=[unique[k] for k in sorted(unique)]
    if len(candles)<100: raise BacktestError(f'داده معتبر کافی نیست: فقط {len(candles)} کندل دریافت شد.')
    return candles

def ema(values: list[float], period: int) -> list[float | None]:
    out=[None]*len(values)
    if len(values)<period:return out
    alpha=2/(period+1); current=sum(values[:period])/period; out[period-1]=current
    for i in range(period,len(values)):
        current=values[i]*alpha+current*(1-alpha);out[i]=current
    return out

def rsi(values: list[float], period: int=14) -> list[float | None]:
    out=[None]*len(values)
    if len(values)<=period:return out
    gains=[]; losses=[]
    for i in range(1,period+1):
        d=values[i]-values[i-1];gains.append(max(d,0));losses.append(max(-d,0))
    ag=sum(gains)/period;al=sum(losses)/period
    out[period]=100 if al==0 and ag>0 else (50 if al==0 else 100-100/(1+ag/al))
    for i in range(period+1,len(values)):
        d=values[i]-values[i-1];ag=(ag*(period-1)+max(d,0))/period;al=(al*(period-1)+max(-d,0))/period
        out[i]=100 if al==0 and ag>0 else (50 if al==0 else 100-100/(1+ag/al))
    return out

def atr(candles: list[dict[str,float]], period: int=14) -> list[float | None]:
    trs=[]
    for i,c in enumerate(candles):
        prev=candles[i-1]['close'] if i else c['close']
        trs.append(max(c['high']-c['low'],abs(c['high']-prev),abs(c['low']-prev)))
    return ema(trs,period)

def run_backtest(candles: list[dict[str,float]], initial_capital: float=10000, risk_pct: float=1, fee_pct: float=0.1, stop_atr: float=2, reward_r: float=2) -> dict[str,Any]:
    if not 100 <= initial_capital <= 10_000_000: raise BacktestError('سرمایه باید بین ۱۰۰ و ۱۰٬۰۰۰٬۰۰۰ USDT باشد.')
    if not 0.1 <= risk_pct <= 2: raise BacktestError('ریسک هر معامله باید بین ۰٫۱٪ و ۲٪ باشد.')
    if not 0 <= fee_pct <= 1: raise BacktestError('کارمزد باید بین ۰٪ و ۱٪ برای هر سمت باشد.')
    if not 1 <= stop_atr <= 5 or not 1 <= reward_r <= 5: raise BacktestError('پارامترهای حد ضرر/سود خارج از محدوده مجاز هستند.')
    closes=[c['close'] for c in candles]; fast=ema(closes,20); slow=ema(closes,50); rs=rsi(closes); av=atr(candles)
    cash=initial_capital; position=None; trades=[]; curve=[]; peak=initial_capital; max_dd=0.0
    fee_rate=fee_pct/100
    for i,c in enumerate(candles):
        # Evaluate exits before any new entry. If stop and target touch in the same candle, assume stop first (conservative).
        if position:
            exit_price=None; reason=None
            if c['open'] <= position['stop']: exit_price=c['open'];reason='stop_gap'
            elif c['open'] >= position['target']: exit_price=c['open'];reason='target_gap'
            elif c['low'] <= position['stop']: exit_price=position['stop'];reason='stop'
            elif c['high'] >= position['target']: exit_price=position['target'];reason='target'
            if exit_price is not None:
                gross=(exit_price-position['entry'])*position['qty']; exit_fee=exit_price*position['qty']*fee_rate
                net=gross-position['entry_fee']-exit_fee
                cash += position['qty']*exit_price-exit_fee
                trades.append({'entry_time':datetime.fromtimestamp(position['time'],timezone.utc).isoformat(),'exit_time':datetime.fromtimestamp(c['time'],timezone.utc).isoformat(),'entry':round(position['entry'],8),'exit':round(exit_price,8),'qty':round(position['qty'],8),'gross_pnl':round(gross,4),'fees':round(position['entry_fee']+exit_fee,4),'net_pnl':round(net,4),'return_pct':round(net/(position['entry']*position['qty'])*100,4),'reason':reason})
                position=None
        # Signal at candle close, fill at next candle open to avoid lookahead bias.
        if not position and i+1<len(candles) and i>0 and fast[i-1] is not None and fast[i] is not None and slow[i-1] is not None and slow[i] is not None and rs[i] is not None and av[i] is not None:
            cross_up=fast[i-1] <= slow[i-1] and fast[i] > slow[i] and rs[i] < 70
            if cross_up:
                entry=candles[i+1]['open']; stop=entry-stop_atr*av[i]; risk_per_unit=entry-stop
                if risk_per_unit>0:
                    risk_cash=cash*risk_pct/100
                    qty=min(risk_cash/risk_per_unit, cash/(entry*(1+fee_rate)))
                    if qty>0:
                        entry_fee=qty*entry*fee_rate
                        cash -= qty*entry+entry_fee
                        position={'entry':entry,'qty':qty,'stop':stop,'target':entry+reward_r*risk_per_unit,'entry_fee':entry_fee,'time':candles[i+1]['time']}
        equity=cash+(position['qty']*c['close'] if position else 0)
        peak=max(peak,equity); dd=(peak-equity)/peak*100 if peak else 0; max_dd=max(max_dd,dd)
        curve.append({'time':c['time'],'equity':round(equity,4),'drawdown_pct':round(dd,4)})
    # Force-close open position on last close to provide a realized final report.
    if position:
        c=candles[-1]; exit_price=c['close'];gross=(exit_price-position['entry'])*position['qty'];exit_fee=exit_price*position['qty']*fee_rate
        net=gross-position['entry_fee']-exit_fee;cash+=position['qty']*exit_price-exit_fee
        trades.append({'entry_time':datetime.fromtimestamp(position['time'],timezone.utc).isoformat(),'exit_time':datetime.fromtimestamp(c['time'],timezone.utc).isoformat(),'entry':round(position['entry'],8),'exit':round(exit_price,8),'qty':round(position['qty'],8),'gross_pnl':round(gross,4),'fees':round(position['entry_fee']+exit_fee,4),'net_pnl':round(net,4),'return_pct':round(net/(position['entry']*position['qty'])*100,4),'reason':'end_of_test'})
        position=None
        if curve: curve[-1]['equity']=round(cash,4)
    final=cash; net=final-initial_capital; wins=sum(t['net_pnl']>0 for t in trades); losses=sum(t['net_pnl']<=0 for t in trades)
    gross_profit=sum(max(t['net_pnl'],0) for t in trades);gross_loss=abs(sum(min(t['net_pnl'],0) for t in trades))
    return {'mode':'PAPER_ONLY','real_orders_enabled':False,'strategy':'EMA20/EMA50 bullish crossover + RSI(14)<70; ATR(14) stop','symbol':'','timeframe':'','candles':len(candles),'initial_capital':round(initial_capital,2),'final_equity':round(final,2),'net_pnl':round(net,2),'return_pct':round(net/initial_capital*100,3),'max_drawdown_pct':round(max_dd,3),'trades_count':len(trades),'wins':wins,'losses':losses,'win_rate_pct':round(wins/len(trades)*100,2) if trades else 0,'profit_factor':round(gross_profit/gross_loss,3) if gross_loss else (None if not gross_profit else 'infinite'),'fees_total':round(sum(t['fees'] for t in trades),4),'risk_pct':risk_pct,'fee_pct_per_side':fee_pct,'stop_atr':stop_atr,'reward_r':reward_r,'trades':trades,'equity_curve':curve,'assumptions':['Long-only spot; no leverage.','Signals use candle close and entries use next candle open.','If stop and target are touched in one candle, stop is assumed first.','Fees are charged on entry and exit; slippage is not modeled.','Open position is closed at the final candle close.']}
