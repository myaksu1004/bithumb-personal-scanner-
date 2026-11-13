"""백테스트 웹 화면 (폰·PC 공용)

backtest.py의 run_market()/summarize()를 그대로 불러 서버에서 돌리고, 결과를 /backtest 화면에 보여준다.
계산 로직은 여기 없음 — PC에서 `python backtest.py`를 돌린 것과 같은 결과가 나온다.

app.py 맨 아래(if __name__ 위)에 두 줄이 있어야 한다:
    from backtest_web import bp as backtest_bp
    app.register_blueprint(backtest_bp)
"""
import threading, time
from types import SimpleNamespace

from flask import Blueprint, jsonify, request

bp = Blueprint("backtest_web", __name__)
MAX_MARKETS, MAX_DAYS = 5, 30
JOB_LOCK = threading.Lock()
JOB = {"state": "idle"}          # idle | running | done | error


def _avg(a):
    return round(sum(a) / len(a), 2) if a else None


def _work(markets, days, args):
    import backtest as bt        # 여기서 불러와야 app.py와 서로 불러오다 꼬이지 않는다
    all_trades, all_dec, per = [], {}, []
    try:
        for m in markets:
            JOB["current"] = m.replace("KRW-", "")
            t0 = time.time()
            try:
                trades, dec, errors = bt.run_market(m, days, args)
            except Exception as e:
                per.append({"market": JOB["current"], "error": f"{type(e).__name__}: {str(e)[:80]}"})
                JOB["markets"] = list(per)
                continue
            all_trades += trades
            for k, v in dec.items():
                a = all_dec.setdefault(k, {"n": 0, "fwd4h": [], "fwd24h": []})
                a["n"] += v["n"]; a["fwd4h"] += v["fwd4h"]; a["fwd24h"] += v["fwd24h"]
            per.append({"market": JOB["current"], "trades": len(trades), "seconds": round(time.time() - t0),
                        "skipped_bars": sum(errors.values()), "skip_reasons": list(errors)[:3]})
            JOB["markets"] = list(per)
        why = {}
        for t in all_trades:
            why[t["사유"]] = why.get(t["사유"], 0) + 1
        JOB.update(state="done", current=None, finished=time.time(),
                   summary=bt.summarize(all_trades), exits=why,
                   decisions=[{"name": k, "n": v["n"], "fwd4h": _avg(v["fwd4h"]), "fwd24h": _avg(v["fwd24h"])}
                              for k, v in sorted(all_dec.items(), key=lambda kv: -kv[1]["n"])],
                   trades=all_trades)
    except Exception as e:                       # 예상 못 한 오류도 화면에 보이게
        JOB.update(state="error", current=None, error=f"{type(e).__name__}: {str(e)[:200]}")


@bp.get("/backtest/start")
def start():
    raw = request.args.get("markets", "").replace(" ", ",")
    markets = []
    for m in raw.split(","):
        m = m.strip().upper().replace("KRW-", "")
        if m and "KRW-" + m not in markets:
            markets.append("KRW-" + m)
    if not markets:
        return jsonify(ok=False, detail="종목을 입력해 주세요."), 400
    if len(markets) > MAX_MARKETS:
        return jsonify(ok=False, detail=f"한 번에 {MAX_MARKETS}개까지 가능합니다."), 400
    try:
        days = int(request.args.get("days", 14)); fee = float(request.args.get("fee", 0.04))
    except ValueError:
        return jsonify(ok=False, detail="기간·수수료 숫자를 확인해 주세요."), 400
    if not 1 <= days <= MAX_DAYS or not 0 <= fee <= 1:
        return jsonify(ok=False, detail=f"기간은 1~{MAX_DAYS}일, 수수료는 0~1% 사이로 입력해 주세요."), 400
    with JOB_LOCK:
        if JOB.get("state") == "running":
            return jsonify(ok=False, detail="이미 백테스트가 진행 중입니다."), 429
        JOB.clear()
        JOB.update(state="running", started=time.time(), days=days, fee=fee, markets=[],
                   requested=[m.replace("KRW-", "") for m in markets], current=None)
    args = SimpleNamespace(cache=True, max_hold=192, entry_wait=4, fee=fee)
    threading.Thread(target=_work, args=(markets, days, args), daemon=True).start()
    return jsonify(ok=True)


@bp.get("/backtest/status")
def status():
    out = dict(JOB)
    if out.get("started"):
        out["elapsed"] = round((out.get("finished") or time.time()) - out["started"])
    return jsonify(out)


@bp.get("/backtest")
def page():
    return PAGE


PAGE = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>탐색기 백테스트</title>
<style>
:root{--bg:#f4f5f7;--card:#fff;--text:#16181c;--sub:#667085;--line:#e5e7eb;--good:#067647;--warn:#b54708;--bad:#b42318}
*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans KR",sans-serif;background:var(--bg);margin:0;color:var(--text)}
header{background:#fff;padding:20px 16px;border-bottom:1px solid var(--line)}h1{font-size:22px;margin:0 0 5px}.sub{font-size:12px;color:var(--sub);line-height:1.5}
main{max-width:980px;margin:auto;padding:14px}.card{background:var(--card);border-radius:17px;padding:15px;margin:13px 0;box-shadow:0 1px 5px #0001}
label{display:block;font-size:12px;color:var(--sub);margin:10px 0 4px}input,select{width:100%;padding:12px;border:1px solid var(--line);border-radius:11px;font-size:16px;background:#fff;color:inherit}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}.btn{width:100%;margin-top:14px;padding:16px;border:0;border-radius:14px;background:#111;color:#fff;font-size:17px;font-weight:800}.btn:disabled{opacity:.45}
#status{text-align:center;color:var(--sub);margin:12px;font-size:13px;line-height:1.6}h2{font-size:15px;margin:0 0 10px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:6px}.s{background:#f7f8fa;border-radius:11px;padding:9px 10px}.s span{display:block;font-size:11px;color:var(--sub)}.s b{font-size:17px}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:7px 4px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:var(--sub);font-weight:600}
.scroll{overflow-x:auto}.good{color:var(--good)}.bad{color:var(--bad)}.warn{color:var(--warn)}.note{font-size:12px;color:var(--sub);line-height:1.6;margin-top:10px}a{color:#175cd3}
@media(min-width:700px){.grid{grid-template-columns:repeat(4,1fr)}}
</style></head><body><header><h1>🧪 탐색기 백테스트</h1><div class="sub">과거 15분봉마다 탐색기 판정을 다시 돌려, 'B형 진입 검토'대로 매매했다면 어땠는지 계산합니다. · <a href="/">탐색기로 돌아가기</a></div></header><main>
<div class="card"><label for="m">종목 (쉼표로 구분, 최대 5개)</label><input id="m" value="ONDO, SOMI, CAP, COW" autocapitalize="characters" autocomplete="off">
<div class="two"><div><label for="d">검증 기간</label><select id="d"><option value="7">최근 7일</option><option value="14" selected>최근 14일</option><option value="30">최근 30일</option></select></div><div><label for="f">편도 수수료 %</label><input id="f" type="number" step="0.01" min="0" max="1" value="0.04"></div></div>
<button class="btn" id="go">▶ 백테스트 시작</button></div>
<div id="status">종목당 수십 초~몇 분 걸립니다. 진행 중에는 이 화면을 열어 두세요.</div><div id="out"></div>
<div class="note">실시간 탐색과 다른 점: 호가·체결강도는 과거 데이터가 없어 중립값 처리, 같은 봉에서 손절과 목표가 모두 닿으면 손절 처리, 수수료 외 슬리피지 미반영. 과거 결과는 미래 수익을 보장하지 않습니다.</div></main>
<script>
const $=q=>document.querySelector(q),esc=t=>String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;');
const sign=v=>v==null?'-':(v>0?'+':'')+v+'%',cls=v=>v==null?'':v>0?'good':v<0?'bad':'';
const num=v=>Number(v).toLocaleString('ko-KR',{maximumFractionDigits:4});
let timer=null;
$('#go').onclick=async()=>{const q=new URLSearchParams({markets:$('#m').value,days:$('#d').value,fee:$('#f').value});$('#out').innerHTML='';
  try{const r=await fetch('/backtest/start?'+q),d=await r.json();if(!d.ok&&r.status!==429){$('#status').textContent=d.detail||'시작 실패';return}}catch(e){$('#status').textContent='서버 연결 실패: '+e.message;return}
  poll()};
async function poll(){clearTimeout(timer);let j;try{j=await(await fetch('/backtest/status')).json()}catch(e){$('#status').textContent='연결이 잠시 끊겼습니다. 다시 확인 중…';timer=setTimeout(poll,5000);return}
  const done=(j.markets||[]).map(x=>x.error?`${x.market} 건너뜀`:`${x.market} ${x.trades}건`).join(' · ');
  if(j.state==='running'){$('#go').disabled=true;$('#status').innerHTML=`진행 중 · ${j.elapsed}초 경과 · 지금 ${esc(j.current||'준비')} 계산 중 (${(j.markets||[]).length}/${j.requested.length})`+(done?'<br>'+esc(done):'');timer=setTimeout(poll,3000);return}
  $('#go').disabled=false;
  if(j.state==='error'){$('#status').innerHTML='<span class="bad">실패: '+esc(j.error)+'</span>';return}
  if(j.state==='done'){$('#status').textContent=`완료 · ${j.requested.join(', ')} · 최근 ${j.days}일 · 편도 수수료 ${j.fee}% · ${j.elapsed}초`;render(j)}}
function render(j){let h='';const s=j.summary;
  const bad=j.markets.filter(x=>x.error||x.skipped_bars);
  if(bad.length)h+='<div class="card warn"><h2>확인 필요</h2>'+bad.map(x=>x.error?`${esc(x.market)}: ${esc(x.error)}`:`${esc(x.market)}: 분석 불가 봉 ${x.skipped_bars}개 (${esc(x.skip_reasons.join(', '))})`).join('<br>')+'</div>';
  h+='<div class="card"><h2>\'B형 진입 검토\' 신호대로 매매한 결과</h2>';
  if(!s)h+='<div class="sub">체결된 거래가 없습니다. 기간을 늘리거나 다른 종목으로 해 보세요.</div>';
  else{h+='<div class="grid">'+Object.entries(s).map(([k,v])=>`<div class="s"><span>${esc(k)}</span><b class="${/수익률|평균 R|R 합계/.test(k)?cls(v):''}">${v==null?'-':v}</b></div>`).join('')+'</div>';
    h+='<div class="note">청산 사유: '+Object.entries(j.exits).map(([k,v])=>`${esc(k)} ${v}건`).join(' · ')+(s['거래 수']<30?'<br><span class="warn">※ 거래 수가 30건 미만이라 통계적으로 믿기 어렵습니다. 방향만 참고하세요.</span>':'')+'</div>'}
  h+='</div><div class="card"><h2>판정별 빈도와 이후 평균 등락률</h2><div class="scroll"><table><tr><th>판정</th><th>횟수</th><th>4시간 뒤</th><th>24시간 뒤</th></tr>'+j.decisions.map(d=>`<tr><td>${esc(d.name)}</td><td>${d.n}</td><td class="${cls(d.fwd4h)}">${sign(d.fwd4h)}</td><td class="${cls(d.fwd24h)}">${sign(d.fwd24h)}</td></tr>`).join('')+'</table></div><div class="note">\'B형 진입 검토\'의 이후 등락률이 다른 판정보다 높아야 판정에 구분력이 있는 것입니다.</div></div>';
  if(j.trades.length)h+='<div class="card"><h2>거래 내역 ('+j.trades.length+'건)</h2><div class="scroll"><table><tr><th>종목</th><th>진입시각</th><th>사유</th><th>수익률</th><th>R</th><th>손절폭</th><th>진입가</th><th>청산가</th></tr>'+j.trades.map(t=>`<tr><td>${esc(t['종목'])}</td><td>${t['진입시각'].slice(5)}</td><td>${esc(t['사유'])}</td><td class="${cls(t['수익률%'])}">${sign(t['수익률%'])}</td><td>${t['R']}</td><td>${t['손절폭%']}%</td><td>${num(t['진입가'])}</td><td>${num(t['청산가'])}</td></tr>`).join('')+'</table></div></div>';
  $('#out').innerHTML=h}
poll();
</script></body></html>'''
