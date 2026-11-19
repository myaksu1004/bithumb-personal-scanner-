from flask import Flask, jsonify, render_template_string
import requests, time, math, statistics, json, os, threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

app = Flask(__name__)
EXCHANGE = os.getenv("EXCHANGE", "bithumb").strip().lower()
if EXCHANGE not in ("bithumb", "upbit"):
    raise ValueError("EXCHANGE must be bithumb or upbit")
BASE = "https://api.bithumb.com" if EXCHANGE == "bithumb" else "https://api.upbit.com"
S = requests.Session()
S.headers.update({"accept":"application/json","user-agent":"CoinStructureScanner/5.3"})

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "strategy_config.json"), "r", encoding="utf-8") as f:
    CFG = json.load(f)

HTML = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>코인 저점상승 탐색기 v5.3.1</title>
<style>
:root{--bg:#f4f5f7;--card:#fff;--text:#16181c;--sub:#667085;--line:#e5e7eb;--good:#067647;--warn:#b54708;--bad:#b42318;--blue:#175cd3}
*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans KR",sans-serif;background:var(--bg);margin:0;color:var(--text)}header{background:#fff;padding:20px 16px;border-bottom:1px solid var(--line)}h1{font-size:23px;margin:0 0 5px}.sub{font-size:12px;color:var(--sub);line-height:1.5}main{max-width:980px;margin:auto;padding:14px}.btn{width:100%;padding:16px;border:0;border-radius:14px;background:#111;color:#fff;font-size:17px;font-weight:800}.card{background:var(--card);border-radius:17px;padding:15px;margin:13px 0;box-shadow:0 1px 5px #0001}.row{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}.coin{font-size:21px;font-weight:850}.badge{padding:6px 9px;border-radius:999px;background:#eef0f2;font-weight:800;font-size:12px;white-space:nowrap}.meta{font-size:12px;color:var(--sub);margin-top:6px;line-height:1.5}.scores{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:12px}.score{background:#f7f8fa;border-radius:11px;padding:9px 4px;text-align:center}.score b{display:block;font-size:18px}.score span{font-size:9px;color:var(--sub)}.patterns{display:flex;flex-wrap:wrap;gap:5px;margin-top:9px}.tag{background:#eef4ff;color:#3538cd;padding:5px 7px;border-radius:999px;font-size:11px;font-weight:700}.decision{margin-top:10px;padding:10px;border-radius:11px;background:#fafafa;font-size:13px;font-weight:800}.plan{display:grid;grid-template-columns:repeat(6,1fr);gap:5px;margin-top:9px}.p{border:1px solid var(--line);border-radius:10px;padding:7px;text-align:center}.p b{display:block;font-size:12px}.p span{font-size:9px;color:var(--sub)}.reason{font-size:12px;line-height:1.65;color:#475467;margin-top:10px}.warn{color:var(--warn)}.bad{color:var(--bad)}.good{color:var(--good)}#status{text-align:center;color:var(--sub);margin:12px;font-size:13px}.foot{font-size:10px;color:#98a2b3;line-height:1.5;margin:14px 2px 28px}.trig{margin-top:9px;font-size:12px;background:#f0f6ff;border-radius:10px;padding:9px;color:#175cd3;line-height:1.55;font-weight:600}.jr{margin-top:9px;font-size:12px}.jr summary{cursor:pointer;font-weight:700;color:#475467}.jr pre{white-space:pre-wrap;word-break:break-word;background:#f7f8fa;border-radius:10px;padding:10px;font-size:11px;line-height:1.65;margin:7px 0}.jr button{padding:9px 14px;border:1px solid var(--line);border-radius:10px;background:#fff;font-weight:700;font-size:12px}.regime{margin:10px 0;padding:11px;border-radius:11px;background:#fff;font-size:13px;font-weight:800;text-align:center;border:1px solid var(--line)}
@media(max-width:700px){.scores{grid-template-columns:repeat(2,1fr)}.plan{grid-template-columns:repeat(2,1fr)}}
</style></head><body><header><h1>📊 코인 저점상승 탐색기 v5.3.1</h1><div class="sub">빗썸·업비트 선택 배포 | B형 저점 상승 우선 | 진입봉 3조건 판정 · 최근 30분 체결강도(건수·체결량 이중) · 호가벽/사다리 탐지 | 일지 블록 자동 생성</div></header><main><button class="btn" onclick="scan()">🔍 지금 탐색</button><a href="/backtest" style="display:block;text-align:center;margin-top:10px;font-size:14px;font-weight:700;color:#175cd3">🧪 백테스트 화면 열기</a><div id="status">버튼을 누르면 선택 거래소의 KRW 종목을 분석합니다.</div><div id="list"></div><div class="foot">분석 보조용 도구입니다. 신호는 미래 수익을 보장하지 않으며, 호가·체결 데이터는 순간적으로 바뀔 수 있습니다. 주문 실행 기능은 포함하지 않았습니다.</div></main>
<script>
const esc=t=>String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;');
function cp(id,btn){const el=document.getElementById(id);if(!el)return;navigator.clipboard.writeText(el.textContent).then(()=>{btn.textContent='복사됨';setTimeout(()=>btn.textContent='복사',1500)}).catch(()=>{const r=document.createRange();r.selectNodeContents(el);const s=getSelection();s.removeAllRanges();s.addRange(r);btn.textContent='길게 눌러 복사'})}
const won=v=>v>=1e8?(v/1e8).toFixed(1)+"억":Math.round(v).toLocaleString();
const px=v=>v==null?'-':(v>=1000?Math.round(v).toLocaleString():v>=100?v.toFixed(1):v>=1?v.toFixed(2):v.toFixed(4));
async function scan(){const s=document.querySelector('#status'),l=document.querySelector('#list');s.textContent='B형 저점 상승 후보 탐색 → 진입 타이밍 분석 중…';l.innerHTML='';try{const r=await fetch('/api/scan');const d=await r.json();if(!r.ok||d.ok===false)throw new Error(d.detail||d.error||'API 오류');s.innerHTML='완료 · '+esc(d.note);l.innerHTML='';l.innerHTML=d.items.map((x,i)=>`<div class="card"><div class="row"><div><span class="coin">${x.market}</span> ${px(x.price)}원<div class="meta">${x.change>=0?'+':''}${x.change.toFixed(2)}% · 24H ${won(x.turnover)} · RVOL ${x.rvol.toFixed(2)} · RSI15 ${x.rsi15.toFixed(1)}</div></div><span class="badge">${x.decision}</span></div><div class="scores"><div class="score"><b>${x.structure}</b><span>Structure</span></div><div class="score"><b>${x.timing}</b><span>Timing</span></div><div class="score"><b>${x.trend}</b><span>Trend</span></div><div class="score"><b>${x.setup}</b><span>Setup</span></div><div class="score"><b>${x.entry}</b><span>Entry</span></div><div class="score"><b>${x.risk}</b><span>Risk (상대 점수)</span></div><div class="score"><b>${x.pressure.score}</b><span>매도 압력 (높을수록 위험)</span></div></div><div class="patterns">${x.patterns.map(p=>`<span class="tag">${p}</span>`).join('')}${(x.rebound||[]).map(p=>`<span class="tag" style="background:#ecfdf3;color:#067647">↗ ${p}</span>`).join('')}</div><div class="decision ${x.decision_class}">${x.summary}</div><div class="plan"><div class="p"><b>${px(x.plan.entry)}</b><span>진입 기준 · ${esc(x.plan.entry_type||'-')}</span></div><div class="p"><b>${px(x.plan.stop)}</b><span>손절${x.plan.stop_source?' · '+esc(x.plan.stop_source):''}</span></div><div class="p"><b>${px(x.plan.recover)}</b><span>원금 회수</span></div><div class="p"><b>${px(x.plan.target1)}</b><span>1차 목표</span></div><div class="p"><b>${px(x.plan.target2)}</b><span>2차 목표</span></div><div class="p"><b>${x.plan.rr==null?'-':x.plan.rr.toFixed(2)+'R'}</b><span>1차 목표 R:R</span></div></div><div class="meta">분석 기준가 ${px(x.basis_price)}원 (현재가와 ${x.price_gap_pct>=0?'+':''}${x.price_gap_pct.toFixed(2)}% 차이) · 손절 거리 ${x.plan.stop_pct.toFixed(2)}% · ATR 기준 최소 ${x.plan.noise_floor_pct.toFixed(2)}% · 패턴 ${x.pattern_type} · MA7 이격 ${x.ma7_gap.toFixed(2)}% · 매수/매도잔량 ${x.bid_ask_ratio.toFixed(2)}배 · 체결강도 ${x.trade_strength==null?'측정 불가':x.trade_strength.toFixed(0)+'%'+(x.strength_basis&&x.strength_window_min?' ('+esc(x.strength_basis)+' 기준·최근 '+x.strength_window_min.toFixed(1)+'분)':'')}${x.rel_strength?' · 장세 대비 '+x.rel_strength.toFixed(2)+'배':''}${x.strength_vol!=null&&x.strength_cnt!=null?' · 체결량 '+x.strength_vol.toFixed(0)+'% / 건수 '+x.strength_cnt.toFixed(0)+'%':''}</div><div class="reason">✓ ${x.reasons.map(esc).join(' · ')||'조건 탐색 중'}${x.guard_flags&&x.guard_flags.length?`<br><span class="bad">⛔ 하락 방어: ${x.guard_flags.map(esc).join(' · ')}</span>`:''}${x.pressure.flags.length?`<br><span class="warn">매도 압력: ${x.pressure.flags.map(esc).join(' · ')}</span>`:''}${x.warnings.length?`<br><span class="warn">⚠ ${x.warnings.map(esc).join(' · ')}</span>`:''}${x.invalidations.length?`<br><span class="bad">⛔ 무효화: ${x.invalidations.map(esc).join(' · ')}</span>`:''}</div><div class="trig">🎯 진입봉 3조건: ${esc(x.entry_check.state)} — ${esc(x.entry_check.detail)}</div><details class="jr"><summary>📋 일지용 요약 (복사해서 일지 대화에 붙여넣기)</summary><pre id="j${i}">${esc((x.journal||[]).join('\n'))}</pre><button onclick="cp('j'+${i},this)">복사</button></details></div>`).join('');}catch(e){s.textContent='탐색 실패: '+e.message}}
</script></body></html>'''

# 빗썸 공개 시세 API: 보수적인 요청 간격 및 429 재시도.
# 서버 내 여러 사용자의 동시 클릭도 공유 IP 한도에 맞추어 직렬화한다.
API_LOCK = threading.Lock()
SCAN_LOCK = threading.Lock()
LAST_CALL = {}

def get(path, params=None):
    group = ('candle' if '/candles/' in path else
             'ticker' if '/ticker' in path else
             'orderbook' if '/orderbook' in path else
             'trade' if '/trades/' in path else 'market')
    for attempt in range(4):
        with API_LOCK:
            now = time.monotonic()
            gap = 0.14 if group == 'candle' else 0.12
            remaining = gap - (now - LAST_CALL.get(group, 0))
            if remaining > 0:
                time.sleep(remaining)
            LAST_CALL[group] = time.monotonic()
            try:
                r = S.get(BASE + path, params=params, timeout=15)
            except requests.RequestException:
                if attempt == 3:
                    raise
                r = None
        if r is not None and r.status_code not in (429, 500, 502, 503, 504):
            r.raise_for_status()
            return r.json()
        if attempt < 3:
            time.sleep(min(2 ** attempt, 4))
    if r is not None:
        r.raise_for_status()
    raise RuntimeError('거래소 시세 API 연결 실패')

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
    # Wilder 평활(RMA): 거래소 차트 RSI와 같은 방식. 첫 n개는 단순평균으로 시드.
    ds=[a[i]-a[i-1] for i in range(1,len(a))]
    g=sum(max(x,0) for x in ds[:n])/n; l=sum(max(-x,0) for x in ds[:n])/n
    for x in ds[n:]:
        g=(g*(n-1)+max(x,0))/n; l=(l*(n-1)+max(-x,0))/n
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

KST = ZoneInfo('Asia/Seoul')

def completed_candles(raw, minutes=None):
    """Exclude unfinished KST candles using exchange candle open times."""
    now=datetime.now(KST)
    out=[]
    for bar in raw:
        stamp=bar.get('candle_date_time_kst')
        if not stamp:
            raise ValueError('거래소 캔들 시각 누락')
        opened=datetime.fromisoformat(stamp).replace(tzinfo=KST)
        duration=timedelta(minutes=minutes) if minutes else timedelta(days=1)
        if opened+duration<=now:
            out.append(bar)
    return out

def candles(market,unit,count=200):
    raw=list(reversed(get(f'/v1/candles/minutes/{unit}',{'market':market,'count':count})))
    return completed_candles(raw,unit)

def days(market,count=200):
    raw=list(reversed(get('/v1/candles/days',{'market':market,'count':count})))
    return completed_candles(raw)

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

EMPTY_FLOW={'ratio':1.0,'wall_ratio':1.0,'strength':None,'strength_vol':None,'strength_cnt':None,
            'strength_basis':None,'window_min':0,'whale_share':0,'ticks':0,'book_ok':False,
            'ask_wall':None,'bid_wall':None,'bid_ladder':None,'ask_ladder':None}

def ladder_block(levels,tol_pct,min_levels):
    """크기가 거의 같은 호가가 연속으로 깔린 구간(마켓메이커 사다리 주문)을 찾는다.
    반환 (호가 단수, 구간 총잔량, 한 단 크기). 없으면 (0,0,0)."""
    if len(levels)<min_levels: return 0,0.0,0.0
    best=(0,0.0,0.0); i=0
    while i<len(levels):
        base=levels[i][1]
        if base<=0:
            i+=1; continue
        j=i+1
        while j<len(levels) and abs(levels[j][1]-base)/base*100<=tol_pct: j+=1
        if j-i>=min_levels and j-i>best[0]:
            best=(j-i,sum(x[1] for x in levels[i:j]),base)
        i=j if j>i+1 else i+1
    return best

def orderflow(market):
    """호가 잔량·벽 구조와 실제 체결 기준 체결강도.
    체결 틱이 모자라면 strength=None. 값을 지어내지 않는다 (v5.2의 200% 더미 제거)."""
    cf=CFG['flow']; co=CFG.get('orderbook',{})
    out=dict(EMPTY_FLOW)
    try:
        book=get('/v1/orderbook',{'markets':market})[0]
        ask_tot=f(book.get('total_ask_size')); bid_tot=f(book.get('total_bid_size'))
        out['ratio']=bid_tot/ask_tot if ask_tot else 1.0
        units=book.get('orderbook_units',[])[:co.get('wall_top_n',15)]
        asks=[(f(u.get('ask_price')),f(u.get('ask_size'))) for u in units if f(u.get('ask_size'))>0]
        bids=[(f(u.get('bid_price')),f(u.get('bid_size'))) for u in units if f(u.get('bid_size'))>0]
        if asks and bids:
            out['book_ok']=True
            a=max(asks,key=lambda x:x[1]); b=max(bids,key=lambda x:x[1])
            out['ask_wall']={'price':a[0],'size':a[1]}
            out['bid_wall']={'price':b[0],'size':b[1]}
            out['wall_ratio']=b[1]/a[1] if a[1] else 1.0
            tol=co.get('ladder_tolerance_pct',3.0); mn=co.get('ladder_min_levels',4)
            for key,arr,tot in (('bid_ladder',bids,bid_tot),('ask_ladder',asks,ask_tot)):
                n,sz,unit=ladder_block(arr,tol,mn)
                if n: out[key]={'levels':n,'size':sz,'unit':unit,'share':(sz/tot if tot else 0)}
    except Exception:
        pass
    # 체결강도: 거래소 앱의 '당일 누적'과 다른 지표다. 틱 API는 한 번에 500건이 한계이고
    # XRP 기준 500건이 약 6분치밖에 안 되므로, 구간을 분으로 고정해 종목 간 비교가 되게 한다.
    try:
        cnt=cf.get('tick_count',500); pages=max(1,cf.get('tick_pages',2))
        raw=[]; cursor=None
        for _ in range(pages):
            params={'market':market,'count':cnt}
            if cursor: params['cursor']=cursor
            page=get('/v1/trades/ticks',params)
            if not page: break
            raw.extend(page)
            cursor=page[-1].get('sequential_id')
            if not cursor: break
        seen={}
        for k,x in enumerate(raw): seen[x.get('sequential_id') or f'_{k}']=x
        ticks=[x for x in seen.values() if f(x.get('timestamp'))>0]
        if ticks:
            newest=max(f(x.get('timestamp')) for x in ticks)
            cutoff=newest-cf.get('max_window_min',30)*60000
            ticks=[x for x in ticks if f(x.get('timestamp'))>=cutoff]
        out['ticks']=len(ticks)
        if len(ticks)>=cf.get('min_ticks_for_strength',60):
            stamps=[f(x.get('timestamp')) for x in ticks]
            out['window_min']=round((max(stamps)-min(stamps))/60000.0,1)
            bv=sum(f(x.get('trade_volume')) for x in ticks if x.get('ask_bid')=='BID')
            sv=sum(f(x.get('trade_volume')) for x in ticks if x.get('ask_bid')=='ASK')
            nb=sum(1 for x in ticks if x.get('ask_bid')=='BID')
            ns=sum(1 for x in ticks if x.get('ask_bid')=='ASK')
            biggest=max((f(x.get('trade_volume')) for x in ticks),default=0)
            out['whale_share']=round(biggest/(bv+sv),3) if (bv+sv)>0 else 0
            out['strength_vol']=100*bv/sv if sv>0 else None
            out['strength_cnt']=100*nb/ns if ns>0 else None
            # 고래 체결 한 건이 구간 체결량의 25% 이상이면 체결량 기준은 신뢰할 수 없다 → 건수 기준 사용
            whale=out['whale_share']>=cf.get('whale_share_warn',0.25)
            if whale and out['strength_cnt'] is not None:
                out['strength']=out['strength_cnt']; out['strength_basis']='건수'
            elif out['strength_vol'] is not None:
                out['strength']=out['strength_vol']; out['strength_basis']='체결량'
            elif out['strength_cnt'] is not None:
                out['strength']=out['strength_cnt']; out['strength_basis']='건수'
            if out['window_min']<cf.get('min_window_min',2.0):
                out['strength']=None; out['strength_basis']='구간 과소'
    except Exception:
        pass
    return out

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

def confirmed_pivots(c, kind='low', left=None, right=None, lookback=100):
    """Only confirmed pivots; right-side candles must already be closed."""
    left=CFG['structure']['pivot_left'] if left is None else left
    right=CFG['structure']['pivot_right'] if right is None else right
    key='low_price' if kind=='low' else 'high_price'
    a=vals(c,key); result=[]
    for i in range(max(left,len(a)-lookback),len(a)-right):
        before=a[i-left:i]; after=a[i+1:i+right+1]
        if kind=='low' and a[i]<min(before) and a[i]<=min(after): result.append((i,a[i]))
        if kind=='high' and a[i]>max(before) and a[i]>=max(after): result.append((i,a[i]))
    return result

def b_structure(c4,cd):
    """Confirmed higher-low structure, with support margin and recent drawdown quality."""
    p4=closes(c4); pivots=confirmed_pivots(c4,'low',lookback=110)
    hp=confirmed_pivots(c4,'high',lookback=110)
    if len(pivots)<3:
        return {'score':0,'valid':False,'support':None,'reason':'확정 스윙 저점 3개 미만',
                'higher_lows':0,'quality':0,'support_margin_pct':None}
    recent=pivots[-3:]; vals3=[x[1] for x in recent]
    threshold=CFG['structure']['min_higher_low_pct']/100
    steps=sum(vals3[i]>vals3[i-1]*(1+threshold) for i in (1,2))
    support=vals3[-1]; last=p4[-1]
    margin=(last-support)/support*100 if support else -100
    # Historical higher lows cannot validate a trend that subsequently lost support.
    intact=last>support and min(lows(c4[recent[-1][0]+1:]))>=support*(1-CFG['structure']['support_wick_tolerance_pct']/100) if recent[-1][0]+1<len(c4) else last>support
    score=steps*25
    if intact: score+=10
    if len(hp)>=2 and hp[-1][1]>hp[-2][1]:score+=10
    if ma(p4,30) and last>ma(p4,30):score+=10
    pd=closes(cd)
    if len(pd)>=30 and pd[-1]>ma(pd,30):score+=5
    if margin>=CFG['structure']['healthy_support_margin_pct']:score+=10
    # A rising low alone is not enough if price is already dumping from its recent peak.
    recent_high=max(highs(c4[-18:]))
    drawdown=(recent_high-last)/recent_high*100 if recent_high else 0
    if drawdown>=CFG['pressure']['four_hour_drawdown_warn_pct']:score-=15
    if drawdown>=CFG['pressure']['four_hour_drawdown_block_pct']:score-=15
    if margin<0:score=min(score,30)
    elif margin<CFG['structure']['near_support_margin_pct']:score-=10
    score=max(0,min(100,score))
    return {'score':score,'valid':steps>=CFG['structure']['min_higher_lows'] and intact,'support':support,
            'reason':'연속 스윙 저점 상승' if steps==2 else '저점 상승 불충분',
            'higher_lows':steps,'quality':score,'support_margin_pct':round(margin,2),
            'drawdown_4h_pct':round(drawdown,2)}


def selling_pressure(c15,c60,t):
    """Conservative selling-pressure heuristic, not a measured probability."""
    cfg=CFG['pressure']; p=closes(c15); r=rsi(p)
    recent=c15[-cfg['lookback_15m']:]
    v=vals(c15,'candle_acc_trade_price')
    baseline=sum(v[-21:-1])/20 if len(v)>=21 else 0
    rv=(v[-1]/baseline) if baseline else 1.0
    drop24=f(t.get('signed_change_rate'))*100
    high=max(highs(recent))
    drawdown=(high-p[-1])/high*100 if high else 0
    hist=macd_hist(p)
    falling=len(hist)>=2 and hist[-1]<0 and hist[-1]<hist[-2]
    down_bar=not bullish(c15[-1]); red=0
    for bar in reversed(c15[-4:]):
        if not bullish(bar):red+=1
        else:break
    points=0; flags=[]; hard=False
    if drop24<=-cfg['daily_drop_warn_pct']:
        points+=20;flags.append(f'24시간 {drop24:.1f}% 하락')
    if drawdown>=cfg['drawdown_warn_pct']:
        points+=20;flags.append(f'최근 15분봉 고점 대비 {drawdown:.1f}% 하락')
    if rv>=cfg['sell_volume_rvol'] and down_bar:
        points+=25;flags.append(f'음봉 거래대금 급증 RVOL {rv:.2f}')
    if falling and r<cfg['rsi_weak']:
        points+=20;flags.append('MACD 하락·RSI 약세')
    if red>=3:
        points+=15;flags.append('15분봉 3개 연속 약세')
    # A sharp daily decline with elevated volume must not pass as an immediate entry.
    if drop24<=-cfg['daily_drop_block_pct'] and rv>=cfg['sell_volume_rvol']:
        hard=True;flags.append('급락 + 거래대금 급증: 신규 진입 차단')
    if drawdown>=cfg['drawdown_block_pct'] and falling:
        hard=True;flags.append('급락 중 모멘텀 악화: 신규 진입 차단')
    return {'score':min(100,points),'flags':flags,'hard_block':hard,
            'change24_pct':round(drop24,2),'drawdown15_pct':round(drawdown,2),
            'rvol':round(rv,2)}

def rsi_series(a,n=14):
    """rsi()와 같은 Wilder 방식으로 봉마다의 RSI를 돌려준다."""
    out=[50.0]*len(a)
    if len(a)<n+1:return out
    ds=[a[i]-a[i-1] for i in range(1,len(a))]
    g=sum(max(x,0) for x in ds[:n])/n; l=sum(max(-x,0) for x in ds[:n])/n
    out[n]=100.0 if l==0 else 100-(100/(1+g/l))
    for k,x in enumerate(ds[n:],start=n+1):
        g=(g*(n-1)+max(x,0))/n; l=(l*(n-1)+max(-x,0))/n
        out[k]=100.0 if l==0 else 100-(100/(1+g/l))
    return out

REBOUND_DEFAULT={'rsi_oversold':30,'div_rsi_max':40,'div_min_rsi_gap':2.0,'fresh_bars':2,
                 'climax_rvol':2.0,'sweep_lookback':40}

def rebound_signals(c15):
    """확정 15분봉 기준 단기 반등 태그. 관찰용이며 판정(decision)·진입 계획에는 영향을 주지 않는다."""
    cfg={**REBOUND_DEFAULT,**CFG.get('rebound',{})}
    n=len(c15)
    if n<40:return []
    p=closes(c15); lo=lows(c15); rs=rsi_series(p); last=c15[-1]; tags=[]
    bn=CFG['bollinger']['period']; bm=CFG['bollinger']['std_mult']
    # 1) 과매도 후 복귀: RSI가 과매도선을 위로 되찾거나, 볼린저 하단 밖 종가 → 밴드 안 종가
    _,_,lb_now,_=bb_at(p,n-1,bn,bm); _,_,lb_prev,_=bb_at(p,n-2,bn,bm)
    if (rs[-2]<cfg['rsi_oversold']<=rs[-1]) or (lb_prev and lb_now and p[-2]<lb_prev and p[-1]>lb_now):
        tags.append('과매도 복귀')
    # 2) RSI 상승 다이버전스: 방금 확정된 스윙 저점이 직전 저점보다 낮은데 RSI는 더 높음
    right=CFG['structure']['pivot_right']
    piv=confirmed_pivots(c15,'low',lookback=60)
    if len(piv)>=2:
        (i1,l1),(i2,l2)=piv[-2],piv[-1]
        if i2>=n-1-right-cfg['fresh_bars'] and l2<l1 and rs[i1]<cfg['div_rsi_max'] and rs[i2]>=rs[i1]+cfg['div_min_rsi_gap'] and bullish(last):
            tags.append('RSI 상승 다이버전스')
    # 3) 투매 후 반전: 직전 봉이 거래대금 터진 음봉, 이번 봉이 그 봉의 중간값 위에서 마감한 양봉
    v=vals(c15,'candle_acc_trade_price'); base=sum(v[-22:-2])/20 if n>=22 else 0
    prev=c15[-2]
    if base and v[-2]/base>=cfg['climax_rvol'] and not bullish(prev) and bullish(last) and p[-1]>(f(prev['high_price'])+f(prev['low_price']))/2:
        tags.append('투매 후 반전')
    # 4) 저점 스윕 후 회복: 최근 2개 봉이 직전 스윙 저점을 처음으로 깼다가 종가는 그 위로 회복
    older=[x for x in piv if n-cfg['sweep_lookback']<=x[0]<=n-3-right]
    if older:
        i0,level=older[-1]
        if min(lo[-2:])<level<p[-1] and bullish(last) and min(lo[i0+1:n-2] or [level])>=level:
            tags.append('저점 스윕 후 회복')
    # 5) 단기 이평 리클레임: 직전 종가는 MA7·MA14 아래, 이번 종가는 둘 다 위
    m7,m14,pm7,pm14=ma(p,7),ma(p,14),ma(p[:-1],7),ma(p[:-1],14)
    if p[-2]<min(pm7,pm14) and p[-1]>max(m7,m14) and bullish(last):
        tags.append('단기 이평 리클레임')
    return tags

def entry_trigger_check(c15,trigger):
    """사용자 진입봉 3조건을 코드가 직접 판정한다.
      ① 돌파선을 꼬리가 아닌 '몸통'으로 넘긴 15분봉
      ② 그 봉 거래량이 직전 5~10봉 평균의 약 2배
      ③ 다음 봉이 그 선 위에서 마감(확인봉)
    확인봉 마감이 진입 시점이고, 돌파봉 자체는 추격하지 않는다."""
    cfg=CFG.get('entry_trigger',{})
    out={'state':'선 미설정','breakout_idx':None,'vol_mult':None,'confirm_low':None,
         'trigger':trigger,'detail':''}
    if not trigger or len(c15)<25: return out
    v=vals(c15,'candle_acc_trade_price'); base_n=cfg.get('vol_base_bars',10)
    look=cfg.get('lookback_bars',5); need=cfg.get('volume_mult',2.0); soft=cfg.get('volume_mult_min',1.7)
    out['state']='대기'
    out['detail']=f'{trigger:,.4f} 위로 몸통 마감 + 거래량 {need:.1f}배를 기다리는 자리'
    last=len(c15)-1
    for i in range(max(1,last-look+1),last+1):
        o=f(c15[i]['opening_price']); c=f(c15[i]['trade_price'])
        if not (c>trigger and o<=trigger):   # 몸통으로 선을 넘긴 봉만 인정 (윗꼬리만 걸친 봉 제외)
            continue
        prev=v[max(0,i-base_n):i]
        mult=(v[i]/(sum(prev)/len(prev))) if prev and sum(prev)>0 else 0
        out['breakout_idx']=i; out['vol_mult']=round(mult,2)
        if mult<soft:
            out['state']='돌파봉 거래량 미달'
            out['detail']=f'몸통 돌파는 나왔지만 거래량 {mult:.2f}배로 기준({need:.1f}배) 미달'
            return out
        if i==last:
            out['state']='돌파봉 발생'
            out['detail']=f'거래량 {mult:.2f}배 몸통 돌파. 다음 15분봉이 {trigger:,.4f} 위에서 마감하면 진입'
            return out
        nxt=c15[i+1]
        if f(nxt['trade_price'])>trigger:
            out['state']='확인 완료'; out['confirm_low']=f(nxt['low_price'])
            out['detail']=f'거래량 {mult:.2f}배 돌파 + 확인봉 마감 완료. 진입 조건 충족'
        else:
            out['state']='돌파 실패'
            out['detail']=f'돌파 후 확인봉이 {trigger:,.4f} 아래에서 마감. 재돌파까지 보류'
        return out
    return out

def apply_rule_stop(plan,c15,trig):
    """확인봉이 나왔으면 손절을 본인 규칙으로 교체한다:
    확인봉 저가 아래 / 15분 60이평 아래 중 가까운 쪽(= 둘 중 높은 값)."""
    if not trig or trig.get('state')!='확인 완료' or trig.get('confirm_low') is None:
        return plan
    entry=plan['entry']; m60=ma(closes(c15),60)
    cands=[x for x in (trig['confirm_low'],m60) if x and 0<x<entry]
    if not cands: return plan
    base=max(cands)
    atrv=atr(c15,CFG['risk']['atr_period']) or entry*.01
    stop=base-max(entry*.001,atrv*CFG['risk']['stop_buffer_atr'])
    if stop<=0 or stop>=entry: return plan
    stop_pct=(entry-stop)/entry*100; noise=plan.get('noise_floor_pct',CFG['risk']['min_stop_pct'])
    plan=dict(plan)
    plan.update({'stop':stop,'stop_pct':stop_pct,
                 'stop_source':'확인봉 저가' if base==trig['confirm_low'] else '15분 60이평',
                 'stop_too_tight':stop_pct<noise,
                 'stop_eligible':stop_pct<=CFG['risk']['max_stop_pct'] and stop_pct>=noise})
    t1=plan.get('target1')
    plan['rr']=(t1-entry)/(entry-stop) if t1 and entry>stop else None
    return plan

def fmt_px(v):
    if v is None: return '-'
    return f'{v:,.0f}' if abs(v)>=1000 else (f'{v:,.2f}' if abs(v)>=1 else f'{v:,.4f}')

def journal_block(r):
    """종목 분석 대화에서 쓰던 7줄 요약을 탐색기가 바로 만들어 준다 (일지 대화에 복사용)."""
    p=r['plan']; ec=r.get('entry_check') or {}
    st=r.get('trade_strength'); rel=r.get('rel_strength')
    bs=r.get('strength_basis'); wn=r.get('strength_window_min') or 0
    strength=('측정 불가' if st is None else
              f"{st:.0f}%"+(f" [{bs} 기준·최근 {wn:.1f}분]" if bs and wn else "")
              +(f' (장세 대비 {rel:.2f}배)' if rel else ''))
    walls=' · '.join(r.get('flow_notes') or []) or '특이 벽 없음'
    rr=p.get('rr')
    return [
        f"추세: {r['pattern_type']} · {'/'.join(r['patterns'])} · Trend {r['trend']} / Structure {r['structure']}",
        f"거래량: RVOL {r['rvol']:.2f} · 24H {r['turnover']/1e8:.1f}억"+(f" · 돌파봉 거래량 {ec['vol_mult']:.2f}배" if ec.get('vol_mult') else ""),
        f"호가: 체결강도 {strength} · 매수/매도잔량 {r['bid_ask_ratio']:.2f}배 · {walls}",
        f"지지·저항: 지지 {fmt_px(p.get('support'))} / 저항 {fmt_px(p.get('target1'))} · {fmt_px(p.get('target2'))}",
        f"판단: {r['decision']} · 진입봉 {ec.get('state','-')} ({ec.get('detail','')})",
        f"진입·손절·목표: {fmt_px(p.get('entry'))}({p.get('entry_type','-')}) / {fmt_px(p.get('stop'))}"
        + (f"[{p['stop_source']}]" if p.get('stop_source') else "")
        + f" / 원금회수 {fmt_px(p.get('recover'))} → 목표 {fmt_px(p.get('target1'))}"
        + (f" ({rr:.2f}R)" if rr else ""),
        f"무효화: {' · '.join(r['invalidations'][:2]) if r.get('invalidations') else '-'}",
    ]

def timing_score(c15,c60):
    p=closes(c15); h=macd_hist(p); r=rsi(p); score=0
    if p[-1]>ma(p,7):score+=20
    if ma(p,7)>ma(p,14):score+=20
    if len(h)>2 and h[-1]>h[-2]:score+=20
    if CFG['entry']['rsi_min']<=r<=CFG['entry']['rsi_max']:score+=15
    if bullish(c15[-1]):score+=10
    if rvol(c15)>=1.1:score+=10
    if closes(c60)[-1]>ma(closes(c60),14):score+=5
    return score

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

def make_trade_plan(c4,c60,c15,pattern_scores,structure=None):
    now=closes(c15)[-1]
    atrv=atr(c15,CFG['risk']['atr_period']) or now*.01
    lows_all=merge_levels(pivot_levels(c15,'low',lookback=80)+pivot_levels(c60,'low',lookback=60),now)
    highs_all=merge_levels(pivot_levels(c15,'high',lookback=100)+pivot_levels(c60,'high',lookback=80)+pivot_levels(c4,'high',lookback=60),now)
    support=nearest_below(lows_all,now)
    resistance=nearest_above(highs_all,now)
    dominant=max(pattern_scores,key=pattern_scores.get)
    # 진입 기준가는 '지금 가격'이 아니라 몸통으로 넘어야 확인되는 구조적 선으로 잡는다.
    # 돌파형은 최근 20봉 고점, 그 외는 현재가 위의 가장 가까운 확정 스윙 고점.
    ce=CFG.get('entry_level',{})
    buf=1+ce.get('trigger_buffer_pct',0.1)/100
    bar_high=max(highs(c15[-21:-1]))*buf if len(c15)>=22 else None
    trigger=bar_high
    if dominant!='돌파형':
        above=[v for _,v in confirmed_pivots(c15,'high',lookback=ce.get('pivot_lookback_15m',60)) if v>now]
        trigger=min(above)*buf if above else bar_high
    entry=now; entry_type='현재가'; trigger_gap=0.0
    if trigger and trigger>now:
        trigger_gap=(trigger-now)/now*100
        if trigger_gap<=ce.get('max_trigger_distance_pct',2.5):
            entry=trigger; entry_type='돌파 확인선'
        else:
            entry_type='돌파선 원거리'
    # Tight stops are not forced above structural invalidation: skip if the structure is too far away.
    buffer=max(entry*.001,atrv*CFG['risk']['stop_buffer_atr'])
    candidate_supports=[v for v in (support,(structure or {}).get('support')) if v and v<entry]
    nearest=max(candidate_supports) if candidate_supports else None
    stop=(nearest-buffer) if nearest else entry-CFG['risk']['stop_atr_mult']*atrv
    stop_pct=(entry-stop)/entry*100 if entry>0 else 100
    min_stop=CFG['risk']['min_stop_pct']
    # Never fabricate a deeper stop just to satisfy a minimum percentage.
    # Require enough room for normal 15m ATR noise and an actual support-based stop.
    noise_floor=max(min_stop, (atrv/entry*100)*CFG['risk']['min_stop_atr_mult'])
    stop_too_tight=stop_pct<noise_floor
    max_stop=CFG['risk']['max_stop_pct']
    stop_eligible=stop_pct<=max_stop and not stop_too_tight and nearest is not None and stop>0 and stop<entry
    target1=resistance if resistance and resistance>entry else None
    higher=[x for x in highs_all if target1 and x>target1*1.005]
    target2=min(higher) if higher else None
    rr=(target1-entry)/(entry-stop) if target1 and entry>stop else None
    return {'entry':entry,'stop':stop,'stop_pct':stop_pct,'stop_eligible':stop_eligible,
            'target1':target1,'target2':target2,'rr':rr,'support':support,
            'resistance':resistance,'dominant':dominant,'stop_too_tight':stop_too_tight,'noise_floor_pct':round(noise_floor,2),'structural_support':nearest,
            'entry_type':entry_type,'trigger_gap_pct':round(trigger_gap,2),'trigger':trigger,'stop_source':None}


def entry_guard(c15, t):
    """Completed 15-minute candles only; veto late-entry / falling-knife setups."""
    g=CFG['guard']
    completed=c15  # upstream already removes unfinished candles
    if len(completed)<max(35,g['drawdown_lookback_15m']):
        return ['15분봉 데이터 부족'], {}
    p=closes(completed)
    h=macd_hist(p)
    recent_high=max(highs(completed[-g['drawdown_lookback_15m']:]))
    drawdown=(recent_high-p[-1])/recent_high*100 if recent_high else 0
    last_rsi=rsi(p); prev_rsi=rsi(p[:-1])
    falling_macd=len(h)>2 and h[-1]<0 and h[-1]<h[-2]
    red_count=0
    for bar in reversed(completed):
        if f(bar['trade_price'])<f(bar['opening_price']):red_count+=1
        else:break
    v=vals(completed,'candle_acc_trade_price')
    vol_ratio=v[-1]/(sum(v[-21:-1])/20) if sum(v[-21:-1]) else 1
    flags=[]
    if drawdown>=g['max_drawdown_from_high_pct'] and (last_rsi<g['rsi_recovery_min'] or falling_macd):
        flags.append(f'고점 대비 {drawdown:.1f}% 하락 + 반등 미확인')
    if falling_macd and last_rsi<g['rsi_recovery_min'] and last_rsi<=prev_rsi:
        flags.append('15M MACD 약세·RSI 회복 실패')
    if red_count>=g['max_consecutive_red_15m'] and vol_ratio<g['min_recent_volume_ratio']:
        flags.append('연속 음봉 및 거래량 약화')
    # Last two completed candles both below their short MA: avoid falling-knife entries.
    if len(p)>=31 and p[-1]<ma(p,7) and p[-1]<ma(p,14) and h[-1]<0 and h[-1]<h[-2]:
        flags.append('15M 단기 이평 하회 및 MACD 약화')
    rise=f(t.get('signed_change_rate'))*100
    if rise>=g['max_24h_rise_pct'] and falling_macd:
        flags.append(f'24H +{rise:.1f}% 급등 후 모멘텀 둔화')
    return flags, {'drawdown_pct':round(drawdown,2),'rsi_closed':round(last_rsi,1),
                   'macd_falling':falling_macd,'red_count':red_count}

def score_all(t,c4,c60,c15,cd,now_dt=None,flow=None,market_strength=None):
    """now_dt/flow는 백테스트용 주입값. 실시간 스캔에서는 비워 둔다.
    market_strength: 같은 회차에 분석한 종목들의 체결강도 중앙값(장세 기준선)."""
    if min(len(c4),len(c60),len(c15))<80 or len(cd)<181:
        raise ValueError('확정봉 분석 데이터 부족')
    last=datetime.fromisoformat(c15[-1]['candle_date_time_kst']).replace(tzinfo=KST)
    if (now_dt or datetime.now(KST))-last>timedelta(minutes=45):
        raise ValueError('15분봉 데이터 오래됨 (45분 초과)')
    p4,p60,p15,pd=map(closes,(c4,c60,c15,cd)); now=p15[-1]; reasons=[]; warnings=[]; invalid=[]
    m4={n:ma(p4,n) for n in (7,14,30,60,180)}; m15={n:ma(p15,n) for n in (7,14,30)}; rr=rsi(p15); rv=rvol(c15)
    patterns,pattern_scores,ctx=detect_patterns(c4,c60,c15,cd)
    structure_info=b_structure(c4,cd)
    structure=structure_info['score']
    timing=timing_score(c15,c60)
    plan=make_trade_plan(c4,c60,c15,pattern_scores,structure_info)
    # 15분봉 진입봉 3조건 판정 → 확인봉이 나왔으면 손절도 본인 규칙으로 교체
    entry_check=entry_trigger_check(c15,plan.get('trigger'))
    plan=apply_rule_stop(plan,c15,entry_check)
    # 익절: 먼저 원금 회수(기본 1R), 잔여 물량만 목표까지
    plan['recover']=(plan['entry']+(plan['entry']-plan['stop'])*CFG.get('exit',{}).get('recover_r',1.0)
                     if plan['entry']>plan['stop'] else None)
    guard_flags,guard_metrics=entry_guard(c15,t)
    pressure=selling_pressure(c15,c60,t)
    rebound=rebound_signals(c15)
    if pressure['flags']:warnings.extend(pressure['flags'])
    if guard_flags:warnings.extend(guard_flags)
    if not plan['stop_eligible']:
        warnings.append('구조 손절 불가: 손절 폭 과대·과소 또는 확인된 지지 없음')
    # 진입·손절 계획은 마지막 확정 15분봉 종가 기준. 실시간 현재가가 그 기준에서 벗어나면 계획이 낡은 것.
    live=f(t.get('trade_price')) or now
    price_gap=(live-now)/now*100 if now else 0
    price_moved=abs(price_gap)>CFG['risk']['max_entry_slippage_pct']
    if price_moved:
        warnings.insert(0,f'현재가가 분석 기준가 대비 {price_gap:+.2f}%: 다음 15분봉 확정 후 재탐색')
    # Trend 0-100
    trend=0
    if m4[7]>m4[14]:trend+=15; reasons.append('4H MA7>MA14')
    if m4[14]>m4[30]:trend+=15; reasons.append('4H MA14>MA30')
    if m4[30]>m4[60]:trend+=10
    if p4[-1]>m4[60]:trend+=10
    if m4[180] and p4[-1]>m4[180]:trend+=10   # 4시간봉이 180개 미만이면 MA180이 없으므로 가점 없음
    if m4[180] and m4[60]>m4[180]:trend+=10
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
    fl=flow if isinstance(flow,dict) else (orderflow(t['market']) if flow is None else
        {**EMPTY_FLOW,'ratio':flow[0],'wall_ratio':flow[1],'strength':flow[2]})
    ratio=fl.get('ratio',1.0); wall_ratio=fl.get('wall_ratio',1.0); strength=fl.get('strength')
    if ratio>=CFG['flow']['bid_ask_strong']:reasons.append(f'매수잔량 우세 {ratio:.1f}배')
    elif ratio<0.75:warnings.append('매도잔량 우세')
    # 체결강도는 절대값이 아니라 같은 회차 다른 종목 대비 상대값으로 본다.
    # 전 종목이 비슷하면 종목 특성이 아니라 장세이기 때문.
    rel_strength=None
    win=fl.get('window_min',0); basis=fl.get('strength_basis'); whale=fl.get('whale_share',0)
    if strength is not None:
        sv_,sc_=fl.get('strength_vol'),fl.get('strength_cnt')
        flow_hint=(f"체결강도 {strength:.0f}%"+(f" ({basis} 기준·최근 {win:.1f}분)" if basis and win else ""))
        if sv_ is not None and sc_ is not None and abs(sv_-sc_)>=30:
            flow_hint+=f" · 체결량 {sv_:.0f}% vs 건수 {sc_:.0f}%"
            warnings.append(f'체결량·건수 기준 괴리 큼({sv_:.0f}% vs {sc_:.0f}%): 큰 체결 한두 건에 쏠린 구간')
        if whale>=CFG['flow'].get('whale_share_warn',0.25):
            warnings.append(f'단일 체결이 구간 체결량의 {whale*100:.0f}%: 건수 기준으로 대체 산정')
    if strength is None:
        if fl.get('ticks',0) or fl.get('book_ok'):
            warnings.append(f"체결 데이터 부족: 체결강도 미산정{'('+basis+')' if basis else ''}")
    elif market_strength:
        rel_strength=strength/market_strength
        if rel_strength>=CFG['flow'].get('rel_strength_strong',1.25):
            reasons.append(f'체결강도 {strength:.0f}% (장세 대비 {rel_strength:.2f}배)')
        elif rel_strength<=CFG['flow'].get('rel_strength_weak',0.85):
            warnings.append(f'체결강도 {strength:.0f}%: 장세 중앙값보다 약함')
    elif strength>=CFG['flow']['trade_strength_strong']:reasons.append(f'체결강도 {strength:.0f}%')
    elif strength<80:warnings.append('최근 매도체결 우세')
    # 호가벽: 바로 위 매도벽과, 지지로 착각하기 쉬운 사다리 주문
    co=CFG.get('orderbook',{}); flow_notes=[]   # 호가벽·사다리 전용. 체결강도는 별도 필드로 표시
    aw=fl.get('ask_wall'); bw=fl.get('bid_wall')
    if aw and aw['price']>now:
        gap=(aw['price']-now)/now*100
        flow_notes.append(f"매도벽 {aw['price']:,.4f} (+{gap:.2f}%)")
        if gap<=co.get('near_wall_pct',1.0):
            warnings.append(f"{aw['price']:,.4f} 바로 위 매도벽: 돌파에 물량 소화 필요")
    if bw and bw['price']<now:
        flow_notes.append(f"매수벽 {bw['price']:,.4f} (-{(now-bw['price'])/now*100:.2f}%)")
    bl=fl.get('bid_ladder')
    if bl and bl.get('share',0)>=co.get('ladder_share_warn',0.4):
        warnings.append(f"매수잔량의 {bl['share']*100:.0f}%가 {bl['levels']}단 사다리 주문: 언제든 취소될 수 있어 지지로 보기 어려움")
        flow_notes.append(f"매수 사다리 {bl['levels']}단")
    # Risk 0-100, higher = worse
    risk=10
    if ma7_gap>CFG['ma']['overextension_warn_pct']:risk+=15
    if ma7_gap>CFG['ma']['overextension_block_pct']:risk+=20
    if rr>CFG['entry']['rsi_hot']:risk+=15
    if strength is not None and strength>=CFG['flow']['trade_strength_hot']:risk+=8; warnings.append('단기 체결 과열 가능')
    tv=f(t.get('acc_trade_price_24h'))
    if tv<5e8:risk+=25; warnings.append('저유동성')
    elif tv<1e9:risk+=15
    elif tv<2e9:risk+=8
    if plan['rr'] is None:
        risk+=25; warnings.append('확인된 상단 저항선 없음: 목표/손익비 미산정')
    elif plan['rr']<1:risk+=25
    elif plan['rr']<CFG['risk']['min_rr']:risk+=15; warnings.append('손익비 1.5R 미만')
    atr_pct=ctx['atr15']/now*100 if now else 0
    if atr_pct>4:risk+=10; warnings.append('15M 변동성 높음')
    if ctx['d180']['false_break']:risk+=15; warnings.append('일봉 180선 돌파 실패 가능')
    risk=min(100,risk+min(45,15*len(guard_flags)))
    if not plan['stop_eligible']:risk=min(100,risk+30)
    if not structure_info['valid']:risk=min(100,risk+10)
    risk=min(100,risk+round(pressure['score']*CFG['pressure']['risk_weight']))
    # Invalidation rules
    if plan['structural_support']: invalid.append(f'{plan["structural_support"]:,.4f} 부근 손절 근거 지지 이탈')
    if structure_info['support']: invalid.append(f'{structure_info["support"]:,.4f} 부근 4H 상승 저점 이탈')
    if plan['dominant']=='돌파형' and plan['resistance']: invalid.append('돌파가격 아래 재진입 후 회복 실패')
    invalid.append('4H MA7<MA14<MA30 역정렬 전환')
    # B is the primary strategy. A/C are watch-only, never automatic buy candidates.
    if structure_info['valid']:
        pattern_type='B 저점 상승'
    elif pattern_scores.get('바닥반전형',0)>=65:
        pattern_type='A 바닥 반등'
    elif pattern_scores.get('눌림형',0)>=65:
        pattern_type='C 급등 후 눌림'
    else:
        pattern_type='기타 관찰'
    if structure_info['valid'] and not guard_flags and not pressure['hard_block'] and pressure['score']<CFG['pressure']['entry_block_score'] and plan['stop_eligible'] and structure>=CFG['structure']['min_structure_score'] and timing>=CFG['structure']['min_timing_score'] and (plan['rr'] or 0)>=CFG['risk']['min_rr'] and risk<=50 and not price_moved:
        decision='B형 진입 검토';dclass='good';summary='확정 스윙 저점 상승 + 단기 반등 확인. 지지·호가·손절 가능 여부를 재확인.'
    elif structure_info['valid'] and not plan['stop_eligible']:
        decision='손절 거리 초과';dclass='warn';summary='저점 상승 구조는 유효하지만 가까운 구조손절이 없어 신규 진입 보류.'
    elif structure_info['valid'] and (guard_flags or pressure['hard_block'] or pressure['score']>=CFG['pressure']['entry_block_score']):
        decision='B형 반등 대기';dclass='warn';summary='중기 저점 상승 유지. 단기 약세가 끝날 때까지 관찰 목록에 유지.'
    elif structure_info['valid']:
        decision='B형 관찰';dclass='warn';summary='저점 상승은 확인됐으나 진입 타이밍·손익비 확인 전.'
    elif pattern_type!='기타 관찰':
        decision='A/C 보조 관찰';dclass='';summary='보조 패턴 탐지. B형의 연속 저점 상승 조건은 아직 충족하지 못함.'
    else:
        decision='구조 미확인';dclass='bad';summary='확정된 4시간봉 저점 상승 구조가 충분하지 않음.'
    if rebound and decision=='B형 반등 대기':
        summary+=' 단기 반등 태그 감지('+', '.join(rebound)+'): 관찰용이며 진입 신호는 아님.'
    # '하루 종일 관망'이 아니라 '무엇이 켜질 때까지 관망'인지 항상 같이 적는다.
    if decision!='B형 진입 검토' and plan.get('trigger'):
        summary+=f" 재판단 시점: {fmt_px(plan['trigger'])} 위로 몸통 마감한 15분봉 + 거래량 {CFG.get('entry_trigger',{}).get('volume_mult',2.0):.1f}배 (이 가격에 알림을 걸어두세요)."
    elif decision=='B형 진입 검토' and entry_check.get('state')!='확인 완료':
        summary+=f" 아직 진입봉 미확인: {entry_check.get('detail','')}"
    result=dict(rebound=rebound,market=t['market'].replace('KRW-',''),price=f(t['trade_price']),basis_price=now,price_gap_pct=round(price_gap,2),change=f(t.get('signed_change_rate'))*100,turnover=tv,rvol=rv,rsi15=rr,trend=trend,setup=int(round(setup)),entry=entry,risk=risk,pressure=pressure,structure=structure,timing=timing,pattern_type=pattern_type,structure_info=structure_info,patterns=patterns,pattern_scores=pattern_scores,decision=decision,decision_class=dclass,summary=summary,plan={k:(round(v,8) if isinstance(v,float) else v) for k,v in plan.items() if k in ('entry','stop','stop_pct','stop_too_tight','noise_floor_pct','target1','target2','rr','entry_type','trigger_gap_pct','trigger','stop_source','recover','support')},ma7_gap=ma7_gap,bid_ask_ratio=ratio,trade_strength=strength,rel_strength=(round(rel_strength,2) if rel_strength else None),flow_notes=flow_notes,entry_check=entry_check,strength_vol=fl.get('strength_vol'),strength_cnt=fl.get('strength_cnt'),strength_basis=basis,strength_window_min=win,whale_share=whale,guard=guard_metrics,guard_flags=guard_flags,reasons=reasons[:10],warnings=warnings[:8],invalidations=invalid[:4])
    result['journal']=journal_block(result)
    return result

def preliminary(t):
    c4=candles(t['market'],240,200); p4=closes(c4); m7,m14,m30=ma(p4,7),ma(p4,14),ma(p4,30); rv=rvol(c4)
    s=0
    if m7 and m14 and m30 and m7>m14>m30:s+=40
    if ma(p4,60) and p4[-1]>ma(p4,60):s+=20
    hh,hl=higher_structure(c4)
    if hh:s+=10
    if hl:s+=15
    piv=confirmed_pivots(c4,'low',lookback=110)
    if len(piv)>=3 and piv[-1][1]>piv[-2][1]>piv[-3][1]:s+=55
    if rv>=1.2:s+=5
    return s,c4

@app.get('/')
def home(): return render_template_string(HTML.replace("<h1>📊", f"<h1>📊 [{EXCHANGE.upper()}]"))

@app.get('/api/config')
def config(): return jsonify(CFG)

@app.get('/api/scan')
def scan():
    if not SCAN_LOCK.acquire(blocking=False):
        return jsonify(ok=False,error='Busy',detail='다른 탐색이 진행 중입니다. 완료 후 다시 시도하세요.'),429
    try:
        markets=[x for x in get('/v1/market/all',{'is_details':'true'}) if x['market'].startswith('KRW-') and x.get('market_warning')!='CAUTION']
        names=[x['market'] for x in markets]; allowed=set(names)
        # 거래소 공식 v1/ticker는 markets 파라미터로 여러 종목 조회.
        tickers=[]
        for i in range(0,len(names),40):
            tickers.extend(t for t in get('/v1/ticker',{'markets':','.join(names[i:i+40])})
                           if t.get('market') in allowed)

        tickers.sort(key=lambda x:f(x.get('acc_trade_price_24h')),reverse=True)
        first=[]; skipped=[]
        for t in tickers[:CFG['scan']['ticker_top_n']]:
            try:
                ps,c4=preliminary(t); first.append((ps,t,c4)); time.sleep(.035)
            except Exception as e: skipped.append(f"{t.get('market')}:{type(e).__name__}")
        first.sort(key=lambda x:x[0],reverse=True)
        deep=first[:CFG['scan']['deep_top_n']]
        # 체결 흐름을 먼저 모아 이번 회차의 '장세 기준선'(체결강도 중앙값)을 만든다.
        # 전 종목 체결강도가 비슷하면 그건 종목 특성이 아니라 장세이기 때문.
        flows={}
        for _,t,_c in deep:
            try: flows[t['market']]=orderflow(t['market']); time.sleep(.03)
            except Exception: flows[t['market']]=dict(EMPTY_FLOW)
        ss=[v['strength'] for v in flows.values() if v and v.get('strength') is not None]
        market_strength=statistics.median(ss) if ss else None
        gate=CFG['flow'].get('market_gate_median',90)
        if market_strength is None: regime='장세 측정 불가'
        elif market_strength<gate: regime=f'매도 우위 장세 (체결강도 중앙값 {market_strength:.0f}%) · 롱 셋업 비권장'
        else: regime=f'매수 우위 장세 (체결강도 중앙값 {market_strength:.0f}%)'
        out=[]
        for _,t,c4 in deep:
            try:
                c60=candles(t['market'],60,160); c15=candles(t['market'],15,160); cd=days(t['market'],200)
                out.append(score_all(t,c4,c60,c15,cd,flow=flows.get(t['market']),market_strength=market_strength)); time.sleep(.05)
            except Exception as e: skipped.append(f"{t.get('market')}:{type(e).__name__}")
        # 매수후보 우선, 그 다음 Entry/Setup/Trend, Risk 낮은 순
        rank={'B형 진입 검토':6,'B형 관찰':5,'B형 반등 대기':4,'손절 거리 초과':3,'A/C 보조 관찰':2,'구조 미확인':0}
        out.sort(key=lambda x:(rank.get(x['decision'],0),x['structure'],x['timing'],x['entry'],-x['risk']),reverse=True)
        out=out[:CFG['scan']['output_n']]
        return jsonify(ok=True,exchange=EXCHANGE,items=out,market_strength=market_strength,regime=regime,
                       note=f"v5.3.1 · {regime} · {EXCHANGE} 거래대금 상위 {CFG['scan']['ticker_top_n']}개 1차 → {len(out)}개 정밀분석",skipped=skipped[:10])
    except Exception as e:
        return jsonify(ok=False,error=type(e).__name__,detail=str(e)[:500]),500
    finally:
        SCAN_LOCK.release()

@app.get('/health')
def health(): return {'ok':True,'version':'v5.3.1','strategy':'higher-low-primary','exchange':EXCHANGE}

# 백테스트 화면(/backtest). 위의 함수들이 모두 정의된 뒤에 불러와야 한다.
from backtest_web import bp as backtest_bp
app.register_blueprint(backtest_bp)

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=False)
