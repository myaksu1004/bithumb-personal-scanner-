from flask import Flask, jsonify, render_template_string
import requests, time

app = Flask(__name__)
BASE = "https://api.bithumb.com"
S = requests.Session()
S.headers.update({"accept":"application/json","user-agent":"BithumbPersonalScanner/1.0"})

HTML = r"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes"><title>내 빗썸 차트 검색기</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans KR",sans-serif;background:#f4f5f7;margin:0;color:#17191c}
header{background:#fff;padding:22px 18px;border-bottom:1px solid #ddd}h1{font-size:24px;margin:0 0 5px}.sub{font-size:13px;color:#667085}
main{max-width:900px;margin:auto;padding:16px}.btn{width:100%;padding:17px;border:0;border-radius:14px;background:#111;color:#fff;font-size:18px;font-weight:800}
.card{background:#fff;border-radius:16px;padding:16px;margin:14px 0;box-shadow:0 1px 5px #0001}.row{display:flex;justify-content:space-between;align-items:center;gap:8px}
.coin{font-size:22px;font-weight:850}.badge{padding:6px 10px;border-radius:999px;background:#eef0f2;font-weight:700}.meta{font-size:12px;color:#667085;margin-top:5px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:13px}.m{background:#f7f8fa;border-radius:10px;padding:9px;text-align:center}.m b{display:block;font-size:17px}.m span{font-size:10px;color:#667085}
.reason{font-size:13px;line-height:1.65;color:#475467;margin-top:11px}.warn{color:#b54708}#status{text-align:center;color:#667085;margin:13px}
@media(max-width:600px){.grid{grid-template-columns:repeat(2,1fr)}}
</style></head><body>
<header><h1>📊 내 빗썸 차트 검색기</h1><div class="sub">4H 구조 · 15M 진입 · 거래량 · 유동성 | 분석 전용</div></header>
<main><button class="btn" onclick="scan()">🔍 지금 검색</button><div id="status">검색 버튼을 눌러주세요.</div><div id="list"></div></main>
<script>
const won=v=>v>=1e8?(v/1e8).toFixed(1)+"억":v.toLocaleString();
async function scan(){let s=document.querySelector("#status"),l=document.querySelector("#list");s.textContent="빗썸 데이터 분석 중…";l.innerHTML="";
try{
let r=await fetch("/api/scan");
let d=await r.json();
if(!r.ok || d.ok===false){throw new Error((d.error||"API 오류")+(d.detail?": "+d.detail:""))}
s.textContent=`완료 · ${d.note}`;
l.innerHTML=d.items.map(x=>`<div class="card"><div class="row"><div><span class="coin">${x.market}</span> ${x.price.toLocaleString()}원</div><span class="badge">${x.total}점 · ${x.label}</span></div>
<div class="meta">${x.change>=0?"+":""}${x.change.toFixed(2)}% · 24H ${won(x.turnover)} · RVOL ${x.rvol.toFixed(2)} · 유동성 ${x.liquidity_grade}</div>
<div class="grid"><div class="m"><b>${x.chart}/30</b><span>4H 구조</span></div><div class="m"><b>${x.entry}/20</b><span>15M 진입</span></div><div class="m"><b>${x.volume}/15</b><span>거래량</span></div><div class="m"><b>${x.liquidity}/15</b><span>유동성</span></div></div>
<div class="reason">✓ ${x.reasons.join(" · ")||"초기 조건"}${x.warnings.length?`<br><span class="warn">⚠ ${x.warnings.join(" · ")}</span>`:""}</div></div>`).join("");
}catch(e){s.textContent="검색 실패: "+e.message;}}
</script></body></html>"""

def get(path, params=None):
    r=S.get(BASE+path,params=params,timeout=12)
    r.raise_for_status()
    return r.json()

def ma(a,n): return sum(a[-n:])/n if len(a)>=n else None

def rsi(a,n=14):
    if len(a)<n+1:return 50.0
    ds=[a[i]-a[i-1] for i in range(len(a)-n,len(a))]
    g=sum(max(x,0) for x in ds)/n
    l=sum(max(-x,0) for x in ds)/n
    if l==0:return 100.0
    rs=g/l
    return 100-(100/(1+rs))

def candles(market,unit,count):
    return list(reversed(get(f"/v1/candles/minutes/{unit}",{"market":market,"count":count})))

def score(t):
    market=t["market"]; c4=candles(market,240,200); c15=candles(market,15,80)
    p4=[float(x["trade_price"]) for x in c4]; p15=[float(x["trade_price"]) for x in c15]
    now=p4[-1]; m20,m60,m180=ma(p4,20),ma(p4,60),ma(p4,180)
    chart=0; reasons=[]; warnings=[]
    if m20 and now>m20: chart+=6; reasons.append("4H 가격>MA20")
    if m20 and m60 and m20>m60: chart+=6; reasons.append("MA20>MA60")
    if m60 and now>m60: chart+=6; reasons.append("4H 가격>MA60")
    if m180 and now>m180: chart+=6; reasons.append("4H 가격>MA180")
    recent=c4[-20:]
    if len(recent)==20:
        lo1=min(float(x["low_price"]) for x in recent[:10]); lo2=min(float(x["low_price"]) for x in recent[10:])
        if lo2>lo1: chart+=6; reasons.append("4H 저점 상승")
    rr=rsi(p15); entry=0
    if ma(p15,30) and p15[-1]>ma(p15,30): entry+=7
    if ma(p15,7) and ma(p15,14) and ma(p15,7)>ma(p15,14): entry+=6
    if 45<=rr<=65: entry+=7; reasons.append("15M RSI 진입 우호")
    if rr>75: warnings.append("15M RSI 과열")
    tv=float(t.get("acc_trade_price_24h",0))
    if tv>=10_000_000_000: liq,grade=15,"A+"
    elif tv>=5_000_000_000: liq,grade=14,"A"
    elif tv>=2_000_000_000: liq,grade=12,"B+"
    elif tv>=1_000_000_000: liq,grade=10,"B"
    elif tv>=500_000_000: liq,grade=8,"C+"
    elif tv>=100_000_000: liq,grade=5,"C"
    else: liq,grade=1,"D"
    if liq<=5:warnings.append("저유동성 주의")
    vols=[float(x["candle_acc_trade_price"]) for x in c4]
    base=sum(vols[-21:-1])/20 if len(vols)>=21 else 0; rv=vols[-1]/base if base else 0
    vol=15 if rv>=3 else 12 if rv>=2 else 9 if rv>=1.5 else 6 if rv>=1.2 else 2
    total=chart+entry+liq+vol
    label="상승/돌파 후보" if total>=65 and liq>=8 else "눌림 관찰" if total>=55 else "초기 변화"
    return dict(market=market.replace("KRW-",""),price=float(t["trade_price"]),
        change=float(t.get("signed_change_rate",0))*100,turnover=tv,chart=chart,entry=entry,
        liquidity=liq,liquidity_grade=grade,volume=vol,total=total,rsi=rr,rvol=rv,label=label,
        reasons=reasons,warnings=warnings)

@app.get("/")
def home(): return render_template_string(HTML)

@app.get("/api/scan")
def scan():
    try:
        markets=[
            x for x in get("/v1/market/all",{"isDetails":"true"})
            if x["market"].startswith("KRW-") and x.get("market_warning")!="CAUTION"
        ]

        # 빗썸 ticker 요청 URL이 너무 길어지는 것을 방지하기 위해
        # KRW 마켓을 여러 묶음으로 나눠 조회한다.
        tickers=[]
        market_names=[x["market"] for x in markets]
        chunk_size=40

        for i in range(0, len(market_names), chunk_size):
            chunk=",".join(market_names[i:i+chunk_size])
            tickers.extend(get("/v1/ticker", {"markets": chunk}))
            time.sleep(0.08)

        tickers.sort(
            key=lambda x: float(x.get("acc_trade_price_24h",0)),
            reverse=True
        )

        out=[]
        skipped=[]
        for t in tickers[:35]:
            try:
                out.append(score(t))
                time.sleep(0.05)
            except Exception as e:
                skipped.append(f"{t.get('market','?')}:{type(e).__name__}")

        out.sort(key=lambda x:x["total"],reverse=True)

        return jsonify({
            "ok": True,
            "count": len(out),
            "items": out[:20],
            "note": f"v1 · 거래대금 상위 35개 KRW 종목 분석 · 성공 {len(out)}개",
            "skipped": skipped[:10]
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": type(e).__name__,
            "detail": str(e)[:500]
        }), 500

@app.get("/health")
def health(): return {"ok":True}
