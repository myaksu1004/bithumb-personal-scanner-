"""코인 저점상승 탐색기 백테스트 (v5.2)

app.py의 score_all()을 과거 15분봉마다 그대로 다시 실행해서,
'B형 진입 검토'가 떴을 때 계획대로(진입·구조 손절·1차 목표) 매매했다면 어땠는지 계산한다.

사용 예:
  python backtest.py --markets BTC,ETH,XRP --days 30
  python backtest.py --top 10 --days 30 --fee 0.04

실시간 탐색과 다른 점 (결과 해석 시 주의):
  - 호가/체결강도는 과거 데이터가 없어 중립값(1.0배, 100%)으로 둔다.
  - 24시간 등락률·거래대금은 캔들로 근사한다.
  - 실시간의 '거래대금 상위 55개 → 1차 점수 상위 24개' 선별은 재현하지 않고, 지정한 종목 전체를 본다.
  - 같은 15분봉 안에서 손절과 목표가 모두 닿으면 손절로 처리한다(보수적).
  - 1차 목표에서 전량 청산으로 가정한다. 슬리피지는 수수료 외에 반영하지 않는다.
"""
import argparse, bisect, csv, json, os, sys, time
from datetime import datetime, timedelta

import app as sc   # strategy_config.json과 전략 로직을 그대로 사용

KST = sc.KST
CACHE_DIR = os.path.join(sc.HERE, "bt_cache")
ENTRY_DECISION = "B형 진입 검토"


def opened(bar):
    return datetime.fromisoformat(bar["candle_date_time_kst"]).replace(tzinfo=KST)


def fetch_history(market, unit, bars, use_cache=True):
    """unit: 15/60/240(분) 또는 'days'. 과거→최신 순, 미완성 봉 제외."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, f"{sc.EXCHANGE}_{market}_{unit}_{bars}_{datetime.now(KST):%Y%m%d}.json")
    if use_cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            return json.load(fh)
    path = "/v1/candles/days" if unit == "days" else f"/v1/candles/minutes/{unit}"
    seen, to = {}, None
    while len(seen) < bars:
        params = {"market": market, "count": 200}
        if to:
            params["to"] = to
        page = sc.get(path, params)
        if not page:
            break
        before = len(seen)
        for bar in page:
            seen.setdefault(bar["candle_date_time_kst"], bar)
        if len(seen) == before:      # 더 과거 데이터가 없음
            break
        # 가장 오래된 봉의 KST 시각을 다음 요청의 끝으로 사용. 거래소가 이 값을 UTC로 해석해도
        # 구간이 겹칠 뿐(중복 제거됨) 빠지는 봉은 생기지 않는다.
        to = min(seen).replace("T", " ")
    out = [seen[k] for k in sorted(seen)]
    out = sc.completed_candles(out, None if unit == "days" else unit)[-bars:]
    if use_cache:
        with open(cache, "w", encoding="utf-8") as fh:
            json.dump(out, fh)
    return out


def close_times(c, minutes=None):
    d = timedelta(minutes=minutes) if minutes else timedelta(days=1)
    return [opened(x) + d for x in c]


def simulate_exit(c15, start, fill, stop, target, max_hold):
    """start 봉부터 청산까지. 반환: (청산 인덱스, 청산가, 사유)"""
    end = min(len(c15) - 1, start + max_hold - 1)
    for j in range(start, end + 1):
        o, h, l = (sc.f(c15[j][k]) for k in ("opening_price", "high_price", "low_price"))
        if l <= stop:
            return j, (min(o, stop) if j > start else stop), "손절"
        if target and h >= target:
            return j, (max(o, target) if j > start else target), "1차 목표"
    return end, sc.f(c15[end]["trade_price"]), ("기간 종료" if end == len(c15) - 1 and end < start + max_hold - 1 else "보유시간 초과")


def run_market(market, days, args):
    n15 = days * 96 + 160
    c15 = fetch_history(market, 15, n15, args.cache)
    c60 = fetch_history(market, 60, days * 24 + 170, args.cache)
    c4 = fetch_history(market, 240, days * 6 + 210, args.cache)
    cd = fetch_history(market, "days", days + 205, args.cache)
    t60, t4, td = close_times(c60, 60), close_times(c4, 240), close_times(cd)
    slip = sc.CFG["risk"]["max_entry_slippage_pct"]
    trades, decisions, errors = [], {}, {}
    turn = sc.vals(c15, "candle_acc_trade_price")
    i = max(160, len(c15) - days * 96)
    while i < len(c15) - 1:
        T = opened(c15[i]) + timedelta(minutes=15)
        w60 = c60[:bisect.bisect_right(t60, T)][-160:]
        w4 = c4[:bisect.bisect_right(t4, T)][-200:]
        wd = cd[:bisect.bisect_right(td, T)][-200:]
        w15 = c15[i - 159:i + 1]
        close = sc.f(c15[i]["trade_price"])
        prev_close = sc.f(wd[-1]["trade_price"]) if wd else close
        tick = {"market": market, "trade_price": close,
                "signed_change_rate": (close - prev_close) / prev_close if prev_close else 0,
                "acc_trade_price_24h": sum(turn[max(0, i - 95):i + 1])}
        try:
            r = sc.score_all(tick, w4, w60, w15, wd, now_dt=T, flow=(1.0, 1.0, 100))
        except Exception as e:
            errors[str(e)[:40] or type(e).__name__] = errors.get(str(e)[:40] or type(e).__name__, 0) + 1
            i += 1
            continue
        d = decisions.setdefault(r["decision"], {"n": 0, "fwd4h": [], "fwd24h": []})
        d["n"] += 1
        for key, ahead in (("fwd4h", 16), ("fwd24h", 96)):
            if i + ahead < len(c15):
                d[key].append((sc.f(c15[i + ahead]["trade_price"]) - close) / close * 100)
        if r["decision"] != ENTRY_DECISION:
            i += 1
            continue
        plan = r["plan"]
        entry, stop, target = plan["entry"], plan["stop"], plan["target1"]
        fill_idx = fill = None
        if entry <= close * (1 + slip / 100):          # 현재가 진입: 다음 봉 시가에 체결
            o = sc.f(c15[i + 1]["opening_price"])
            if abs(o - entry) / entry * 100 <= slip and o > stop:
                fill_idx, fill = i + 1, o
        else:                                           # 돌파 대기: 진입가에 닿아야 체결
            for j in range(i + 1, min(len(c15), i + 1 + args.entry_wait)):
                o, h, l = (sc.f(c15[j][k]) for k in ("opening_price", "high_price", "low_price"))
                if l <= stop:
                    break
                if h >= entry:
                    if o <= entry * (1 + slip / 100):
                        fill_idx, fill = j, max(o, entry)
                    break
        if fill_idx is None or (target and target <= fill):
            i += 1
            continue
        x, exit_price, why = simulate_exit(c15, fill_idx, fill, stop, target, args.max_hold)
        gross = (exit_price - fill) / fill * 100
        net = gross - 2 * args.fee
        risk_pct = (fill - stop) / fill * 100
        trades.append({"종목": market.replace("KRW-", ""),
                       "신호시각": T.strftime("%Y-%m-%d %H:%M"),
                       "진입시각": (opened(c15[fill_idx])).strftime("%Y-%m-%d %H:%M"),
                       "청산시각": (opened(c15[x]) + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M"),
                       "진입가": fill, "손절가": stop, "목표가": target, "청산가": exit_price,
                       "사유": why, "손절폭%": round(risk_pct, 2), "수익률%": round(net, 3),
                       "R": round(net / risk_pct, 2) if risk_pct > 0 else 0,
                       "계획RR": plan["rr"], "Structure": r["structure"], "Timing": r["timing"],
                       "Risk": r["risk"], "매도압력": r["pressure"]["score"],
                       "패턴": "/".join(r["patterns"])})
        i = x + 1                                       # 보유 중에는 같은 종목 신규 진입 없음
    return trades, decisions, errors


def summarize(trades):
    if not trades:
        return None
    rs = [t["R"] for t in trades]; pct = [t["수익률%"] for t in trades]
    wins = [p for p in pct if p > 0]; losses = [p for p in pct if p <= 0]
    streak = worst = 0
    for p in pct:
        streak = streak + 1 if p <= 0 else 0
        worst = max(worst, streak)
    equity = peak = mdd = 0.0
    for p in pct:
        equity += p; peak = max(peak, equity); mdd = max(mdd, peak - equity)
    return {"거래 수": len(trades), "승률%": round(100 * len(wins) / len(trades), 1),
            "평균 수익률%": round(sum(pct) / len(pct), 3), "수익률 합계%": round(sum(pct), 2),
            "평균 R": round(sum(rs) / len(rs), 2), "R 합계": round(sum(rs), 2),
            "평균 이익%": round(sum(wins) / len(wins), 2) if wins else 0,
            "평균 손실%": round(sum(losses) / len(losses), 2) if losses else 0,
            "손익비(PF)": round(sum(wins) / -sum(losses), 2) if losses and sum(losses) < 0 else None,
            "최대 연속 손실": worst, "최대 낙폭(수익률 합 기준)%": round(mdd, 2)}


def main():
    ap = argparse.ArgumentParser(description="저점상승 탐색기 백테스트")
    ap.add_argument("--markets", help="쉼표로 구분한 종목 (예: BTC,ETH,ONDO)")
    ap.add_argument("--top", type=int, default=10, help="--markets가 없을 때 현재 거래대금 상위 N개")
    ap.add_argument("--days", type=int, default=30, help="검증 기간(일)")
    ap.add_argument("--fee", type=float, default=0.04, help="편도 수수료 %% (본인 계정 수수료율로 지정)")
    ap.add_argument("--max-hold", type=int, default=192, help="최대 보유 15분봉 수 (192=2일)")
    ap.add_argument("--entry-wait", type=int, default=4, help="돌파형 진입가 대기 15분봉 수")
    ap.add_argument("--out", default="backtest_trades.csv")
    ap.add_argument("--no-cache", dest="cache", action="store_false", help="캔들 캐시(bt_cache/) 미사용")
    args = ap.parse_args()

    if args.markets:
        markets = ["KRW-" + m.strip().upper().replace("KRW-", "") for m in args.markets.split(",") if m.strip()]
    else:
        names = [x["market"] for x in sc.get("/v1/market/all", {"is_details": "true"})
                 if x["market"].startswith("KRW-") and x.get("market_warning") != "CAUTION"]
        ticks = []
        for k in range(0, len(names), 40):
            ticks.extend(sc.get("/v1/ticker", {"markets": ",".join(names[k:k + 40])}))
        ticks.sort(key=lambda x: sc.f(x.get("acc_trade_price_24h")), reverse=True)
        markets = [x["market"] for x in ticks[:args.top]]

    print(f"[{sc.EXCHANGE}] {len(markets)}개 종목 · 최근 {args.days}일 · 편도 수수료 {args.fee}%")
    all_trades, all_dec = [], {}
    for m in markets:
        t0 = time.time()
        try:
            trades, dec, errors = run_market(m, args.days, args)
        except Exception as e:
            print(f"  {m}: 건너뜀 ({type(e).__name__}: {str(e)[:80]})")
            continue
        all_trades += trades
        for k, v in dec.items():
            a = all_dec.setdefault(k, {"n": 0, "fwd4h": [], "fwd24h": []})
            a["n"] += v["n"]; a["fwd4h"] += v["fwd4h"]; a["fwd24h"] += v["fwd24h"]
        note = f" · 분석 불가 봉 {sum(errors.values())}개({', '.join(errors)})" if errors else ""
        print(f"  {m}: 거래 {len(trades)}건 · {time.time() - t0:.0f}초{note}")

    print("\n■ 판정별 빈도와 이후 평균 등락률 (판정이 실제로 구분력이 있는지 확인용)")
    avg = lambda a: f"{sum(a) / len(a):+.2f}%" if a else "-"
    for k, v in sorted(all_dec.items(), key=lambda kv: -kv[1]["n"]):
        print(f"  {k:<12} {v['n']:>6}회 · 4시간 뒤 {avg(v['fwd4h'])} · 24시간 뒤 {avg(v['fwd24h'])}")

    s = summarize(all_trades)
    print(f"\n■ '{ENTRY_DECISION}' 신호대로 매매한 결과")
    if not s:
        print("  체결된 거래 없음. 기간(--days)이나 종목 수(--top)를 늘려 보세요.")
        return
    for k, v in s.items():
        print(f"  {k}: {v}")
    if s["거래 수"] < 30:
        print("  ※ 거래 수가 30건 미만이라 통계적으로 믿기 어렵습니다. 방향만 참고하세요.")
    why = {}
    for t in all_trades:
        why[t["사유"]] = why.get(t["사유"], 0) + 1
    print("  청산 사유: " + " · ".join(f"{k} {v}건" for k, v in why.items()))
    with open(args.out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_trades[0].keys()))
        w.writeheader(); w.writerows(all_trades)
    print(f"\n거래 내역 저장: {args.out}")


if __name__ == "__main__":
    main()
