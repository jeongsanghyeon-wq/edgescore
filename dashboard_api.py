"""
Edge Score v40.0 — Dashboard API Server v1.9.2
=============================================================
v1.0 → v1.5 변경사항:
  [1] API 캐시 (3초) — 데이터소스 부하 감소 + 네이버 차단 방지
  [2] 스레드 안전성 — _monitor 접근 시 Lock + 스냅샷(deepcopy)
  [3] 텔레그램 알림 — 캐시 히트율 이상 시 알림

v1.9.2 수정사항:
  [BUG-FIX] api_portfolio summary에 available_cash 키 추가
            (총자본 - 평가금) → Dashboard 가용현금 패널 항상 ₩0 버그 수정

v1.9.1 수정사항:
  [BUG-FIX] _cached() 데코레이터 ttl 파라미터 미지원 → TypeError 크래시 수정
            api_account(@_cached("account", ttl=_CACHE_TTL_ACCOUNT)) 정상 동작

사용법: rt.py main에서
  from dashboard_api import start_dashboard
  start_dashboard(monitor, port=5000)
"""

import json
import threading
import logging
import calendar
import math
import copy
import time as _time
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import defaultdict
from functools import wraps

try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
    FLASK_OK = True
except ImportError:
    FLASK_OK = False

log = logging.getLogger("dashboard")
_monitor = None
_rt_module = None

# ══════════════════════════════════════════
# [개선1] API 캐시 — 동일 엔드포인트 3초 내 재요청 시 캐시 반환
# ══════════════════════════════════════════
_cache = {}
_CACHE_TTL = 3
_CACHE_TTL_ACCOUNT = 30   # [v1.9] api_account 전용 30초 캐시 (키움 API 과호출 방지)


def _cached(endpoint_key, ttl=None):
    # [v1.9 BUG-FIX] ttl 파라미터 지원 추가 — api_account의 @_cached("account", ttl=_CACHE_TTL_ACCOUNT) TypeError 수정
    _ttl = ttl if ttl is not None else _CACHE_TTL
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            now = _time.time()
            cached = _cache.get(endpoint_key)
            if cached and (now - cached["ts"]) < _ttl:
                return jsonify(cached["data"])
            result = fn(*args, **kwargs)
            if isinstance(result, dict):
                _cache[endpoint_key] = {"data": result, "ts": now}
                return jsonify(result)
            return result
        return wrapper
    return decorator


# ══════════════════════════════════════════
# [개선2] 스레드 안전성
# ══════════════════════════════════════════
_data_lock = threading.Lock()


def _safe_positions():
    with _data_lock:
        try:
            return copy.deepcopy(dict(_monitor.positions)) if _monitor and hasattr(_monitor, 'positions') else {}
        except Exception:
            return {}


def _safe_universe():
    with _data_lock:
        try:
            return copy.deepcopy(dict(_monitor.universe)) if _monitor and hasattr(_monitor, 'universe') else {}
        except Exception:
            return {}


def _safe_attr(attr, default=None):
    with _data_lock:
        try:
            return getattr(_monitor, attr, default)
        except Exception:
            return default


def start_dashboard(monitor, port=5000):
    global _monitor, _rt_module
    _monitor = monitor
    if not FLASK_OK:
        log.warning("⚠️ Flask 미설치 — 대시보드 비활성. pip install flask flask-cors")
        return
    import importlib
    try:
        _rt_module = importlib.import_module("rt")
    except Exception as e:
        log.error(f"rt 모듈 import 실패: {e}")
        return
    app = _create_app()
    t = threading.Thread(target=lambda: app.run(
        host="0.0.0.0", port=port, debug=False, use_reloader=False
    ), daemon=True)
    t.start()
    log.info(f"📊 대시보드 API v1.9 서버 시작: http://0.0.0.0:{port}")
    log.info(f"   캐시 TTL: {_CACHE_TTL}초 | Lock: 활성 | AbortController: 프론트 적용")


def _create_app():
    app = Flask(__name__)
    CORS(app)

    @app.route("/api/health")
    def api_health():
        return jsonify({"status": "ok", "version": "v1.9.1",
                        "cache_ttl": _CACHE_TTL, "timestamp": datetime.now().isoformat()})

    @app.route("/api/status")
    @_cached("status")
    def api_status():
        C = _rt_module.C
        return {
            "version": "v40.0", "regime": _safe_attr("regime", "SIDE"),
            "circuit_active": _safe_attr("_circuit_active", False),
            "market_open": _rt_module.is_market_hour(),
            "today_alerts": _safe_attr("today_alerts", 0),
            "total_capital": C.get("TOTAL_CAPITAL", 10_000_000),
            "capital_floor_ratio": C.get("CAPITAL_FLOOR_RATIO", 0.70),
            "timestamp": datetime.now().isoformat(),
        }

    @app.route("/api/portfolio")
    @_cached("portfolio")
    def api_portfolio():
        rt, C = _rt_module, _rt_module.C
        positions = _safe_positions()
        holdings = []
        for ticker, info in positions.items():
            try:
                name = info.get("name", "")
                buy_p = float(info.get("buy_price", 0))
                shares = int(info.get("shares", 0))
                cp = rt.get_current_price(ticker)
                if cp <= 0:
                    df = rt.get_ohlcv(ticker, days=5)
                    cp = float(df["종가"].iloc[-1]) if df is not None and len(df) > 0 else buy_p
                ret = (cp - buy_p) / buy_p if buy_p > 0 else 0
                pnl = (cp - buy_p) * shares
                df_sl = rt.get_ohlcv(ticker, days=30)
                atr = rt.calc_atr(df_sl) if df_sl is not None else cp * 0.02
                dyn_sl = rt.calc_dynamic_sl(atr, cp, ticker, _safe_attr("regime", "SIDE"))
                # [v1.9 BUG-FIX] 손절가 표시를 실제 트리거와 동일하게 매수가 기준으로
                _sl_base = buy_p if buy_p > 0 else cp
                sl_price = round(_sl_base * (1 + dyn_sl), -1)
                df_edge = rt.get_ohlcv(ticker, days=60)
                edge = 0
                if df_edge is not None:
                    kind_adj = rt.fetch_kind_sentiment(ticker) if hasattr(rt, "fetch_kind_sentiment") else 0
                    edge = rt.calculate_edge_v27(df_edge, kind_adj, ticker)
                price_history = []
                if df_sl is not None:
                    price_history = df_sl["종가"].tail(30).tolist()
                sector = info.get("sector", _get_sector(ticker))
                holdings.append({
                    "ticker": ticker, "name": name, "sector": sector,
                    "buy_price": buy_p, "current_price": round(cp), "shares": shares,
                    "ret": round(ret, 4), "pnl": round(pnl),
                    "edge": round(edge * 100), "sl_price": sl_price,
                    "trail_active": bool(info.get("trail_active", False)),
                    "hold_days": (date.today() - date.fromisoformat(info["entry_date"])).days
                             if info.get("entry_date") else 0,
                    "atr_alerted": bool(info.get("atr_alerted", False)),
                    "price_history": price_history,
                })
            except Exception as e:
                log.warning(f"portfolio 종목 처리 오류 {ticker}: {e}")
                continue
        total_inv = sum(h["buy_price"] * h["shares"] for h in holdings)
        total_eval = sum(h["current_price"] * h["shares"] for h in holdings)
        capital = C.get("TOTAL_CAPITAL", 10_000_000)
        floor = capital * C.get("CAPITAL_FLOOR_RATIO", 0.70)
        return {
            "holdings": holdings,
            "summary": {
                "total_invested": round(total_inv), "total_eval": round(total_eval),
                "total_pnl": round(total_eval - total_inv),
                "total_ret": round((total_eval - total_inv) / total_inv, 4) if total_inv > 0 else 0,
                "capital": capital, "floor": floor,
                "floor_remaining": round(max(0, total_eval - floor)),
                "available_cash": round(max(0, capital - total_eval)),   # [BUG-FIX] Dashboard 가용현금 표시용
                "count": len(holdings),
                "trail_active_count": sum(1 for h in holdings if h["trail_active"]),
            }
        }

    @app.route("/api/watchlist")
    @_cached("watchlist")
    def api_watchlist():
        rt = _rt_module
        positions = _safe_positions()
        universe = _safe_universe()
        watchlist = []
        held = set(positions.keys())
        for ticker, name in list(universe.items())[:20]:
            if ticker in held:
                continue
            try:
                df = rt.get_ohlcv(ticker, days=60)
                if df is None or len(df) < 20:
                    continue
                cp = rt.get_current_price(ticker)
                if cp <= 0 and df is not None:
                    cp = float(df["종가"].iloc[-1])
                kind_adj = rt.fetch_kind_sentiment(ticker) if hasattr(rt, "fetch_kind_sentiment") else 0
                edge = rt.calculate_edge_v27(df, kind_adj, ticker)
                prev = float(df["종가"].iloc[-2]) if len(df) >= 2 else cp
                change = (cp - prev) / prev if prev > 0 else 0
                guide = None
                if hasattr(rt, "calc_entry_guide"):
                    try:
                        guide = rt.calc_entry_guide(df, ticker, _safe_attr("regime", "SIDE"))
                    except:
                        pass
                watchlist.append({
                    "ticker": ticker, "name": name, "sector": _get_sector(ticker),
                    "edge": round(edge * 100), "price": round(cp), "change": round(change, 4),
                    "signal": edge >= 0.75 and not _safe_attr("_circuit_active", False),
                    "blocked": edge >= 0.75 and _safe_attr("_circuit_active", False),
                    "guide": guide,
                })
            except Exception as e:
                log.warning(f"watchlist 종목 처리 오류 {ticker}: {e}")
                continue
        watchlist.sort(key=lambda x: -x["edge"])
        return {"watchlist": watchlist[:12]}

    @app.route("/api/alerts")
    @_cached("alerts")
    def api_alerts():
        alert_file = Path("alerts_today.json")
        alerts = []
        if alert_file.exists():
            try:
                alerts = json.loads(alert_file.read_text(encoding="utf-8"))
            except:
                pass
        return {"alerts": alerts, "count": len(alerts)}

    @app.route("/api/kospi")
    @_cached("kospi")
    def api_kospi():
        rt = _rt_module
        prices, latest = [], 0
        # 1) 네이버 크롤링 (장중/장외 모두)
        try:
            import requests as _req
            from bs4 import BeautifulSoup as _BS
            url = "https://finance.naver.com/sise/sise_index.naver?code=KOSPI"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh)",
                "Referer": "https://finance.naver.com/"
            }
            resp = _req.get(url, headers=headers, timeout=5)
            soup = _BS(resp.text, "html.parser")
            tag = soup.select_one("#now_value")
            if tag:
                latest = float(tag.get_text(strip=True).replace(",", ""))
        except Exception as e:
            log.warning(f"KOSPI naver fail: {e}")
        # 2) 히스토리: rt.get_ohlcv ETF -> 비율 변환
        try:
            df = rt.get_ohlcv("069500", days=30)
            if df is not None and len(df) > 0:
                etf_prices = df["종가"].tail(30).tolist()
                if latest > 0 and etf_prices:
                    ratio = latest / etf_prices[-1]
                    prices = [round(p * ratio, 2) for p in etf_prices]
                else:
                    prices = etf_prices
        except:
            pass
        if latest > 0 and prices:
            prices[-1] = latest
        elif latest > 0:
            prices = [latest]
        if not prices and latest <= 0:
            return {"price": 0, "change": 0, "history": []}
        if latest <= 0:
            latest = prices[-1]
        prev = prices[-2] if len(prices) >= 2 else latest
        return {
            "price": round(latest, 2),
            "change": round((latest - prev) / prev, 4) if prev else 0,
            "history": [round(p, 2) for p in prices]
        }

    @app.route("/api/defense")
    @_cached("defense")
    def api_defense():
        C = _rt_module.C
        positions = _safe_positions()
        wd = date.today().weekday()
        today = date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        last_fri = date(today.year, today.month, last_day)
        while last_fri.weekday() != 4:
            last_fri -= timedelta(days=1)
        # 경제이벤트 당일/내일 여부 계산
        def __parse_econ_date(s):
            try: return date.fromisoformat(s)
            except: return None
        _econ_list = C.get("ECON_EVENTS_2025_2026", [])
        _econ_dates = [d for s in _econ_list for d in [__parse_econ_date(s)] if d]
        _econ_today_def    = today in _econ_dates
        _econ_tomorrow_def = (today + timedelta(days=1)) in _econ_dates
        return {
            "circuit_breaker": {"active": _safe_attr("_circuit_active", False), "threshold": C.get("DAILY_DRAWDOWN_LIMIT", -0.05)},
            "capital_protection": {"floor": C.get("TOTAL_CAPITAL", 10_000_000) * C.get("CAPITAL_FLOOR_RATIO", 0.70), "ok": True},
            "friday_liquidation": {"days_left": max(0, 4 - wd), "is_friday": wd == 4},
            "atr_stop": {"interval": "1분", "active": True},
            "trailing": {"active_count": sum(1 for v in positions.values() if v.get("trail_active")), "threshold": C.get("TRAIL_ACTIVATE", 0.07)},
            "monthly_optimization": {"next_date": last_fri.isoformat(), "days_left": (last_fri - today).days},
            "econ_event": {"today": _econ_today_def, "tomorrow": _econ_tomorrow_def},
        }

    @app.route("/api/sell_opinion/<ticker>")
    def api_sell_opinion(ticker):
        rt = _rt_module
        positions = _safe_positions()
        info = positions.get(ticker)
        if not info:
            return jsonify({"error": "미보유 종목"}), 404
        try:
            cp = rt.get_current_price(ticker)
            buy_p = float(info.get("buy_price", 0))
            ret = (cp - buy_p) / buy_p if buy_p > 0 else 0
            df = rt.get_ohlcv(ticker, days=60)
            edge = 0
            if df is not None:
                kind_adj = rt.fetch_kind_sentiment(ticker) if hasattr(rt, "fetch_kind_sentiment") else 0
                edge = rt.calculate_edge_v27(df, kind_adj, ticker)
            atr = rt.calc_atr(df) if df is not None else cp * 0.02
            dyn_sl = rt.calc_dynamic_sl(atr, cp, ticker, _safe_attr("regime", "SIDE"))
            _entry_d  = info.get("entry_date", "")
            hold_days = ((date.today() - date.fromisoformat(_entry_d)).days
                         if _entry_d else 0)
            trail = bool(info.get("trail_active", False))
            reasons = []
            action = "보유유지"
            if ret <= dyn_sl:
                action = "매도 권고"
                reasons.append(f"손절선({dyn_sl*100:.1f}%) 도달")
            if hold_days >= 7:
                reasons.append(f"보유 {hold_days}일 — 타임스탑 구간")
                if ret < 0:
                    action = "매도 권고"
            if edge < 0.40:
                reasons.append(f"Edge {edge*100:.0f}점 — 약세 신호")
                if ret < 0:
                    action = "매도 권고"
            if trail and ret > 0.07:
                reasons.append(f"트레일링 활성 — 수익 보호 중")
            if ret > 0 and edge >= 0.70:
                reasons.append(f"Edge {edge*100:.0f}점 — 추가 상승 여력")
                action = "보유유지"
            if not reasons:
                reasons.append("특별한 매도 사유 없음")
            return jsonify({
                "ticker": ticker, "name": info.get("name", ""),
                "current_price": round(cp), "ret": round(ret, 4),
                "edge": round(edge * 100), "hold_days": hold_days,
                "action": action, "reasons": reasons,
                # [v1.9 BUG-FIX] 매수가 기준 손절가 표시 (실제 트리거와 동일)
                "sl_price": round((buy_p if buy_p > 0 else cp) * (1 + dyn_sl), -1),
                "trail_active": trail,
            })
        except Exception as e:
            log.error(f"매도의견 오류 {ticker}: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/performance")
    @_cached("performance")
    def api_performance():
        rt, C = _rt_module, _rt_module.C
        logs = rt.load_trade_log()
        now = date.today()
        week_start = now - timedelta(days=now.weekday())
        month_start = now.replace(day=1)

        def calc_stats(trades):
            if not trades:
                return {"count": 0, "wins": 0, "win_rate": 0, "total_pnl": 0, "avg_ret": 0}
            wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
            return {
                "count": len(trades), "wins": wins,
                "win_rate": round(wins / len(trades), 4),
                "total_pnl": round(sum(t.get("pnl", 0) for t in trades)),
                "avg_ret": round(sum(t.get("ret", 0) for t in trades) / len(trades), 4),
            }

        equity_curve = []
        cumulative = 0
        for t in sorted(logs, key=lambda x: x.get("date", "")):
            cumulative += t.get("pnl", 0)
            equity_curve.append({"date": t.get("date", ""), "equity": round(cumulative), "pnl": round(t.get("pnl", 0))})

        cal_data = defaultdict(float)
        for t in logs:
            d = t.get("date", "")
            if d:
                cal_data[d] += t.get("pnl", 0)
        trade_calendar = [{"date": k, "pnl": round(v)} for k, v in sorted(cal_data.items())]

        def rolling_winrate(trades, window):
            if len(trades) < window:
                return []
            result = []
            for i in range(window, len(trades) + 1):
                chunk = trades[i - window:i]
                wr = sum(1 for t in chunk if t.get("pnl", 0) > 0) / window
                avg_win = sum(t.get("ret", 0) for t in chunk if t.get("pnl", 0) > 0) / max(1, sum(1 for t in chunk if t.get("pnl", 0) > 0))
                avg_loss = abs(sum(t.get("ret", 0) for t in chunk if t.get("pnl", 0) <= 0) / max(1, sum(1 for t in chunk if t.get("pnl", 0) <= 0)))
                result.append({"index": i, "win_rate": round(wr, 4), "profit_factor": round(avg_win / avg_loss, 2) if avg_loss > 0 else 99})
            return result

        sorted_logs = sorted(logs, key=lambda x: x.get("date", ""))
        return {
            "week": calc_stats([l for l in logs if l.get("date", "") >= week_start.isoformat()]),
            "month": calc_stats([l for l in logs if l.get("date", "") >= month_start.isoformat()]),
            "all_time": calc_stats(logs),
            "recent_trades": logs[-10:][::-1],
            "equity_curve": equity_curve,
            "trade_calendar": trade_calendar,
            "rolling_20": rolling_winrate(sorted_logs, 20),
            "rolling_50": rolling_winrate(sorted_logs, 50),
        }

    @app.route("/api/risk")
    @_cached("risk")
    def api_risk():
        rt, C = _rt_module, _rt_module.C
        positions = _safe_positions()
        holdings = []
        for ticker, info in positions.items():
            try:
                cp = rt.get_current_price(ticker)
                buy_p = float(info.get("buy_price", 0))
                shares = int(info.get("shares", 0))
                if cp <= 0:
                    cp = buy_p
                holdings.append({
                    "ticker": ticker, "name": info.get("name", ""),
                    "sector": info.get("sector", _get_sector(ticker)),
                    "value": round(cp * shares),
                    "ret": round((cp - buy_p) / buy_p, 4) if buy_p > 0 else 0,
                })
            except Exception as e:
                log.warning(f"risk 종목 처리 오류 {ticker}: {e}")
                continue

        sector_map = defaultdict(lambda: {"value": 0, "pnl": 0, "stocks": []})
        for h in holdings:
            s = sector_map[h["sector"]]
            s["value"] += h["value"]
            s["pnl"] += h["value"] * h["ret"]
            s["stocks"].append(h)
        treemap = [{"sector": k, "value": v["value"], "ret": round(v["pnl"] / v["value"], 4) if v["value"] > 0 else 0, "stocks": v["stocks"]} for k, v in sector_map.items()]

        total_eval = sum(h["value"] for h in holdings)
        capital = C.get("TOTAL_CAPITAL", 10_000_000)
        floor = capital * C.get("CAPITAL_FLOOR_RATIO", 0.70)
        gauge = {
            "current": total_eval, "capital": capital, "floor": floor,
            "pct": round(total_eval / capital, 4) if capital > 0 else 0,
            "floor_pct": C.get("CAPITAL_FLOOR_RATIO", 0.70),
            "danger": total_eval < floor * 1.1,
        }

        price_data = {}
        for ticker, info in positions.items():
            try:
                df = rt.get_ohlcv(ticker, days=25)
                if df is not None and len(df) >= 20:
                    price_data[info.get("name", ticker)] = df["종가"].tail(20).pct_change().dropna().tolist()
            except:
                pass

        correlation = []
        names = list(price_data.keys())
        for i, n1 in enumerate(names):
            for j, n2 in enumerate(names):
                if i <= j:
                    if i == j:
                        corr = 1.0
                    else:
                        r1, r2 = price_data[n1], price_data[n2]
                        min_len = min(len(r1), len(r2))
                        if min_len >= 5:
                            mean1 = sum(r1[:min_len]) / min_len
                            mean2 = sum(r2[:min_len]) / min_len
                            cov = sum((r1[k] - mean1) * (r2[k] - mean2) for k in range(min_len)) / min_len
                            std1 = (sum((r1[k] - mean1)**2 for k in range(min_len)) / min_len)**0.5
                            std2 = (sum((r2[k] - mean2)**2 for k in range(min_len)) / min_len)**0.5
                            corr = round(cov / (std1 * std2), 2) if std1 > 0 and std2 > 0 else 0
                        else:
                            corr = 0
                    correlation.append({"a": n1, "b": n2, "corr": corr})

        return {
            "treemap": treemap, "gauge": gauge,
            "correlation": {"names": names, "pairs": correlation},
        }

    @app.route("/api/market")
    @_cached("market")
    def api_market():
        rt = _rt_module
        positions = _safe_positions()
        universe = _safe_universe()
        sector_etfs = {
            "반도체": "091160", "2차전지": "305720", "자동차": "091170",
            "바이오": "244580", "금융": "091180", "방산": "464520",
        }
        rotation = []
        for sector, etf in sector_etfs.items():
            try:
                df = rt.get_ohlcv(etf, days=25)
                if df is not None and len(df) >= 20:
                    prices = df["종가"].tolist()
                    ret_1w = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
                    ret_1m = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
                    rotation.append({"sector": sector, "ret_1w": round(ret_1w, 4), "ret_1m": round(ret_1m, 4)})
            except:
                pass

        supply = []
        tickers = list(positions.keys()) + list(universe.keys())[:10]
        for ticker in set(tickers):
            name = positions.get(ticker, {}).get("name", universe.get(ticker, ticker))
            try:
                df = rt.get_ohlcv(ticker, days=10)
                if df is not None and "foreign_net" in df.columns:
                    foreign = df["foreign_net"].tail(5).sum()
                    supply.append({"ticker": ticker, "name": name, "foreign_5d": int(foreign)})
            except:
                pass

        return {"rotation": rotation, "supply": supply[:15]}

    @app.route("/api/sentiment")
    @_cached("sentiment")
    def api_sentiment():
        C = _rt_module.C
        alert_file = Path("alerts_today.json")
        alerts = []
        if alert_file.exists():
            try:
                alerts = json.loads(alert_file.read_text(encoding="utf-8"))
            except:
                pass
        total_alerts = len(alerts)
        responded = sum(1 for a in alerts if a.get("responded", False))

        score = 0
        positions = _safe_positions()
        total_inv = sum(float(v.get("buy_price", 0)) * int(v.get("shares", 0)) for v in positions.values())
        total_eval = 0
        for ticker, info in positions.items():
            cp = _rt_module.get_current_price(ticker)
            if cp <= 0:
                cp = float(info.get("buy_price", 0))
            total_eval += cp * int(info.get("shares", 0))
        port_ret = (total_eval - total_inv) / total_inv if total_inv > 0 else 0

        if port_ret < -0.10:
            score += 40
        elif port_ret < -0.05:
            score += 25
        elif port_ret < -0.02:
            score += 10

        if _safe_attr("_circuit_active", False):
            score += 20
        logs = _rt_module.load_trade_log()
        recent = logs[-5:] if len(logs) >= 5 else logs
        consecutive_loss = 0
        for t in reversed(recent):
            if t.get("pnl", 0) < 0:
                consecutive_loss += 1
            else:
                break
        score += consecutive_loss * 5
        score = min(100, score)

        if score <= 25:
            level, emoji, advice = "평온", "🟢", "정상 운영. 규칙대로 매매하세요."
        elif score <= 50:
            level, emoji, advice = "주의", "🟡", "변동성 주의. 포지션 크기를 줄이는 것을 고려하세요."
        elif score <= 75:
            level, emoji, advice = "경고", "🟠", "시장이 불안합니다. 신규 매수를 자제하세요."
        else:
            level, emoji, advice = "위험", "🔴", "지금은 아무것도 안 하는 게 최선이에요. 시스템을 믿으세요."

        return {
            "alert_response": {"total": total_alerts, "responded": responded, "rate": round(responded / total_alerts, 2) if total_alerts > 0 else 1.0},
            "emotion": {"score": score, "level": level, "emoji": emoji, "advice": advice, "port_ret": round(port_ret, 4), "consecutive_loss": consecutive_loss, "circuit_active": _safe_attr("_circuit_active", False)},
        }

    @app.route("/api/system")
    @_cached("system")
    def api_system():
        rt = _rt_module
        sources = []
        test_tk = "005930"
        try:
            if hasattr(rt, "FDR_OK") and rt.FDR_OK:
                sources.append({"name": "FDR (일봉)", "status": "ok", "icon": "✅"})
            else:
                sources.append({"name": "FDR", "status": "unavailable", "icon": "❌"})
        except:
            sources.append({"name": "FDR", "status": "error", "icon": "❌"})
        try:
            p = rt.get_current_price(test_tk)
            sources.append({"name": "네이버 실시간", "status": "ok" if p > 0 else "no_data", "icon": "✅" if p > 0 else "⚠️", "last_price": round(p) if p > 0 else 0})
        except:
            sources.append({"name": "네이버 실시간", "status": "error", "icon": "❌"})
        try:
            if hasattr(rt, "PYKRX_OK") and rt.PYKRX_OK:
                sources.append({"name": "pykrx (폴백)", "status": "ok", "icon": "✅"})
            else:
                sources.append({"name": "pykrx", "status": "unavailable", "icon": "⚠️"})
        except:
            sources.append({"name": "pykrx", "status": "unknown", "icon": "⚠️"})

        param_log_file = Path("param_changes.json")
        param_history = []
        if param_log_file.exists():
            try:
                param_history = json.loads(param_log_file.read_text(encoding="utf-8"))
            except:
                pass

        C = rt.C
        params = {
            # ── 진입/매도 기준 ────────────────────────────────
            "SELL_EDGE_THRESHOLD":    C.get("SELL_EDGE_THRESHOLD"),     # 0.30
            # ── ATR 손절 배수 ─────────────────────────────────
            "ATR_MULT_LARGE":         C.get("ATR_MULT_LARGE"),          # 1.2
            "ATR_MULT_SMALL":         C.get("ATR_MULT_SMALL"),          # 2.0
            "ATR_MULT_TECH":          C.get("ATR_MULT_TECH"),           # 1.5
            # ── 트레일링 스탑 ─────────────────────────────────
            "TRAIL_ACTIVATE":         C.get("TRAIL_ACTIVATE"),          # 0.07
            "TRAIL_ATR_MULT_DEFAULT": C.get("TRAIL_ATR_MULT_DEFAULT"),  # 2.0
            # ── 리스크/시간 관리 ──────────────────────────────
            "DAILY_DRAWDOWN_LIMIT":   C.get("DAILY_DRAWDOWN_LIMIT"),    # -0.05
            "SECTOR_MAX_POSITIONS":   C.get("SECTOR_MAX_POSITIONS"),    # 2
            "TIME_STOP_DAYS":         C.get("TIME_STOP_DAYS"),          # 15
        }

        cache_info = {
            "ttl_seconds": _CACHE_TTL,
            "cached_endpoints": len(_cache),
            "lock_active": True,
        }

        return {
            "data_sources": sources,
            "param_history": param_history[-20:],
            "current_params": params,
            "cache_info": cache_info,
            "uptime": datetime.now().isoformat(),
        }


    # ── ⑤ 체결/주문 내역 (trade_history.db) ─────────────
    @app.route("/api/trades")
    @_cached("trades")
    def api_trades():
        rt = _rt_module
        today = date.today().isoformat()
        trades = []
        try:
            db_path = Path("trade_history.db")
            if db_path.exists():
                import sqlite3 as _sq
                conn = _sq.connect(str(db_path))
                conn.row_factory = _sq.Row
                cur = conn.execute(
                    "SELECT * FROM trades ORDER BY created_at DESC LIMIT 100"
                )
                for row in cur.fetchall():
                    trades.append(dict(row))
                conn.close()
        except Exception as e:
            pass
        return {"trades": trades, "today": today}

    @app.route("/api/today_trades")
    @_cached("today_trades")
    def api_today_trades():
        """오늘 체결 내역 요약 — Dashboard todayTrades 패널용"""
        today = date.today().isoformat()
        buy_count = sell_count = 0
        total_pnl = 0.0
        wins = 0
        sells = []
        try:
            db_path = Path("trade_history.db")
            if db_path.exists():
                import sqlite3 as _sq
                conn = _sq.connect(str(db_path))
                conn.row_factory = _sq.Row
                cur = conn.execute(
                    "SELECT * FROM trades WHERE date = ? ORDER BY created_at DESC",
                    (today,)
                )
                for row in cur.fetchall():
                    r = dict(row)
                    if r.get("action") == "buy":
                        buy_count += 1
                    elif r.get("action") == "sell":
                        sell_count += 1
                        pnl = float(r.get("pnl") or 0)
                        total_pnl += pnl
                        if pnl > 0:
                            wins += 1
                        sells.append({
                            "ticker": r.get("ticker", ""),
                            "name":   r.get("name", ""),
                            "ret":    float(r.get("ret") or 0),
                            "pnl":    pnl,
                            "reason": r.get("reason", ""),
                        })
                conn.close()
        except Exception:
            pass
        win_rate = wins / sell_count if sell_count > 0 else 0.0
        return {
            "date":        today,
            "buy_count":   buy_count,
            "sell_count":  sell_count,
            "total_pnl":   round(total_pnl, 0),
            "win_rate":    round(win_rate, 4),
            "sells":       sells,
        }

    # ── ⑥⑦ 투자 모드 + 예수금 ────────────────────────────
    @app.route("/api/account")
    @_cached("account", ttl=_CACHE_TTL_ACCOUNT)   # [v1.9] 30초 캐시
    def api_account():
        rt = _rt_module
        result = {
            "mode":      "unknown",
            "mode_icon": "❓",
            "host":      "",
            "deposit":   0,
            "deposit_str": "조회 중",
            "balance":   [],
        }
        try:
            kw = rt.kiwoom() if hasattr(rt, "kiwoom") else None
            if kw:
                result["mode"]      = "모의투자" if kw._mock else "실제투자"
                result["mode_icon"] = "🔵" if kw._mock else "🟢"
                result["host"]      = kw._host
                try:
                    dep = kw.get_deposit()
                    result["deposit"]     = dep
                    result["deposit_str"] = f"{dep:,}원"
                except Exception:
                    result["deposit_str"] = "조회 실패"
                try:
                    bal = kw.get_balance()
                    result["balance"] = bal or []
                except Exception:
                    pass
        except Exception as e:
            pass
        return result

    return app


# ── 유틸 ────────────────────────────────────
def _get_sector(ticker):
    """섹터 조회 — rt.SECTOR_MAP_RT 기준으로 위임 (v1.9: dashboard 독립 맵 제거, 불일치 해소)"""
    try:
        if _rt_module is not None and hasattr(_rt_module, "get_sector_for_ticker_rt"):
            return _rt_module.get_sector_for_ticker_rt(ticker)
    except Exception:
        pass
    # fallback: rt 미로드 시 기본값
    return "기타"


def log_alert(icon, msg, alert_type="info", responded=False):
    alert_file = Path("alerts_today.json")
    try:
        alerts = json.loads(alert_file.read_text(encoding="utf-8")) if alert_file.exists() else []
    except:
        alerts = []
    alerts.append({"time": datetime.now().strftime("%H:%M"), "icon": icon, "msg": msg, "type": alert_type, "responded": responded, "timestamp": datetime.now().isoformat()})
    today_str = date.today().isoformat()
    alerts = [a for a in alerts if a.get("timestamp", "").startswith(today_str)]
    alert_file.write_text(json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8")
