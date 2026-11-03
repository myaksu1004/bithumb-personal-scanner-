from flask import Flask, jsonify, render_template_string
import requests, time, math, statistics, json, os

app = Flask(__name__)
BASE = "https://api.bithumb.com"
S = requests.Session()
S.headers.update({"accept":"application/json","user-agent":"BithumbPersonalScanner/3.0"})

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "strategy_config.json"), "r", encoding="utf-8") as f:
    CFG = json.load(f)

HTML = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>내 차트 관점 탐색기 v3</title>
<style>
:root{--bg:#f4f5f7;--card:#fff;--text:#16181c;--sub:#667085;--line:#e5e7eb;--good:#067647;--warn:#b54708;--bad:#b42318;--blue:#175cd3}
*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans KR",sans-serif;background:var(--bg);margin:0;color:var(--text)}header{background:#fff;padding:20px 16px;border-bottom:1px solid var(--line)}h1{font-size:23px;margin:0 0 5px}.sub{font-size:12px;color:var(--sub);line-height:1.5}main{max-width:980px;margin:auto;padding:14px}.btn{width:100%;padding:16px;border:0;border-radius:14px;background:#111;color:#fff;font-size:17px;font-weight:800}.card{background:var(--card);border-radius:17px;padding:15px;margin:13px 0;box-shadow:0 1px 5px #0001}.row{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}.coin{font-size:21px;font-weight:850}.badge{padding:6px 9px;border-radius:999px;background:#eef0f2;font-weight:800;font-size:12px;white-space:nowrap}.meta{font-size:12px;color:var(--sub);margin-top:6px;line-height:1.5}.scores{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:12px}.score{background:#f7f8fa;border-radius:11px;padding:9px 4px;text-align:center}.score b{display:block;font-size:18px}.score span{font-size:9px;color:var(--sub)}.patterns{display:flex;flex-wrap:wrap;gap:5px;margin-top:9px}.tag{background:#eef4ff;color:#3538cd;padding:5px 7px;border-radius:999px;font-size:11px;font-weight:700}.decision{margin-top:10px;padding:10px;border-radius:11px;background:#fafafa;font-size:13px;font-weight:800}.plan{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-top:9px}.p{border:1px solid var(--line);border-radius:10px;padding:7px;text-align:center}.p b{display:block;font-size:12px}.p span{font-size:9px;color:var(--sub)}.reason{font-size:12px;line-height:1.65;color:#475467;margin-top:10px}.warn{color:var(--warn)}.bad{color:var(--bad)}.good{color:var(--good)}#status{text-align:center;color:var(--sub);margin:12px;font-size:13px}.foot{font-size:10px;color:#98a2b3;line-height:1.5;margin:14px 2px 28px}
@media(max-width:700px){.scores{grid-template-columns:repeat(2,1fr)}.plan{grid-template-columns:repeat(2,1fr)}.plan .p:last-child{grid-column:span 2}}
</style></head><body><header><h1>📊 내 차트 관점 탐색기 v3</h1><div class="sub">Trend · Setup · Entry · Risk 분리 | 돌파형 · 눌림형 · 180일선 리클레임 · 바닥반전형 | 진입·손절·목표·R:R 자동 계산</div></header><main><button class="btn" onclick="scan()">🔍 지금 탐색</button><div id="status">버튼을 누르면 빗썸 KRW 종목을 분석합니다.</div><div id="list"></div><div class="foot">분석 보조용 도구입니다. 신호는 미래 수익을 보장하지 않으며, 호가·체결 데이터는 순간적으로 바뀔 수 있습니다. 주문 실행 기능은 포함하지 않았습니다.</div></main>
<script>
const won=v=>v>=1e8?(v/1e8).toFixed(1)+"억":Math.round(v).toLocaleString();
const px=v=>v==null?'-':(v>=1000?Math.round(v).toLocaleString():v>=100?v.toFixed(1):v>=1?v.toFixed(2):v.toFixed(4));
async function scan(){const s=document.querySelector('#status'),l=document.querySelector('#list');s.textContent='1차 후보 탐색 → 멀티타임프레임 정밀분석 중…';l.innerHTML='';try{const r=await fetch('/api/scan');const d=await r.json();if(!r.ok||d.ok===false)throw new Error(d.detail||d.error||'API 오류');s.textContent='완료 · '+d.note;l.innerHTML=d.items.map(x=>`<div class="card"><div class="row"><div><span class="coin">${x.market}</span> ${px(x.price)}원<div class="meta">${x.change>=0?'+':''}${x.change.toFixed(2)}% · 24H ${won(x.turnover)} · RVOL ${x.rvol.toFixed(2)} · RSI15 ${x.rsi15.toFixed(1)}</div></div><span class="badge">${x.decision}</span></div><div class="scores"><div class="score"><b>${x.trend}</b><span>Trend</span></div><div class="score"><b>${x.setup}</b><span>Setup</span></div><div class="score"><b>${x.entry}</b><span>Entry</span></div><div class="score"><b>${x.risk}</b><span>Risk (낮을수록 좋음)</span></div></div><div class="patterns">${x.patterns.map(p=>`<span class="tag">${p}</span>`).join('')}</div><div class="decision ${x.decision_class}">${x.summary}</div><div class="plan"><div class="p"><b>${px(x.plan.entry)}</b><span>진입 기준</span></div><div class="p"><b>${px(x.plan.stop)}</b><span>구조/ATR 손절</span></div><div class="p"><b>${px(x.plan.target1)}</b><span>1차 목표</span></div><div class="p"><b>${px(x.plan.target2)}</b><span>2차 목표</span></div><div class="p"><b>${x.plan.rr==null?'-':x.plan.rr.toFixed(2)+'R'}</b><span>1차 목표 R:R</span></div></div><div class="meta">MA7 이격 ${x.ma7_gap.toFixed(2)}% · 매수/매도잔량 ${x.bid_ask_ratio.toFixed(2)}배 · 체결강도(근사) ${x.trade_strength.toFixed(0)}%</div><div class="reason">✓ ${x.reasons.join(' · ')||'조건 탐색 중'}${x.warnings.length?`<br><span class="warn">⚠ ${x.warnings.join(' · ')}</span>`:''}${x.invalidations.length?`<br><span class="bad">⛔ 무효화: ${x.invalidations.join(' · ')}</span>`:''}</div></div>`).join('');}catch(e){s.textContent='탐색 실패: '+e.message}}
</script></body></html>'''

def get(path, params=None):
    r=S.get(BASE+path, params=params, timeout=12)
    r.raise_for_status()
    return r.json()

def f(x, default=0.0):
    try:return float(x)
    except:return default

def closes(c): return [f(x['trade_price']) for x in c]
def highs(c): return [f(x['high_price']) for x in c]
def lows(c): return [f(x['low_price']) for x in c]
def opens(c): return [f(x['opening_price']) for x in c]
def vals(c,k): return [f(x[k]) for x in c]
def ma(a,n): return sum(a[-n:])/n if len(a)>=n else None

def sma_series(a,n):
    out=[]
    for i in range(len(a)):
        out.append(sum(a[i-n+1:i+1])/n if i>=n-1 else None)
    return out

def ema_series(a,n):
    if not a:return []
    k=2/(n+1); out=[a[0]]
    for x in a[1:]: out.append(x*k+out[-1]*(1-k))
    return out

def rsi(a,n=14):
    if len(a)<n+1:return 50.0
    ds=[a[i]-a[i-1] for i in range(len(a)-n,len(a))]
    g=sum(max(x,0) for x in ds)/n; l=sum(max(-x,0) for x in ds)/n
    return 100.0 if l==0 else 100-(100/(1+g/l))

def macd_hist(a):
    e12,e26=ema_series(a,12),ema_series(a,26); m=[x-y for x,y in zip(e12,e26)]; sig=ema_series(m,9)
    return [x-y for x,y in zip(m,sig)]

def true_ranges(c):
    out=[]
    for i,x in enumerate(c):
        h=f(x['high_price']); l=f(x['low_price'])
        if i==0: out.append(h-l)
        else:
            pc=f(c[i-1]['trade_price']); out.append(max(h-l,abs(h-pc),abs(l-pc)))
    return out

def atr(c,n=14):
    tr=true_ranges(c); return sum(tr[-n:])/n if len(tr)>=n else (sum(tr)/len(tr) if tr else 0)

def bb_at(a,i,n=20,mult=2):
    if i<n-1:return (None,None,None,None)
    w=a[i-n+1:i+1]; mid=sum(w)/n; sd=statistics.pstdev(w); up=mid+mult*sd; lo=mid-mult*sd
    return mid,up,lo,(up-lo)/mid*100 if mid else 0

def bb(a,n=20,mult=2): return bb_at(a,len(a)-1,n,mult)

def percentile_rank(arr, value):
    if not arr:return 100
    return 100*sum(1 for x in arr if x<=value)/len(arr)

def close_position(candle):
    h=f(candle['high_price']); l=f(candle['low_price']); c=f(candle['trade_price'])
    return (c-l)/(h-l) if h>l else .5

def bullish(candle): return f(candle['trade_price']) > f(candle['opening_price'])

def candles(market,unit,count=200): return list(reversed(get(f'/v1/candles/minutes/{unit}',{'market':market,'count':count})))
def days(market,count=200): return list(reversed(get('/v1/candles/days',{'market':market,'count':count})))

def pivot_levels(c, mode='high', left=2, right=2, lookback=80):
    key='high_price' if mode=='high' else 'low_price'; a=vals(c,key); start=max(left,len(a)-lookback)
    lv=[]
    for i in range(start,len(a)-right):
        w=a[i-left:i+right+1]
        if (mode=='high' and a[i]==max(w)) or (mode=='low' and a[i]==min(w)): lv.append(a[i])
    return lv

def merge_levels(levels, ref, tol_pct=.8):
    if not levels:return []
    out=[]
    for x in sorted(levels):
        if not out or abs(x-out[-1])/max(ref,1)*100>tol_pct: out.append(x)
        else: out[-1]=(out[-1]+x)/2
    return out

def nearest_above(levels, price):
    a=[x for x in levels if x>price*1.002]
    return min(a) if a else None

def nearest_below(levels, price):
    a=[x for x in levels if x<price*.998]
    return max(a) if a else None

def orderflow(market):
    try:
        book=get('/v1/orderbook',{'markets':market})[0]; asks=f(book.get('total_ask_size')); bids=f(book.get('total_bid_size')); ratio=bids/asks if asks else 9.99
        units=book.get('orderbook_units',[])[:10]
        max_ask=max((f(x.get('ask_size')) for x in units),default=0); max_bid=max((f(x.get('bid_size')) for x in units),default=0)
        wall_ratio=max_bid/max_ask if max_ask else 9.99
    except Exception:
        ratio,wall_ratio=1.0,1.0
    try:
        ticks=get('/v1/trades/ticks',{'market':market,'count':120}); bv=sum(f(x.get('trade_volume')) for x in ticks if x.get('ask_bid')=='BID'); sv=sum(f(x.get('trade_volume')) for x in ticks if x.get('ask_bid')=='ASK'); strength=100*bv/sv if sv else 999
    except Exception: strength=100
    return ratio,wall_ratio,strength

def rvol(c,n=20):
    v=vals(c,'candle_acc_trade_price')
    if len(v)<n+1:return 1.0
    base=sum(v[-n-1:-1])/n
    return v[-1]/base if base else 1.0

def ma_gap(price, m): return (price-m)/m*100 if m else 0

def higher_structure(c, span=12):
    if len(c)<span*2:return False,False
    a=c[-span*2:-span]; b=c[-span:]
    return max(highs(b))>max(highs(a)), min(lows(b))>min(lows(a))

def daily_180_state(pd):
    if len(pd)<181:return {'above':False,'reclaim':False,'hold':False,'ma180':None,'false_break':False}
    s=sma_series(pd,180); above=pd[-1]>s[-1]
    recent_cross=False
    for i in range(max(180,len(pd)-10),len(pd)):
        if s[i] and s[i-1] and pd[i]>s[i] and pd[i-1]<=s[i-1]: recent_cross=True
    last3=sum(1 for i in range(len(pd)-3,len(pd)) if s[i] and pd[i]>s[i])
    hold=last3>=2
    false_break=False
    if len(pd)>=3 and s[-1] and s[-2] and pd[-2]>s[-2] and pd[-1]<s[-1]: false_break=True
    return {'above':above,'reclaim':recent_cross,'hold':hold,'ma180':s[-1],'false_break':false_break}

def squeeze_state(p4):
    n=CFG['bollinger']['period']; mult=CFG['bollinger']['std_mult']; widths=[]
    for i in range(n-1,len(p4)):
        *_,w=bb_at(p4,i,n,mult); widths.append(w)
    if not widths:return False,False,100
    cur=widths[-1]; hist=widths[-80:]; pct=percentile_rank(hist,cur)
    recent_squeeze=any(percentile_rank(hist, x)<=CFG['bollinger']['squeeze_percentile'] for x in widths[-10:])
    expanding=len(widths)>=3 and widths[-1]>widths[-2]>widths[-3]
    return recent_squeeze,expanding,pct

def upper_band_ride(p4):
    n=CFG['bollinger']['period']; mult=CFG['bollinger']['std_mult']; near=CFG['bollinger']['upper_near_pct']/100
    count=0
    for i in range(max(n-1,len(p4)-5),len(p4)):
        _,u,_,_=bb_at(p4,i,n,mult)
        if u and p4[i]>=u*(1-near): count+=1
    return count

def detect_patterns(c4,c60,c15,cd):
    p4,p60,p15,pd=map(closes,(c4,c60,c15,cd)); now=p15[-1]
    m4={n:ma(p4,n) for n in (7,14,30,60,180)}; m15={n:ma(p15,n) for n in (7,14,30)}; m60={n:ma(p60,n) for n in (7,14,30)}
    rv15=rvol(c15); rv60=rvol(c60); atr15=atr(c15,CFG['risk']['atr_period']); atr60=atr(c60,CFG['risk']['atr_period'])
    resistance15=max(highs(c15[-21:-1])) if len(c15)>=22 else max(highs(c15[:-1])); support15=min(lows(c15[-20:]))
    cp=close_position(c15[-1]); gc15=False
    if len(p15)>=15:
        prev7=sum(p15[-8:-1])/7; prev14=sum(p15[-15:-1])/14; gc15=prev7<=prev14 and m15[7]>m15[14]
    spread4=(max(m4[7],m4[14],m4[30])-min(m4[7],m4[14],m4[30]))/p4[-1]*100
    squeeze,bb_expanding,_=squeeze_state(p4)
    d180=daily_180_state(pd)
    hh4,hl4=higher_structure(c4)
    hist15=macd_hist(p15)
    macd_improve=len(hist15)>=3 and hist15[-1]>hist15[-2]>hist15[-3]
    patterns=[]; scores={}
    # 1 breakout
    breakout=0
    if m4[7]>m4[14]>m4[30]:breakout+=25
    if now>resistance15:breakout+=30
    elif (resistance15-now)/now*100<=1.0:breakout+=15
    if rv15>=CFG['volume']['rvol_confirm']:breakout+=20
    elif rv15>=CFG['volume']['rvol_watch']:breakout+=10
    if cp>=CFG['entry']['breakout_close_position']:breakout+=15
    if squeeze and bb_expanding:breakout+=10
    scores['돌파형']=min(100,breakout)
    if breakout>=65:patterns.append('돌파형')
    # 2 pullback
    pull=0; mid60,_,_,_=bb(p60)
    if m4[7]>m4[14]>m4[30]:pull+=30
    near_support=min(abs(now-m60[7]),abs(now-m60[14]),abs(now-(mid60 or now)))/now*100
    if near_support<=CFG['entry']['near_level_pct']:pull+=25
    swing_lows=merge_levels(pivot_levels(c60,'low'),now); structural=nearest_below(swing_lows,now)
    if structural and min(lows(c60[-4:]))>structural*.997:pull+=15
    if bullish(c15[-1]):pull+=10
    if rv15>=1.1:pull+=10
    if m15[7]>m15[14] or gc15:pull+=10
    scores['눌림형']=min(100,pull)
    if pull>=65:patterns.append('눌림형')
    # 3 daily 180 reclaim
    rec=0
    if d180['reclaim']:rec+=35
    if d180['hold']:rec+=25
    if d180['above']:rec+=10
    if m4[7]>m4[14]>m4[30]:rec+=20
    if rv60>=1.2:rec+=10
    scores['180일선 리클레임']=min(100,rec)
    if rec>=65:patterns.append('180일선 리클레임')
    # 4 bottom reversal
    bottom=0
    recent_low=min(lows(c4[-40:])); dist_low=(p4[-1]-recent_low)/recent_low*100 if recent_low else 99
    if dist_low<=8:bottom+=15
    if hl4:bottom+=20
    if gc15:bottom+=20
    if macd_improve:bottom+=15
    if m15[7]>m15[14]:bottom+=10
    if p15[-1]>m15[30]:bottom+=10
    if rv15>=1.2:bottom+=10
    scores['바닥반전형']=min(100,bottom)
    if bottom>=65:patterns.append('바닥반전형')
    if not patterns:
        top=max(scores,key=scores.get); patterns=[f'{top} 관찰']
    return patterns,scores,{'resistance15':resistance15,'support15':support15,'atr15':atr15,'atr60':atr60,'spread4':spread4,'hh4':hh4,'hl4':hl4,'d180':d180,'rv15':rv15,'rv60':rv60,'cp':cp,'squeeze':squeeze,'bb_expanding':bb_expanding}

def make_trade_plan(c4,c60,c15,pattern_scores):
    now=closes(c15)[-1]; atrv=atr(c15,CFG['risk']['atr_period']) or now*.01
    lows_all=merge_levels(pivot_levels(c15,'low',lookback=80)+pivot_levels(c60,'low',lookback=60),now)
    highs_all=merge_levels(pivot_levels(c15,'high',lookback=100)+pivot_levels(c60,'high',lookback=80)+pivot_levels(c4,'high',lookback=60),now)
    support=nearest_below(lows_all,now); resistance=nearest_above(highs_all,now)
    dominant=max(pattern_scores,key=pattern_scores.get)
    # Entry: confirmed pullback uses current; breakout uses level + small buffer if not already broken.
    if dominant=='돌파형':
        recent_res=max(highs(c15[-21:-1]))
        entry=max(now,recent_res*(1.001))
    else: entry=now
    buffer=max(entry*.003, atrv*CFG['risk']['structure_buffer_atr'])
    structure_stop=(support-buffer) if support else entry-1.25*atrv
    atr_stop=entry-CFG['risk']['atr_stop_mult']*atrv
    stop=min(structure_stop,atr_stop)
    if stop<=0 or stop>=entry: stop=entry-1.5*atrv
    risk_per=entry-stop
    if resistance and resistance>entry+0.5*risk_per: target1=resistance
    else: target1=entry+CFG['risk']['preferred_rr']*risk_per
    higher=[x for x in highs_all if x>target1*1.005]
    target2=min(higher) if higher else entry+3.0*risk_per
    rr=(target1-entry)/risk_per if risk_per>0 else None
    return {'entry':entry,'stop':stop,'target1':target1,'target2':target2,'rr':rr,'support':support,'resistance':resistance,'dominant':dominant}

def score_all(t,c4,c60,c15,cd):
    p4,p60,p15,pd=map(closes,(c4,c60,c15,cd)); now=p15[-1]; reasons=[]; warnings=[]; invalid=[]
    m4={n:ma(p4,n) for n in (7,14,30,60,180)}; m15={n:ma(p15,n) for n in (7,14,30)}; rr=rsi(p15); rv=rvol(c15)
    patterns,pattern_scores,ctx=detect_patterns(c4,c60,c15,cd); plan=make_trade_plan(c4,c60,c15,pattern_scores)
    # Trend 0-100
    trend=0
    if m4[7]>m4[14]:trend+=15; reasons.append('4H MA7>MA14')
    if m4[14]>m4[30]:trend+=15; reasons.append('4H MA14>MA30')
    if m4[30]>m4[60]:trend+=10
    if p4[-1]>m4[60]:trend+=10
    if p4[-1]>m4[180]:trend+=10
    if m4[60]>m4[180]:trend+=10
    if ctx['hh4']:trend+=10; reasons.append('4H 고점 상승')
    if ctx['hl4']:trend+=10; reasons.append('4H 저점 상승')
    if ctx['d180']['above']:trend+=10; reasons.append('일봉 180선 위')
    trend=min(100,trend)
    # Setup 0-100 = strongest pattern + structural quality modifiers
    setup=max(pattern_scores.values())
    if ctx['spread4']<=CFG['ma']['good_spread_pct']: setup=min(100,setup+5); reasons.append('4H 단기이평 수렴')
    if ctx['squeeze'] and ctx['bb_expanding']: setup=min(100,setup+5); reasons.append('BB 수축 후 확장')
    # Entry 0-100
    entry=0
    if m15[7]>m15[14]:entry+=15
    if p15[-1]>m15[30]:entry+=15
    if CFG['entry']['rsi_min']<=rr<=CFG['entry']['rsi_max']:entry+=15; reasons.append('15M RSI 우호')
    elif rr>CFG['entry']['rsi_hot']:warnings.append('15M RSI 과열')
    if rv>=CFG['volume']['rvol_confirm']:entry+=20; reasons.append(f'15M RVOL {rv:.2f}')
    elif rv>=CFG['volume']['rvol_watch']:entry+=10
    if ctx['cp']>=CFG['entry']['breakout_close_position']:entry+=10
    ma7_gap=ma_gap(p4[-1],m4[7])
    if 0<=ma7_gap<=CFG['ma']['overextension_warn_pct']:entry+=15
    elif ma7_gap>CFG['ma']['overextension_block_pct']:warnings.append(f'MA7 과이격 {ma7_gap:.1f}%: 추격 금지')
    if plan['rr'] is not None and plan['rr']>=CFG['risk']['preferred_rr']:entry+=10; reasons.append(f'예상 R:R {plan["rr"]:.2f}')
    elif plan['rr'] is not None and plan['rr']>=CFG['risk']['min_rr']:entry+=5
    entry=min(100,entry)
    # Flow confirm (not core signal)
    ratio,wall_ratio,strength=orderflow(t['market'])
    if ratio>=CFG['flow']['bid_ask_strong']:reasons.append(f'매수잔량 우세 {ratio:.1f}배')
    elif ratio<0.75:warnings.append('매도잔량 우세')
    if strength>=CFG['flow']['trade_strength_strong']:reasons.append(f'체결강도 {strength:.0f}%')
    elif strength<80:warnings.append('최근 매도체결 우세')
    # Risk 0-100, higher = worse
    risk=10
    if ma7_gap>CFG['ma']['overextension_warn_pct']:risk+=15
    if ma7_gap>CFG['ma']['overextension_block_pct']:risk+=20
    if rr>CFG['entry']['rsi_hot']:risk+=15
    if strength>=CFG['flow']['trade_strength_hot']:risk+=8; warnings.append('단기 체결 과열 가능')
    tv=f(t.get('acc_trade_price_24h'))
    if tv<5e8:risk+=25; warnings.append('저유동성')
    elif tv<1e9:risk+=15
    elif tv<2e9:risk+=8
    if plan['rr'] is None or plan['rr']<1:risk+=25
    elif plan['rr']<CFG['risk']['min_rr']:risk+=15; warnings.append('손익비 1.5R 미만')
    atr_pct=ctx['atr15']/now*100 if now else 0
    if atr_pct>4:risk+=10; warnings.append('15M 변동성 높음')
    if ctx['d180']['false_break']:risk+=15; warnings.append('일봉 180선 돌파 실패 가능')
    risk=min(100,risk)
    # Invalidation rules
    if plan['support']: invalid.append(f'{plan["support"]:,.4f} 부근 핵심 지지 종가 이탈')
    if plan['dominant']=='돌파형' and plan['resistance']: invalid.append('돌파가격 아래 재진입 후 회복 실패')
    invalid.append('4H MA7<MA14<MA30 역정렬 전환')
    # Decision
    if trend>=70 and setup>=75 and entry>=70 and risk<=40 and (plan['rr'] or 0)>=CFG['risk']['min_rr']:
        decision='매수 후보'; dclass='good'; summary='조건이 동시 충족된 구간. 진입 전 구조손절과 실제 체결 흐름을 재확인.'
    elif trend>=75 and setup>=70 and ma7_gap>CFG['ma']['overextension_warn_pct']:
        decision='눌림 대기'; dclass='warn'; summary='종목은 강하지만 가격이 단기이평에서 벌어져 있음. 추격보다 MA/BB 중심선 눌림 확인.'
    elif setup>=70 and entry<70:
        decision='확인 대기'; dclass='warn'; summary='패턴은 형성됐지만 진입 확인이 부족함. 거래량·종가·재반등 확인 대기.'
    elif risk>=65:
        decision='위험/제외'; dclass='bad'; summary='현재 자리의 위험도가 높음. 좋은 차트여도 진입 우선순위에서 제외.'
    else:
        decision='관찰'; dclass=''; summary='일부 조건만 충족. 다음 구조 변화가 확인될 때까지 관찰.'
    return dict(market=t['market'].replace('KRW-',''),price=f(t['trade_price']),change=f(t.get('signed_change_rate'))*100,turnover=tv,rvol=rv,rsi15=rr,trend=trend,setup=int(round(setup)),entry=entry,risk=risk,patterns=patterns,pattern_scores=pattern_scores,decision=decision,decision_class=dclass,summary=summary,plan={k:(round(v,8) if isinstance(v,float) else v) for k,v in plan.items() if k in ('entry','stop','target1','target2','rr')},ma7_gap=ma7_gap,bid_ask_ratio=ratio,trade_strength=strength,reasons=reasons[:10],warnings=warnings[:8],invalidations=invalid[:4])

def preliminary(t):
    c4=candles(t['market'],240,200); p4=closes(c4); m7,m14,m30=ma(p4,7),ma(p4,14),ma(p4,30); rv=rvol(c4)
    s=0
    if m7 and m14 and m30 and m7>m14>m30:s+=40
    if ma(p4,60) and p4[-1]>ma(p4,60):s+=20
    hh,hl=higher_structure(c4)
    if hh:s+=10
    if hl:s+=15
    if rv>=1.2:s+=15
    return s,c4

@app.get('/')
def home(): return render_template_string(HTML)

@app.get('/api/config')
def config(): return jsonify(CFG)

@app.get('/api/scan')
def scan():
    try:
        markets=[x for x in get('/v1/market/all',{'isDetails':'true'}) if x['market'].startswith('KRW-') and x.get('market_warning')!='CAUTION']
        names=[x['market'] for x in markets]; tickers=[]
        for i in range(0,len(names),100):
            tickers.extend(get('/v1/ticker',{'markets':','.join(names[i:i+100])})); time.sleep(.05)
        tickers.sort(key=lambda x:f(x.get('acc_trade_price_24h')),reverse=True)
        first=[]; skipped=[]
        for t in tickers[:CFG['scan']['ticker_top_n']]:
            try:
                ps,c4=preliminary(t); first.append((ps,t,c4)); time.sleep(.035)
            except Exception as e: skipped.append(f"{t.get('market')}:{type(e).__name__}")
        first.sort(key=lambda x:x[0],reverse=True)
        out=[]
        for _,t,c4 in first[:CFG['scan']['deep_top_n']]:
            try:
                c60=candles(t['market'],60,160); c15=candles(t['market'],15,160); cd=days(t['market'],200)
                out.append(score_all(t,c4,c60,c15,cd)); time.sleep(.05)
            except Exception as e: skipped.append(f"{t.get('market')}:{type(e).__name__}")
        # 매수후보 우선, 그 다음 Entry/Setup/Trend, Risk 낮은 순
        rank={'매수 후보':4,'눌림 대기':3,'확인 대기':2,'관찰':1,'위험/제외':0}
        out.sort(key=lambda x:(rank.get(x['decision'],0),x['entry'],x['setup'],x['trend'],-x['risk']),reverse=True)
        out=out[:CFG['scan']['output_n']]
        return jsonify(ok=True,items=out,note=f"v3 · 거래대금 상위 {CFG['scan']['ticker_top_n']}개 1차 → {len(out)}개 정밀분석",skipped=skipped[:10])
    except Exception as e:
        return jsonify(ok=False,error=type(e).__name__,detail=str(e)[:500]),500

@app.get('/health')
def health(): return {'ok':True,'version':'v3.0','strategy':'personal-chart-view'}

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=True)
