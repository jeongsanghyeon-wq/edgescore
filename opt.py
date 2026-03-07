#!/usr/bin/env python3
"""
EQS V1.0 (Edge Quant Signal) — Auto Optimizer v1.5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
실거래 결과(trade_log.json)를 분석해서
  1) 최적 파라미터를 그리드 서치로 도출
  2) config.json 자동 업데이트
  3) edge_score_backtest_v27.py 상수 자동 수정
  4) 텔레그램으로 변경 내역 보고

실행 방법:
  python3 edge_optimizer.py              # 분석만 (미리보기)
  python3 edge_optimizer.py --apply      # 실제 파일 수정 적용
  python3 edge_optimizer.py --apply --tg # 수정 + 텔레그램 보고
"""

import json, re, sys, time, math
import numpy as np
from pathlib import Path
from datetime import datetime, date
from itertools import product

DRY_RUN   = "--apply" not in sys.argv
SEND_TG   = "--tg"    in sys.argv

BASE           = Path(__file__).parent
TRADE_LOG_FILE = BASE / "trade_log.json"
CONFIG_FILE    = BASE / "config.json"

# ════════════════════════════════════════════════
# 실전 거래 비용 상수 (Optimizer 시뮬레이션에 반영)
# ════════════════════════════════════════════════
# [New-A] 실전 왕복 수수료: 매수 0.015% + 매도 0.015% + 증권거래세 0.20% (KOSPI 기준)
COMMISSION_ROUND_TRIP = 0.0023   # 0.015% + 0.015% + 0.20% = 0.230%

# 클러스터별 슬리피지 — BT/RT SLIPPAGE_BY_CLUSTER와 동일
_SLIPPAGE_BY_CLUSTER_OPT = {
    "대형가치주":   0.003,
    "금융주":       0.003,
    "기술대형주":   0.003,
    "중소형성장주": 0.008,
    "기타":         0.005,
}

# [BUG-2 수정] 클러스터별 기본 ATR 배수 — BT ATR_MULT_BY_CLUSTER와 동일
_DEFAULT_ATR_MULT_OPT = {
    "대형가치주":   1.2,
    "금융주":       1.2,
    "기술대형주":   1.5,
    "중소형성장주": 2.0,
    "기타":         1.5,
}
# 개별 종목 → 클러스터 매핑 (RT/BT와 동일 — ticker 기반 슬리피지 결정)
_TICKER_CLUSTER_OPT = {
    "005930": "대형가치주", "005380": "대형가치주", "105560": "대형가치주",
    "055550": "대형가치주", "032830": "대형가치주", "000270": "대형가치주",
    "031980": "중소형성장주", "035420": "중소형성장주", "068270": "중소형성장주",
    "051910": "중소형성장주", "112610": "중소형성장주",
    "316140": "금융주",      "138930": "금융주",
    "000660": "기술대형주",  "066570": "기술대형주",
    "005490": "기술대형주",  "373220": "기술대형주",
}

def _get_trade_slip(trade: dict) -> float:
    """거래 기록에서 종목별 슬리피지 반환 (클러스터 우선, 없으면 ticker 매핑)"""
    cluster = trade.get("cluster", "")
    if cluster in _SLIPPAGE_BY_CLUSTER_OPT:
        return _SLIPPAGE_BY_CLUSTER_OPT[cluster]
    ticker = str(trade.get("ticker", ""))
    cluster = _TICKER_CLUSTER_OPT.get(ticker, "기타")
    return _SLIPPAGE_BY_CLUSTER_OPT.get(cluster, 0.005)
REALTIME_FILE  = sorted(BASE.glob("edge_score_realtime_v*.py"), reverse=True)
BACKTEST_FILE  = sorted(BASE.glob("edge_score_backtest_v*.py"),  reverse=True)
REALTIME_FILE  = REALTIME_FILE[0] if REALTIME_FILE else None
BACKTEST_FILE  = BACKTEST_FILE[0] if BACKTEST_FILE else None

# ════════════════════════════════════════════════
# 텔레그램
# ════════════════════════════════════════════════
def tg(msg: str):
    if not SEND_TG:
        return
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
        token   = cfg.get("TELEGRAM_TOKEN", "")
        chat_id = cfg.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

# ════════════════════════════════════════════════
# 1. 실거래 데이터 로드 & 기본 통계
# ════════════════════════════════════════════════
def load_trades() -> list:
    if not TRADE_LOG_FILE.exists():
        print("❌ trade_log.json 없음"); return []
    trades = json.loads(TRADE_LOG_FILE.read_text(encoding="utf-8"))
    # 청산된 거래만 — 이월 로그(carry_over=True) 제외
    # [Minor-11 수정] BT 주간이월 로그는 미실현 수익률이 기록되어 통계 오염 가능
    return [t for t in trades
            if t.get("exit_price", 0) > 0
            and t.get("buy_price", 0) > 0
            and not t.get("carry_over", False)]   # 이월 행 제외

def calc_stats(trades: list) -> dict:
    if not trades:
        return {}
    rets  = [(t["exit_price"] - t["buy_price"]) / t["buy_price"] for t in trades]
    # pnl: RT 로그에 저장된 값 우선 사용, 없으면 재계산 (부분매도 정확도 보정)
    pnls  = [t.get("pnl") if t.get("pnl") is not None
             else (t["exit_price"] - t["buy_price"]) * t.get("shares", 1)
             for t in trades]
    wins  = [r for r in rets if r > 0]
    losses= [r for r in rets if r < 0]

    stats = {
        "count":      len(trades),
        "win_rate":   len(wins) / len(trades),
        "avg_ret":    float(np.mean(rets)),
        "avg_win":    float(np.mean(wins))   if wins   else 0.0,
        "avg_loss":   float(np.mean(losses)) if losses else 0.0,
        "total_pnl":  float(sum(pnls)),
        "max_win":    float(max(rets))        if rets   else 0.0,
        "max_loss":   float(min(rets))        if rets   else 0.0,
        "std_ret":    float(np.std(rets))     if rets   else 0.0,
        "rets":       rets,
        "pnls":       pnls,
    }

    # 국면별
    for regime in ["BULL", "SIDE", "BEAR"]:
        sub = [t for t in trades if t.get("regime", "SIDE") == regime]
        if sub:
            sr = [(t["exit_price"] - t["buy_price"]) / t["buy_price"] for t in sub]
            stats[f"win_rate_{regime}"] = sum(1 for r in sr if r > 0) / len(sr)
            stats[f"avg_ret_{regime}"]  = float(np.mean(sr))
            stats[f"count_{regime}"]    = len(sub)

    # 이유별 분류
    reason_map = {}
    for t in trades:
        r = t.get("reason", "기타")
        if r not in reason_map:
            reason_map[r] = {"count": 0, "rets": []}
        ret = (t["exit_price"] - t["buy_price"]) / t["buy_price"]
        reason_map[r]["count"] += 1
        reason_map[r]["rets"].append(ret)
    stats["by_reason"] = {
        k: {
            "count":    v["count"],
            "win_rate": sum(1 for r in v["rets"] if r > 0) / len(v["rets"]),
            "avg_ret":  float(np.mean(v["rets"])),
        }
        for k, v in reason_map.items()
    }

    # 손절 비율
    sl_count    = reason_map.get("ATR손절", {}).get("count", 0)
    trail_count = reason_map.get("트레일링스탑", {}).get("count", 0)
    weekly_count= reason_map.get("주간청산(금요일)", {}).get("count", 0)
    stats["sl_rate"]     = sl_count    / len(trades)
    stats["trail_rate"]  = trail_count / len(trades)
    stats["weekly_rate"] = weekly_count / len(trades)  # 주간 청산 비율

    # 이월 통계
    carry_trades = [t for t in trades if t.get("reason","") == "주간이월(보유유지)"]
    stats["carry_rate"] = len(carry_trades) / len(trades) if trades else 0

    # 주간 청산 평균 보유일 / 수익률
    w_trades = [t for t in trades if t.get("reason","") == "주간청산(금요일)"]
    if w_trades:
        w_rets = [(t["exit_price"]-t["buy_price"])/t["buy_price"] for t in w_trades]
        w_days = [t.get("hold_days", 5) for t in w_trades]
        stats["weekly_avg_ret"]  = float(np.mean(w_rets))
        stats["weekly_avg_days"] = float(np.mean(w_days))
        stats["weekly_win_rate"] = sum(1 for r in w_rets if r > 0) / len(w_rets)
    else:
        stats["weekly_avg_ret"]  = 0.0
        stats["weekly_avg_days"] = 0.0
        stats["weekly_win_rate"] = 0.0

    return stats

# ════════════════════════════════════════════════
# 2. 파라미터 그리드 서치
#    실제 거래 데이터 기반으로 시뮬레이션
# ════════════════════════════════════════════════
def simulate_params(trades: list, params: dict) -> dict:
    """
    주어진 파라미터로 실거래 내역을 재시뮬레이션
    → 수익률 / 승률 / MDD 반환
    v38.4 반영: 이월 케이스(주간청산 예외) 시뮬레이션 포함
    """
    atr_mult_large  = params.get("atr_mult_large", 1.2)
    atr_mult_small  = params.get("atr_mult_small", 2.0)
    # 클러스터별 탐색 배수 매핑 (BT ATR_MULT_BY_CLUSTER와 동일 구조)
    _CLUSTER_MULT_MAP = {
        "대형가치주":   atr_mult_large,
        "금융주":       atr_mult_large,
        "기술대형주":   1.5,    # 기술대형주는 독립 고정 (BT와 동일)
        "중소형성장주": atr_mult_small,
        "기타":         1.5,
    }
    trail_act       = params.get("trail_activate", 0.07)
    take_profit     = params.get("take_profit", 0.15)
    kelly           = params.get("kelly", 0.25)
    atr_stop_max    = params.get("atr_stop_max", 0.12)
    # sell_edge_thr: 그리드에서 제거됨 (설계 모순 수정)
    # OPT simulate_params는 이미 확정된 reason 기반 재시뮬 → 청산 트리거 재현 불가
    # SELL_EDGE_THRESHOLD는 merge_recommendations에서 avg_ret 기반 직접 조정
    friday_hold_thr = params.get("friday_hold_thr", 0.45)  # 금요일 보유 유지 기준
    # [Issue-5 수정 / Fix-1 연계] 세 파일 모두 동일 실효 기준으로 통일
    # OPT(여기): -0.03 / BT: FRIDAY_HOLD_EDGE_THR_EFF = THR - 0.03 / RT: hold_thr_eff = thr - 0.03
    # → Optimizer 시뮬·BT 검증·RT 실전이 동일 기준으로 이월 여부 판단 (파이프라인 무결성 확보)
    friday_hold_thr_eff = friday_hold_thr - 0.03
    capital_floor   = params.get("capital_floor", 0.70)    # 자본 하방 보호 비율

    capital      = 10_000_000
    week_capital = capital   # [Issue-2 수정] 주차 시작 자본 추적 — 하방 보호 기준
    equity    = [capital]
    pnls_sim  = []

    for t in trades:
        buy_p  = t.get("buy_price", 0)
        exit_p = t.get("exit_price", 0)
        shares = t.get("shares", 1)
        if buy_p <= 0 or exit_p <= 0:
            continue

        ret = (exit_p - buy_p) / buy_p

        # [BUG-1 수정] trade → t (NameError 수정)
        # [BUG-2 수정] _orig_mult fallback을 슬리피지 dict → ATR 배수 dict로 교체
        cluster_for_sl = t.get("cluster", "기타")
        search_mult    = _CLUSTER_MULT_MAP.get(cluster_for_sl, 1.5)
        atr_sl_logged  = t.get("ATR손절선")
        if (atr_sl_logged is not None
                and isinstance(atr_sl_logged, (int, float))
                and atr_sl_logged < 0):
            base_sl    = float(atr_sl_logged)
            # atr_mult_orig: RT가 저장한 실제 배수. 없으면 클러스터 기본 ATR 배수로 fallback
            _orig_mult = t.get("atr_mult_orig",
                               _DEFAULT_ATR_MULT_OPT.get(cluster_for_sl, 1.5))
            _orig_mult = _orig_mult if (_orig_mult and _orig_mult > 0) else 1.5
            atr_ratio  = abs(base_sl) / _orig_mult
            sl_level   = -(atr_ratio * search_mult)
        else:
            # ATR손절선 미기록 시: buy_price 기준 2% ATR 근사
            atr_fallback = buy_p * 0.02
            sl_level     = -(atr_fallback * search_mult) / buy_p
        sl_level = max(sl_level, -atr_stop_max)   # BT ATR_STOP_MAX 동일 적용

        original_reason = t.get("reason", "")

        if original_reason == "ATR손절":
            sl_level = max(sl_level, -atr_stop_max)
            sim_ret  = max(ret, sl_level * 1.05)

        elif original_reason == "트레일링스탑":
            # [BUG-4 수정] trail_activate 파라미터가 실제로 효과를 갖도록 수정
            #       trail_act 이상이면 발동 구간 → take_profit cap 적용 (수익 보전)
            if ret < trail_act:
                # 새 파라미터 기준 트레일링이 발동하지 않았을 케이스
                # → 손절선까지 버티거나 손절 (ATR손절 결과로 근사)
                sim_ret = max(ret, sl_level * 1.05)
            else:
                # 트레일링 발동 후 고점 대비 ATR 간격 하락으로 청산
                # → 수익의 일부 보전 (take_profit cap)
                sim_ret = min(ret, take_profit)

        elif original_reason == "주간청산(금요일)":
            # 수정된 원칙2 시뮬레이션:
            # edge 정보가 있고 friday_hold_thr 이상이면 → 이월 (추가 보유)
            edge         = t.get("edge_at_exit", 0)
            trail_active = t.get("trail_active", False)  # RT trade_log 저장값
            # [이월 모순 수정] BT/RT 이월 조건 동일: trail_active OR edge >= thr_eff
            if ret > 0 and (trail_active or edge >= friday_hold_thr_eff):
                # 이월 케이스: 다음 주에 트레일링 or 익절로 청산 가정
                # 보수적으로 수익의 80%만 실현 (주말 갭 리스크 반영)
                sim_ret = ret * 0.80
            else:
                # 원칙2 청산: 현재 수익/손실 그대로
                sim_ret = ret

        elif original_reason == "타임스탑":
            # ㊳ 타임스탑: 새 파라미터 기준으로 재시뮬
            hold_d = t.get("hold_days", 15)
            ts_days = params.get("time_stop_days", 15)
            if hold_d < ts_days:
                # 새 기준에서는 아직 타임스탑 미발동 → 계속 보유했을 것
                sim_ret = min(ret * 1.1, take_profit)  # 보수적 추정
            else:
                sim_ret = ret  # 원래대로

        else:
            sim_ret = min(ret, take_profit) if ret > take_profit else ret

        # 켈리 기반 포지션 크기 — MAX_POSITION_RATIO와 동기화 (L-3 수정)
        max_pos_ratio = params.get("max_pos_ratio", 0.30)
        pos_size = min(capital * kelly, capital * max_pos_ratio)

        # [New-A] 실전 왕복 비용 차감 — 슬리피지(클러스터별) + 수수료(고정)
        slip_rate         = _get_trade_slip(t)
        round_trip_cost   = (slip_rate * 2) + COMMISSION_ROUND_TRIP
        sim_ret_net       = sim_ret - round_trip_cost   # 비용 차감 후 순수익률
        pnl = pos_size * sim_ret_net
        pnls_sim.append(pnl)
        capital = max(capital + pnl, 0)

        # [Issue-2 수정] capital_floor 실제 적용 — 주간 경계 감지 후 하방 보호
        exit_date_str = t.get("exit_date", "")
        if exit_date_str:
            try:
                _exit = date.fromisoformat(exit_date_str)
                # [capital_floor 시점 수정] BT/RT와 동일하게 월요일 기준 적용
                if _exit.weekday() == 4:   # 금요일 청산 → 주 마감
                    # BT/RT는 월요일 시가 기준, OPT는 금요일 확정값 → 동일 주간 내 처리로 근사
                    capital = max(capital, week_capital * capital_floor)
                    week_capital = capital  # 다음 주 기준으로 갱신
                elif _exit.weekday() == 0:  # 월요일 청산 → 신규 주간 시작
                    # 이전 주 마감 이후 포지션 없이 월요일 진입 케이스
                    capital = max(capital, week_capital * capital_floor)
                    week_capital = capital
            except (ValueError, TypeError):
                pass

        equity.append(capital)

    if not pnls_sim:
        return {"total_ret": 0, "win_rate": 0, "mdd": 0, "sharpe": 0}

    equity_arr = np.array(equity)
    peak       = np.maximum.accumulate(equity_arr)
    dd         = (equity_arr - peak) / peak
    mdd        = float(dd.min())

    wins     = [p for p in pnls_sim if p > 0]
    rets_sim = [p / 10_000_000 for p in pnls_sim]
    sharpe   = (float(np.mean(rets_sim)) / float(np.std(rets_sim))
                * math.sqrt(252) if np.std(rets_sim) > 0 else 0)

    return {
        "total_ret": (capital - 10_000_000) / 10_000_000,
        "win_rate":  len(wins) / len(pnls_sim),
        "mdd":       mdd,
        "sharpe":    sharpe,
        "final_cap": capital,
    }

def grid_search(trades: list, stats: dict, cfg: dict = None) -> dict:
    """
    핵심 파라미터 그리드 서치
    목적함수: 샤프지수 최대화 (MDD 패널티 포함)
    """
    print("\n🔍 그리드 서치 실행 중...")

    # 탐색 공간 정의
    # [BUG-5 수정] atr_mult_large/small 추가로 조합이 480,000개(원본 20x) → 실용 불가
    grid = {
        "atr_mult_large":  [1.0, 1.2, 1.5],       # 대형주 ATR 배수 (BT 기본 1.2 포함)
        "atr_mult_small":  [1.5, 2.0, 2.5],        # 소형주 ATR 배수 (BT 기본 2.0 포함)
        "trail_activate":  [0.05, 0.07, 0.10],      # 트레일링 발동 수익률
        "take_profit":     [0.10, 0.15, 0.20],      # 고정 익절
        "kelly":           [0.15, 0.25, 0.33],      # 켈리 비율
        "atr_stop_max":    [0.08, 0.12],            # ATR 손절 최대폭
        # sell_edge_thr: 그리드 제거 — simulate_params에서 청산 reason 재현 불가
        # (BT/RT: edge<SELL_EDGE_THRESHOLD → 매도트리거, OPT: 확정 reason 기반 → 재현 불가)
        # → SELL_EDGE_THRESHOLD는 실거래 통계(avg_ret)로 직접 설정 (merge_recommendations)
        "friday_hold_thr": [0.40, 0.45],            # 금요일 보유 유지 기준
        "capital_floor":   [0.65, 0.70],            # 자본 하방 보호
        "time_stop_days":  [10, 15],                # ㊳ 타임스탑 보유일
        "vol_target":      [0.015, 0.020, 0.025],   # ㊲ 목표 일간 변동성
    }
    # → 3×3×3×3×3×2×2×2×2×3 = 11,664개

    # 샘플 적을 경우 탐색 공간 추가 축소
    if len(trades) < 20:
        grid = {
            "atr_mult_large":  [1.0, 1.2, 1.5],
            "atr_mult_small":  [1.5, 2.0, 2.5],
            "trail_activate":  [0.05, 0.10],
            "take_profit":     [0.12, 0.15],
            "kelly":           [0.20, 0.25],
            "atr_stop_max":    [0.10, 0.12],
            # sell_edge_thr: 대형 그리드와 동일 이유로 제거
            "friday_hold_thr": [0.40, 0.45],
            "capital_floor":   [0.65, 0.70],
            "time_stop_days":  [10, 15],
            "vol_target":      [0.020],
        }
        # → 3×3×2×2×2×2×2×2×2×1 = 1,152개

    cfg = cfg or {}
    _max_pos = cfg.get("MAX_POSITION_RATIO", 0.30)
    best_score  = -999
    best_params = {}
    best_result = {}
    # BUG-B 수정: 소형/대형 그리드 공통 total 계산 (진행률 정확 표시)
    total = 1
    for _v in grid.values():
        total *= len(_v)
    cnt = 0

    for atr_l, atr_s, trail, tp, kelly, asl, fhold, cfloor, ts_days, vol_t in product(
            grid["atr_mult_large"], grid["atr_mult_small"],
            grid["trail_activate"],
            grid["take_profit"], grid["kelly"],
            grid["atr_stop_max"],
            grid["friday_hold_thr"], grid["capital_floor"],
            grid["time_stop_days"], grid["vol_target"]):
        params = {"atr_mult_large": atr_l, "atr_mult_small": atr_s,
                  "trail_activate": trail,
                  "take_profit": tp,  "kelly": kelly,
                  "atr_stop_max": asl,
                  "friday_hold_thr": fhold, "capital_floor": cfloor,
                  "time_stop_days": ts_days, "vol_target": vol_t,
                  "max_pos_ratio": cfg.get("MAX_POSITION_RATIO", 0.30)}
        result = simulate_params(trades, params)

        # 목적함수: 샤프지수 × (1 - MDD패널티) × 승률
        mdd_penalty = max(0, abs(result["mdd"]) - 0.15)  # 15% 초과 MDD 패널티
        score = (result["sharpe"]
                 * (1 - mdd_penalty * 3)
                 * (1 + result["win_rate"]))

        if score > best_score:
            best_score  = score
            best_params = params
            best_result = result
        cnt += 1

    print(f"   완료: {cnt}개 조합 탐색")
    print(f"   최적: {best_params}")
    print(f"   성과: 수익률 {best_result.get('total_ret',0):+.2%} | "
          f"승률 {best_result.get('win_rate',0):.1%} | "
          f"MDD {best_result.get('mdd',0):.1%} | "
          f"샤프 {best_result.get('sharpe',0):.2f}")

    return {"params": best_params, "result": best_result, "score": best_score}

# ════════════════════════════════════════════════
# 3. 실거래 기반 파라미터 진단
#    (그리드 서치 외 규칙 기반 조정)
# ════════════════════════════════════════════════
def diagnose(stats: dict) -> list:
    """
    실거래 통계에서 직접 문제 진단 → 조정 권고안 반환
    """
    suggestions = []

    if not stats:
        return suggestions

    wr   = stats.get("win_rate", 0)
    sl_r = stats.get("sl_rate", 0)
    tr_r = stats.get("trail_rate", 0)
    avg_w= stats.get("avg_win", 0)
    avg_l= stats.get("avg_loss", 0)
    cnt  = stats.get("count", 0)

    # ① 손절 너무 자주 → ATR 배수 확대
    if sl_r > 0.4 and cnt >= 5:
        suggestions.append({
            "param":   "ATR_MULT_SMALL",
            "reason":  f"손절 비율 {sl_r:.0%} (기준 40% 초과) → 손절선 넓히기",
            "current": None,
            "suggest": lambda v: round(min(v * 1.25, 3.0), 1),
            "severity": "HIGH",
        })
        suggestions.append({
            "param":   "ATR_MULT_LARGE",
            "reason":  f"손절 비율 {sl_r:.0%} → 대형주 손절선도 넓히기",
            "current": None,
            "suggest": lambda v: round(min(v * 1.2, 2.0), 1),
            "severity": "MEDIUM",
        })

    # ② 손절이 너무 적음 → ATR 배수 축소 (손절 안 치고 큰 손실)
    if sl_r < 0.10 and avg_l < -0.12 and cnt >= 5:
        suggestions.append({
            "param":   "ATR_MULT_SMALL",
            "reason":  f"평균 손실 {avg_l:.1%} 과다 (손절 미작동) → 손절선 좁히기",
            "current": None,
            "suggest": lambda v: round(max(v * 0.85, 1.2), 1),
            "severity": "HIGH",
        })

    # ③ 트레일링 너무 이른 발동 → TRAIL_ACTIVATE 상향
    if tr_r > 0.5 and stats.get("avg_ret_by_trail", avg_w) < 0.05 and cnt >= 5:
        suggestions.append({
            "param":   "TRAIL_ACTIVATE",
            "reason":  f"트레일링 발동 비율 {tr_r:.0%} 과다 → 활성 기준 높이기",
            "current": None,
            "suggest": lambda v: round(min(v * 1.3, 0.15), 3),
            "severity": "MEDIUM",
        })

    # ④ 승률 낮음 → Edge 기준 상향
    if wr < 0.35 and cnt >= 10:
        suggestions.append({
            "param":   "EDGE_SURGE_THRESHOLD",
            "reason":  f"승률 {wr:.0%} (35% 미만) → AI 진입 기준 강화",
            "current": None,
            "suggest": lambda v: round(min(v * 1.2, 0.25), 3),
            "severity": "HIGH",
        })

    # ⑤ 승률 높음 → Kelly 상향 가능
    if wr > 0.60 and avg_w > 0.10 and cnt >= 10:
        b = abs(avg_w / avg_l) if avg_l < 0 else 2.0
        p = wr
        full_kelly = p - (1 - p) / b
        opt_kelly  = round(min(max(full_kelly * 0.5, 0.15), 0.33), 2)
        suggestions.append({
            "param":   "KELLY_MAX_FRACTION",
            "reason":  f"승률 {wr:.0%} / 손익비 {b:.1f} → 켈리 비율 최적화",
            "current": None,
            "suggest": lambda v, k=opt_kelly: k,
            "severity": "LOW",
        })

    # ⑥ 국면별 승률 분석 → EXPOSURE_CAP 조정
    for regime, cap_key in [("BULL","EXPOSURE_CAP_BULL"),
                            ("SIDE","EXPOSURE_CAP_SIDE"),
                            ("BEAR","EXPOSURE_CAP_BEAR")]:
        r_wr  = stats.get(f"win_rate_{regime}", wr)
        r_cnt = stats.get(f"count_{regime}", 0)
        if r_cnt < 3:
            continue
        r_ret = stats.get(f"avg_ret_{regime}", 0)
        if regime == "BEAR" and r_ret < -0.03:
            suggestions.append({
                "param":   cap_key,
                "reason":  f"하락장 평균 수익률 {r_ret:.1%} → 비중 축소",
                "current": None,
                "suggest": lambda v: round(max(v * 0.75, 0.20), 2),
                "severity": "HIGH",
            })
        elif regime == "BULL" and r_wr > 0.65 and r_ret > 0.08:
            suggestions.append({
                "param":   cap_key,
                "reason":  f"상승장 승률 {r_wr:.0%} / 수익 {r_ret:.1%} → 비중 확대",
                "current": None,
                "suggest": lambda v: round(min(v * 1.1, 1.0), 2),
                "severity": "LOW",
            })

    # ⑦ 주간 강제청산 비율 과다 + 승률 낮음 → 익절 기준 낮춰 자발 청산 유도
    weekly_r  = stats.get("weekly_rate", 0)
    weekly_wr = stats.get("weekly_win_rate", 0)
    if weekly_r > 0.50 and weekly_wr < 0.40 and cnt >= 10:
        suggestions.append({
            "param":    "TAKE_PROFIT_FIXED",
            "reason":   (f"주간 강제청산 {weekly_r:.0%} / 승률 {weekly_wr:.0%} — "
                         f"익절 기준 낮춰 자발적 청산 유도"),
            "current":  None,
            "suggest":  lambda v: round(max(v * 0.85, 0.08), 3),
            "severity": "MEDIUM",
        })

    return suggestions

# ════════════════════════════════════════════════
# 4. 최종 업데이트 항목 결정
# ════════════════════════════════════════════════
def merge_recommendations(grid_result: dict, diagnose_result: list,
                          current_cfg: dict) -> dict:
    """
    그리드 서치 + 진단 결과를 합쳐서 최종 업데이트 딕셔너리 반환
    변경폭 제한: 1회 최대 ±30%
    """
    updates = {}

    # 그리드 서치 결과 반영
    if grid_result:
        p = grid_result["params"]
        # [Fix-BUG-3] atr_mult_large/small 독립 적용
        updates["ATR_MULT_LARGE"] = round(
            clamp(p["atr_mult_large"], current_cfg.get("ATR_MULT_LARGE", 1.2), 0.30), 1)
        updates["ATR_MULT_SMALL"] = round(
            clamp(p["atr_mult_small"], current_cfg.get("ATR_MULT_SMALL", 2.0), 0.30), 1)
        updates["TRAIL_ACTIVATE"] = round(
            clamp(p["trail_activate"], current_cfg.get("TRAIL_ACTIVATE", 0.07), 0.30), 3)
        updates["TAKE_PROFIT_FIXED"] = round(
            clamp(p["take_profit"], current_cfg.get("TAKE_PROFIT_FIXED", 0.15), 0.30), 3)
        updates["KELLY_MAX_FRACTION"] = round(
            clamp(p["kelly"], current_cfg.get("KELLY_MAX_FRACTION", 0.25), 0.30), 3)
        updates["ATR_STOP_MAX"] = round(
            clamp(p["atr_stop_max"], current_cfg.get("ATR_STOP_MAX", 0.12), 0.30), 3)
        # SELL_EDGE_THRESHOLD: 그리드 탐색 불가 (OPT simulate에서 청산 트리거 재현 불가)
        # → 실거래 avg_ret 기반으로 직접 조정 (성과 좋으면 완화, 나쁘면 강화)
        _cur_sell = current_cfg.get("SELL_EDGE_THRESHOLD", 0.30)
        _avg_ret  = grid_result.get("result", {}).get("total_ret", 0)
        if _avg_ret > 0.10:    # 좋은 성과 → 기준 소폭 완화 (더 오래 보유)
            _sell_adj = round(max(_cur_sell * 0.95, 0.20), 3)
        elif _avg_ret < -0.05: # 나쁜 성과 → 기준 강화 (빨리 매도)
            _sell_adj = round(min(_cur_sell * 1.10, 0.40), 3)
        else:
            _sell_adj = _cur_sell  # 보통 성과 → 유지
        updates["SELL_EDGE_THRESHOLD"] = round(
            clamp(_sell_adj, _cur_sell, 0.15), 3)
        # ── 투자원칙 신규 변수 ──
        updates["FRIDAY_HOLD_EDGE_THR"] = round(
            clamp(p["friday_hold_thr"], current_cfg.get("FRIDAY_HOLD_EDGE_THR", 0.45), 0.20), 3)
        updates["CAPITAL_FLOOR_RATIO"] = round(
            clamp(p["capital_floor"], current_cfg.get("CAPITAL_FLOOR_RATIO", 0.70), 0.15), 3)
        # ㊳ 타임스탑, ㊲ 변동성 타겟
        updates["TIME_STOP_DAYS"] = int(p.get("time_stop_days", 15))
        updates["VOL_TARGET_DAILY"] = round(
            clamp(p.get("vol_target", 0.02), current_cfg.get("VOL_TARGET_DAILY", 0.02), 0.30), 4)

    # 진단 결과 반영 — grid 미커버 키만 (L-2 수정: grid 우선)
    # grid = data-driven 최적값, diagnose = 규칙 기반 안전망
    #       diagnose는 EDGE_SURGE_THRESHOLD 등 grid 외 키 전담
    for sug in diagnose_result:
        key  = sug["param"]
        if key in updates:          # grid가 이미 최적화한 키 → 유지
            continue
        cur  = current_cfg.get(key)
        if cur is None:
            continue
        new_val = sug["suggest"](cur)
        clamped = clamp(new_val, cur, 0.30)
        updates[key] = clamped

    return updates

def clamp(new_val: float, cur_val: float, max_change_ratio: float) -> float:
    """변화폭 제한 — 1회 최대 max_change_ratio 비율로 제한"""
    if cur_val == 0:
        return new_val
    lo = cur_val * (1 - max_change_ratio)
    hi = cur_val * (1 + max_change_ratio)
    return max(lo, min(hi, new_val))

# ════════════════════════════════════════════════
# 5. config.json 업데이트
# ════════════════════════════════════════════════
def update_config(updates: dict) -> dict:
    """config.json에 변경사항 저장. 이전값 반환."""
    if not CONFIG_FILE.exists():
        print("❌ config.json 없음"); return {}

    # [config sync] rt.py DEFAULT_CONFIG를 baseline으로 — 저장 시 누락 키 보존
    _base = {}
    try:
        import importlib.util
        _spec = importlib.util.spec_from_file_location("rt", BASE / "rt.py")
        _rt   = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_rt)
        _base = getattr(_rt, "DEFAULT_CONFIG", {})
    except Exception:
        pass
    cfg  = dict(_base)
    cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))

    prev = {}
    for k, v in updates.items():
        prev[k] = cfg.get(k)
        cfg[k]  = v

    if not DRY_RUN:
        CONFIG_FILE.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print("✅ config.json 업데이트 완료")
    else:
        print("🔍 [미리보기] config.json 변경 예정:")
        for k, v in updates.items():
            print(f"   {k}: {prev.get(k)} → {v}")

    return prev

# ════════════════════════════════════════════════
# 6. 백테스트 소스 상수 자동 수정
# ════════════════════════════════════════════════
BACKTEST_PARAM_MAP = {
    # config.json 키 → 백테스트 파일 상수명 (정규식 패턴)
    "ATR_MULT_SMALL":    ("ATR_MULT_BY_CLUSTER", None),   # 중소형성장주 값
    "ATR_MULT_LARGE":    ("ATR_MULT_BY_CLUSTER", None),   # 대형가치주 값
    "TRAIL_ACTIVATE":    ("TRAIL_ACTIVATE_RET",  r"TRAIL_ACTIVATE_RET\s*=\s*[\d.]+"),
    "TAKE_PROFIT_FIXED": ("TAKE_PROFIT_FIXED",   r"TAKE_PROFIT_FIXED\s*=\s*[\d.]+"),
    "KELLY_MAX_FRACTION":("KELLY_FRACTION",       r"KELLY_FRACTION\s*=\s*[\d.]+"),
    "EXPOSURE_CAP_BULL": ("EXPOSURE_CAP",         None),  # 딕셔너리 내부
    "EXPOSURE_CAP_SIDE": ("EXPOSURE_CAP",         None),
    "EXPOSURE_CAP_BEAR":      ("EXPOSURE_CAP",          None),
    "ATR_STOP_MAX":           ("ATR_STOP_MAX",           r"ATR_STOP_MAX\s*=\s*[\d.]+"),
    "SELL_EDGE_THRESHOLD":    ("SELL_EDGE_THRESHOLD",    r"SELL_EDGE_THRESHOLD\s*=\s*[\d.]+"),
    "CORR_HIGH_THRESHOLD":    ("CORR_HIGH_THRESHOLD",   r"CORR_HIGH_THRESHOLD\s*=\s*[\d.]+"),
    "FRIDAY_HOLD_EDGE_THR":   ("FRIDAY_HOLD_EDGE_THR",  r"FRIDAY_HOLD_EDGE_THR\s*=\s*[\d.]+"),
    "CAPITAL_FLOOR_RATIO":    ("CAPITAL_FLOOR_RATIO",   r"CAPITAL_FLOOR_RATIO\s*=\s*[\d.]+"),
}

def update_backtest_source(updates: dict) -> list:
    """
    백테스트 파이썬 소스 파일의 상수를 직접 수정
    """
    if BACKTEST_FILE is None:
        print("⚠️  백테스트 파일을 찾을 수 없음"); return []

    src     = BACKTEST_FILE.read_text(encoding="utf-8")
    changed = []

    # ── 단순 float 상수 직접 치환 ──────────────────
    simple_map = {
        "TRAIL_ACTIVATE":      (r"(TRAIL_ACTIVATE_RET\s*=\s*)[\d.]+",     "{:.3f}"),
        "TAKE_PROFIT_FIXED":   (r"(TAKE_PROFIT_FIXED\s*=\s*)[\d.]+",      "{:.3f}"),
        "KELLY_MAX_FRACTION":  (r"(KELLY_FRACTION\s*=\s*)[\d.]+",          "{:.3f}"),
        "ATR_STOP_MAX":        (r"(ATR_STOP_MAX\s*=\s*)[\d.]+",           "{:.3f}"),
        "SELL_EDGE_THRESHOLD": (r"(SELL_EDGE_THRESHOLD\s*=\s*)[\d.]+",    "{:.3f}"),
        "CORR_HIGH_THRESHOLD": (r"(CORR_HIGH_THRESHOLD\s*=\s*)[\d.]+",    "{:.3f}"),
        "FRIDAY_HOLD_EDGE_THR":(r"(FRIDAY_HOLD_EDGE_THR\s*=\s*)[\d.]+",   "{:.3f}"),
        "CAPITAL_FLOOR_RATIO": (r"(CAPITAL_FLOOR_RATIO\s*=\s*)[\d.]+",    "{:.3f}"),
    }
    for cfg_key, (pattern, fmt) in simple_map.items():
        if cfg_key not in updates:
            continue
        new_val = updates[cfg_key]
        m = re.search(pattern, src)
        if m:
            old_val_str = re.search(r"[\d.]+$", m.group(0)).group(0)
            new_src = re.sub(pattern,
                             lambda x: x.group(1) + fmt.format(new_val), src)
            if new_src != src:
                src = new_src
                changed.append((cfg_key, float(old_val_str), new_val))

    # ── ATR_MULT_BY_CLUSTER 딕셔너리 치환 ──────────
    # [BUG-3 수정] context-aware 블록 치환 — 전체 파일 re.sub 금지
    #       (대형가치주 키가 3개 dict에 존재 → 슬리피지 0.003이 ATR값으로 덮어써짐)
    # 수정: ATR_MULT_BY_CLUSTER 블록 구간만 추출 후 내부에서만 치환
    #       블록 교체로 나머지 dict 불변 보장
    if "ATR_MULT_LARGE" in updates or "ATR_MULT_SMALL" in updates:
        atr_l = updates.get("ATR_MULT_LARGE")
        atr_s = updates.get("ATR_MULT_SMALL")

        # ATR_MULT_BY_CLUSTER 블록만 추출 (닫는 } 까지)
        block_m = re.search(r'(ATR_MULT_BY_CLUSTER\s*=\s*\{[^}]*\})', src, re.DOTALL)
        if block_m:
            block_orig = block_m.group(1)
            block_new  = block_orig

            if atr_l is not None:
                for k in ['"대형가치주"', '"금융주"']:
                    pat = rf'({k}:\s*)[\d.]+'
                    km = re.search(pat, block_new)
                    if km:
                        old_v = float(re.search(r'[\d.]+$', km.group(0)).group(0))
                        block_new = re.sub(pat,
                                           lambda x, v=atr_l: x.group(1) + f"{v:.1f}",
                                           block_new)
                        changed.append((f"ATR_MULT_{k}", old_v, atr_l))

            if atr_s is not None:
                for k in ['"중소형성장주"']:
                    pat = rf'({k}:\s*)[\d.]+'
                    km = re.search(pat, block_new)
                    if km:
                        old_v = float(re.search(r'[\d.]+$', km.group(0)).group(0))
                        block_new = re.sub(pat,
                                           lambda x, v=atr_s: x.group(1) + f"{v:.1f}",
                                           block_new)
                        changed.append((f"ATR_MULT_{k}", old_v, atr_s))

            # 기술대형주 1.5 동기화 (블록 내부만 — TRAIL_ATR_MULT의 기술대형주 2.0 불변)
            for k in ['"기술대형주"']:
                pat = rf'({k}:\s*)[\d.]+'
                km = re.search(pat, block_new)
                if km:
                    cur_v = float(re.search(r'[\d.]+$', km.group(0)).group(0))
                    if cur_v != 1.5:
                        block_new = re.sub(pat, lambda x: x.group(1) + "1.5", block_new)
                        changed.append((f"ATR_MULT_{k}_강제동기화", cur_v, 1.5))

            # 블록 교체 (1회만) — 블록 외부 dict 값 불변
            if block_new != block_orig:
                src = src.replace(block_orig, block_new, 1)

    # ── EXPOSURE_CAP 딕셔너리 치환 ──────────────────
    # [BUG-6 수정] context-aware 블록 치환 — 전체 파일 re.sub 금지
    #         ALT_FILTER_BY_REGIME["BULL"]=3.0 → 패치값으로 파괴 (진입 임계값 오염)
    #         regime_al.map({"BULL": 1.0}) → 패치값으로 파괴 (ATR BULL 조정 파괴)
    # 수정: EXPOSURE_CAP 블록만 추출 후 내부에서만 치환 → 다른 dict 불변 보장
    expo_map = {
        "EXPOSURE_CAP_BULL": '"BULL"',
        "EXPOSURE_CAP_SIDE": '"SIDE"',
        "EXPOSURE_CAP_BEAR": '"BEAR"',
    }
    expo_needed = {k: v for k, v in updates.items() if k in expo_map}
    if expo_needed:
        # EXPOSURE_CAP 블록만 추출 (닫는 } 까지)
        cap_m = re.search(r'(EXPOSURE_CAP\s*=\s*\{[^}]*\})', src, re.DOTALL)
        if cap_m:
            cap_orig = cap_m.group(1)
            cap_new  = cap_orig
            for cfg_key, dict_key in expo_map.items():
                if cfg_key not in expo_needed:
                    continue
                new_val = expo_needed[cfg_key]
                pat = rf'({dict_key}:\s*)[\d.]+'
                km = re.search(pat, cap_new)
                if km:
                    old_v = float(re.search(r'[\d.]+$', km.group(0)).group(0))
                    cap_new = re.sub(pat,
                                     lambda x, v=new_val: x.group(1) + f"{v:.2f}",
                                     cap_new)
                    changed.append((cfg_key, old_v, new_val))
            # 블록 교체 (1회만) — ALT_FILTER_BY_REGIME, regime_al.map 불변
            if cap_new != cap_orig:
                src = src.replace(cap_orig, cap_new, 1)

    if not DRY_RUN and changed:
        BACKTEST_FILE.write_text(src, encoding="utf-8")
        print(f"✅ 백테스트 소스 업데이트: {BACKTEST_FILE.name}")
    elif changed:
        print(f"🔍 [미리보기] 백테스트 소스 변경 예정:")
        for key, old, new in changed:
            print(f"   {key}: {old} → {new}")

    return changed

# ════════════════════════════════════════════════
# 7. 리얼타임 소스 업데이트 (버전 기록)
# ════════════════════════════════════════════════
def update_realtime_version_comment(summary: str):
    """
    realtime 소스 상단 패치 노트에 최적화 내역 추가
    """
    if REALTIME_FILE is None or DRY_RUN:
        return
    src = REALTIME_FILE.read_text(encoding="utf-8")
    today = date.today().strftime("%Y-%m-%d")
    patch = f"\n# [{today}] 자동 최적화: {summary}"
    # 첫 번째 코드 줄 앞에 삽입
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# v") or line.startswith("\"\"\""):
            lines.insert(i + 1, patch)
            break
    REALTIME_FILE.write_text("\n".join(lines), encoding="utf-8")

# ════════════════════════════════════════════════
# 8. 보고서 생성
# ════════════════════════════════════════════════
def build_report(stats: dict, updates: dict, prev_cfg: dict,
                 bt_changed: list, diagnose_sug: list) -> str:
    today = datetime.now().strftime("%Y/%m/%d %H:%M")
    lines = [
        f"🤖 <b>Edge Score 자동 최적화 완료</b>",
        f"━━━━━━━━━━━━━━━━━━",
        f"📅 {today}",
        f"",
        f"📊 <b>분석된 실거래</b>",
        f"  총 {stats.get('count',0)}건 · 승률 {stats.get('win_rate',0):.0%}",
        f"  평균 수익: {stats.get('avg_ret',0):+.2%}",
        f"  평균 수익/손실: +{stats.get('avg_win',0):.2%} / {stats.get('avg_loss',0):.2%}",
        f"  손절 비율: {stats.get('sl_rate',0):.0%} · 트레일링: {stats.get('trail_rate',0):.0%}",
        f"  주간청산: {stats.get('weekly_rate',0):.0%} · 주간승률: {stats.get('weekly_win_rate',0):.0%} · 주간평균: {stats.get('weekly_avg_ret',0):+.2%}",
    ]

    if updates:
        lines += ["", "⚙️ <b>자동 변경된 파라미터</b>"]
        param_labels = {
            "ATR_MULT_SMALL":     "🛑 ATR 손절 중소형",
            "ATR_MULT_LARGE":     "🛑 ATR 손절 대형주",
            "TRAIL_ACTIVATE":     "🔺 트레일링 시작",
            "TAKE_PROFIT_FIXED":  "🎯 고정 익절",
            "KELLY_MAX_FRACTION": "📐 켈리 비율",
            "EXPOSURE_CAP_BULL":  "📈 상승장 한도",
            "EXPOSURE_CAP_SIDE":  "➡️ 보합장 한도",
            "EXPOSURE_CAP_BEAR":  "📉 하락장 한도",
            "EDGE_SURGE_THRESHOLD":   "🚀 AI급등 기준",
            "SELL_EDGE_THRESHOLD":    "📉 AI점수 매도 기준",
            "ATR_STOP_MAX":           "🛑 손절 최대폭",
            "CORR_HIGH_THRESHOLD":    "🔗 상관관계 기준",
            # [Fix-7] MAX_POSITION_RATIO: merge_recommendations/grid_search 탐색 대상 아님
            # → updates에 절대 들어오지 않으므로 레이블 제거 (텔레그램 보고서 오인 방지)
            "FRIDAY_HOLD_EDGE_THR":   "📅 금요일 보유 기준",
            "CAPITAL_FLOOR_RATIO":    "🛡️ 자본 하방 보호",
            "TIME_STOP_DAYS":         "⏱️ 타임스탑 보유일",
            "VOL_TARGET_DAILY":       "📊 목표 일간 변동성",
        }
        for k, new_v in updates.items():
            old_v = prev_cfg.get(k)
            lbl   = param_labels.get(k, k)
            if old_v is not None and old_v != new_v:
                if isinstance(new_v, float) and new_v <= 1.0:
                    lines.append(f"  {lbl}: {old_v:.0%} → <b>{new_v:.0%}</b>")
                else:
                    lines.append(f"  {lbl}: {old_v} → <b>{new_v}</b>")

    if bt_changed:
        lines += ["", "📝 <b>백테스트 소스 동기화 완료</b>",
                  f"  {len(bt_changed)}개 상수 업데이트됨"]

    if diagnose_sug:
        high = [s for s in diagnose_sug if s.get("severity") == "HIGH"]
        if high:
            lines += ["", "🚨 <b>주요 진단 결과</b>"]
            for s in high[:3]:
                lines.append(f"  · {s['reason']}")

    mode = "🔍 미리보기 (--apply 없음)" if DRY_RUN else "✅ 실제 적용 완료"
    lines += ["", f"💡 {mode}", "   재시작 없이 즉시 반영돼요"]

    return "\n".join(lines)

# ════════════════════════════════════════════════
# 9. 메인 실행
# ════════════════════════════════════════════════
def main():
    print("\n" + "=" * 55)
    print("  🤖 EQS V1.0 (Edge Quant Signal) — Auto Optimizer v1.5")
    print("=" * 55)
    print(f"  모드: {'미리보기 (DRY RUN)' if DRY_RUN else '🔴 실제 적용'}")
    print(f"  텔레그램: {'ON' if SEND_TG else 'OFF'}")
    if REALTIME_FILE: print(f"  리얼타임: {REALTIME_FILE.name}")
    if BACKTEST_FILE: print(f"  백테스트: {BACKTEST_FILE.name}")
    print()

    # ① 실거래 데이터 로드
    trades = load_trades()
    if not trades:
        print("❌ 분석할 거래 데이터가 없어요")
        print("   trade_log.json 에 청산된 거래가 있어야 해요")
        return

    print(f"✅ 실거래 {len(trades)}건 로드")

    # ② 통계 계산
    stats = calc_stats(trades)
    print(f"\n📊 기본 통계")
    print(f"   승률:     {stats['win_rate']:.1%}")
    print(f"   평균 수익: {stats['avg_ret']:+.2%}")
    print(f"   손절 비율: {stats['sl_rate']:.1%}")
    print(f"   트레일링:  {stats['trail_rate']:.1%}")
    print(f"   주간 강제청산: {stats['weekly_rate']:.1%} / 주간 승률: {stats['weekly_win_rate']:.1%} / 주간 평균: {stats['weekly_avg_ret']:+.2%}")
    for regime in ["BULL", "SIDE", "BEAR"]:
        cnt = stats.get(f"count_{regime}", 0)
        if cnt > 0:
            wr = stats.get(f"win_rate_{regime}", 0)
            ar = stats.get(f"avg_ret_{regime}", 0)
            print(f"   {regime}: {cnt}건 | 승률 {wr:.0%} | 평균 {ar:+.2%}")

    # ③ 진단
    diagnose_sug = diagnose(stats)
    if diagnose_sug:
        print(f"\n🔍 진단 결과 ({len(diagnose_sug)}건)")
        for s in diagnose_sug:
            icon = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(s["severity"],"⚪")
            print(f"   {icon} {s['reason']}")

    # ④ 현재 config 로드 — grid_search 전에 반드시 먼저 (BUG-A 수정)
    # [config sync] rt.py DEFAULT_CONFIG를 baseline으로 fallback → 누락 키 방지
    _rt_default = {}
    try:
        import importlib.util, sys as _sys
        _spec = importlib.util.spec_from_file_location("rt", BASE / "rt.py")
        _rt   = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_rt)
        _rt_default = getattr(_rt, "DEFAULT_CONFIG", {})
    except Exception as _e:
        print(f"⚠️  rt.py DEFAULT_CONFIG 로드 실패 ({_e}) — 하드코딩 fallback 사용")

    current_cfg = dict(_rt_default)   # baseline: DEFAULT_CONFIG 전체
    if CONFIG_FILE.exists():
        _saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        current_cfg.update(_saved)    # 실제 저장값으로 덮어쓰기 (사용자 설정 우선)
        # 신규 키가 있으면 disk에도 write-back (rt.py load_config와 동일 정책)
        _new_keys = [k for k in current_cfg if k not in _saved]
        if _new_keys and not DRY_RUN:
            CONFIG_FILE.write_text(
                json.dumps(current_cfg, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"✅ [config sync] 신규 키 {len(_new_keys)}개 자동 추가됨: {_new_keys}")
        elif _new_keys:
            print(f"🔍 [config sync 미리보기] 신규 키 {len(_new_keys)}개 감지: {_new_keys}")

    # ⑤ 그리드 서치 (거래 5건 이상) — current_cfg 로드 후 호출
    grid_result = {}
    if len(trades) >= 5:
        grid_result = grid_search(trades, stats, current_cfg)
    else:
        print(f"\n⚠️  거래 {len(trades)}건 (5건 미만) → 그리드 서치 스킵")

    # ⑥ 최종 업데이트 항목 결정
    updates = merge_recommendations(grid_result, diagnose_sug, current_cfg)

    # 변화 없는 항목 제거
    updates = {k: v for k, v in updates.items()
               if v is not None and current_cfg.get(k) != v}

    if not updates:
        print("\n✅ 현재 설정이 이미 최적 상태예요 — 변경 없음")
        tg("✅ <b>자동 최적화 완료</b>\n현재 설정이 이미 최적 상태예요.\n변경 없음.")
        return

    print(f"\n📋 최종 업데이트 항목 ({len(updates)}건)")
    for k, v in updates.items():
        old = current_cfg.get(k)
        if isinstance(v, float) and v <= 1.0:
            print(f"   {k}: {old} → {v:.3f}")
        else:
            print(f"   {k}: {old} → {v}")

    # ⑦ config.json 업데이트
    prev_cfg = update_config(updates)

    # ⑧ 백테스트 소스 업데이트
    bt_changed = update_backtest_source(updates)

    # ⑨ 리얼타임 소스 버전 메모
    summary = ", ".join([f"{k}={v}" for k, v in list(updates.items())[:3]])
    update_realtime_version_comment(summary)

    # ⑩ 보고서 생성 & 텔레그램 전송
    report = build_report(stats, updates, prev_cfg, bt_changed, diagnose_sug)
    print("\n" + "=" * 55)
    print(report)
    print("=" * 55)

    if SEND_TG:
        tg(report)
        print("\n✅ 텔레그램 전송 완료")

    if DRY_RUN:
        print("\n💡 실제 적용하려면: python3 edge_optimizer.py --apply --tg")


if __name__ == "__main__":
    main()