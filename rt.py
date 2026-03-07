"""
Edge Score v40.0 — 완전 통합 엔진
=====================================================
v40.0 패치:

  [버그수정-CRITICAL] ① prev_edge 단위 불일치 (check_holdings=정수↔scan_universe=float 교차오염)
    - 증상: Edge 급등/급락 알림 비정상 발동, 섹터 모멘텀 항상 보너스 적용
    - 수정: 정수(100배) 통일 + float 오염 자동 보정
  [버그수정] ② sl_price 표시 불일치 전체 수정
    - _status, _sell_opinion, close_report, friday_force_exit, morning_report
    - cp*(1+dyn_sl) → buy_p*(1+dyn_sl) (실제 트리거와 동일 기준)
  [버그수정] ③ _optimizer_preview 최소 건수 3→5 (apply와 통일)
  [버그수정] ④ get_order_fill ord_dt "" → 오늘 날짜 명시 (kiwoom_client.py)

v39.9 패치 (이전):

  [버그수정] ① sl_warn 리셋 조건 항상 True 수정 (접근 경보 매분 스팸)
    - 기존: _sl_price_check = cp*(1+dyn_sl)*1.02 → 항상 cp 미만 → 조건 항상 True
    - 결과: sl_warn 플래그 매 분 리셋 → 손절가 접근 경보 매분 재발송 스팸
    - 수정: ret vs dyn_sl 직접 비교 (ret > dyn_sl + 0.03 시에만 리셋)
    - 효과: 경보 1회 발송 후 ret이 dyn_sl보다 3% 회복됐을 때만 리셋

  [버그수정] ② 접근 경보 조건 수식 오류 수정 (ATR 손절폭 5% 초과 시 미발동)
    - 기존: sl_price_now = cp*(1+dyn_sl) → |dyn_sl|>5% 시 sl_price_now/0.95 < cp
            → cp <= sl_price_now*(1/0.95) 조건 절대 True 불가
    - 결과: ATR 손절폭 5~12% 구간에서 접근 경보 전혀 발동 안 됨
    - 수정: sl_price_now = buy_p*(1+dyn_sl) (매수가 기준 절대 손절가)
            조건: cp <= sl_price_now*1.05 and cp > sl_price_now
    - 효과: 실제 손절가의 5% 이내 접근 시 정상 경보

v39.8 패치:

  [버그수정] ① _dash_alert 필드명 불일치 수정
    - 기존: kind/message 저장 → Dashboard.jsx 알림 탭 무효화
    - 수정: type/icon/msg/timestamp 필드 추가 (Dashboard.jsx 호환)
    - kind→type 매핑: buy→success, sell→danger, warning→warning, info→info
    - kind→icon 매핑: buy→📈, sell→📤, warning→⚠️, info→ℹ️
    - 기존 kind/ticker 필드 유지 (하위 호환)

  [버그수정] ② monday_reset 스케줄 08:35→08:34 변경
    - 기존: daily_capital_sync(08:35)와 동시 실행
    - schedule은 등록 순서대로 실행 → daily_capital_sync 먼저 실행
    - monday_reset의 _pre_cap가 이미 sync된 값 → 주간 PnL 항상 0 오류
    - 수정: monday_reset 08:34 실행 → _pre_cap 전주 자본 정확히 캡처

  [개선] ③ scan_universe _dash_alert ticker 실제 코드 전달
    - 기존: ticker="" 하드코딩 → 대시보드 종목별 필터 불가
    - 수정: rows에 ticker 필드(인덱스6) 추가 → 실제 종목 코드 전달

v37.1 패치:

  [버그수정] 장외 보유현황 반복 스팸 수정
    - 장 시작 전(00:00~15:34) 전송 완전 차단
    - 내용 변화 없으면 전송 안 함 (hash 비교)
    - 장외 시간 0원 표시 수정 → 전일 종가 사용

v37.0 신규:

  [개선] ① 캐시 Purge — 유니버스 기반 정밀 정리
    - do_refresh_universe 실행 시 유니버스·보유에 없는 종목만 선택 삭제
    - 집합 차집합(O(n)) 처리 → datetime 순회 방식보다 효율적
    - edge_cache TTL 만료 항목도 동시 정리
    - 장기 가동 시 미사용 캐시 키 누적 방지

  [신규] ② Edge 계산 결과 캐시 (_edge_cache)
    - id(df) 기반 키: 같은 스캔 사이클 내 중복 계산 완전 차단
    - API 시그니처 변경 없이 calculate_edge_v27 내부에 투명 적용
    - ohlcv_cache 갱신 시 새 df 객체 → 자동 캐시 미스 → 재계산
    - scan_universe 1회 기준 종목당 최대 3회 → 1회로 감소
    - check_slippage_filter 내부 중복 호출도 자동 적중

v36.0 기능 전체 유지. 원래 v34 → v36 변경사항:

  [신규] ① 공휴일 자동 처리
    - pykrx 휴장일 달력 기반 → 공휴일 API 호출 자동 스킵
    - 삼일절·추석·설날 등 전 공휴일 자동 인식

  [신규] ② 수익 구간별 알림
    - +5% / +10% 중간 체크 알림
    - +15% 익절 신호 (기존 유지)
    - +20% 이상 트레일링 중 추가 알림

  [신규] ③ 당일 재진입 차단
    - 당일 손절·트레일링 청산 종목은 같은 날 추천 목록 제외
    - 연속 손절 방지

  [신규] ④ config.json 통합
    - 모든 파라미터를 config.json 하나로 관리
    - 백테스트·실시간 공통 사용
    - 파일 없으면 기본값으로 자동 생성

  [신규] ⑤ 분할 매수 추천
    - Edge 0.65 이상 → 1/3 진입 추천
    - Edge 0.75 이상 → 추가 1/3 추천
    - Edge 0.85 이상 → 나머지 1/3 추천

  [신규] ⑥ 켈리 공식 투자금액 추천
    - trade_log 승률·평균수익 기반 켈리 비율 자동 계산
    - /buy 시 추천 투자금액 자동 표시

  [신규] ⑦ 네트워크 복구 알림
    - 연결 끊김 감지 → 재연결 시 즉시 알림
    - 재연결 후 보유 종목 즉시 전체 체크 실행

  [신규] ⑧ 주간 성과 자동 집계
    - 매주 금요일 15:35 자동 발송
    - 주간 거래건수·승률·손익 / 누적 손익 / 다음주 주목 예고

  [유지] v34.0 전 기능 완전 유지

필요 라이브러리:
    pip3 install finance-datareader pykrx yfinance pandas numpy \
                 requests schedule beautifulsoup4
"""

import json, time, logging, hashlib, threading, sqlite3, re
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict
from io import StringIO

import numpy as np
import pandas as pd
import requests
import schedule

# ── 키움 REST API 클라이언트 ──────────────────────────────────
try:
    from kiwoom_client import get_client as _kiwoom_get_client
    KIWOOM_OK = True
except ImportError:
    KIWOOM_OK = False
    log_tmp = logging.getLogger("rt")
    log_tmp.warning("[키움] kiwoom_client.py 없음 — 주문 기능 비활성화")

def kiwoom():
    """키움 클라이언트 싱글턴 반환 (KIWOOM_OK=False면 None)"""
    if not KIWOOM_OK:
        return None
    try:
        return _kiwoom_get_client()
    except Exception as e:
        logging.getLogger("rt").error(f"[키움] 클라이언트 오류: {e}")
        return None

# 비상정지 플래그 (True면 모든 자동 주문 차단)
EMERGENCY_STOP = False

try:
    import FinanceDataReader as fdr
    FDR_OK = True
except ImportError:
    FDR_OK = False

# pykrx는 FDR 실패 시 폴백으로만 유지
try:
    from pykrx import stock as krx
    PYKRX_OK = True
except ImportError:
    PYKRX_OK = False

# 네이버 금융 크롤링 헤더 (외국인순매수 / 전종목 거래대금)
_NAVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
}

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False


try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

# ═══════════════════════════════════════════════════
# ④ config.json 통합 관리
# ═══════════════════════════════════════════════════

CONFIG_FILE = Path("config.json")

DEFAULT_CONFIG = {
    # ── 유니버스 ──────────────────────────────
    "AUTO_UNIVERSE_SIZE":  20,
    "AUTO_SCAN_POOL_SIZE": 40,

    # ── 장 시간 ───────────────────────────────
    "MARKET_OPEN":  "09:00",
    "MARKET_CLOSE": "15:30",

    # ── API 주기 ──────────────────────────────
    "HOLD_CHECK_MIN": 1,
    "SCAN_CHECK_MIN": 5,
    "CACHE_TTL_SEC":  300,

    # ── Edge 가중치 ───────────────────────────
    "W_MF":    0.40,
    "W_TECH":  0.30,
    "W_MOM":   0.30,
    "MF_CAP":  0.10,
    "TECH_CAP":0.02,

    # ── 슬리피지 필터 ─────────────────────────
    "SLIPPAGE_LARGE":        0.003,
    "SLIPPAGE_SMALL":        0.008,
    "SLIPPAGE_FILTER_RATIO": 3.0,

    # ── ATR 손절 ──────────────────────────────
    "ATR_MULT_LARGE": 1.2,
    "ATR_MULT_SMALL": 2.0,
    "ATR_MULT_TECH":  1.5,   # 기술대형주·기타 ATR 배수 (BT ATR_MULT_BY_CLUSTER 동일)
    "ATR_BEAR_MULT":  0.8,

    # ── 트레일링 스탑 ─────────────────────────
    "TRAIL_ACTIVATE":     0.07,
    # 트레일링 ATR 배수 — 클러스터별 (백테스트 v27 동일)
    "TRAIL_ATR_MULT_LARGE": 1.5,   # 대형가치주·금융주
    "TRAIL_ATR_MULT_SMALL": 2.5,   # 중소형성장주
    "TRAIL_ATR_MULT_DEFAULT": 2.0, # 미분류 기타
    "TRAIL_TIGHTEN_RET":  0.25,
    "TRAIL_TIGHTEN_MULT": 0.7,
    "TRAIL_BEAR_MULT":    0.8,

    # ── 익절 / 수익 알림 구간 ─────────────────
    "TAKE_PROFIT_FIXED":   0.15,
    "PROFIT_ALERT_STEPS": [0.05, 0.10, 0.20],  # 중간 알림 구간

    # ── 거래량 급증 ───────────────────────────
    "VOL_SURGE_MULT": 3.0,

    # ── Edge 급등 감지 ────────────────────────
    "EDGE_SURGE_THRESHOLD": 0.15,

    # ── 포트폴리오 리스크 ─────────────────────
    "EXPOSURE_CAP_BULL": 1.00,
    "EXPOSURE_CAP_SIDE": 0.70,
    "EXPOSURE_CAP_BEAR": 0.40,
    "CORR_HIGH_THRESHOLD": 0.70,   # 백테스트 v27 검증값으로 통일
    "ATR_STOP_MIN":        0.03,   # ATR 손절 최솟값 3%  (백테스트 동일)
    "ATR_STOP_MAX":        0.12,   # ATR 손절 최댓값 12% (백테스트 동일)
    "MAX_POSITION_RATIO":  0.30,   # 단일 종목 최대 비중 (백테스트 동일)
    "SELL_EDGE_THRESHOLD": 0.30,   # 보유 중 AI점수 이 이하 → 매도 경보 (백테스트 동일)
    # ── 투자원칙 ────────────────────────────────
    "MAX_HOLD_DAYS":         5,    # 원칙2: 최대 보유 거래일 (월~금)
    "FRIDAY_FORCE_EXIT":     True, # 원칙2: 금요일 강제 청산 알림
    "FRIDAY_HOLD_EDGE_THR":  0.45, # 원칙2: 금요일 보유 유지 AI점수 기준 (독립 변수)
    "WEEKLY_CAPITAL_RESET":  True, # 원칙1: 월요일 자본금 자동 재계산
    "CAPITAL_FLOOR_RATIO":   0.70, # 원칙1: 손실 시 자본 하방 보호 (초기의 70%)
    "TOTAL_CAPITAL": 10000000,

    # ── 분할 매수 구간 ────────────────────────
    "SPLIT_BUY_STEPS": [
        {"edge": 0.65, "ratio": 0.333, "label": "1/3"},
        {"edge": 0.75, "ratio": 0.333, "label": "추가 1/3"},
        {"edge": 0.85, "ratio": 0.334, "label": "나머지 1/3"},
    ],

    # ── 켈리 공식 ─────────────────────────────
    "KELLY_MAX_FRACTION": 0.25,  # 켈리 비율 상한 (전체 자본 대비)

    # ── ㉝~㊶ 신규 기능 ──────────────────────
    "RSI_DIVERGENCE_PENALTY": 0.08,
    "SECTOR_MOMENTUM_BONUS":  0.05,
    "SECTOR_MOMENTUM_PENALTY":0.03,
    "WEEKLY_TREND_REQUIRED":  True,
    "DAILY_DRAWDOWN_LIMIT":   -0.05,
    "CIRCUIT_BREAKER_ENABLED":True,
    "VOL_TARGET_DAILY":       0.02,
    "VOL_TARGET_ENABLED":     True,
    "TIME_STOP_DAYS":         15,
    "TIME_STOP_THRESHOLD":    0.02,
    "TIME_STOP_ENABLED":      True,
    "SECTOR_MAX_POSITIONS":   2,
    "SECTOR_LIMIT_ENABLED":   True,

    # ── 미매도 후속 분석 ──────────────────────
    "SL_FOLLOWUP_DELAY_MIN":  10,    # 손절 알림 후 N분 뒤 후속 분석
    "ECON_EVENT_EDGE_UPLIFT": 0.10,

    # ── KIND 공시 ─────────────────────────────
    "KIND_POS_KW": ["수주","계약","공급","양산","상향","돌파","흑자","호실적","특허","MOU","성장"],
    "KIND_NEG_KW": ["지연","하회","분쟁","소송","유상증자","적자","취소","리콜","조사","제재"],
    "KIND_EDGE_ADJ": 0.05,

    # ── 오류 알림 ─────────────────────────────
    "API_FAIL_THRESHOLD": 3,

    # ── 네트워크 체크 ─────────────────────────
    "NET_CHECK_URL":      "https://api.telegram.org",
    "NET_CHECK_INTERVAL": 60,   # 초

    # ── 경제 이벤트 (매수 제한 날짜 목록) ──────
    # 형식: ["2025-01-15", "2025-01-29", ...] — FOMC·CPI·금통위 등 주요 발표일
    "ECON_EVENTS_2025_2026": [],
}

_ENV_ONLY_KEYS = {"TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"}  # .env 전용 — config.json 불저장

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 개인정보 키는 config.json에서 제거
            for k in _ENV_ONLY_KEYS:
                saved.pop(k, None)
            # DEFAULT_CONFIG 기준으로 merge (새 키 = 기본값 보충)
            merged = DEFAULT_CONFIG.copy()
            merged.update(saved)
            # ── 신규 키 감지 → disk 자동 write-back ──────────────────────
            new_keys = [k for k in merged if k not in saved and k not in _ENV_ONLY_KEYS]
            if new_keys:
                save_data = {k: v for k, v in merged.items() if k not in _ENV_ONLY_KEYS}
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                log.info(f"[config] 신규 키 {len(new_keys)}개 자동 추가: {new_keys}")
            return merged
        except Exception as e:
            log.warning(f"[config] 로드 실패 ({e}) — 기본값 사용")
    # 파일 없으면 DEFAULT_CONFIG 전체로 생성 (env 전용 키 제외)
    save_data = {k: v for k, v in DEFAULT_CONFIG.items() if k not in _ENV_ONLY_KEYS}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    log.info("[config] config.json 생성됨 — 필요 시 수정 후 재시작")
    return DEFAULT_CONFIG.copy()

C = load_config()   # 전역 설정 객체

# ═══════════════════════════════════════════════════
# ★ 텔레그램 설정 — .env 파일에서만 로드
#   TELEGRAM_TOKEN   : BotFather 에서 발급한 봇 토큰
#   TELEGRAM_CHAT_ID : 본인 텔레그램 chat_id
# ═══════════════════════════════════════════════════

def _load_env_file():
    """스크립트 위치 기준 .env 로드"""
    env_path = Path(__file__).parent / ".env"
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        if env_path.exists():
            with open(env_path) as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _v = _line.split("=", 1)
                        os.environ.setdefault(_k.strip(), _v.strip())

import os
import os as _os_tg
_load_env_file()

TELEGRAM = {
    "token":   _os_tg.getenv("TELEGRAM_TOKEN",   ""),
    "chat_id": _os_tg.getenv("TELEGRAM_CHAT_ID", ""),
}

POSITIONS_FILE   = Path("positions.json")
UNIVERSE_FILE    = Path("universe_cache.json")
TRADE_LOG_FILE   = Path("trade_log.json")
TRADE_DB_FILE    = Path("trade_history.db")
ALERTS_FILE      = Path("alerts_today.json")   # 대시보드 /api/alerts 연동

# ── 수수료/세금 상수 ─────────────────────────────────
COMMISSION_RATE  = 0.00015   # 키움 매매수수료 (매수+매도 각 0.015%)
TAX_RATE         = 0.0020    # 증권거래세 (매도 시 0.20%)
# 실제 수익률 = 가격차 - 매수수수료 - 매도수수료 - 세금
# 실제 손익   = (매도가 - 매수가) * 주식수 - (매수금액 * COMMISSION) - (매도금액 * (COMMISSION + TAX))

INITIAL_UNIVERSE = {
    "005930": "삼성전자",   "000660": "SK하이닉스",
    "068270": "셀트리온",   "005380": "현대차",
    "000270": "기아",       "035420": "NAVER",
    "005490": "POSCO홀딩스","031980": "피에스케이홀딩스",
    "066570": "LG전자",     "112610": "씨에스윈드",
}

# [레거시] LARGE_CAP — Issue-4에서 클러스터 기반으로 완전 대체됨
LARGE_CAP = set()

# [Issue-4 수정] 슬리피지 클러스터 기반 매핑 추가 — BT SLIPPAGE_BY_CLUSTER와 동일 기준으로 통일
# [Fix-3] '기타' 클러스터 0.008 → 0.005 로 BT/OPT와 통일
SLIPPAGE_BY_CLUSTER_RT = {
    "대형가치주":   0.003,  # C["SLIPPAGE_LARGE"]와 동일
    "금융주":       0.003,
    "기술대형주":   0.003,
    "중소형성장주": 0.008,  # C["SLIPPAGE_SMALL"]와 동일
    "기타":         0.005,  # [Fix-3] BT/OPT 0.005와 통일 (이전: 0.008)
}

# ══════════════════════════════════════════════════
# 종목 클러스터별 Edge 가중치 (백테스트 v27 검증값)
# ══════════════════════════════════════════════════
# 종목 특성에 따라 MF/TECH/MOM 가중치를 다르게 적용
# - 대형가치주: 수급(MF) 중시
# - 중소형성장주: 모멘텀(MOM) 중시
# - 금융주: 수급(MF) 강조
CLUSTER_PARAMS = {
    "대형가치주": {
        "tickers":  {"005930","005380","105560","055550","032830","000270"},
        "W_MF": 0.40, "W_TECH": 0.30, "W_MOM": 0.30,
        "MF_CAP": 0.08, "TECH_CAP": 0.015,
    },
    "중소형성장주": {
        "tickers":  {"031980","035420","068270","051910","112610"},
        "W_MF": 0.30, "W_TECH": 0.25, "W_MOM": 0.45,
        "MF_CAP": 0.12, "TECH_CAP": 0.030,
    },
    "금융주": {
        # [Bug-2 수정] 105560·055550·032830은 대형가치주와 중복 → 첫매칭 반환으로 항상 대형가치주 분류
        # 중복 3종목 제거, 316140(우리금융)·138930(IBK기업은행)만 유지
        "tickers":  {"316140","138930"},
        "W_MF": 0.45, "W_TECH": 0.30, "W_MOM": 0.25,
        "MF_CAP": 0.08, "TECH_CAP": 0.012,
    },
    "기술대형주": {
        "tickers":  {"000660","066570","005490","373220"},
        "W_MF": 0.35, "W_TECH": 0.35, "W_MOM": 0.30,
        "MF_CAP": 0.10, "TECH_CAP": 0.020,
    },
}
# 클러스터 미분류 종목 기본값
# ㉞ 섹터 로테이션 매핑
SECTOR_MAP_RT = {
    "반도체":  {"005930","000660","031980"},
    "자동차":  {"005380","000270"},
    "금융":    {"105560","055550","032830","316140","138930"},
    "소재":    {"005490","373220"},
    "IT서비스":{"035420","068270"},
}

def get_sector_for_ticker_rt(ticker: str) -> str:
    for sector, tickers in SECTOR_MAP_RT.items():
        if ticker in tickers:
            return sector
    return "기타"

CLUSTER_DEFAULT = {"W_MF": 0.40, "W_TECH": 0.30, "W_MOM": 0.30,
                   "MF_CAP": 0.10, "TECH_CAP": 0.020}

def get_cluster_params(ticker: str) -> dict:
    """종목코드 → 해당 클러스터 파라미터 반환"""
    for params in CLUSTER_PARAMS.values():
        if ticker in params["tickers"]:
            return params
    return CLUSTER_DEFAULT

# ══════════════════════════════════════════════════
# 국면별 Edge 진입 기준 (백테스트 v27 검증값)
# ══════════════════════════════════════════════════
# BEAR 국면에서는 더 높은 점수가 나와야만 진입 허용
REGIME_EDGE_THRESHOLD = {
    "BULL": 0.55,   # 상승장: 완화된 기준
    "SIDE": 0.60,   # 보합장: 중간 기준
    "BEAR": 0.75,   # 하락장: 엄격한 기준
}

def get_regime_threshold(regime: str) -> float:
    return REGIME_EDGE_THRESHOLD.get(regime, 0.60)

# ══════════════════════════════════════════════════
# 로깅
# ══════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("realtime.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger("EdgeRT")
# [BUG-FIX] pykrx 내부 logger가 JSONDecodeError 로깅 시 Formatter 크래시 유발
# → CRITICAL로 완전 차단하여 연쇄 크래시 방지
for _noisy_logger in ["pykrx", "pykrx.stock", "pykrx.website",
                       "pykrx.website.krx", "pykrx.website.krx.market",
                       "urllib3", "requests",
                       "FinanceDataReader", "finance_datareader"]:
    logging.getLogger(_noisy_logger).setLevel(logging.CRITICAL)

# [BUG-FIX] pykrx가 root logger로 직접 logging.info(args, kwargs)를 호출하여
# Python logging Formatter가 % 포매팅 크래시. root logger에 필터를 추가하여 차단.
class _PykrxNoiseFilter(logging.Filter):
    def filter(self, record):
        # pykrx util.py에서 오는 잘못된 로그 메시지 차단
        try:
            if record.funcName == "wrapper" and "pykrx" in (record.pathname or ""):
                return False
            if record.funcName == "__init__" and "pykrx" in (record.pathname or ""):
                return False
        except:
            pass
        return True

logging.getLogger().addFilter(_PykrxNoiseFilter())

# ══════════════════════════════════════════════════
# 오류 추적기
# ══════════════════════════════════════════════════

class ErrorTracker:
    def __init__(self):
        self.fail_counts = defaultdict(int)
        self.alerted     = set()

    def record_fail(self, key: str):
        self.fail_counts[key] += 1
        cnt = self.fail_counts[key]
        if cnt >= C["API_FAIL_THRESHOLD"] and key not in self.alerted:
            tg(f"⚠️ <b>시스템 오류 발생</b>\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"🔴 {key} 연결에 문제가 생겼어요\n"
               f"   ({cnt}번 연속 실패)\n\n"
               f"📱 앱은 계속 실행 중이에요.\n"
               f"   계속 이 메시지가 오면 맥미니를 재시작해보세요.")
            self.alerted.add(key)

    def record_ok(self, key: str):
        if self.fail_counts[key] > 0:
            log.info(f"[{key}] 정상 복구")
        self.fail_counts[key] = 0
        self.alerted.discard(key)

err_tracker = ErrorTracker()

# ══════════════════════════════════════════════════
# 종목명 캐시
# ══════════════════════════════════════════════════

_name_cache: dict = {}
_fdr_listing_cache: dict = {}  # {market: DataFrame} — FDR 종목 리스트 캐시

def _get_fdr_listing(market: str = "KOSPI") -> "pd.DataFrame":
    """
    FDR StockListing 캐시 래퍼.
    반환: Code, Name 컬럼 보유 DataFrame (없으면 빈 DF)
    """
    if market in _fdr_listing_cache:
        return _fdr_listing_cache[market]
    df = pd.DataFrame()
    if FDR_OK:
        try:
            raw = fdr.StockListing(market)
            col_map = {}
            for c in raw.columns:
                cs = str(c).strip()
                if cs in ("Code", "Symbol", "종목코드"):  col_map[c] = "Code"
                elif cs in ("Name", "종목명"):             col_map[c] = "Name"
                elif cs in ("Marcap", "시가총액"):         col_map[c] = "Marcap"
            raw = raw.rename(columns=col_map)
            if "Code" in raw.columns and "Name" in raw.columns:
                extra = ["Marcap"] if "Marcap" in raw.columns else []
                df = raw[["Code", "Name"] + extra].copy()
                df["Code"] = df["Code"].astype(str).str.zfill(6)
                # 이름 캐시 사전 로딩
                for _, row in df.iterrows():
                    _name_cache[str(row["Code"])] = str(row["Name"])
            log.debug(f"FDR StockListing({market}): {len(df)}개")
        except Exception as e:
            log.debug(f"FDR StockListing: {e}")
    _fdr_listing_cache[market] = df
    return df


def resolve_ticker(query: str,
                   universe: dict = None,
                   positions: dict = None) -> tuple:
    """
    종목코드 또는 종목명 → (ticker, name) 반환
    - 6자리 숫자면 코드로 바로 처리
    - 종목명이면: positions → universe → _name_cache → pykrx 순서로 검색
    반환: (ticker, name) 또는 (None, None) 검색 실패 시
    """
    query = query.strip()

    # 숫자로만 구성 → 종목코드로 처리
    if query.isdigit():
        ticker = query.zfill(6)
        name   = resolve_name(ticker, universe, positions)
        return ticker, name

    # 종목명 검색 — 보유 종목 우선
    q_lower = query.lower()
    if positions:
        for tk, info in positions.items():
            nm = info.get("name", "")
            if nm and q_lower in nm.lower():
                return tk, nm

    # 유니버스 검색
    if universe:
        for tk, nm in universe.items():
            if nm and q_lower in nm.lower():
                return tk, nm

    # _name_cache 검색
    for tk, nm in _name_cache.items():
        if nm and q_lower in nm.lower():
            return tk, nm

    # FDR StockListing 전체 종목 검색 (최후 수단)
    listing = _get_fdr_listing("KOSPI")
    if not listing.empty:
        for _, row in listing.iterrows():
            tk = str(row["Code"])
            nm = str(row["Name"])
            if q_lower in nm.lower():
                return tk, nm

    # pykrx 폴백 (FDR 실패 시)
    if PYKRX_OK:
        try:
            tickers = krx.get_market_ticker_list(market="KOSPI")
            for tk in tickers:
                nm = krx.get_market_ticker_name(tk)
                if nm:
                    _name_cache[tk] = nm
                    if q_lower in nm.lower():
                        return tk, nm
        except Exception:
            pass

    return None, None

def resolve_name(ticker: str,
                 universe: dict = None,
                 positions: dict = None) -> str:
    if ticker in _name_cache:
        return _name_cache[ticker]
    name = ""
    if universe and ticker in universe:
        name = universe[ticker]
    if not name and positions and ticker in positions:
        name = positions[ticker].get("name", "")
    if not name:
        # FDR listing 캐시에서 먼저 조회
        listing = _get_fdr_listing("KOSPI")
        if not listing.empty:
            row = listing[listing["Code"] == ticker]
            if not row.empty:
                name = str(row.iloc[0]["Name"])
    if not name and PYKRX_OK:
        try:
            fetched = krx.get_market_ticker_name(ticker)
            if fetched:
                name = fetched
        except Exception:
            pass
    if not name:
        name = ticker
    _name_cache[ticker] = name
    return name

# ══════════════════════════════════════════════════
# 텔레그램 전송
# ══════════════════════════════════════════════════

_holiday_cache: dict = {}   # {year: set(date)} — 연도별 휴장일 캐시

def get_holidays(year: int) -> set:
    if year in _holiday_cache:
        return _holiday_cache[year]
    holidays = set()
    today     = date.today()

    def _parse_trading_days(raw) -> set:
        if raw is None or len(raw) == 0:
            return set()
        return set(pd.to_datetime(raw.index).date)

    def _build_holidays(trading_days: set) -> set:
        h = set()
        d = date(year, 1, 1)
        while d.year == year:
            # 오늘 이전 평일 중 거래일 목록에 없는 날 → 휴장
            if d.weekday() < 5 and d < today and d not in trading_days:
                h.add(d)
            d += timedelta(days=1)
        return h

    # ① FDR — 1순위
    if FDR_OK:
        try:
            raw = fdr.DataReader(
                "005930",
                f"{year}-01-01",
                f"{year}-12-31"
            )
            td = _parse_trading_days(raw)
            if td:
                holidays = _build_holidays(td)
                _holiday_cache[year] = holidays
                return holidays
        except Exception as e:
            log.debug(f"FDR 휴장일 조회: {type(e).__name__}")

    # ② pykrx — FDR 실패 시 폴백
    if PYKRX_OK:
        try:
            raw = krx.get_market_ohlcv_by_date(
                f"{year}0101", f"{year}1231", "005930"
            )
            td = _parse_trading_days(raw)
            if td:
                holidays = _build_holidays(td)
        except Exception as e:
            log.debug(f"pykrx 휴장일 조회: {type(e).__name__}")

    _holiday_cache[year] = holidays
    return holidays

def is_trading_day(d: date = None) -> bool:
    if d is None:
        d = date.today()
    if d.weekday() >= 5:
        return False
    # 오늘 당일: 데이터 소스에서 직접 당일 데이터 확인
    # → 데이터가 있으면 확정, 없으면(장 시작 전) holidays 캐시로 판단
    if d == date.today():
        ds_fdr = d.strftime("%Y-%m-%d")
        ds_krx = d.strftime("%Y%m%d")
        # FDR 직접 확인
        if FDR_OK:
            try:
                raw = fdr.DataReader("005930", ds_fdr, ds_fdr)
                if raw is not None and len(raw) > 0:
                    return True
            except Exception:
                pass
        # pykrx 직접 확인 (FDR 실패 시)
        if PYKRX_OK:
            try:
                raw = krx.get_market_ohlcv_by_date(ds_krx, ds_krx, "005930")
                if raw is not None and len(raw) > 0:
                    return True
            except Exception:
                pass
    holidays = get_holidays(d.year)
    return d not in holidays

def is_market_hour() -> bool:
    if not is_trading_day():
        return False
    now = datetime.now().strftime("%H:%M")
    return C["MARKET_OPEN"] <= now <= C["MARKET_CLOSE"]

def get_closed_df(df) -> object:
    """
    [New-C] 신호 생성 전용 — 확정 봉 데이터만 반환 (Look-ahead Bias 방지)

    pykrx는 장중에도 당일 미완성 봉을 마지막 행으로 반환합니다.
    이 봉을 포함해 Edge를 계산하면 백테스트(전일 종가 기준)와 다른 값이 나와
    검증된 파라미터가 실전에서 다르게 동작하는 구조적 괴리가 발생합니다.

    용도 구분:
      - 신호 생성 (scan_universe, 매수 판단):   get_closed_df(df) 사용  ← 봉 마감 보장
      - 체결 감시 (check_holdings, 손절·트레일링): df 원본 사용           ← 실시간 가격 필요
    """
    if df is None or len(df) == 0:
        return df
    if is_market_hour():
        # 장중: 마지막 행이 미완성 봉 → 제외하고 전일 확정봉까지만 사용
        return df.iloc[:-1] if len(df) > 1 else df
    # 장 외: 마지막 봉이 당일 확정봉 → 그대로 사용
    return df

def is_weekday() -> bool:
    return date.today().weekday() < 5

def today_str():
    return date.today().strftime("%Y%m%d")

# ══════════════════════════════════════════════════
# ⑦ 네트워크 모니터
# ══════════════════════════════════════════════════

class NetworkMonitor:
    """
    별도 스레드에서 네트워크 연결 상태를 주기적으로 체크합니다.
    끊김 → 복구 시 텔레그램 알림 + 보유 종목 즉시 체크 콜백 실행
    """
    def __init__(self, on_recover=None):
        self.on_recover  = on_recover   # 복구 시 실행할 콜백
        self.connected   = True
        self.running     = True

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        log.info("✅ 네트워크 모니터 시작")

    def _loop(self):
        while self.running:
            try:
                r = requests.get(C["NET_CHECK_URL"], timeout=5)
                ok = r.status_code < 500
            except:
                ok = False

            if not ok and self.connected:
                self.connected = False
                log.warning("🔴 네트워크 연결 끊김")

            elif ok and not self.connected:
                self.connected = True
                log.info("🟢 네트워크 재연결")
                tg("🔄 <b>인터넷 연결 복구!</b>\n"
                   "━━━━━━━━━━━━━━━━━━\n"
                   "잠시 끊겼다가 다시 연결됐어요.\n"
                   "내 주식 현황을 즉시 다시 확인할게요.")
                if self.on_recover:
                    try:
                        self.on_recover()
                    except Exception as e:
                        log.error(f"복구 콜백 오류: {e}")

            time.sleep(C["NET_CHECK_INTERVAL"])

# ══════════════════════════════════════════════════
# 데이터 캐시
# ══════════════════════════════════════════════════

_ohlcv_cache: dict = {}

# ══════════════════════════════════════════════════
# 네이버 금융 크롤링 — 외국인 순매수 / 전종목 거래대금
# ══════════════════════════════════════════════════

# 외국인 순매수 캐시 — 네이버 크롤링 빈도 제한 (IP 차단 방지)
_foreign_net_cache: dict = {}   # {ticker: {"data": pd.Series, "ts": float}}
_FOREIGN_NET_CACHE_TTL = 300    # 5분 캐시 (외국인 데이터는 일봉 단위라 빈번한 갱신 불필요)

def fetch_foreign_net_naver(ticker: str, days: int = 90) -> "pd.Series":
    """
    네이버 금융 외국인 매매 추이 페이지 크롤링 → 날짜 인덱스 pd.Series
    URL: https://finance.naver.com/item/frgn.naver?code={ticker}
    실패 시 빈 Series 반환 (get_ohlcv에서 거래량 대체값으로 폴백)
    """
    # ── 캐시 확인 ──
    now = time.time()
    cached = _foreign_net_cache.get(ticker)
    if cached and (now - cached["ts"]) < _FOREIGN_NET_CACHE_TTL:
        return cached["data"]

    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={ticker}"
        resp = requests.get(url, headers=_NAVER_HEADERS, timeout=8)
        resp.raise_for_status()

        tables = pd.read_html(StringIO(resp.text), thousands=",")
        for tbl in tables:
            # 날짜 컬럼 + 외국인순매수량 컬럼이 있는 테이블 찾기
            date_col = next((c for c in tbl.columns
                             if "날짜" in str(c) or "일자" in str(c)), None)
            net_col  = next((c for c in tbl.columns
                             if "순매수" in str(c) and "외국인" not in str(c)
                             or ("외국인" in str(c) and "순매수" in str(c))), None)
            if net_col is None:
                net_col = next((c for c in tbl.columns
                                if "순매수" in str(c)), None)
            if date_col is None or net_col is None:
                continue
            tbl = tbl[[date_col, net_col]].dropna()
            tbl = tbl[tbl[date_col].astype(str).str.match(r"\d{4}\.\d{2}\.\d{2}")]
            if len(tbl) == 0:
                continue
            tbl.index = pd.to_datetime(tbl[date_col].astype(str), format="%Y.%m.%d")
            series = pd.to_numeric(
                tbl[net_col].astype(str).str.replace(",", "").str.replace("+", ""),
                errors="coerce"
            ).fillna(0)
            series.index = tbl.index
            result = series.sort_index().tail(days)
            _foreign_net_cache[ticker] = {"data": result, "ts": time.time()}
            return result
    except Exception as e:
        log.debug(f"네이버 외국인순매수 [{ticker}]: {e}")
    empty = pd.Series(dtype=float)
    _foreign_net_cache[ticker] = {"data": empty, "ts": time.time()}
    return empty


def fetch_kospi_top_by_volume_naver(pool_size: int = 60) -> dict:
    """
    네이버 금융 시가총액 페이지 → 거래대금 기준 상위 종목 dict
    URL: https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={n}
    반환: {ticker_6digit: 거래대금(int)}
    실패 시 빈 dict 반환
    """
    if not BS4_OK:
        log.debug("네이버 거래대금: BeautifulSoup 미설치")
        return {}
    results = {}
    try:
        for page in range(1, 6):  # 최대 5페이지(~100종목)
            url = (f"https://finance.naver.com/sise/sise_market_sum.naver"
                   f"?sosok=0&page={page}")
            resp = requests.get(url, headers=_NAVER_HEADERS, timeout=8)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("table.type_2 tr")
            found_this_page = 0
            for row in rows:
                a_tag = row.select_one('a[href*="code="]')
                if not a_tag:
                    continue
                m = re.search(r"code=(\d{6})", a_tag["href"])
                if not m:
                    continue
                ticker = m.group(1)
                cells  = row.select("td")
                # 컬럼 순서: 종목명, 현재가, 전일비, 등락률, 액면가,
                #            시가총액, 상장주식수, 외국인비율, 거래량, PER, ROE
                # 거래량: index 8 (0-base)
                if len(cells) >= 9:
                    try:
                        vol_raw = cells[8].get_text(strip=True).replace(",", "")
                        results[ticker] = int(vol_raw) if vol_raw.isdigit() else 0
                        found_this_page += 1
                    except Exception:
                        pass
            if found_this_page == 0:  # 빈 페이지 → 종료
                break
            if len(results) >= pool_size:
                break
            time.sleep(0.2)  # 과도한 요청 방지
    except Exception as e:
        log.debug(f"네이버 거래대금 크롤링: {e}")

    # 거래대금 내림차순 정렬 후 pool_size개 반환
    return dict(
        sorted(results.items(), key=lambda x: -x[1])[:pool_size]
    )


def get_ohlcv(ticker: str, days: int = 90):
    now    = time.time()
    cached = _ohlcv_cache.get(ticker)
    # 장중 60초 / 장외 3600초(1시간) — 일봉은 하루에 한 번만 바뀜
    eff_ttl = 60 if is_market_hour() else 3600
    if cached and (now - cached["ts"]) < eff_ttl:
        return cached["df"]

    df = None
    start_dt = date.today() - timedelta(days=int(days * 1.8))

    # ── ① 키움 API (최우선) — 429 rate limit 시 자동 폴백 ────
    _kw_rl_key = "_kiwoom_ohlcv_rl"
    _kw_rl_until = _ohlcv_cache.get(_kw_rl_key, {}).get("until", 0)
    if now < _kw_rl_until:
        log.debug(f"[키움] 일봉 rate limit 대기 중 ({int(_kw_rl_until - now)}초 남음)")
    else:
        try:
            kw = kiwoom()
            if kw:
                rows = kw.get_ohlcv(ticker, days=days)
                if rows and len(rows) >= 20:
                    df = pd.DataFrame({
                        "종가":   [r["close"]  for r in rows],
                        "고가":   [r["high"]   for r in rows],
                        "저가":   [r["low"]    for r in rows],
                        "거래량": [r["volume"] for r in rows],
                    }, index=pd.to_datetime([r["date"] for r in rows]))
                    try:
                        fnet = fetch_foreign_net_naver(ticker, days)
                        df["foreign_net"] = (
                            fnet.reindex(df.index).fillna(0) if len(fnet) > 0 else 0
                        )
                    except Exception:
                        df["foreign_net"] = 0
                    err_tracker.record_ok(f"kiwoom_ohlcv:{ticker}")
                    log.debug(f"[키움] 일봉 {ticker} {len(df)}행")
        except Exception as e:
            emsg = str(e)
            if "429" in emsg or "허용된 요청 개수를 초과" in emsg or "return_code" in emsg:
                # 429: 1시간 rate limit 설정
                _ohlcv_cache[_kw_rl_key] = {"until": now + 3600}
                log.warning(f"[키움] 일봉 429 rate limit → 1시간 FDR 폴백 전환")
            else:
                log.debug(f"[키움] 일봉 실패 {ticker}: {type(e).__name__}")
            err_tracker.record_fail(f"kiwoom_ohlcv:{ticker}")

    # ── ② FDR (키움 실패 시) ─────────────────────────────────
    if df is None and FDR_OK:
        try:
            start_s = start_dt.strftime("%Y-%m-%d")
            raw = fdr.DataReader(ticker, start_s)
            if raw is not None and len(raw) >= 20:
                raw.index = pd.to_datetime(raw.index)
                cm = {}
                for c in raw.columns:
                    cs = str(c).strip()
                    if cs in ("Close", "종가"):       cm[c] = "종가"
                    elif cs in ("High", "고가"):      cm[c] = "고가"
                    elif cs in ("Low", "저가"):       cm[c] = "저가"
                    elif cs in ("Volume", "거래량"):  cm[c] = "거래량"
                raw = raw.rename(columns=cm)
                need = [c for c in ["종가", "고가", "저가", "거래량"]
                        if c in raw.columns]
                if len(need) == 4:
                    df = raw[need].copy().tail(days)
                    try:
                        fnet = fetch_foreign_net_naver(ticker, days)
                        df["foreign_net"] = (
                            fnet.reindex(df.index).fillna(0) if len(fnet) > 0 else 0
                        )
                    except Exception:
                        df["foreign_net"] = 0
                    err_tracker.record_ok(f"fdr:{ticker}")
        except Exception as e:
            log.debug(f"FDR [{ticker}]: {type(e).__name__}")
            err_tracker.record_fail(f"fdr:{ticker}")

    # ── ③ pykrx — FDR 실패 시 폴백 ─────────────────────────
    if df is None and PYKRX_OK:
        try:
            start_s = start_dt.strftime("%Y%m%d")
            end_s   = today_str()
            raw     = krx.get_market_ohlcv_by_date(start_s, end_s, ticker)
            if raw is not None and len(raw) >= 20:
                raw.index   = pd.to_datetime(raw.index)
                raw.columns = [str(c).strip() for c in raw.columns]
                cm = {}
                for c in raw.columns:
                    if "종가" in c or c == "Close":      cm[c] = "종가"
                    elif "고가" in c or c == "High":     cm[c] = "고가"
                    elif "저가" in c or c == "Low":      cm[c] = "저가"
                    elif "거래량" in c or c == "Volume": cm[c] = "거래량"
                raw  = raw.rename(columns=cm)
                need = [c for c in ["종가", "고가", "저가", "거래량"]
                        if c in raw.columns]
                df   = raw[need].copy()
                try:
                    fnet = fetch_foreign_net_naver(ticker, days)
                    df["foreign_net"] = (
                        fnet.reindex(df.index).fillna(0) if len(fnet) > 0 else 0
                    )
                except Exception:
                    df["foreign_net"] = 0
                df = df.tail(days)
                err_tracker.record_ok(f"pykrx:{ticker}")
        except Exception as e:
            log.debug(f"pykrx [{ticker}]: {type(e).__name__}")
            err_tracker.record_fail(f"pykrx:{ticker}")

    # ── ④ yfinance — 최종 폴백 ──────────────────────────────
    if df is None and YF_OK:
        try:
            sym = f"{ticker}.KS"
            raw = yf.download(sym, period="3mo", progress=False, auto_adjust=True)
            if not raw.empty:
                raw.columns = [c[0] if isinstance(c, tuple) else c
                               for c in raw.columns]
                df = pd.DataFrame({
                    "종가":        raw["Close"].values.flatten(),
                    "고가":        raw["High"].values.flatten(),
                    "저가":        raw["Low"].values.flatten(),
                    "거래량":      raw["Volume"].values.flatten(),
                    "foreign_net": 0,
                }, index=raw.index).tail(days)
                log.debug(f"[{ticker}] yfinance(15분지연) 사용")
        except Exception as e:
            log.debug(f"yfinance [{ticker}]: {e}")

    if df is not None:
        _ohlcv_cache[ticker] = {"df": df, "ts": now}
    return df

# Edge 계산 결과 캐시
# key: (id(df), round(kind_adj,4)) — df 객체 동일성 기반
# ohlcv_cache 갱신 → 새 df id → 자동 캐시 미스 → 재계산
_edge_cache: dict = {}

def _purge_edge_cache() -> int:
    """TTL 만료된 edge_cache 항목 제거. 제거된 개수 반환."""
    now    = time.time()
    ttl    = C["CACHE_TTL_SEC"]
    stale  = [k for k, v in _edge_cache.items()
              if (now - v["ts"]) >= ttl]
    for k in stale:
        _edge_cache.pop(k, None)
    return len(stale)

def invalidate_cache(ticker: str = None):
    """ohlcv_cache 무효화. ticker 미지정 시 전체 삭제."""
    if ticker:
        _ohlcv_cache.pop(ticker, None)
        _foreign_net_cache.pop(ticker, None)
        # 해당 ticker df의 edge_cache는 id 기반이라 자동 미스 처리됨
    else:
        _ohlcv_cache.clear()
        _edge_cache.clear()
        _foreign_net_cache.clear()

# ══════════════════════════════════════════════════
# 실시간 현재가 — 네이버 금융 크롤링 1순위 (장중 실시간)
# ══════════════════════════════════════════════════
_realtime_price_cache: dict = {}   # {ticker: {"price": float, "ts": float}}
_REALTIME_CACHE_TTL  = 10          # 10초 캐시 (장중 빠른 반응)
_data_source_status: dict = {"source": "초기화중", "ok": False}

def _fetch_naver_realtime(ticker: str) -> float:
    """네이버 금융 실시간 체결가 크롤링 (지연 없음)"""
    try:
        if not BS4_OK: return 0.0
        url  = f"https://finance.naver.com/item/sise.naver?code={ticker}"
        resp = requests.get(url, headers=_NAVER_HEADERS, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        tag  = soup.select_one("#_nowVal")
        if tag:
            price = float(tag.get_text(strip=True).replace(",", ""))
            if price > 0:
                _data_source_status["source"] = "네이버(실시간)"
                _data_source_status["ok"] = True
                return price
    except Exception as e:
        log.debug(f"[네이버 실시간] {ticker}: {type(e).__name__}")
    return 0.0

def get_current_price(ticker: str) -> float:
    """실시간 현재가 — ① 키움 API ② 네이버 크롤링 ③ FDR/pykrx 일봉(폴백)"""
    now    = time.time()
    cached = _realtime_price_cache.get(ticker)
    if cached and (now - cached["ts"]) < _REALTIME_CACHE_TTL:
        return cached["price"]
    price = 0.0

    # ── ① 키움 API (최우선) ──────────────────────────────────
    if is_market_hour():
        try:
            kw = kiwoom()
            if kw:
                _kp = kw.get_price(ticker)
                if _kp and _kp > 0:
                    price = float(_kp)
                    _data_source_status["source"] = "키움(실시간)"
                    _data_source_status["ok"]     = True
        except Exception as _e:
            log.debug(f"[키움] 현재가 실패 {ticker}: {_e}")

    # ── ② 네이버 크롤링 (키움 실패 시) ──────────────────────
    if price <= 0 and is_market_hour():
        price = _fetch_naver_realtime(ticker)
        if price > 0:
            _data_source_status["source"] = "네이버(실시간)"
            _data_source_status["ok"]     = True

    # ── ③ FDR/pykrx 일봉 종가 (최종 폴백) ───────────────────
    if price <= 0:
        df = get_ohlcv(ticker, days=5)
        if df is not None and len(df) > 0:
            price = float(df["종가"].iloc[-1])
            if _data_source_status["source"] == "초기화중":
                _data_source_status["source"] = "FDR(일봉)"
                _data_source_status["ok"]     = True

    if price > 0:
        _realtime_price_cache[ticker] = {"price": price, "ts": now}
    return price

# ══════════════════════════════════════════════════
# v27 Edge 계산
# ══════════════════════════════════════════════════

def calculate_edge_v27(df, kind_adj: float = 0.0,
                       ticker: str = None) -> float:
    """
    Edge 계산 — 백테스트 v27 로직 완전 동기화
    ticker 지정 시 종목 클러스터별 가중치 자동 적용
    """
    # ── Edge 캐시 확인 ──
    _key = (id(df), round(kind_adj, 4), ticker or "")
    _now = time.time()
    _hit = _edge_cache.get(_key)
    if _hit and (_now - _hit["ts"]) < C["CACHE_TTL_SEC"]:
        return _hit["edge"]

    # ── 클러스터 파라미터 결정 ──
    cp = get_cluster_params(ticker) if ticker else CLUSTER_DEFAULT

    try:
        if ("foreign_net" in df.columns
                and df["foreign_net"].abs().sum() > 0):
            mf_raw = (df["foreign_net"].rolling(5).sum()
                      / df["거래량"].rolling(20).mean()
                      ).fillna(0).clip(0, cp["MF_CAP"]) / cp["MF_CAP"]
        else:
            vol_ma = df["거래량"].rolling(20).mean()
            mf_raw = ((df["거래량"] / vol_ma).fillna(1)
                      .clip(0.5, 3).apply(lambda x: (x - 0.5) / 2.5))
        mf = float(mf_raw.iloc[-1])

        ma20     = df["종가"].rolling(20).mean()
        tech_raw = ((df["종가"] - ma20) / ma20
                    ).fillna(0).clip(0, cp["TECH_CAP"]) / cp["TECH_CAP"]
        tech = float(tech_raw.iloc[-1])

        delta = df["종가"].diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rsi   = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        mom   = float(
            rsi.rolling(min(60, len(df))).rank(pct=True).fillna(0.5).iloc[-1]
        )

        edge = cp["W_MF"] * mf + cp["W_TECH"] * tech + cp["W_MOM"] * mom + kind_adj
        # 참고: BT는 calc_ensemble_weights()로 동적 가중치 적용
        #       RT는 고정 클러스터 가중치 사용 (실시간 단순화)
        #       → 금요일 보유 유지 판단(FRIDAY_HOLD_EDGE_THR)은
        #         BT 기준보다 ±0.03 안전 마진을 두고 설정할 것 권장
        result = round(float(np.clip(edge, 0.0, 1.0)), 4)
        _edge_cache[_key] = {"edge": result, "ts": _now}
        return result
    except:
        return 0.5

# ══════════════════════════════════════════════════
# 슬리피지 필터
# ══════════════════════════════════════════════════

# [Fix-6] BT check_slippage_filter와 tp 계산 구조 근사화
# BT tp = cp * (1 + sigma * beta_eff * bias) 이지만 RT는 beta 계산 없이 sigma*bias만 사용
# → 동일 종목 동일 날짜에 filter 통과/차단 결과 불일치 가능
# 수정: 클러스터별 대표 beta 근사값을 곱해 BT 수준에 근사
_BETA_APPROX_BY_CLUSTER = {
    "대형가치주":   0.90,   # 방어주 성격 → 시장 대비 낮은 베타
    "금융주":       0.85,   # 금리 민감 but 코스피 상관 낮음
    "기술대형주":   1.10,   # 코스피 이상 움직임
    "중소형성장주": 1.30,   # 고베타 성장주
    "기타":         1.00,   # 시장 평균
}

def check_slippage_filter(df, ticker: str) -> tuple:
    try:
        # [Issue-4 수정] LARGE_CAP 집합 기반 → 클러스터 기반 슬리피지로 통일 (BT와 일관성 확보)
        _cluster = get_cluster_name(ticker)
        slip     = SLIPPAGE_BY_CLUSTER_RT.get(_cluster, C["SLIPPAGE_SMALL"])
        cp       = float(df["종가"].iloc[-1])
        sigma    = float(df["종가"].pct_change().rolling(20).std().iloc[-1])
        edge     = calculate_edge_v27(df, 0.0, ticker)
        bias     = (edge - 0.5) * 2
        # [Fix-6] 클러스터별 beta 근사값 반영 — BT tp = cp*(1+sigma*beta*bias)에 근사
        beta_approx = _BETA_APPROX_BY_CLUSTER.get(_cluster, 1.0)
        tp       = cp * (1 + sigma * beta_approx * bias)
        if tp <= cp:
            return False, 0.0, slip * 2 * C["SLIPPAGE_FILTER_RATIO"]
        expected = (tp - cp) / cp
        required = slip * 2 * C["SLIPPAGE_FILTER_RATIO"]
        return expected >= required, round(expected, 4), round(required, 4)
    except:
        return False, 0.0, 0.0

# ══════════════════════════════════════════════════
# ⑤ 분할 매수 추천
# ══════════════════════════════════════════════════

def get_split_buy_advice(ticker: str, edge: float,
                         total_capital: float) -> str:
    """
    Edge 점수와 총 자본 기준으로 분할 매수 단계 추천 문자열 반환
    """
    steps = C["SPLIT_BUY_STEPS"]
    advice = []
    for step in steps:
        if edge >= step["edge"]:
            amt = total_capital * step["ratio"]
            advice.append(f"  {step['label']} 진입 가능 (약 {amt:,.0f}원)")

    if not advice:
        return ""

    lines = ["💡 <b>분할 매수 가이드</b>"]
    for a in advice[:1]:   # 현재 단계만 표시
        lines.append(a)

    # 다음 단계 예고
    remaining = [s for s in steps if edge < s["edge"]]
    if remaining:
        next_step = remaining[0]
        lines.append(f"  다음 단계: Edge {next_step['edge']} 도달 시 {next_step['label']}")

    return "\n".join(lines)

# ══════════════════════════════════════════════════
# ⑥ 켈리 공식 투자금액 추천
# ══════════════════════════════════════════════════

def get_remaining_trading_days() -> int:
    """
    오늘 포함 이번 주 남은 거래일 수 반환
    월=5, 화=4, 수=3, 목=2, 금=1
    토/일은 다음 주 월요일 기준 5 반환
    """
    wd = date.today().weekday()
    mapping = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 5, 6: 5}
    return mapping.get(wd, 5)


def is_friday_hold_ok(ticker: str, info: dict, cp: float) -> tuple:
    """
    수정된 투자원칙 2 — 금요일 보유 유지 여부 판단
    반환: (보유유지여부, 이유)
    조건: 수익 중 AND (트레일링 발동 중 OR AI점수 ≥ SELL_EDGE_THRESHOLD * 1.5)
    """
    try:
        buy_p = float(info.get("buy_price", cp))
        if buy_p <= 0 or cp <= 0:
            return False, "가격 데이터 없음"

        ret = (cp - buy_p) / buy_p
        if ret <= 0:
            return False, f"손실 중 ({ret:+.2%}) — 청산 필요"

        # 조건 ①: 트레일링 발동 중
        if info.get("trail_active"):
            return True, f"수익 중 ({ret:+.2%}) + 🔺트레일링 자동 추적 중"

        # 조건 ②: AI점수 충분히 높음
        #   FRIDAY_HOLD_EDGE_THR: SELL_EDGE_THRESHOLD와 완전히 독립된 변수
        #   옵티마이저가 실거래 기반으로 각각 별도 최적화함
        df = get_ohlcv(ticker, days=60)
        if df is not None:
            kind_adj = fetch_kind_sentiment(ticker)
            edge     = calculate_edge_v27(df, kind_adj, ticker)
            # BT와 RT의 Edge 계산 방식 차이(앙상블 vs 고정) 보완:
            # 경계값 근처 오판 방지를 위해 RT에서는 FRIDAY_HOLD_EDGE_THR - 0.03을 실효 기준으로 사용
            hold_thr     = C.get("FRIDAY_HOLD_EDGE_THR", 0.45)
            hold_thr_eff = hold_thr - 0.03   # RT-BT 앙상블 차이 안전 마진
            if edge >= hold_thr_eff:
                return True, (f"수익 중 ({ret:+.2%}) + AI점수 {int(edge*100)}점 "
                              f"(기준 {int(hold_thr_eff*100)}점 / 설정 {int(hold_thr*100)}점)")
            else:
                return False, (f"수익 중이나 AI점수 {int(edge*100)}점 낮음 "
                               f"(기준 {int(hold_thr_eff*100)}점)")

        return False, "데이터 없음 — 청산 권고"
    except Exception as e:
        return False, f"판단 오류: {e}"


def _save_cfg_direct(key: str, val) -> None:
    """config.json 단일 키 직접 저장 (monitor 없이 사용)"""
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
        cfg[key] = val
        CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.error(f"config 저장 실패: {e}")


def calc_effective_capital(positions: dict) -> float:
    """
    투자원칙 1 — 동적 실질 자본 계산
    = 현금(총자본 - 원투자금) + 보유 주식 평가금
    손실 시 CAPITAL_FLOOR_RATIO 이하로 안 내려감 (하방 보호)
    """
    try:
        base     = C.get("TOTAL_CAPITAL", 10_000_000)
        floor    = base * C.get("CAPITAL_FLOOR_RATIO", 0.70)
        invested = 0.0
        stock_val = 0.0
        for ticker, info in positions.items():
            buy_p  = float(info.get("buy_price", 0))
            shares = int(info.get("shares", 0))
            if buy_p <= 0 or shares <= 0:
                continue
            cp = get_current_price(ticker)
            if cp <= 0:
                cp = buy_p
            invested  += buy_p * shares
            stock_val += cp * shares
        cash  = max(base - invested, 0)
        total = cash + stock_val
        return max(total, floor)
    except Exception as e:
        log.error(f"calc_effective_capital 오류: {e}")
        return C.get("TOTAL_CAPITAL", 10_000_000)


def calc_kelly_amount(total_capital: float) -> float:
    """
    trade_log 기반 켈리 비율 계산 → 추천 투자금액 반환
    켈리 공식: f = (bp - q) / b
      b = 평균 수익 / 평균 손실 비율
      p = 승률
      q = 1 - p
    """
    try:
        logs   = load_trade_log()
        closed = [t for t in logs if t.get("exit_price", 0) > 0]
        if len(closed) < 5:   # 데이터 부족 시 기본 20%
            return total_capital * 0.20

        rets  = [(t["exit_price"] - t["buy_price"]) / t["buy_price"]
                 for t in closed]
        wins  = [r for r in rets if r > 0]
        loses = [abs(r) for r in rets if r < 0]

        if not wins or not loses:
            return total_capital * 0.20

        p     = len(wins) / len(rets)
        q     = 1 - p
        b     = np.mean(wins) / np.mean(loses)
        kelly = (b * p - q) / b

        # 절반 켈리 + 상한 적용 (과도한 집중 방지)
        kelly = max(0, kelly * 0.5)
        kelly = min(kelly, C["KELLY_MAX_FRACTION"])
        # 단일 종목 최대 비중 제한 (백테스트 MAX_POSITION_RATIO 동일 적용)
        kelly = min(kelly, C.get("MAX_POSITION_RATIO", 0.30))

        return round(total_capital * kelly, -4)   # 만원 단위 반올림
    except:
        return total_capital * 0.20

# ══════════════════════════════════════════════════
# KIND 공시 감성 분석
# ══════════════════════════════════════════════════

_kind_cache: dict = {}

def fetch_kind_sentiment(ticker: str) -> float:
    today = today_str()
    cached = _kind_cache.get(ticker)
    if cached and cached[1] == today:
        return cached[0]
    if not BS4_OK:
        return 0.0
    try:
        resp = requests.get(
            "https://kind.krx.co.kr/disclosure/todaydisclosure.do",
            params={
                "method": "searchTodayDisclosureMain",
                "currentPage": 1, "maxResults": 20,
                "marketType": "kospi", "searchFilter": "T",
                "lstCrtDt": today, "isuCd": ticker, "typeCode": "",
            },
            timeout=5,
        )
        soup   = BeautifulSoup(resp.text, "html.parser")
        titles = [r.get_text(strip=True)
                  for r in soup.select("td.disclosure-title")]
        pos = sum(1 for t in titles for kw in C["KIND_POS_KW"] if kw in t)
        neg = sum(1 for t in titles for kw in C["KIND_NEG_KW"] if kw in t)
        adj = 0.0 if pos + neg == 0 else round(
            C["KIND_EDGE_ADJ"] * (pos - neg) / (pos + neg), 4)
        _kind_cache[ticker] = (adj, today)
        if adj != 0.0:
            log.info(f"  KIND [{ticker}] {len(titles)}건 → 보정 {adj:+.3f}")
        return adj
    except Exception as e:
        log.debug(f"KIND [{ticker}]: {e}")
        return 0.0

# ══════════════════════════════════════════════════
# 거래량 급증
# ══════════════════════════════════════════════════

def check_vol_surge(df, ticker: str, name: str,
                    held_info: dict = None) -> str:
    """거래량 급증 알람 — 보유 여부·AI점수·설명 통합"""
    try:
        if "거래량" not in df.columns:
            return ""
        vol_today = float(df["거래량"].iloc[-1])
        vol_ma20  = float(df["거래량"].rolling(20).mean().iloc[-1])
        if vol_ma20 <= 0:
            return ""
        ratio = vol_today / vol_ma20
        if ratio < C["VOL_SURGE_MULT"]:
            return ""
        cp   = float(df["종가"].iloc[-1])
        edge = calculate_edge_v27(df, 0.0, ticker)

        if held_info:
            buy_p  = float(held_info.get("buy_price", cp))
            shares = int(held_info.get("shares", 0))
            ret    = (cp - buy_p) / buy_p if buy_p > 0 else 0
            r_icon = "✅" if ret >= 0 else "🔴"
            hold_line = (f"📌 현재 {shares:,}주 보유 중  "
                         f"{r_icon} 수익률 {ret:+.2%}")
        else:
            hold_line = "📌 관심 종목  |  미보유"

        return (f"📢 <b>{name} 거래량 급증!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"지금 이 주식이 평소보다\n"
                f"<b>{ratio:.1f}배</b> 더 많이 거래되고 있어요\n"
                f"\n"
                f"💰 현재 가격: {cp:,.0f}원\n"
                f"🤖 AI 점수: {int(edge*100)}점\n"
                f"{hold_line}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💡 큰 뉴스나 공시가 있을 때 이런 현상이 생겨요\n"
                f"   네이버 금융에서 뉴스를 확인해보세요\n"
                f"   좋은 뉴스면 더 오를 수 있고\n"
                f"   나쁜 뉴스면 빨리 내릴 수 있어요")
    except:
        pass
    return ""

# ══════════════════════════════════════════════════
# ATR / 손절선 / 트레일링
# ══════════════════════════════════════════════════

def calc_atr(df, period: int = 14) -> float:
    try:
        cp_fallback = float(df["종가"].iloc[-1]) if df is not None and len(df) > 0 else 1.0
        if "고가" in df.columns and "저가" in df.columns:
            prev = df["종가"].shift(1)
            tr   = pd.concat([
                df["고가"] - df["저가"],
                (df["고가"] - prev).abs(),
                (df["저가"] - prev).abs(),
            ], axis=1).max(axis=1)
            val = float(tr.rolling(period).mean().iloc[-1])
            if np.isnan(val) or val <= 0:
                raise ValueError("ATR nan")
            return val
    except:
        pass
    try:
        sigma = float(df["종가"].pct_change().rolling(period).std().iloc[-1])
        if np.isnan(sigma) or sigma <= 0:
            sigma = 0.02
        return sigma * float(df["종가"].iloc[-1]) * 1.5
    except:
        return cp_fallback * 0.02   # 최후 fallback: 현재가의 2%

def get_trail_atr_mult(ticker: str) -> float:
    """클러스터에 따라 트레일링 ATR 배수 반환 — 백테스트 TRAIL_ATR_MULT 동일"""
    cluster = get_cluster_name(ticker)
    if cluster in ("대형가치주", "금융주"):
        return C.get("TRAIL_ATR_MULT_LARGE", 1.5)
    elif cluster == "중소형성장주":
        return C.get("TRAIL_ATR_MULT_SMALL", 2.5)
    else:
        return C.get("TRAIL_ATR_MULT_DEFAULT", 2.0)


def get_cluster_name(ticker: str) -> str:
    """종목코드 → 클러스터명 반환"""
    for name, params in CLUSTER_PARAMS.items():
        if ticker in params.get("tickers", set()):
            return name
    return "기타"


# ATR 손절 배수 — 클러스터별 (백테스트 ATR_MULT_BY_CLUSTER와 동일)
# LARGE_CAP 여부 대신 클러스터 기반으로 통일하여 RT-BT 일관성 확보
# [H-2 수정] '기술대형주' 클러스터 ATR 배수 BT 기준으로 통일
# BT CLUSTER_PARAMS에 '기술대형주' 존재 (ATR 1.5, TRAIL 2.0, SLIP 0.003)
#
# [Fix-2] 정적 딕셔너리 → 동적 함수로 변환
# 이전: 모듈 로드 시 C 값으로 고정 → Optimizer 자동 최적화 후 config.json 갱신해도
#       ATR_MULT_LARGE/SMALL이 반영되지 않고 기동 당시 값으로 계속 동작
# 수정: 호출 시마다 C.get()으로 읽음 → 런타임 config 변경 즉시 반영
def get_atr_mult_rt(cluster: str) -> float:
    """클러스터별 ATR 배수 반환 — config 변경 즉시 반영 (동적)
    기술대형주/기타: ATR_MULT_TECH (기본값 1.5, BT ATR_MULT_BY_CLUSTER와 동일)
    """
    _map = {
        "대형가치주":   C.get("ATR_MULT_LARGE", 1.2),
        "금융주":       C.get("ATR_MULT_LARGE", 1.2),
        "중소형성장주": C.get("ATR_MULT_SMALL", 2.0),
        "기술대형주":   C.get("ATR_MULT_TECH",  1.5),  # config 동적 반영
        "기타":         C.get("ATR_MULT_TECH",  1.5),  # BT 기본값 1.5
    }
    return _map.get(cluster, C.get("ATR_MULT_TECH", 1.5))

def calc_dynamic_sl(atr: float, price: float,
                    ticker: str, regime: str) -> float:
    try:
        if price <= 0 or np.isnan(atr) or np.isnan(price) or atr <= 0:
            return -C.get("ATR_STOP_MIN", 0.03) * 2  # 안전 기본값
        # 클러스터 기반 ATR 배수 결정 (백테스트 ATR_MULT_BY_CLUSTER 동일)
        cluster = get_cluster_name(ticker)
        mult = get_atr_mult_rt(cluster)  # [Fix-2] 동적 함수 → config 변경 즉시 반영
        if regime == "BEAR":
            mult *= C.get("ATR_BEAR_MULT", 0.8)
        raw = -(atr / price) * mult
        # 백테스트 ATR_STOP_MIN/MAX 동일 적용 (3%~12% 범위 제한)
        sl_min = -C.get("ATR_STOP_MAX", 0.12)  # 최대 손실 제한
        sl_max = -C.get("ATR_STOP_MIN", 0.03)  # 최소 손실 보장
        val = float(max(sl_min, min(sl_max, raw)))
        return val if not np.isnan(val) else -C.get("ATR_STOP_MIN", 0.03) * 2
    except:
        return -0.07

def calc_entry_guide(df, ticker: str, regime: str) -> dict:
    """
    매수 적정가 범위 / 목표가 / 손절가 계산
    반환: {entry_low, entry_high, target, sl_price, sl_pct}
    """
    try:
        cp  = float(df["종가"].iloc[-1])
        atr = calc_atr(df)
        if np.isnan(atr) or atr <= 0:
            atr = cp * 0.02

        # 매수 적정가: 현재가 ~ 현재가 - 0.5 ATR (눌림목 대기)
        entry_high = cp
        entry_low  = round(cp - atr * 0.5, -1)   # 10원 단위

        # 목표가: Edge 기반 sigma × bias
        sigma = float(df["종가"].pct_change().rolling(20).std().iloc[-1])
        if np.isnan(sigma) or sigma <= 0: sigma = 0.02
        edge  = calculate_edge_v27(df, 0.0, ticker)
        bias  = (edge - 0.5) * 2
        target = round(cp * (1 + sigma * max(bias, 0.1) * 3), -1)

        # 손절가
        dyn_sl   = calc_dynamic_sl(atr, cp, ticker, regime)
        sl_price = round(cp * (1 + dyn_sl), -1)
        if np.isnan(sl_price) or sl_price <= 0:
            sl_price = round(cp * 0.93, -1)

        return {
            "cp":         cp,
            "entry_low":  entry_low,
            "entry_high": entry_high,
            "target":     target,
            "sl_price":   sl_price,
            "sl_pct":     dyn_sl,
            "atr":        atr,
        }
    except:
        return None

def calc_switch_value(held_info: dict, held_df, held_ticker: str,
                      cand: dict, cand_df, regime: str) -> dict:
    """
    보유 종목 → 추천 종목 교체 시 순이득 계산 + 부분교체 비율 결정

    Edge 점수 차이에 따른 교체 비율:
      차이 0.05~0.10 → 30% 부분 교체  (신중)
      차이 0.10~0.20 → 50% 부분 교체  (적극)
      차이 0.20 이상 → 70% 대부분 교체 (강력)
      보유 종목이 손실 중 + 차이 크면 → 전량 교체 고려
    """
    try:
        held_kind = fetch_kind_sentiment(held_ticker)
        held_edge = calculate_edge_v27(held_df, held_kind, held_ticker) if held_df is not None else 0.5
        cand_edge = cand["edge"]

        # [Issue-4 수정] LARGE_CAP 집합 기반 → 클러스터 기반 슬리피지로 통일
        slip_held = SLIPPAGE_BY_CLUSTER_RT.get(get_cluster_name(held_ticker), C["SLIPPAGE_SMALL"])
        slip_cand = SLIPPAGE_BY_CLUSTER_RT.get(get_cluster_name(cand["ticker"]), C["SLIPPAGE_SMALL"])
        switch_cost = slip_held * 1.5 + slip_cand

        edge_gain = cand_edge - held_edge
        worth     = edge_gain > switch_cost * 3.0

        # ── 부분 교체 비율 결정 ──────────────────────────────
        held_ret  = float(held_info.get("ret", 0))   # 현재 수익률
        buy_p     = float(held_info.get("buy_price", 0))
        shares    = int(held_info.get("shares", 0))

        # Edge 차이 + 수익률 상태에 따라 비율 결정
        if edge_gain >= 0.20 and held_ret < -0.03:
            # 강한 신호 + 손실 중 → 전량 교체
            sell_ratio   = 1.0
            ratio_label  = "전량"
            ratio_reason = "추천 종목이 훨씬 유리하고 보유 종목이 손실 중이에요"
        elif edge_gain >= 0.20:
            # 강한 신호 + 수익 중 → 70%
            sell_ratio   = 0.7
            ratio_label  = "70%"
            ratio_reason = "추천 종목이 크게 유리해요. 70%만 옮기고 나머지는 유지해요"
        elif edge_gain >= 0.10:
            # 중간 신호 → 50%
            sell_ratio   = 0.5
            ratio_label  = "50%"
            ratio_reason = "절반만 옮겨서 리스크를 분산해요"
        else:
            # 약한 신호 → 30%
            sell_ratio   = 0.3
            ratio_label  = "30%"
            ratio_reason = "차이가 크지 않아요. 30%만 시험적으로 옮겨보세요"

        # 실제 주식 수 계산
        sell_shares = max(1, int(shares * sell_ratio))
        sell_amt    = sell_shares * buy_p
        buy_amt     = sell_amt * (1 - slip_held)   # 매도 후 실수령액

        guide = calc_entry_guide(cand_df, cand["ticker"], regime)
        entry_str  = (f"{guide['entry_low']:,.0f}~{guide['entry_high']:,.0f}원"
                      if guide else f"{cand['price']:,.0f}원")
        target_str = f"{guide['target']:,.0f}원" if guide else "-"
        sl_str     = f"{guide['sl_price']:,.0f}원" if guide else "-"

        # 매수 가능 주수 계산
        cand_price = guide["entry_high"] if guide else cand["price"]
        buy_shares = int(buy_amt / cand_price) if cand_price > 0 else 0

        return {
            "worth_switch": worth,
            "held_edge":    held_edge,
            "cand_edge":    cand_edge,
            "edge_gain":    edge_gain,
            "switch_cost":  switch_cost,
            "sell_ratio":   sell_ratio,
            "sell_shares":  sell_shares,
            "sell_amt":     sell_amt,
            "buy_shares":   buy_shares,
            "buy_amt":      buy_amt,
            "ratio_label":  ratio_label,
            "ratio_reason": ratio_reason,
            "entry_str":    entry_str,
            "target_str":   target_str,
            "sl_str":       sl_str,
        }
    except:
        return {"worth_switch": False}

def update_trailing(pos: dict, cp: float,
                    atr: float, regime: str) -> tuple:
    buy_p = float(pos.get("buy_price", 0))
    if buy_p <= 0:
        return False, ""
    ret = (cp - buy_p) / buy_p

    if not pos.get("trail_active") and ret >= C["TRAIL_ACTIVATE"]:
        pos["trail_active"] = True
        pos["peak_price"]   = cp
        log.info(f"  🔺 트레일링 활성화 ({ret:+.1%})")

    if not pos.get("trail_active"):
        return False, ""

    if cp > pos.get("peak_price", 0):
        pos["peak_price"] = cp

    peak_ret = (pos["peak_price"] - buy_p) / buy_p
    # 클러스터별 트레일링 ATR 배수 적용 (백테스트 TRAIL_ATR_MULT 동일)
    ticker   = pos.get("ticker", "")
    mult     = get_trail_atr_mult(ticker)
    if peak_ret >= C.get("TRAIL_TIGHTEN_RET", 0.25): mult *= C.get("TRAIL_TIGHTEN_MULT", 0.7)
    if regime  == "BEAR":                            mult *= C.get("TRAIL_BEAR_MULT",    0.8)

    atr_ratio          = atr / pos["peak_price"] if pos["peak_price"] > 0 else 0.02
    gap                = pos["peak_price"] * atr_ratio * mult
    pos["trail_price"] = pos["peak_price"] - gap

    if cp <= pos["trail_price"]:
        return True, (f"트레일링스탑 발동\n"
                      f"  고점 {pos['peak_price']:,.0f}원 → 현재 {cp:,.0f}원\n"
                      f"  간격 {gap:,.0f}원 ({regime}국면)")
    return False, ""

# ══════════════════════════════════════════════════
# 포트폴리오 리스크
# ══════════════════════════════════════════════════

def check_portfolio_risk(positions: dict, regime: str) -> list:
    warnings = []
    if not positions:
        return warnings

    total_invested = sum(float(info.get("amount", 0))
                        for info in positions.values())
    cap_key = f"EXPOSURE_CAP_{regime}"
    cap     = C.get(cap_key, 0.70)
    used    = total_invested / C["TOTAL_CAPITAL"] if C["TOTAL_CAPITAL"] > 0 else 0
    if used > cap:
        warnings.append(
            f"⚠️ <b>투자 비중이 너무 높아요!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"현재 투자 비중: {used:.0%}\n"
            f"권장 비중: {cap:.0%} 이하  ({_regime_plain(regime)})\n"
            f"총 투자금: {total_invested:,.0f}원\n"
            f"💡 일부 매도로 현금 비중을 높여보세요."
        )

    tickers = list(positions.keys())
    if len(tickers) >= 2:
        dfs = {}
        for tk in tickers:
            df = get_ohlcv(tk, days=60)
            if df is not None:
                dfs[tk] = df["종가"].pct_change().dropna()
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                tk1, tk2 = tickers[i], tickers[j]
                if tk1 not in dfs or tk2 not in dfs: continue
                try:
                    s1  = dfs[tk1]; s2 = dfs[tk2]
                    idx = s1.index.intersection(s2.index)
                    if len(idx) < 20: continue
                    corr = float(s1[idx].corr(s2[idx]))
                    if corr >= C["CORR_HIGH_THRESHOLD"]:
                        nm1 = positions[tk1].get("name", tk1)
                        nm2 = positions[tk2].get("name", tk2)
                        warnings.append(
                            f"⚠️ <b>함께 움직이는 종목 주의</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"{nm1}  ↔  {nm2}\n"
                            f"이 두 종목은 같은 방향으로 움직이는 경향이 {corr:.0%}예요.\n"
                            f"한 종목이 떨어지면 다른 종목도 떨어질 수 있어요.\n"
                            f"💡 두 종목을 동시에 보유하면 위험이 커질 수 있어요."
                        )
                except:
                    continue
    return warnings

# ══════════════════════════════════════════════════
# 국면 판단
# ══════════════════════════════════════════════════

def calc_regime_from_kospi() -> str:
    start = (date.today() - timedelta(days=40)).strftime("%Y-%m-%d")

    def _classify(series: "pd.Series") -> str:
        if series is None or len(series) < 20:
            return "SIDE"
        ma = series.rolling(20).mean().iloc[-1]
        cp = series.iloc[-1]
        if cp > ma * 1.02: return "BULL"
        if cp < ma * 0.98: return "BEAR"
        return "SIDE"

    # ① FDR — KOSPI 지수 (심볼: KS11)
    if FDR_OK:
        try:
            raw = fdr.DataReader("KS11", start)
            if raw is not None and len(raw) >= 20:
                col = next((c for c in raw.columns
                            if str(c) in ("Close", "종가")), None)
                if col:
                    return _classify(raw[col])
        except Exception as e:
            log.debug(f"FDR 국면 계산: {type(e).__name__}")

    # ② pykrx 폴백
    if PYKRX_OK:
        try:
            start_k = (date.today() - timedelta(days=40)).strftime("%Y%m%d")
            raw     = krx.get_index_ohlcv_by_date(start_k, today_str(), "1001")
            if raw is None or len(raw) < 5:
                raise ValueError("pykrx KOSPI 데이터 부족")
            raw.index   = pd.to_datetime(raw.index)
            raw.columns = [str(c).strip() for c in raw.columns]
            col = next((c for c in raw.columns
                        if "종가" in c or c == "Close"), None)
            if col:
                return _classify(raw[col])
        except Exception as e:
            log.debug(f"pykrx 국면 계산: {type(e).__name__}")

    return "SIDE"

# ══════════════════════════════════════════════════
# 거래 내역 기록
# ══════════════════════════════════════════════════

def load_trade_log() -> list:
    if TRADE_LOG_FILE.exists():
        try:
            with open(TRADE_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []

def _db_init():
    """SQLite trade_history.db 테이블 초기화 (없으면 생성)"""
    try:
        con = sqlite3.connect(TRADE_DB_FILE, check_same_thread=False)
        con.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT,
                ticker      TEXT,
                name        TEXT,
                action      TEXT,
                price       REAL,
                shares      INTEGER,
                pnl         REAL,
                ret         REAL,
                reason      TEXT,
                mode        TEXT DEFAULT 'unknown',
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        # 기존 DB 마이그레이션: mode 컬럼 없으면 추가
        try:
            con.execute("ALTER TABLE trades ADD COLUMN mode TEXT DEFAULT 'unknown'")
            con.commit()
            log.info("[DB] mode 컬럼 마이그레이션 완료")
        except Exception:
            pass  # 이미 있으면 무시
        con.commit()
        con.close()
    except Exception as e:
        log.error(f"[DB] 초기화 실패: {e}")

_db_init()

def _db_insert(entry: dict):
    """거래 내역 SQLite에 삽입"""
    try:
        action = entry.get("action", "")
        # date: exit_date(매도) → entry_date(매수) → today 순서로 fallback
        _date = (entry.get("exit_date")
                 or entry.get("entry_date")
                 or str(date.today()))
        # price: 매도는 체결가(exit_price), 매수는 매수가(buy_price)
        if action == "sell":
            _price = float(entry.get("exit_price") or entry.get("sell_price") or 0)
        else:
            _price = float(entry.get("buy_price") or 0)
        con = sqlite3.connect(TRADE_DB_FILE, check_same_thread=False)
        # mode 결정: entry에 명시 → kiwoom 상태 → 'unknown'
        _mode = entry.get("mode", None)
        if _mode is None:
            try:
                _kw = kiwoom()
                _mode = "mock" if (_kw and _kw._mock) else "real"
            except Exception:
                _mode = "unknown"
        con.execute("""
            INSERT INTO trades (date, ticker, name, action, price, shares, pnl, ret, reason, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            _date,
            entry.get("ticker", ""),
            entry.get("name", ""),
            action,
            _price,
            int(entry.get("shares", 0)),
            float(entry.get("pnl", 0)),
            float(entry.get("ret", 0)),
            entry.get("reason", ""),
            _mode,
        ))
        con.commit()
        con.close()
    except Exception as e:
        log.error(f"[DB] 삽입 실패: {e}")

def db_query_today() -> list:
    """오늘 체결 내역 조회 (list of dict)"""
    try:
        con = sqlite3.connect(TRADE_DB_FILE, check_same_thread=False)
        con.row_factory = sqlite3.Row
        cur = con.execute(
            "SELECT * FROM trades WHERE date = ? ORDER BY id",
            (str(date.today()),)
        )
        rows = [dict(r) for r in cur.fetchall()]
        con.close()
        return rows
    except Exception as e:
        log.error(f"[DB] 오늘 조회 실패: {e}")
        return []

def db_daily_summary(target_date: str = None) -> dict:
    """일별 요약 (매수건수, 매도건수, 실현손익, 승률)"""
    if target_date is None:
        target_date = str(date.today())
    try:
        con = sqlite3.connect(TRADE_DB_FILE, check_same_thread=False)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(
            "SELECT * FROM trades WHERE date = ?", (target_date,)
        ).fetchall()]
        con.close()
        buys  = [r for r in rows if r.get("action") == "buy"]
        sells = [r for r in rows if r.get("action") == "sell"]
        pnls  = [r["pnl"] for r in sells if r.get("pnl")]
        wins  = [p for p in pnls if p > 0]
        return {
            "buy_count":  len(buys),
            "sell_count": len(sells),
            "total_pnl":  sum(pnls),
            "win_rate":   len(wins) / len(pnls) if pnls else 0,
        }
    except Exception as e:
        log.error(f"[DB] 일별 요약 실패: {e}")
        return {"buy_count": 0, "sell_count": 0, "total_pnl": 0, "win_rate": 0}

def append_trade_log(entry: dict):
    # [설계 의도] positions 저장 직후 기록 → 앱 재시작 시 포지션-로그 일관성 보장
    # 키움 주문 실패 시 로그는 남지만 positions도 이미 업데이트된 상태이므로 허용
    # JSON 백업
    logs = load_trade_log()
    logs.append(entry)
    try:
        with open(TRADE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        log.error(f"거래로그 저장 실패: {e}")
    # SQLite 동시 기록
    _db_insert(entry)

def calc_performance(logs: list = None) -> dict:
    if logs is None:
        logs = load_trade_log()
    closed = [t for t in logs if t.get("exit_price", 0) > 0]
    if not closed:
        return {"count":0, "win_rate":0, "avg_ret":0,
                "total_pnl":0, "avg_days":0}
    rets  = [(t["exit_price"] - t["buy_price"]) / t["buy_price"]
             for t in closed]
    pnls  = [t.get("pnl", 0) for t in closed]
    days  = [t.get("hold_days", 0) for t in closed]
    wins  = sum(1 for r in rets if r > 0)
    return {
        "count":    len(closed),
        "win_rate": wins / len(closed),
        "avg_ret":  float(np.mean(rets)),
        "total_pnl":float(sum(pnls)),
        "avg_days": float(np.mean(days)) if days else 0,
    }

# ══════════════════════════════════════════════════
# 포지션 저장/로드
# ══════════════════════════════════════════════════

def load_positions() -> dict:
    if POSITIONS_FILE.exists():
        try:
            with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # 0주 또는 매수가 0인 잘못된 항목 자동 제거
            cleaned = {tk: info for tk, info in raw.items()
                       if int(info.get("shares", 0)) > 0
                       and float(info.get("buy_price", 0)) > 0}
            if len(cleaned) != len(raw):
                removed = len(raw) - len(cleaned)
                log.warning(f"⚠️ positions.json: 잘못된 항목 {removed}개 자동 제거")
                # 정리된 내용 즉시 저장
                with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
                    json.dump(cleaned, f, ensure_ascii=False, indent=2, default=str)
            return cleaned
        except:
            pass
    return {}

def save_positions(pos: dict):
    try:
        with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(pos, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        log.error(f"포지션 저장 실패: {e}")

# ══════════════════════════════════════════════════
# 유니버스
# ══════════════════════════════════════════════════

def load_universe() -> dict:
    if UNIVERSE_FILE.exists():
        try:
            with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return INITIAL_UNIVERSE.copy()

def save_universe(univ: dict):
    try:
        with open(UNIVERSE_FILE, "w", encoding="utf-8") as f:
            json.dump(univ, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"유니버스 저장 실패: {e}")

def _notify_on_fill(order_no: str, ticker: str, name: str,
                    action: str, qty: int, price: int,
                    buy_price: float = 0.0,
                    reason: str = ""):
    """
    백그라운드에서 체결 확인 후 텔레그램 알림 발송
    action: 'buy' or 'sell'
    buy_price: 매도 시 손익 계산용 매수단가
    최대 60초간 3초 간격으로 폴링
    """
    def _wait_and_notify():
        kw = kiwoom()
        if not kw:
            return
        _mode   = "모의" if kw._mock else "실계좌"
        _icon   = "🔵" if kw._mock else "🟢"
        _action = "매수" if action == "buy" else "매도"

        for _ in range(20):  # 3초 × 20 = 최대 60초
            time.sleep(3)
            try:
                fill = kw.get_order_fill(order_no, ticker)
                if fill and fill.get("filled"):
                    cntr_qty = fill["cntr_qty"]
                    cntr_uv  = fill["cntr_uv"]
                    cntr_tm  = fill.get("cntr_tm", "")
                    amount   = cntr_qty * cntr_uv

                    if action == "buy":
                        msg = (
                            f"{_icon} <b>[{_mode}] 매수 체결 완료!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"📌 종목: <b>{name}</b> ({ticker})\n"
                            f"💰 체결가: {cntr_uv:,}원\n"
                            f"📦 체결수량: {cntr_qty:,}주\n"
                            f"💵 체결금액: {amount:,}원\n"
                            f"⏰ 체결시간: {cntr_tm}"
                        )
                    else:
                        # 실제 체결가 기준으로 손익 재계산
                        _pnl = (cntr_uv - buy_price) * cntr_qty if buy_price > 0 else 0
                        _ret = (cntr_uv - buy_price) / buy_price if buy_price > 0 else 0
                        pnl_icon = "✅" if _pnl >= 0 else "🔴"
                        msg = (
                            f"{_icon} <b>[{_mode}] 매도 체결 완료!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"📌 종목: <b>{name}</b> ({ticker})\n"
                            f"{('🔔 사유: ' + reason + chr(10)) if reason else ''}"
                            f"💰 체결가: {cntr_uv:,}원\n"
                            f"📦 체결수량: {cntr_qty:,}주\n"
                            f"💵 체결금액: {amount:,}원\n"
                            f"{pnl_icon} 손익: {_pnl:+,.0f}원 ({_ret:+.2%})\n"
                            f"⏰ 체결시간: {cntr_tm}"
                        )
                    tg(msg)
                    return
            except Exception as e:
                log.warning(f"[키움] 체결 확인 오류: {e}")

        # 60초 후에도 미체결 → 미체결 알림
        tg(
            f"⚠️ <b>[{_mode}] {_action} 미체결</b>\n"
            f"종목: {name} ({ticker}) | 주문번호: {order_no}\n"
            f"직접 확인이 필요해요."
        )

    threading.Thread(target=_wait_and_notify, daemon=True).start()

def _get_env_path() -> str:
    """스크립트 위치 기준 .env 경로 반환"""
    return str(Path(__file__).parent / ".env")

def _set_env_value(env_path: str, key: str, value: str):
    """기존 .env 파일에서 특정 키 값을 변경 (없으면 추가)"""
    try:
        lines = []
        found = False
        if Path(env_path).exists():
            with open(env_path, "r") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                        lines.append(f"{key}={value}\n")
                        found = True
                    else:
                        lines.append(line)
        if not found:
            lines.append(f"{key}={value}\n")
        with open(env_path, "w") as f:
            f.writelines(lines)
        # 런타임 환경변수도 즉시 반영
        import os
        os.environ[key] = value
        log.info(f"[.env] {key}={value} 저장 완료")
    except Exception as e:
        log.error(f"[.env] 수정 실패: {e}")

def refresh_universe(current_positions: dict) -> dict:
    log.info("🔍 유니버스 자동 갱신 시작...")
    try:
        # ① 네이버 금융 거래대금 기준 상위 종목 풀 구성 (⑦ pykrx 전종목 대체)
        top_vol = fetch_kospi_top_by_volume_naver(C["AUTO_SCAN_POOL_SIZE"])

        if not top_vol:
            # 네이버 실패 → FDR listing 시가총액 순 폴백
            listing = _get_fdr_listing("KOSPI")
            if not listing.empty and "Marcap" in listing.columns:
                top_vol = {
                    str(row["Code"]): int(row["Marcap"])
                    for _, row in listing.nlargest(
                        C["AUTO_SCAN_POOL_SIZE"], "Marcap"
                    ).iterrows()
                }

        if not top_vol:
            log.warning("유니버스 갱신: 종목 풀 구성 실패 → 기존 유지")
            return load_universe()

        top_pool = list(top_vol.keys())
        log.info(f"  종목 풀: {len(top_pool)}개 (거래대금 기준)")

        scored = []
        for ticker in top_pool:
            try:
                name = resolve_name(ticker)
                if not name or name == ticker: continue
                df   = get_ohlcv(ticker, days=60)
                if df is None or len(df) < 20: continue
                edge = calculate_edge_v27(df, 0.0, ticker)
                scored.append({"ticker": ticker, "name": name, "edge": edge})
                time.sleep(0.08)
            except Exception:
                continue

        scored.sort(key=lambda x: x["edge"], reverse=True)
        new_univ = {tk: info.get("name", tk)
                    for tk, info in current_positions.items()}
        for s in scored:
            if len(new_univ) >= C["AUTO_UNIVERSE_SIZE"]: break
            if s["ticker"] not in new_univ:
                new_univ[s["ticker"]] = s["name"]

        save_universe(new_univ)
        invalidate_cache()

        held_str = (', '.join(info.get("name", tk)
                              for tk, info in current_positions.items())
                    if current_positions else "없음")
        added = [nm for tk, nm in new_univ.items()
                 if tk not in current_positions]
        log.info(f"✅ 유니버스 갱신: {len(new_univ)}개")
        tg(f"🔄 <b>오늘의 관심 종목 업데이트 완료!</b>\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"AI가 오늘 가장 유망한 종목을 새로 선별했어요.\n"
           f"📊 총 {len(new_univ)}개 선정\n"
           f"📂 내 보유 종목: {held_str}\n"
           f"📈 새로 추가: {', '.join(added[:10])}"
           f"{'...' if len(added) > 10 else ''}")
        return new_univ
    except Exception as e:
        log.error(f"유니버스 갱신 실패: {e}")
        return load_universe()


# ══════════════════════════════════════════════════
# 메시지 헬퍼 — 초보자 언어 변환
# ══════════════════════════════════════════════════

def _regime_plain(regime: str) -> str:
    return {"BULL": "📈 상승장", "SIDE": "➡️ 보합장", "BEAR": "📉 하락장"}.get(regime, "❓")

def _regime_tip(regime: str) -> str:
    return {
        "BULL": "지금은 적극적으로 투자할 만한 시기예요.",
        "SIDE": "방향이 불확실해요. 신중하게 접근하세요.",
        "BEAR": "하락장이에요. 현금 비중을 높이는 게 안전해요.",
    }.get(regime, "")

def _edge_label(edge: float) -> str:
    s = int(edge * 100)
    if s >= 80: grade = "🔥 매우 강함"
    elif s >= 70: grade = "✅ 강함"
    elif s >= 60: grade = "🟡 보통"
    elif s >= 50: grade = "⚠️ 약함"
    else: grade = "❌ 매우 약함"
    return f"{s}점  {grade}"

def _ret_str(ret: float) -> str:
    icon = "✅" if ret >= 0 else "🔴"
    return f"{icon} {ret:+.2%} {'수익' if ret >= 0 else '손실'} 중"

# ══════════════════════════════════════════════════
# 텔레그램 전송 (버튼 포함 / 미포함)
# ══════════════════════════════════════════════════

def _ds_footer() -> str:
    """현재 데이터 소스를 한 줄 푸터로 반환"""
    src = _data_source_status.get("source", "확인중")
    ok  = _data_source_status.get("ok", False)
    icon = "🟢" if ok else "🔴"
    return f"\n<i>{icon} 데이터: {src}</i>"

def _dash_alert(text: str, kind: str = "info", ticker: str = "") -> None:
    """
    대시보드 /api/alerts 연동 — alerts_today.json 에 알림 저장
    kind: 'buy' | 'sell' | 'warning' | 'info'
    오늘 날짜가 바뀌면 자동 초기화

    Dashboard.jsx 호환 필드:
      - type  : 'success'(매수) | 'danger'(매도) | 'warning' | 'info'
      - icon  : 이모지
      - msg   : 표시 메시지
      - time  : HH:MM
      - timestamp : ISO 문자열
    """
    # kind → Dashboard 호환 type/icon 매핑
    _TYPE_MAP = {"buy": "success", "sell": "danger",
                 "warning": "warning", "info": "info"}
    _ICON_MAP = {"buy": "📈", "sell": "📤",
                 "warning": "⚠️", "info": "ℹ️"}
    _type = _TYPE_MAP.get(kind, "info")
    _icon = _ICON_MAP.get(kind, "ℹ️")

    try:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        alerts: list = []
        if ALERTS_FILE.exists():
            try:
                raw = json.loads(ALERTS_FILE.read_text(encoding="utf-8"))
                # 날짜가 다르면 초기화 (자정 자동 리셋)
                if raw and isinstance(raw, list) and raw[0].get("date", "") == today:
                    alerts = raw
            except Exception:
                pass
        alerts.append({
            # ── Dashboard.jsx 호환 필드 ──────────────────
            "time":      now.strftime("%H:%M"),
            "icon":      _icon,
            "msg":       text[:200],
            "type":      _type,
            "responded": False,
            "timestamp": now.isoformat(),
            # ── 추가 메타 (내부 조회용) ──────────────────
            "date":      today,
            "kind":      kind,
            "ticker":    ticker,
        })
        ALERTS_FILE.write_text(
            json.dumps(alerts[-200:], ensure_ascii=False, indent=2),  # 최대 200건 유지
            encoding="utf-8"
        )
    except Exception as e:
        log.debug(f"[대시보드] 알림 저장 실패: {e}")

def tg(text: str, silent: bool = False, no_menu: bool = False):
    if len(TELEGRAM["token"]) < 20 or "여기에" in TELEGRAM["token"]:
        log.warning("[TG 미설정] " + text[:60]); return
    # 메인 메뉴 버튼 자동 추가 (짧은 에러/조용한 알림 제외)
    _add_menu = (not no_menu and not silent and len(text) > 20)
    try:
        if _add_menu:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM['token']}/sendMessage",
                json={"chat_id": TELEGRAM["chat_id"], "text": text + _ds_footer(),
                      "parse_mode": "HTML", "disable_notification": silent,
                      "reply_markup": {"inline_keyboard": [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]]}},
                timeout=10,
            )
        else:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM['token']}/sendMessage",
                json={"chat_id": TELEGRAM["chat_id"], "text": text + _ds_footer(),
                      "parse_mode": "HTML", "disable_notification": silent},
                timeout=10,
            )
        err_tracker.record_ok("텔레그램")
    except Exception as e:
        log.error(f"[TG] {e}")
        err_tracker.record_fail("텔레그램")

def tg_btn(text: str, buttons: list, silent: bool = False):
    """인라인 버튼 포함 메시지. buttons = [[{text, callback_data}], ...]"""
    if len(TELEGRAM["token"]) < 20 or "여기에" in TELEGRAM["token"]:
        log.warning("[TG 버튼 미설정] " + text[:40]); return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM['token']}/sendMessage",
            json={"chat_id": TELEGRAM["chat_id"], "text": text + _ds_footer(),
                  "parse_mode": "HTML", "disable_notification": silent,
                  "reply_markup": {"inline_keyboard": buttons}},
            timeout=10,
        )
    except Exception as e:
        log.error(f"[TG 버튼] {e}")

def tg_answer(qid: str):
    if len(TELEGRAM["token"]) < 20 or "여기에" in TELEGRAM["token"]: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM['token']}/answerCallbackQuery",
            json={"callback_query_id": qid}, timeout=5)
    except: pass

# 메인 메뉴 버튼 레이아웃
MAIN_MENU = [
    [{"text": "📊 내 주식 현황",   "callback_data": "status"},
     {"text": "🤖 오늘의 추천",    "callback_data": "recommend"}],
    [{"text": "💰 매수 등록",      "callback_data": "buy_start"},
     {"text": "💸 매도 처리",      "callback_data": "sell_start"}],
    [{"text": "💬 매도 의견",      "callback_data": "sell_opinion"},
     {"text": "📋 수익 리포트",    "callback_data": "report"}],
    [{"text": "🌐 관심 종목 목록", "callback_data": "universe"},
     {"text": "⚙️ 설정",           "callback_data": "settings"}],
    [{"text": "🧠 자동 최적화",    "callback_data": "optimizer"},
     {"text": "❓ 도움말",         "callback_data": "help"}],
    [{"text": "🟢 실제투자 실행",  "callback_data": "trading_real"},
     {"text": "🔵 모의투자 전환",  "callback_data": "trading_mock"}],
    [{"text": "🔍 연결 확인",      "callback_data": "check_connection"},
     {"text": "🔴 비상정지",       "callback_data": "emergency_stop"}],
]

# ══════════════════════════════════════════════════
# TelegramCommander — 버튼 + 텍스트 통합 처리
# ══════════════════════════════════════════════════

class TelegramCommander:
    def __init__(self, monitor):
        self.monitor = monitor
        self.offset  = 0
        self.base    = f"https://api.telegram.org/bot{TELEGRAM['token']}"
        self.running = True
        self.state   = ""   # 단계별 입력 상태

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        log.info("✅ 텔레그램 버튼 인터페이스 시작")

    def _loop(self):
        while self.running:
            try:
                r = requests.get(f"{self.base}/getUpdates",
                                 params={"offset": self.offset, "timeout": 30},
                                 timeout=35)
                if r.status_code != 200:
                    time.sleep(5); continue

                for upd in r.json().get("result", []):
                    self.offset = upd["update_id"] + 1

                    # 버튼 클릭
                    if "callback_query" in upd:
                        cq = upd["callback_query"]
                        cid = str(cq.get("message", {}).get("chat", {}).get("id", ""))
                        if cid == str(TELEGRAM["chat_id"]):
                            tg_answer(cq["id"])
                            try:
                                self._on_btn(cq.get("data", ""))
                            except Exception as btn_err:
                                log.error(f"[버튼 에러] {cq.get('data','')}: {btn_err}")
                                tg(f"⚠️ 버튼 처리 중 오류가 발생했어요\n{btn_err}")
                        continue

                    # 텍스트
                    msg  = upd.get("message", {})
                    text = msg.get("text", "").strip()
                    cid  = str(msg.get("chat", {}).get("id", ""))
                    if cid == str(TELEGRAM["chat_id"]) and text:
                        try:
                            self._on_text(text)
                        except Exception as txt_err:
                            log.error(f"[텍스트 에러] {text[:30]}: {txt_err}")
                            tg(f"⚠️ 명령 처리 중 오류가 발생했어요\n{txt_err}")

            except Exception as e:
                log.warning(f"[TG 폴링] {e}"); time.sleep(5)

    # ────────────────────────────────────────────
    # 버튼 콜백
    # ────────────────────────────────────────────
    def _on_btn(self, data: str):
        cmd, _, arg = data.partition(":")
        dispatch = {
            "menu":      self._menu,
            "status":    self._status,
            "recommend": self._recommend,
            "buy_start": self._buy_start,
            "sell_start":self._sell_start,
            "sell_opinion": self._sell_opinion,
            "report":    self._report,
            "universe":  self._universe,
            "help":      self._help,
            "settings":       self._settings,
            "set_showconfig": self._set_showconfig,
            "set_reload":     self._set_reload,
            "optimizer":          self._optimizer_menu,
            "opt_preview":        self._optimizer_preview,
            "opt_apply":          self._optimizer_apply,
            "opt_apply_confirm":  self._optimizer_apply_confirm,
            "opt_last":           self._optimizer_last,
            "trading_real":       self._trading_real,
            "trading_mock":       self._trading_mock,
            "check_connection":   self._check_connection,
            "emergency_stop":     self._emergency_stop,
        }
        if cmd in dispatch:
            dispatch[cmd]()
        elif cmd == "sell_pick":
            self._sell_pick(arg)
        elif cmd == "edge_detail":
            self._edge_detail(arg)
        elif cmd == "set_cat":
            self._set_cat(arg)
        elif cmd == "set_cap":
            self._set_cap_input()
        elif cmd == "set_pct":
            p = arg.split(":")
            if len(p) == 3: self._set_pct(p[0], p[1], p[2])
        elif cmd == "set_mult":
            p = arg.split(":")
            if len(p) == 3: self._set_mult(p[0], p[1], p[2])
        elif cmd == "set_min":
            p = arg.split(":")
            if len(p) == 3: self._set_min(p[0], p[1], p[2])
        elif cmd == "set_apply":
            p = arg.split(":")
            if len(p) == 3: self._set_apply(p[0], p[1], p[2])
        elif cmd == "set_apply_f":
            p = arg.split(":")
            if len(p) == 3: self._set_apply_f(p[0], p[1], p[2])
        elif cmd == "set_apply_i":
            p = arg.split(":")
            if len(p) == 3: self._set_apply_i(p[0], p[1], p[2])
        elif cmd == "set_steps":
            self._set_steps(arg)
        elif cmd == "set_steps_toggle":
            p = arg.split(":")
            if len(p) == 2: self._set_steps_toggle(p[0], p[1])

    # ────────────────────────────────────────────
    # 텍스트 입력
    # ────────────────────────────────────────────
    def _on_text(self, text: str):
        parts = text.strip().split()
        cmd   = parts[0].lower() if parts else ""

        # 단계별 입력 처리
        if self.state == "awaiting_buy":
            self._do_buy(parts); return
        if self.state.startswith("awaiting_sell:"):
            self._do_sell(parts); return
        if self.state == "awaiting_edge":
            if parts:
                self.state = ""
                self._edge_detail(parts[0])
            return
        if self.state == "awaiting_capital":
            self._do_set_capital(parts); return

        # 텍스트 명령어
        if cmd in ("/start", "/menu", "/메뉴"):
            self._menu()
        elif cmd == "/status":   self._status()
        elif cmd == "/report":   self._report()
        elif cmd == "/universe": self._universe()
        elif cmd == "/help":     self._help()
        elif cmd == "/buy":
            if len(parts) >= 4: self._do_buy(parts[1:])
            else: self._buy_start()
        elif cmd == "/sell":
            if len(parts) >= 3: self._do_sell(parts[1:])
            else: self._sell_start()
        elif cmd == "/edge":
            if len(parts) >= 2: self._edge_detail(parts[1])
            else:
                self.state = "awaiting_edge"
                tg("🔍 조회할 종목코드를 입력해주세요\n예) <code>031980</code>")
        elif cmd == "/add":
            if len(parts) >= 2: self._add(parts[1])
        elif cmd == "/remove":
            if len(parts) >= 2: self._remove(parts[1])
        else:
            self._menu()

    # ════════════════════════════════════════════
    # 메인 메뉴
    # ════════════════════════════════════════════
    def _menu(self):
        self.state = ""
        regime     = self.monitor.regime
        held_cnt   = len(self.monitor.positions)
        market_str = "🟢 장중" if is_market_hour() else "🔴 장 마감"

        # 투자 모드 표시
        if EMERGENCY_STOP:
            mode_str = "🔴 비상정지 중"
        else:
            kw = kiwoom()
            if kw and not kw._mock:
                mode_str = "🟢 실제투자 중"
            else:
                mode_str = "🔵 모의투자 중"

        tg_btn(
            f"🤖 <b>Edge Score 메인 메뉴</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {datetime.now().strftime('%H:%M')}  {market_str}\n"
            f"📈 시장: {_regime_plain(regime)}\n"
            f"💼 현재 보유 종목: {held_cnt}개\n"
            f"💡 투자 모드: {mode_str}\n\n"
            f"원하는 기능을 눌러주세요 👇",
            MAIN_MENU
        )

    # ════════════════════════════════════════════
    # 내 주식 현황
    # ════════════════════════════════════════════
    def _status(self):
        self.state  = ""
        positions   = self.monitor.positions
        regime      = self.monitor.regime

        if not positions:
            tg_btn(
                "📊 <b>내 주식 현황</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "현재 보유 중인 주식이 없어요.\n"
                "AI가 추천하는 종목을 확인해보세요! 👇",
                [[{"text": "🤖 오늘의 추천 보기", "callback_data": "recommend"}],
                 [{"text": "🏠 메인 메뉴",        "callback_data": "menu"}]]
            )
            return

        total_pnl  = 0
        total_eval = 0
        msg = (f"📊 <b>내 주식 현황</b>\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"🕐 {datetime.now().strftime('%H:%M')} 기준\n"
               f"📈 시장: {_regime_plain(regime)}\n"
               f"💡 {_regime_tip(regime)}\n"
               f"━━━━━━━━━━━━━━━━━━\n")

        for ticker, info in positions.items():
            name      = info.get("name", resolve_name(ticker))
            buy_price = float(info.get("buy_price", 0))
            shares    = int(info.get("shares", 0))
            cp        = get_current_price(ticker)
            if cp <= 0: cp = buy_price
            ret       = (cp - buy_price) / buy_price if buy_price > 0 else 0
            pnl       = (cp - buy_price) * shares
            eval_amt  = cp * shares
            total_pnl  += pnl
            total_eval += eval_amt

            df     = get_ohlcv(ticker, days=30)
            atr    = calc_atr(df) if df is not None else cp * 0.02
            dyn_sl = calc_dynamic_sl(atr, cp, ticker, regime)
            # [v40.0 BUG-FIX] 표시 손절가를 실제 트리거와 동일하게 매수가 기준으로 통일
            _sl_base = buy_price if buy_price > 0 else cp
            sl_price = _sl_base * (1 + dyn_sl)
            if np.isnan(sl_price) or sl_price <= 0:
                sl_price = _sl_base * 0.93

            entry_date = info.get("entry_date", "")
            hold_days  = (date.today() - date.fromisoformat(entry_date)).days \
                         if entry_date else "-"

            trail_txt = "\n   🔺 고점 추적 중 — 고점 대비 하락 시 매도 신호" \
                        if info.get("trail_active") else ""
            pnl_icon  = "✅" if pnl >= 0 else "🔴"

            msg += (f"\n📌 <b>{name}</b>  ({hold_days}일 보유)\n"
                    f"   산 가격: {buy_price:,.0f}원  →  현재: {cp:,.0f}원\n"
                    f"   {_ret_str(ret)}\n"
                    f"   {shares:,}주  |  평가금액: {eval_amt:,.0f}원\n"
                    f"   {pnl_icon} 손익: <b>{pnl:+,.0f}원</b>\n"
                    f"   ⚠️ 손절 기준가: {sl_price:,.0f}원{trail_txt}\n")

        pnl_icon = "✅" if total_pnl >= 0 else "🔴"
        msg += (f"━━━━━━━━━━━━━━━━━━\n"
                f"{pnl_icon} 총 평가손익: <b>{total_pnl:+,.0f}원</b>\n"
                f"💼 총 평가금액: {total_eval:,.0f}원")

        btns = [[{"text": f"💸 {info.get('name', resolve_name(tk))} 팔기",
                  "callback_data": f"sell_pick:{tk}"}]
                for tk, info in positions.items()
                if int(info.get("shares", 0)) > 0]   # 0주 항목 버튼에서 제외
        btns.append([{"text": "🏠 메인 메뉴", "callback_data": "menu"}])
        tg_btn(msg, btns)

    # ════════════════════════════════════════════
    # 오늘의 추천
    # ════════════════════════════════════════════
    def _recommend(self):
        self.state = ""
        regime     = self.monitor.regime
        held       = set(self.monitor.positions.keys())
        scored     = []

        for ticker, name in self.monitor.universe.items():
            if ticker in held or ticker in self.monitor.today_exited: continue
            df = get_ohlcv(ticker, days=60)
            if df is None or len(df) < 20: continue
            kind_adj = fetch_kind_sentiment(ticker)
            edge     = calculate_edge_v27(df, kind_adj, ticker)
            cp       = float(df["종가"].iloc[-1])
            slip_ok, exp, _ = check_slippage_filter(df, ticker)
            thr2 = get_regime_threshold(regime)
            if edge >= thr2 and slip_ok:
                scored.append({"ticker": ticker, "name": name,
                               "edge": edge, "price": cp, "exp": exp,
                               "kind": kind_adj})

        scored.sort(key=lambda x: x["edge"], reverse=True)
        top5 = scored[:5]

        if not top5:
            tg_btn(
                f"🤖 <b>오늘의 추천 종목</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"지금 당장 추천할 종목이 없어요.\n"
                f"시장 상황을 더 지켜봐야 할 것 같아요.\n\n"
                f"📈 현재 시장: {_regime_plain(regime)}\n"
                f"💡 {_regime_tip(regime)}",
                [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
            return

        msg = (f"🤖 <b>오늘의 추천 종목 TOP {len(top5)}</b>\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"📈 시장: {_regime_plain(regime)}\n"
               f"💡 {_regime_tip(regime)}\n"
               f"━━━━━━━━━━━━━━━━━━\n\n")

        for i, s in enumerate(top5):
            # 분할매수 단계
            split_str = ""
            for step in C["SPLIT_BUY_STEPS"]:
                if s["edge"] >= step["edge"]:
                    split_str = f"  →  {step['label']} 진입 추천"
            kind_str = ""
            if s["kind"] > 0:
                kind_str = "\n   📢 오늘 긍정적인 공시가 있어요"
            elif s["kind"] < 0:
                kind_str = "\n   📢 오늘 부정적인 공시가 있어요 (주의)"
            msg += (f"{i+1}위  <b>{s['name']}</b>\n"
                    f"   🎯 AI 점수: {_edge_label(s['edge'])}\n"
                    f"   💰 현재가: {s['price']:,.0f}원\n"
                    f"   📈 예상 수익 가능성: {s['exp']:.1%}{split_str}{kind_str}\n\n")

        msg += "⚠️ AI 추천은 참고용이에요. 최종 판단은 본인이 하세요."

        btns = [[{"text": f"🔍 {s['name']} 자세히",
                  "callback_data": f"edge_detail:{s['ticker']}"}]
                for s in top5]
        btns.append([{"text": "💰 매수 등록하기",  "callback_data": "buy_start"},
                     {"text": "🏠 메인 메뉴",       "callback_data": "menu"}])
        tg_btn(msg, btns)

    # ════════════════════════════════════════════
    # 매수 등록
    # ════════════════════════════════════════════
    def _buy_start(self):
        self.state = "awaiting_buy"
        tg_btn(
            "💰 <b>매수 등록</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "아래 형식으로 입력해주세요 👇\n\n"
            "<code>종목명(또는 코드)  매수가  주식수</code>\n\n"
            "📌 <b>종목명으로 입력</b>\n"
            "<code>피에스케이홀딩스 48500 30</code>\n"
            "→ 자동으로 종목코드를 찾아줘요\n\n"
            "📌 <b>종목코드로 입력</b>\n"
            "<code>031980 48500 30</code>\n"
            "→ 6자리 숫자로 직접 입력도 가능해요",
            [[{"text": "❌ 취소", "callback_data": "menu"}]]
        )

    def _do_buy(self, parts: list):
        self.state = ""
        try:
            buy_price = float(str(parts[1]).replace(",", ""))
            shares    = int(str(parts[2]).replace(",", ""))
            amount    = buy_price * shares
        except:
            tg_btn(
                "❌ <b>입력 형식이 맞지 않아요.</b>\n\n"
                "종목명 또는 코드로 입력하세요:\n"
                "<code>피에스케이홀딩스 48500 30</code>\n"
                "<code>031980 48500 30</code>",
                [[{"text": "💰 다시 입력", "callback_data": "buy_start"},
                  {"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
            return

        # 종목명 또는 코드 → ticker 확정
        query  = str(parts[0]).strip()
        ticker, found_name = resolve_ticker(
            query,
            self.monitor.universe,
            self.monitor.positions
        )
        if ticker is None:
            tg_btn(
                f"❌ <b>종목을 찾을 수 없어요.</b>\n\n"
                f"'{query}'에 해당하는 종목이 없어요.\n"
                f"종목명을 다시 확인해주세요.\n\n"
                f"예) <code>피에스케이홀딩스 48500 30</code>\n"
                f"예) <code>031980 48500 30</code>",
                [[{"text": "💰 다시 입력", "callback_data": "buy_start"},
                  {"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
            return

        name     = resolve_name(ticker, self.monitor.universe,
                                self.monitor.positions)
        existing = self.monitor.positions.get(ticker)

        if existing:
            old_price    = float(existing.get("buy_price", buy_price))
            old_shares   = int(existing.get("shares", 0))
            total_shares = old_shares + shares
            avg_price    = (old_price * old_shares + buy_price * shares) / total_shares
            total_amount = float(existing.get("amount", 0)) + amount
            entry_date   = existing.get("entry_date", str(date.today()))
            is_add       = True
        else:
            avg_price    = buy_price
            total_shares = shares
            total_amount = amount
            entry_date   = str(date.today())
            is_add       = False

        self.monitor.positions[ticker] = {
            "ticker": ticker, "name": name,
            "buy_price":    round(avg_price, 2),
            "shares":       total_shares,
            "amount":       total_amount,
            "entry_date":   entry_date,
            "trail_active": existing.get("trail_active", False) if existing else False,
            "peak_price":   existing.get("peak_price", avg_price) if existing else avg_price,
            "trail_price":  existing.get("trail_price", 0.0) if existing else 0.0,
            "alerted_steps":existing.get("alerted_steps", []) if existing else [],
            # [H-3 수정] 신규/재매수 시 알림 플래그 초기화
            # 이전 사이클의 atr_alerted/trail_alerted 인계 방지
            "atr_alerted":         False,
            "trail_alerted":       False,
            "sell_edge_alerted":   False,
            "max_hold_warned":     False,
        }
        save_positions(self.monitor.positions)

        if ticker not in self.monitor.universe:
            self.monitor.universe[ticker] = name
            save_universe(self.monitor.universe)

        append_trade_log({
            "action": "buy", "ticker": ticker, "name": name,
            "buy_price": buy_price, "shares": shares, "amount": amount,
            "date": str(date.today()),       # api_performance equity_curve용
            "entry_date": str(date.today()),
            "exit_price": 0, "hold_days": 0,
            "reason": "추가매수" if is_add else "수동매수",
        })

        # ── 키움 실주문 + 체결 대기 알림 ────────────────────
        if not EMERGENCY_STOP:
            kw = kiwoom()
            if kw:
                _mode = "모의" if kw._mock else "실계좌"
                _res  = kw.buy(ticker, shares, buy_price, order_type="0")
                if _res.get("success"):
                    tg(f"📨 [{_mode}] 매수주문 접수 → 체결 대기 중...\n"
                       f"종목: {name} | {shares:,}주 | {buy_price:,}원")
                    _notify_on_fill(
                        _res.get("order_no", ""), ticker, name,
                        action="buy", qty=shares, price=buy_price
                    )
                else:
                    tg(f"⚠️ [{_mode}] 매수주문 실패: {_res.get('error','')}\n종목: {name}")
        # ─────────────────────────────────────────────────────

        kelly_amt = calc_kelly_amount(C["TOTAL_CAPITAL"])
        add_line  = f"\n🔄 추가 매수!  평균단가 → {avg_price:,.0f}원" if is_add else ""

        # 분할매수 안내
        df_tmp   = get_ohlcv(ticker, days=60)
        edge_now = calculate_edge_v27(df_tmp, 0.0, ticker) if df_tmp is not None else 0.5
        split_line = ""
        for step in C["SPLIT_BUY_STEPS"]:
            if edge_now >= step["edge"]:
                amt = C["TOTAL_CAPITAL"] * step["ratio"]
                split_line = f"\n💡 현재 AI 점수 기준: {step['label']} ({amt:,.0f}원) 적합"

        # ── 원칙2: 남은 거래일 컨텍스트 계산 ──
        _remain = get_remaining_trading_days()
        _wd     = date.today().weekday()
        if _wd == 4:   # 금요일
            _week_ctx = (
                "⚠️ <b>오늘이 이번 주 마지막 거래일이에요!</b>\n"
                "   장 마감 전 수익·AI점수 상태에 따라\n"
                "   자동으로 보유 유지 여부를 알려드려요"
            )
        elif _wd == 3:  # 목요일
            _week_ctx = (
                "⏰ 내일(금요일)이 이번 주 마지막 거래일이에요\n"
                "   ✅ 수익 중 + AI점수 양호 → 보유 유지 가능\n"
                "   🔴 손실 중이거나 AI점수 낮으면 → 내일 정리 필요"
            )
        else:
            _days_ko = {0:"월",1:"화",2:"수"}
            _week_ctx = f"📅 이번 주 남은 거래일: <b>{_remain}일</b> (오늘 {_days_ko.get(_wd,'')}요일 포함)"

        tg_btn(
            f"✅ <b>매수 등록 완료!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 종목: <b>{name}</b>\n"
            f"💰 매수가: {buy_price:,.0f}원\n"
            f"📦 주식수: {shares:,}주\n"
            f"💼 매수금액: {amount:,.0f}원{add_line}\n"
            f"📊 총 보유: {total_shares:,}주  (평균단가 {avg_price:,.0f}원)\n"
            f"📅 매수일: {entry_date}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧮 AI 추천 투자금액: {kelly_amt:,.0f}원\n"
            f"   (내 승률 기반으로 자동 계산됐어요){split_line}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{_week_ctx}",
            [[{"text": "📊 내 주식 현황",  "callback_data": "status"},
              {"text": "🏠 메인 메뉴",     "callback_data": "menu"}]]
        )
        log.info(f"[매수] {name} {buy_price:,.0f}원 {shares}주")

    # ════════════════════════════════════════════
    # 매도 처리
    # ════════════════════════════════════════════
    def _sell_start(self):
        self.state = ""
        positions  = self.monitor.positions

        if not positions:
            tg_btn(
                "💸 <b>매도 처리</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "현재 보유 중인 주식이 없어요.",
                [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
            return

        msg  = ("💸 <b>어떤 주식을 팔까요?</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "팔고 싶은 종목을 선택해주세요 👇\n\n")
        btns = []
        for ticker, info in positions.items():
            name      = info.get("name", resolve_name(ticker))
            buy_price = float(info.get("buy_price", 0))
            cp        = get_current_price(ticker)
            ret       = (cp - buy_price) / buy_price \
                        if buy_price > 0 and cp > 0 else 0
            icon = "✅" if ret >= 0 else "🔴"
            msg += f"{icon} <b>{name}</b>  {ret:+.2%}\n"
            btns.append([{"text": f"💸 {name} 팔기  ({ret:+.2%})",
                          "callback_data": f"sell_pick:{ticker}"}])
        btns.append([{"text": "❌ 취소", "callback_data": "menu"}])
        tg_btn(msg, btns)

    def _sell_pick(self, ticker: str):
        ticker = ticker.zfill(6)
        pos    = self.monitor.positions.get(ticker)
        if not pos:
            tg("⚠️ 해당 종목을 찾을 수 없어요."); return

        name      = pos.get("name", resolve_name(ticker))
        buy_price = float(pos.get("buy_price", 0))
        shares    = int(pos.get("shares", 0))
        cp        = get_current_price(ticker)
        ret       = (cp - buy_price) / buy_price \
                    if buy_price > 0 and cp > 0 else 0

        self.state = f"awaiting_sell:{ticker}"
        tg_btn(
            f"💸 <b>{name} 매도</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 내가 산 가격: {buy_price:,.0f}원\n"
            f"📦 보유 주식수: {shares:,}주\n"
            f"💰 현재가: {cp:,.0f}원\n"
            f"   {_ret_str(ret)}\n\n"
            f"아래 형식으로 입력해주세요 👇\n\n"
            f"<b>전체 매도:</b>\n"
            f"<code>{ticker} {int(cp)}</code>\n\n"
            f"<b>일부 매도 (예: 15주만):</b>\n"
            f"<code>{ticker} {int(cp)} 15</code>",
            [[{"text": "❌ 취소", "callback_data": "menu"}]]
        )

    def _do_sell(self, parts: list):
        # state에서 ticker 추출
        pre_ticker = self.state.split(":")[1] if ":" in self.state else ""
        self.state = ""

        try:
            if len(parts) >= 2 and len(parts[0]) >= 5 and parts[0].isdigit():
                ticker     = parts[0].zfill(6)
                sell_price = float(str(parts[1]).replace(",", ""))
                extra      = parts[2:]
            elif pre_ticker:
                ticker     = pre_ticker
                sell_price = float(str(parts[0]).replace(",", ""))
                extra      = parts[1:]
            else:
                raise ValueError
        except:
            tg_btn(
                "❌ <b>입력 형식이 맞지 않아요.</b>\n\n"
                "올바른 형식:\n"
                "<code>종목코드  매도가</code>\n"
                "예) <code>031980 52300</code>",
                [[{"text": "💸 다시 매도", "callback_data": "sell_start"},
                  {"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
            return

        pos = self.monitor.positions.get(ticker)
        if not pos:
            tg("⚠️ 보유 종목에 없어요."); return

        name         = pos.get("name", resolve_name(ticker))
        buy_price    = float(pos.get("buy_price", 0))
        total_shares = int(pos.get("shares", 0))
        entry_date   = pos.get("entry_date", "")
        hold_days    = (date.today() - date.fromisoformat(entry_date)).days \
                       if entry_date else 0

        if extra:
            try:
                sell_shares = int(str(extra[0]).replace(",", ""))
            except:
                tg("❌ 주식수 형식이 맞지 않아요."); return
            if sell_shares > total_shares:
                tg(f"❌ 보유 주식수({total_shares:,}주)보다 많아요."); return
            is_partial = sell_shares < total_shares
        else:
            sell_shares = total_shares
            is_partial  = False

        sell_amount  = sell_price * sell_shares
        _buy_amt_m   = buy_price * sell_shares
        _sell_amt_m  = sell_price * sell_shares
        _commission_m= (_buy_amt_m + _sell_amt_m) * COMMISSION_RATE
        _tax_m       = _sell_amt_m * TAX_RATE
        ret  = (sell_price - buy_price) / buy_price if buy_price > 0 else 0
        pnl  = (_sell_amt_m - _buy_amt_m) - _commission_m - _tax_m  # 수수료·세금 반영
        pnl_icon = "✅" if pnl >= 0 else "🔴"

        _cluster_manual = get_cluster_name(ticker)
        append_trade_log({
            "action": "sell", "ticker": ticker, "name": name,
            "buy_price": buy_price, "sell_price": sell_price,
            "shares": sell_shares, "amount": buy_price * sell_shares,
            "date": str(date.today()),       # api_performance equity_curve용
            "entry_date": entry_date, "exit_date": str(date.today()),
            "exit_price": sell_price, "hold_days": hold_days,
            "ret": round(ret, 4), "pnl": round(pnl, 0),
            "reason": "일부청산" if is_partial else "수동청산",
            "regime": self.monitor.regime,
            "edge_at_exit": pos.get("last_edge", 0),
            "cluster":       _cluster_manual,
            # [Fix-BUG-1] atr_mult_orig 추가 (수동청산도 OPT 분석 대상)
            "atr_mult_orig": get_atr_mult_rt(_cluster_manual),
            "carry_over":   False,
        })

        # ── 키움 실주문 + 체결 대기 알림 ────────────────────
        if not EMERGENCY_STOP:
            kw = kiwoom()
            if kw:
                _mode = "모의" if kw._mock else "실계좌"
                _res  = kw.sell(ticker, sell_shares, sell_price, order_type="0")
                if _res.get("success"):
                    tg(f"📨 [{_mode}] 매도주문 접수 → 체결 대기 중...\n"
                       f"종목: {name} | {sell_shares:,}주 | {sell_price:,}원")
                    _notify_on_fill(
                        _res.get("order_no", ""), ticker, name,
                        action="sell", qty=sell_shares, price=sell_price,
                        buy_price=buy_price
                    )
                else:
                    tg(f"⚠️ [{_mode}] 매도주문 실패: {_res.get('error','')}\n종목: {name}")
        # ─────────────────────────────────────────────────────

        if is_partial:
            remain = total_shares - sell_shares
            pos["shares"] = remain
            pos["amount"] = buy_price * remain
            pos["alerted_steps"] = []
            save_positions(self.monitor.positions)
            tg_btn(
                f"📤 <b>일부 매도 완료!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 종목: <b>{name}</b>\n"
                f"💰 산 가격: {buy_price:,.0f}원  →  판 가격: {sell_price:,.0f}원\n"
                f"📦 판 주식수: {sell_shares:,}주  |  매도금액: {sell_amount:,.0f}원\n"
                f"   {_ret_str(ret)}\n"
                f"{pnl_icon} 손익: <b>{pnl:+,.0f}원</b>\n"
                f"📅 보유 기간: {hold_days}일\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 남은 주식: {remain:,}주",
                [[{"text": "📊 현황 보기",  "callback_data": "status"},
                  {"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
        else:
            del self.monitor.positions[ticker]
            save_positions(self.monitor.positions)
            tg_btn(
                f"📤 <b>전체 매도 완료!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 종목: <b>{name}</b>\n"
                f"💰 산 가격: {buy_price:,.0f}원  →  판 가격: {sell_price:,.0f}원\n"
                f"📦 판 주식수: {sell_shares:,}주  |  매도금액: {sell_amount:,.0f}원\n"
                f"   {_ret_str(ret)}\n"
                f"{pnl_icon} 최종 손익: <b>{pnl:+,.0f}원</b>\n"
                f"📅 보유 기간: {hold_days}일",
                [[{"text": "🤖 다음 추천 보기", "callback_data": "recommend"},
                  {"text": "🏠 메인 메뉴",      "callback_data": "menu"}]]
            )
        log.info(f"[매도] {name} {sell_price:,.0f}원 {sell_shares}주 {ret:+.2%}")

    # ════════════════════════════════════════════
    # 종목 상세 분석
    # ════════════════════════════════════════════
    def _edge_detail(self, ticker_raw: str):
        self.state = ""
        ticker     = str(ticker_raw).zfill(6)
        invalidate_cache(ticker)
        df = get_ohlcv(ticker, days=60)
        if df is None:
            tg_btn("❌ 해당 종목 데이터를 가져올 수 없어요.",
                   [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]])
            return

        name      = resolve_name(ticker, self.monitor.universe,
                                 self.monitor.positions)
        edge      = calculate_edge_v27(df, 0.0, ticker)
        cp        = float(df["종가"].iloc[-1])
        slip_ok, exp, req = check_slippage_filter(df, ticker)
        kind_adj  = fetch_kind_sentiment(ticker)
        edge_kind = calculate_edge_v27(df, kind_adj, ticker)
        kelly_amt = calc_kelly_amount(C["TOTAL_CAPITAL"])

        slip_str = ("✅ 거래비용 감안해도 수익 가능해요\n"
                    f"   예상 수익 {exp:.1%}  ≥  필요 {req:.1%}"
                    if slip_ok else
                    "⚠️ 거래비용 대비 수익이 부족해요\n"
                    f"   예상 수익 {exp:.1%}  <  필요 {req:.1%}")

        kind_str = ""
        if kind_adj > 0:
            kind_str = f"\n📢 오늘 긍정적인 공시가 있어요  (+{kind_adj:.2f})"
        elif kind_adj < 0:
            kind_str = f"\n📢 오늘 부정적인 공시가 있어요  ({kind_adj:.2f})"

        split_str = ""
        for step in C["SPLIT_BUY_STEPS"]:
            if edge >= step["edge"]:
                amt = C["TOTAL_CAPITAL"] * step["ratio"]
                split_str = f"\n💡 지금 {step['label']} ({amt:,.0f}원) 진입 추천"

        use_edge = edge_kind if kind_adj != 0 else edge
        tg_btn(
            f"🔍 <b>{name} 종목 분석</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 현재가: {cp:,.0f}원\n"
            f"🎯 AI 점수: {_edge_label(use_edge)}{kind_str}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔍 거래비용 체크:\n   {slip_str}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧮 AI 추천 투자금액: {kelly_amt:,.0f}원{split_str}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ 투자 결정은 반드시 본인이 하세요.",
            [[{"text": "💰 이 종목 매수하기", "callback_data": "buy_start"},
              {"text": "🏠 메인 메뉴",        "callback_data": "menu"}]]
        )

    # ════════════════════════════════════════════
    # 💬 매도 의견 — 실시간 데이터 기반 종합 판단
    # ════════════════════════════════════════════
    def _sell_opinion(self):
        self.state = ""
        positions = self.monitor.positions
        regime    = self.monitor.regime

        if not positions:
            tg_btn(
                "💬 <b>매도 의견</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "현재 보유 중인 주식이 없어요.",
                [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
            return

        msg = (f"💬 <b>매도 의견</b>  ({datetime.now().strftime('%H:%M')} 기준)\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"📈 시장: {_regime_plain(regime)}\n\n")

        for ticker, info in positions.items():
            name   = info.get("name", resolve_name(ticker))
            buy_p  = float(info.get("buy_price", 0))
            shares = int(info.get("shares", 0))

            df = get_ohlcv(ticker, days=60)
            cp = get_current_price(ticker)
            if cp <= 0 and df is not None:
                cp = float(df["종가"].iloc[-1])
            if cp <= 0:
                cp = buy_p

            ret = (cp - buy_p) / buy_p if buy_p > 0 else 0
            pnl = (cp - buy_p) * shares
            atr = calc_atr(df) if df is not None else cp * 0.02
            dyn_sl = calc_dynamic_sl(atr, cp, ticker, regime)
            # [v40.0 BUG-FIX] 표시 손절가를 실제 트리거와 동일하게 매수가 기준으로 통일
            _sl_base_so = buy_p if buy_p > 0 else cp
            sl_price = round(_sl_base_so * (1 + dyn_sl), -1)

            # Edge 점수
            df_signal = get_closed_df(df) if df is not None else None
            edge = 0.0
            if df_signal is not None and len(df_signal) >= 20:
                kind_adj = fetch_kind_sentiment(ticker)
                edge = calculate_edge_v27(df_signal, kind_adj, ticker)

            # 거래량 비율
            vol_ratio = 1.0
            if df is not None and len(df) >= 20:
                vol_avg = df["거래량"].iloc[-20:].mean()
                vol_now = df["거래량"].iloc[-1]
                vol_ratio = vol_now / vol_avg if vol_avg > 0 else 1.0

            # 보유일수
            _entry = info.get("entry_date", "")
            hold_days = (date.today() - date.fromisoformat(_entry)).days if _entry else 0

            # 트레일링/타임스탑 상태
            trail_on  = info.get("trail_active", False)
            ts_fired  = info.get("timestop_alerted", False)
            sl_fired  = info.get("atr_alerted", False)

            # 손절선까지 거리
            sl_dist = ret - dyn_sl  # 양수 = 여유, 음수 = 이탈

            # ── 종합 판단 로직 ──
            reasons = []
            score = 0   # 양수=보유, 음수=매도

            # 1) 손절선 이탈
            if sl_fired or ret <= dyn_sl:
                score -= 3
                reasons.append("🔴 손절선에 도달했어요")

            # 2) 타임스탑 발동
            if ts_fired:
                score -= 3
                reasons.append("🔴 보유 기간이 너무 길어요 (타임스탑)")

            # 3) 손절선 근접 (3% 이내)
            elif sl_dist < 0.03 and sl_dist > 0:
                score -= 1
                reasons.append(f"🟡 손절선까지 {sl_dist:.1%} 남았어요")

            # 4) Edge 점수
            if edge >= 0.75:
                score += 2
                reasons.append(f"🟢 AI점수 {int(edge*100)}점, 좋아요")
            elif edge >= 0.60:
                score += 1
                reasons.append(f"🟢 AI점수 {int(edge*100)}점, 괜찮아요")
            elif edge >= 0.40:
                score -= 1
                reasons.append(f"🟡 AI점수 {int(edge*100)}점, 다소 낮아요")
            else:
                score -= 2
                reasons.append(f"🔴 AI점수 {int(edge*100)}점, 매력 없어요")

            # 5) 수익 상태
            if ret >= C.get("TAKE_PROFIT_FIXED", 0.15):
                score -= 1
                reasons.append(f"🟡 목표 수익률 달성 ({ret:+.2%}), 차익실현 고려")
            elif ret >= 0.05:
                score += 1
                reasons.append(f"🟢 수익 중 ({ret:+.2%})")
            elif ret >= 0:
                reasons.append(f"↔️ 본전 부근 ({ret:+.2%})")
            else:
                score -= 1
                reasons.append(f"🔴 손실 중 ({ret:+.2%})")

            # 6) 트레일링 활성
            if trail_on:
                score += 1
                reasons.append("🟢 트레일링 진행 중 — 수익 보호 중")

            # 7) 거래량
            if vol_ratio >= 2.0:
                reasons.append("📊 거래량 급증 — 방향 전환 가능성")
            elif vol_ratio <= 0.5:
                score -= 1
                reasons.append("📊 거래량 감소 — 관심 줄어드는 중")

            # 8) 보유일수
            max_hold = C.get("MAX_HOLD_DAYS", 5)
            if hold_days >= max_hold:
                score -= 1
                reasons.append(f"⏰ {hold_days}일째 보유 (최대 {max_hold}일)")

            # ── 최종 의견 ──
            if score <= -3:
                opinion = "🔴 즉시 매도"
                advice  = "지금 바로 매도하는 게 좋아요"
            elif score <= -1:
                opinion = "🟡 매도 권장"
                advice  = "오늘 중으로 매도를 고려하세요"
            elif score <= 1:
                opinion = "🟢 보유 유지"
                advice  = "지금은 더 지켜봐도 괜찮아요"
            else:
                opinion = "🔵 강력 보유"
                advice  = "추세가 좋아요, 계속 보유하세요"

            r_icon = "✅" if ret >= 0 else "🔴"
            msg += (
                f"📌 <b>{name}</b>\n"
                f"   {r_icon} {ret:+.2%}  ({pnl:+,.0f}원)  |  {hold_days}일째\n"
                f"   현재가: {cp:,.0f}원  |  손절가: {sl_price:,.0f}원\n"
                f"\n"
                f"   <b>{opinion}</b>\n"
                f"   {advice}\n"
                f"\n"
            )
            for r in reasons:
                msg += f"   {r}\n"
            msg += "\n━━━━━━━━━━━━━━━━━━\n"

        msg += "\n⚠️ AI 참고 의견이에요. 최종 판단은 본인이 하세요."

        tg_btn(msg,
               [[{"text": "💸 매도 처리", "callback_data": "sell_start"},
                 {"text": "🏠 메인 메뉴", "callback_data": "menu"}]])

    # ════════════════════════════════════════════
    # 수익 리포트
    # ════════════════════════════════════════════
    def _report(self):
        self.state = ""
        perf = calc_performance()
        logs = load_trade_log()
        this_month = [t for t in logs
                      if t.get("exit_date","")[:7] == date.today().strftime("%Y-%m")]
        month_pnl = sum(t.get("pnl", 0) for t in this_month
                        if t.get("exit_price", 0) > 0)
        kelly_amt = calc_kelly_amount(C["TOTAL_CAPITAL"])

        if perf["count"] == 0:
            tg_btn(
                "📋 <b>수익 리포트</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "아직 완료된 거래 내역이 없어요.\n"
                "매수 후 매도를 하면 성과가 기록돼요!",
                [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
            return

        w_icon  = "🏆" if perf["win_rate"] >= 0.5 else "📉"
        p_icon  = "✅" if perf["total_pnl"] >= 0 else "🔴"
        m_icon  = "✅" if month_pnl >= 0 else "🔴"

        tg_btn(
            f"📋 <b>나의 투자 성과</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 전체 거래 횟수: {perf['count']}번\n"
            f"{w_icon} 승률: {perf['win_rate']:.1%}\n"
            f"   → 10번 중 {round(perf['win_rate']*10,1)}번 수익\n"
            f"📈 평균 수익률: {perf['avg_ret']:+.2%}\n"
            f"📅 평균 보유 기간: {perf['avg_days']:.1f}일\n"
            f"{p_icon} 전체 누적 손익: <b>{perf['total_pnl']:+,.0f}원</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{m_icon} 이번 달 손익: <b>{month_pnl:+,.0f}원</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧮 AI 추천 투자금액: {kelly_amt:,.0f}원\n"
            f"   (내 승률 기반으로 자동 계산됐어요)",
            [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
        )

    # ════════════════════════════════════════════
    # 관심 종목 목록
    # ════════════════════════════════════════════
    def _universe(self):
        self.state = ""
        univ = self.monitor.universe
        held = set(self.monitor.positions.keys())
        msg  = (f"🌐 <b>관심 종목 목록</b>  ({len(univ)}개)\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"AI가 매일 자동으로 분석하는 종목들이에요.\n\n")
        for tk, nm in univ.items():
            icon = "📂 보유중" if tk in held else "👀 관찰중"
            msg += f"• {nm}  {icon}\n"
        msg += "\n💡 종목 추가: <code>/add 종목코드</code>\n"
        msg +=    "💡 종목 제거: <code>/remove 종목코드</code>"
        tg_btn(msg, [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]])

    # ════════════════════════════════════════════
    # 도움말
    # ════════════════════════════════════════════
    def _help(self):
        self.state = ""
        tg_btn(
            "❓ <b>Edge Score 사용 가이드</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🤖 AI가 주식을 분석해서\n"
            "   매수·손절 신호를 알려드려요.\n\n"
            "📊 <b>내 주식 현황</b>\n"
            "보유 주식의 수익률과\n"
            "손절 기준가를 확인해요.\n\n"
            "🤖 <b>오늘의 추천</b>\n"
            "AI가 지금 가장 유망하다고\n"
            "판단하는 종목 TOP 5예요.\n\n"
            "💰 <b>매수 등록</b>\n"
            "주식을 샀을 때 여기에 기록하면\n"
            "자동으로 손절·익절 알림이 와요.\n\n"
            "💸 <b>매도 처리</b>\n"
            "주식을 팔았을 때 기록해요.\n"
            "손익이 자동으로 계산돼요.\n\n"
            "📋 <b>수익 리포트</b>\n"
            "지금까지 투자 성과를\n"
            "한눈에 볼 수 있어요.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚠️ AI 신호는 참고용이에요.\n"
            "   최종 판단은 본인이 하세요!",
            [[{"text": "🏠 메인 메뉴로", "callback_data": "menu"}]]
        )

    # ════════════════════════════════════════════
    # ⚙️ 설정 메뉴 (전체)
    # ════════════════════════════════════════════

    # ── 설정 저장 헬퍼 ──────────────────────────
    def _save_cfg(self, key: str, val):
        """C[key] 변경 + config.json 즉시 저장"""
        C[key] = val
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg[key] = val
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"config 저장 실패: {e}")

    def _back_btn(self, parent: str = "settings"):
        return [{"text": f"🔙 돌아가기", "callback_data": parent},
                {"text": "🏠 메인 메뉴", "callback_data": "menu"}]

    # ── 메인 설정 화면 ───────────────────────────
    def _settings(self):
        self.state = ""
        cap  = C.get("TOTAL_CAPITAL", 0)
        bull = C.get("EXPOSURE_CAP_BULL", 1.0)
        side = C.get("EXPOSURE_CAP_SIDE", 0.7)
        bear = C.get("EXPOSURE_CAP_BEAR", 0.4)
        tp   = C.get("TAKE_PROFIT_FIXED", 0.15)
        ta   = C.get("TRAIL_ACTIVATE", 0.07)
        tg_btn(
            f"⚙️ <b>설정</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💵 총 자본: <b>{cap:,.0f}원</b>\n"
            f"📊 투자 한도: 상승 {bull:.0%} / 보합 {side:.0%} / 하락 {bear:.0%}\n"
            f"🎯 고정 익절: {tp:.0%}  |  🔺 트레일링 시작: {ta:.0%}\n"
            f"\n변경할 항목을 눌러주세요 👇",
            [[{"text": "💵 자본 & 투자 한도",  "callback_data": "set_cat:capital"}],
             [{"text": "🎯 수익 & 손절 기준",  "callback_data": "set_cat:profit"}],
             [{"text": "🔺 트레일링 스탑",     "callback_data": "set_cat:trail"}],
             [{"text": "🤖 AI 분석 기준",      "callback_data": "set_cat:ai"}],
             [{"text": "⏱️ 스캔 주기",         "callback_data": "set_cat:scan"}],
             [{"text": "📋 전체 설정 보기",    "callback_data": "set_showconfig"},
              {"text": "🔄 새로고침",          "callback_data": "set_reload"}],
             [{"text": "🧠 자동 최적화",       "callback_data": "optimizer"}],
             [{"text": "🏠 메인 메뉴",         "callback_data": "menu"}]]
        )

    # ── 카테고리 라우터 ──────────────────────────
    def _set_cat(self, cat: str):
        if cat == "capital": self._set_cat_capital()
        elif cat == "profit": self._set_cat_profit()
        elif cat == "trail":  self._set_cat_trail()
        elif cat == "ai":     self._set_cat_ai()
        elif cat == "scan":   self._set_cat_scan()

    # ════════════════════════════════════════════
    # 카테고리 1 — 💵 자본 & 투자 한도
    # ════════════════════════════════════════════
    def _set_cat_capital(self):
        cap  = C.get("TOTAL_CAPITAL", 0)
        bull = C.get("EXPOSURE_CAP_BULL", 1.0)
        side = C.get("EXPOSURE_CAP_SIDE", 0.7)
        bear = C.get("EXPOSURE_CAP_BEAR", 0.4)
        kelly = C.get("KELLY_MAX_FRACTION", 0.25)
        tg_btn(
            f"💵 <b>자본 & 투자 한도</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"총 자본: <b>{cap:,.0f}원</b>\n"
            f"투자 한도: 상승 {bull:.0%} / 보합 {side:.0%} / 하락 {bear:.0%}\n"
            f"켈리 상한: {kelly:.0%}",
            [[{"text": f"💵 총 자본  {cap:,.0f}원",     "callback_data": "set_cap:input"}],
             [{"text": f"📈 상승장 한도  {bull:.0%}",   "callback_data": "set_pct:EXPOSURE_CAP_BULL:70,80,100:capital"},
              {"text": f"➡️ 보합장 한도  {side:.0%}",   "callback_data": "set_pct:EXPOSURE_CAP_SIDE:50,70,80:capital"}],
             [{"text": f"📉 하락장 한도  {bear:.0%}",   "callback_data": "set_pct:EXPOSURE_CAP_BEAR:20,40,60:capital"},
              {"text": f"📐 켈리 상한  {kelly:.0%}",    "callback_data": "set_pct:KELLY_MAX_FRACTION:15,25,33:capital"}],
             [{"text": "🔙 설정으로", "callback_data": "settings"}]]
        )

    def _set_cap_input(self):
        cap = C.get("TOTAL_CAPITAL", 0)
        self.state = "awaiting_capital"
        tg_btn(
            f"💵 <b>총 자본 변경</b>\n"
            f"현재: <b>{cap:,.0f}원</b>\n\n"
            f"변경할 금액을 숫자로 입력해주세요\n"
            f"예) <code>5000000</code>  (500만원)",
            [[{"text": "❌ 취소", "callback_data": "set_cat:capital"}]]
        )

    def _do_set_capital(self, parts):
        self.state = ""
        try:
            new_cap = int(parts[0].replace(",", "").replace("원", ""))
            if new_cap < 100000:
                tg_btn("❌ 10만원 이상으로 입력해주세요",
                       [[{"text": "🔙 다시 입력", "callback_data": "set_cap:input"}]]); return
            old_cap = C.get("TOTAL_CAPITAL", 0)
            self._save_cfg("TOTAL_CAPITAL", new_cap)
            tg_btn(
                f"✅ <b>총 자본 변경 완료</b>\n"
                f"{old_cap:,.0f}원  →  <b>{new_cap:,.0f}원</b>\n즉시 반영됐어요",
                [[{"text": "🔙 자본 설정으로", "callback_data": "set_cat:capital"},
                  {"text": "🏠 메인 메뉴",    "callback_data": "menu"}]]
            )
        except:
            tg_btn("❌ 숫자만 입력해주세요\n예) <code>5000000</code>",
                   [[{"text": "🔙 다시 입력", "callback_data": "set_cap:input"}]])

    # ════════════════════════════════════════════
    # 카테고리 2 — 🎯 수익 & 손절
    # ════════════════════════════════════════════
    def _set_cat_profit(self):
        tp    = C.get("TAKE_PROFIT_FIXED", 0.15)
        atr_l = C.get("ATR_MULT_LARGE", 1.2)
        atr_s = C.get("ATR_MULT_SMALL", 2.0)
        atr_b = C.get("ATR_BEAR_MULT", 0.8)
        steps = C.get("PROFIT_ALERT_STEPS", [0.05, 0.10, 0.20])
        tg_btn(
            f"🎯 <b>수익 & 손절 기준</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"고정 익절: <b>{tp:.0%}</b>\n"
            f"수익 알림 구간: {', '.join([f'+{s:.0%}' for s in steps])}\n"
            f"ATR 손절 배수: 대형 {atr_l:.1f}× / 중소형 {atr_s:.1f}×\n"
            f"하락장 손절 강화: {atr_b:.1f}×",
            [[{"text": f"🎯 고정 익절  {tp:.0%}",          "callback_data": "set_pct:TAKE_PROFIT_FIXED:10,15,20,25:profit"}],
             [{"text": f"📢 수익 알림 구간",                "callback_data": "set_steps:profit"}],
             [{"text": f"🛑 ATR 대형주  {atr_l:.1f}×",     "callback_data": "set_mult:ATR_MULT_LARGE:0.8,1.0,1.2,1.5:profit"},
              {"text": f"🛑 ATR 중소형  {atr_s:.1f}×",     "callback_data": "set_mult:ATR_MULT_SMALL:1.5,2.0,2.5:profit"}],
             [{"text": f"🛑 하락장 강화  {atr_b:.1f}×",    "callback_data": "set_mult:ATR_BEAR_MULT:0.7,0.8,1.0:profit"}],
             [{"text": "🔙 설정으로", "callback_data": "settings"}]]
        )

    def _set_steps(self, cat: str):
        """수익 알림 구간 ON/OFF 토글"""
        steps   = C.get("PROFIT_ALERT_STEPS", [0.05, 0.10, 0.20])
        all_opt = [0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.25, 0.30]
        btns = []
        row = []
        for s in all_opt:
            mark = "✅" if s in steps else "⬜"
            row.append({"text": f"{mark} +{s:.0%}",
                        "callback_data": f"set_steps_toggle:{s:.2f}:{cat}"})
            if len(row) == 4:
                btns.append(row); row = []
        if row: btns.append(row)
        btns.append([{"text": "🔙 돌아가기", "callback_data": f"set_cat:{cat}"}])
        cur = ", ".join([f"+{s:.0%}" for s in sorted(steps)])
        tg_btn(f"📢 <b>수익 알림 구간</b>\n현재: <b>{cur}</b>\n\n버튼을 눌러 ON/OFF 토글하세요", btns)

    def _set_steps_toggle(self, val_str: str, cat: str):
        try:
            val   = float(val_str)
            steps = list(C.get("PROFIT_ALERT_STEPS", [0.05, 0.10, 0.20]))
            if val in steps:
                if len(steps) > 1: steps.remove(val)
            else:
                steps.append(val)
            steps.sort()
            self._save_cfg("PROFIT_ALERT_STEPS", steps)
            self._set_steps(cat)
        except:
            self._set_steps(cat)

    # ════════════════════════════════════════════
    # 카테고리 3 — 🔺 트레일링 스탑
    # ════════════════════════════════════════════
    def _set_cat_trail(self):
        ta   = C.get("TRAIL_ACTIVATE", 0.07)
        tm   = C.get("TRAIL_ATR_MULT_DEFAULT", 2.0)  # 기본 배수 (대형·소형 별도 설정)
        tt   = C.get("TRAIL_TIGHTEN_RET", 0.25)
        ttm  = C.get("TRAIL_TIGHTEN_MULT", 0.7)
        tbm  = C.get("TRAIL_BEAR_MULT", 0.8)
        tg_btn(
            f"🔺 <b>트레일링 스탑</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"시작 수익률: <b>{ta:.0%}</b>  (이 수익 넘으면 추적 시작)\n"
            f"ATR 배수: <b>{tm:.1f}×</b>  (고점에서 이만큼 내리면 매도)\n"
            f"조임 시작: <b>{tt:.0%}</b>  (이 수익 넘으면 더 빡빡하게)\n"
            f"조임 배수: <b>{ttm:.1f}×</b>  (조임 시 ATR 배수 감소)\n"
            f"하락장 배수: <b>{tbm:.1f}×</b>",
            [[{"text": f"🔺 시작 수익률  {ta:.0%}",    "callback_data": "set_pct:TRAIL_ACTIVATE:5,7,10,15:trail"}],
             [{"text": f"📏 기본 ATR 배수  {tm:.1f}×",  "callback_data": "set_mult:TRAIL_ATR_MULT_DEFAULT:1.5,2.0,2.5,3.0:trail"}],
             [{"text": f"📐 조임 시작  {tt:.0%}",      "callback_data": "set_pct:TRAIL_TIGHTEN_RET:15,20,25,30:trail"},
              {"text": f"📐 조임 배수  {ttm:.1f}×",    "callback_data": "set_mult:TRAIL_TIGHTEN_MULT:0.5,0.7,0.8:trail"}],
             [{"text": f"📉 하락장 배수  {tbm:.1f}×",  "callback_data": "set_mult:TRAIL_BEAR_MULT:0.7,0.8,1.0:trail"}],
             [{"text": "🔙 설정으로", "callback_data": "settings"}]]
        )

    # ════════════════════════════════════════════
    # 카테고리 4 — 🤖 AI 분석 기준
    # ════════════════════════════════════════════
    def _set_cat_ai(self):
        es   = C.get("EDGE_SURGE_THRESHOLD", 0.15)
        vol  = C.get("VOL_SURGE_MULT", 3.0)
        kadj = C.get("KIND_EDGE_ADJ", 0.05)
        # [Issue-7 수정] fallback 0.75 → 0.70 (DEFAULT_CONFIG 실제값 및 BT 상수와 통일)
        corr = C.get("CORR_HIGH_THRESHOLD", 0.70)
        slip = C.get("SLIPPAGE_FILTER_RATIO", 3.0)
        # REGIME_EDGE_THRESHOLD는 별도 상수라 표시만
        bull_e = REGIME_EDGE_THRESHOLD.get("BULL", 0.55)
        side_e = REGIME_EDGE_THRESHOLD.get("SIDE", 0.60)
        bear_e = REGIME_EDGE_THRESHOLD.get("BEAR", 0.75)
        tg_btn(
            f"🤖 <b>AI 분석 기준</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"AI 진입 기준: 상승 {bull_e:.0%} / 보합 {side_e:.0%} / 하락 {bear_e:.0%}\n"
            f"AI점수 급등 알림: <b>+{es:.0%}</b> 이상 변동 시\n"
            f"거래량 급증 알림: 평소 <b>{vol:.1f}배</b> 이상\n"
            f"공시 보정값: <b>{kadj:.2f}</b>\n"
            f"상관관계 경고: <b>{corr:.0%}</b> 이상",
            [[{"text": f"🚀 AI점수 급등 기준  +{es:.0%}",  "callback_data": "set_pct:EDGE_SURGE_THRESHOLD:10,15,20,25:ai"}],
             [{"text": f"📢 거래량 급증  {vol:.1f}배",      "callback_data": "set_mult:VOL_SURGE_MULT:2.0,3.0,5.0:ai"}],
             [{"text": f"📰 공시 보정값  {kadj:.2f}",       "callback_data": "set_mult:KIND_EDGE_ADJ:0.03,0.05,0.08:ai"},
              {"text": f"🔗 상관관계 경고  {corr:.0%}",     "callback_data": "set_pct:CORR_HIGH_THRESHOLD:60,75,85:ai"}],
             [{"text": f"🎚️ 슬리피지 필터  {slip:.1f}×",   "callback_data": "set_mult:SLIPPAGE_FILTER_RATIO:2.0,3.0,4.0:ai"}],
             [{"text": "🔙 설정으로", "callback_data": "settings"}]]
        )

    # ════════════════════════════════════════════
    # 카테고리 5 — ⏱️ 스캔 주기
    # ════════════════════════════════════════════
    def _set_cat_scan(self):
        hc  = C.get("HOLD_CHECK_MIN", 1)
        sc  = C.get("SCAN_CHECK_MIN", 5)
        ttl = C.get("CACHE_TTL_SEC", 300)
        tg_btn(
            f"⏱️ <b>스캔 주기</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"보유 종목 체크: <b>{hc}분</b>마다\n"
            f"유니버스 스캔: <b>{sc}분</b>마다\n"
            f"데이터 캐시: <b>{ttl}초</b>",
            [[{"text": f"🔍 보유 체크  {hc}분",     "callback_data": "set_min:HOLD_CHECK_MIN:1,3,5:scan"},
              {"text": f"📡 유니버스 스캔  {sc}분",  "callback_data": "set_min:SCAN_CHECK_MIN:3,5,10:scan"}],
             [{"text": f"💾 캐시 시간  {ttl}초",     "callback_data": "set_min:CACHE_TTL_SEC:60,300,600:scan"}],
             [{"text": "🔙 설정으로", "callback_data": "settings"}]]
        )

    # ════════════════════════════════════════════
    # 공용 프리셋 선택기
    # ════════════════════════════════════════════
    def _set_pct(self, key: str, opts_str: str, back: str):
        """% 단위 프리셋 선택 (opts_str = '10,15,20,25')"""
        cur  = C.get(key, 0)
        opts = [int(x) for x in opts_str.split(",")]
        label_map = {
            "EXPOSURE_CAP_BULL":     "📈 상승장 한도",
            "EXPOSURE_CAP_SIDE":     "➡️ 보합장 한도",
            "EXPOSURE_CAP_BEAR":     "📉 하락장 한도",
            "KELLY_MAX_FRACTION":    "📐 켈리 상한",
            "TAKE_PROFIT_FIXED":     "🎯 고정 익절",
            "TRAIL_ACTIVATE":        "🔺 트레일링 시작",
            "TRAIL_TIGHTEN_RET":     "📐 트레일링 조임 시작",
            "EDGE_SURGE_THRESHOLD":  "🚀 AI점수 급등 기준",
            "CORR_HIGH_THRESHOLD":   "🔗 상관관계 경고",
            "SLIPPAGE_FILTER_RATIO": "🎚️ 슬리피지 필터",
        }
        lbl  = label_map.get(key, key)
        btns = []
        row  = []
        for pct in opts:
            val  = pct / 100
            mark = " ✅" if abs(val - cur) < 0.005 else ""
            row.append({"text": f"{pct}%{mark}",
                        "callback_data": f"set_apply:{key}:{pct}:{back}"})
            if len(row) == 4: btns.append(row); row = []
        if row: btns.append(row)
        btns.append([{"text": "🔙 돌아가기", "callback_data": f"set_cat:{back}"}])
        tg_btn(f"{lbl}\n현재: <b>{cur:.0%}</b>\n\n변경할 값을 선택하세요", btns)

    def _set_mult(self, key: str, opts_str: str, back: str):
        """배수/소수 단위 프리셋 선택"""
        cur  = C.get(key, 0)
        opts = [float(x) for x in opts_str.split(",")]
        label_map = {
            "ATR_MULT_LARGE":        "🛑 ATR 손절 대형주",
            "ATR_MULT_SMALL":        "🛑 ATR 손절 중소형",
            "ATR_BEAR_MULT":         "🛑 하락장 손절 강화",
            "TRAIL_ATR_MULT_DEFAULT":"📏 트레일링 ATR 배수(기본)",
            "TRAIL_TIGHTEN_MULT":    "📐 트레일링 조임 배수",
            "TRAIL_BEAR_MULT":       "📉 하락장 트레일링",
            "VOL_SURGE_MULT":        "📢 거래량 급증 배수",
            "KIND_EDGE_ADJ":         "📰 공시 보정값",
            "SLIPPAGE_FILTER_RATIO": "🎚️ 슬리피지 필터",
        }
        lbl  = label_map.get(key, key)
        btns = []
        row  = []
        for val in opts:
            mark = " ✅" if abs(val - cur) < 0.01 else ""
            txt  = f"{val:.0%}" if val < 1 else f"{val:.1f}×"
            row.append({"text": f"{txt}{mark}",
                        "callback_data": f"set_apply_f:{key}:{val}:{back}"})
            if len(row) == 4: btns.append(row); row = []
        if row: btns.append(row)
        btns.append([{"text": "🔙 돌아가기", "callback_data": f"set_cat:{back}"}])
        cur_txt = f"{cur:.0%}" if cur < 1 else f"{cur:.1f}×"
        tg_btn(f"{lbl}\n현재: <b>{cur_txt}</b>\n\n변경할 값을 선택하세요", btns)

    def _set_min(self, key: str, opts_str: str, back: str):
        """분/초 단위 프리셋 선택"""
        cur  = C.get(key, 0)
        opts = [int(x) for x in opts_str.split(",")]
        label_map = {
            "HOLD_CHECK_MIN":  "🔍 보유 체크 주기",
            "SCAN_CHECK_MIN":  "📡 유니버스 스캔 주기",
            "CACHE_TTL_SEC":   "💾 데이터 캐시 시간",
        }
        unit = "초" if "SEC" in key else "분"
        lbl  = label_map.get(key, key)
        btns = []
        row  = []
        for v in opts:
            mark = " ✅" if v == cur else ""
            row.append({"text": f"{v}{unit}{mark}",
                        "callback_data": f"set_apply_i:{key}:{v}:{back}"})
        btns.append(row)
        btns.append([{"text": "🔙 돌아가기", "callback_data": f"set_cat:{back}"}])
        tg_btn(f"{lbl}\n현재: <b>{cur}{unit}</b>\n\n변경할 값을 선택하세요", btns)

    def _set_apply(self, key: str, pct_str: str, back: str):
        """% 값 적용"""
        try:
            new_val = int(pct_str) / 100
            old_val = C.get(key, 0)
            self._save_cfg(key, new_val)
            tg_btn(
                f"✅ <b>변경 완료</b>\n{old_val:.0%}  →  <b>{new_val:.0%}</b>\n즉시 반영됐어요",
                [[{"text": f"🔙 {back}으로", "callback_data": f"set_cat:{back}"},
                  {"text": "🏠 메인 메뉴",   "callback_data": "menu"}]]
            )
        except: self._set_pct(key, pct_str, back)

    def _set_apply_f(self, key: str, val_str: str, back: str):
        """float 값 적용"""
        try:
            new_val = float(val_str)
            old_val = C.get(key, 0)
            self._save_cfg(key, new_val)
            old_txt = f"{old_val:.0%}" if old_val < 1 else f"{old_val:.1f}×"
            new_txt = f"{new_val:.0%}" if new_val < 1 else f"{new_val:.1f}×"
            tg_btn(
                f"✅ <b>변경 완료</b>\n{old_txt}  →  <b>{new_txt}</b>\n즉시 반영됐어요",
                [[{"text": f"🔙 돌아가기", "callback_data": f"set_cat:{back}"},
                  {"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
        except: pass

    def _set_apply_i(self, key: str, val_str: str, back: str):
        """int 값 적용"""
        try:
            new_val = int(val_str)
            old_val = C.get(key, 0)
            self._save_cfg(key, new_val)
            unit = "초" if "SEC" in key else "분"
            tg_btn(
                f"✅ <b>변경 완료</b>\n{old_val}{unit}  →  <b>{new_val}{unit}</b>\n즉시 반영됐어요",
                [[{"text": f"🔙 돌아가기", "callback_data": f"set_cat:{back}"},
                  {"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
            )
        except: pass

    # ── 전체 설정 보기 ───────────────────────────
    def _set_showconfig(self):
        labels = {
            "TOTAL_CAPITAL":         "💵 총 자본",
            "EXPOSURE_CAP_BULL":     "📈 상승장 한도",
            "EXPOSURE_CAP_SIDE":     "➡️ 보합장 한도",
            "EXPOSURE_CAP_BEAR":     "📉 하락장 한도",
            "KELLY_MAX_FRACTION":    "📐 켈리 상한",
            "TAKE_PROFIT_FIXED":     "🎯 고정 익절",
            "TRAIL_ACTIVATE":        "🔺 트레일링 시작",
            "TRAIL_ATR_MULT_DEFAULT":"🔺 트레일링 배수(기본)",
            "TRAIL_TIGHTEN_RET":     "🔺 조임 시작",
            "ATR_MULT_LARGE":        "🛑 ATR 대형주",
            "ATR_MULT_SMALL":        "🛑 ATR 중소형",
            "ATR_BEAR_MULT":         "🛑 하락장 강화",
            "EDGE_SURGE_THRESHOLD":  "🚀 AI급등 기준",
            "VOL_SURGE_MULT":        "📢 거래량 급증",
            "KIND_EDGE_ADJ":         "📰 공시 보정",
            "HOLD_CHECK_MIN":        "⏱️ 보유 체크",
            "SCAN_CHECK_MIN":        "⏱️ 유니버스 스캔",
        }
        lines = ["📋 <b>전체 설정값</b>", "━━━━━━━━━━━━━━━━━━"]
        for k, lbl in labels.items():
            v = C.get(k)
            if v is None: continue
            if k == "TOTAL_CAPITAL":
                lines.append(f"  {lbl}: <b>{v:,.0f}원</b>")
            elif isinstance(v, float) and v <= 1.0:
                lines.append(f"  {lbl}: <b>{v:.0%}</b>")
            elif isinstance(v, float):
                lines.append(f"  {lbl}: <b>{v:.1f}×</b>")
            elif isinstance(v, int) and "MIN" in k:
                lines.append(f"  {lbl}: <b>{v}분</b>")
            elif isinstance(v, int) and "SEC" in k:
                lines.append(f"  {lbl}: <b>{v}초</b>")
            else:
                lines.append(f"  {lbl}: <b>{v}</b>")
        tg_btn("\n".join(lines),
               [[{"text": "⚙️ 설정으로", "callback_data": "settings"},
                 {"text": "🏠 메인 메뉴", "callback_data": "menu"}]])

    # ── 설정 새로고침 ────────────────────────────
    def _set_reload(self):
        global C
        C = load_config()
        tg_btn(
            f"🔄 <b>설정 새로고침 완료</b>\n"
            f"config.json을 다시 읽었어요\n\n"
            f"💵 총 자본: {C.get('TOTAL_CAPITAL',0):,.0f}원\n"
            f"📈 상승 {C.get('EXPOSURE_CAP_BULL',1):.0%} / "
            f"➡️ 보합 {C.get('EXPOSURE_CAP_SIDE',0.7):.0%} / "
            f"📉 하락 {C.get('EXPOSURE_CAP_BEAR',0.4):.0%}",
            [[{"text": "⚙️ 설정으로", "callback_data": "settings"},
              {"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
        )

    # ════════════════════════════════════════════
    # 🤖 자동 최적화 메뉴
    # ════════════════════════════════════════════
    def _optimizer_menu(self):
        logs  = load_trade_log()
        closed = [t for t in logs if t.get("exit_price", 0) > 0]
        cnt   = len(closed)
        wr    = (sum(1 for t in closed
                     if (t.get("exit_price",0)-t.get("buy_price",0)) > 0) / cnt
                 if cnt > 0 else 0)
        tg_btn(
            f"🤖 <b>자동 최적화</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"실거래 데이터를 분석해서\n"
            f"파라미터를 자동으로 조정해요\n"
            f"\n"
            f"📊 분석 가능한 거래: <b>{cnt}건</b>\n"
            f"🏆 현재 승률: <b>{wr:.1%}</b>\n"
            f"\n"
            f"💡 최소 5건 이상 필요해요\n"
            f"   매월 마지막 금요일 자동 실행됩니다",
            [[{"text": "🔍 미리보기 (변경 없음)", "callback_data": "opt_preview"}],
             [{"text": "⚡ 지금 바로 최적화 적용", "callback_data": "opt_apply"}],
             [{"text": "📊 최근 분석 결과 보기",  "callback_data": "opt_last"}],
             [{"text": "🔙 설정으로", "callback_data": "settings"},
              {"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
        )

    def _optimizer_preview(self):
        logs   = load_trade_log()
        closed = [t for t in logs if t.get("exit_price", 0) > 0]
        if len(closed) < 5:  # [v40.0] apply와 동일하게 5건으로 통일
            tg_btn(
                f"❌ <b>거래 데이터 부족</b>\n"
                f"현재 {len(closed)}건\n"
                f"최소 5건 이상 필요해요\n"
                f"조금 더 거래하고 다시 시도해주세요",
                [[{"text": "🔙 돌아가기", "callback_data": "optimizer"}]]
            )
            return
        tg("🔍 <b>최적화 미리보기 실행 중...</b>\n잠시 기다려주세요 (30초 내)")
        self.monitor._run_auto_optimizer(dry_run=True)

    def _optimizer_apply(self):
        logs   = load_trade_log()
        closed = [t for t in logs if t.get("exit_price", 0) > 0]
        if len(closed) < 5:
            tg_btn(
                f"❌ <b>거래 데이터 부족</b>\n"
                f"현재 {len(closed)}건\n"
                f"최소 5건 이상 필요해요",
                [[{"text": "🔙 돌아가기", "callback_data": "optimizer"}]]
            )
            return
        tg_btn(
            f"⚠️ <b>최적화를 적용할까요?</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"실거래 {len(closed)}건을 분석해서\n"
            f"config.json과 백테스트 소스를\n"
            f"자동으로 수정해요\n"
            f"\n"
            f"⚠️ 이 작업은 되돌리기 어려워요\n"
            f"먼저 미리보기를 확인하세요",
            [[{"text": "✅ 예, 최적화 적용",   "callback_data": "opt_apply_confirm"}],
             [{"text": "🔍 미리보기 먼저",      "callback_data": "opt_preview"}],
             [{"text": "❌ 취소",               "callback_data": "optimizer"}]]
        )

    def _optimizer_apply_confirm(self):
        tg("⚡ <b>자동 최적화 실행 중...</b>\n완료되면 결과를 보내드려요")
        self.monitor._run_auto_optimizer(dry_run=False)

    def _optimizer_last(self):
        """마지막 최적화 결과 요약"""
        logs   = load_trade_log()
        closed = [t for t in logs if t.get("exit_price", 0) > 0]
        if not closed:
            tg_btn("📊 아직 완료된 거래가 없어요",
                   [[{"text": "🔙 돌아가기", "callback_data": "optimizer"}]])
            return
        rets  = [(t["exit_price"] - t["buy_price"]) / t["buy_price"] for t in closed]
        wins  = [r for r in rets if r > 0]
        pnls  = [(t["exit_price"] - t["buy_price"]) * t.get("shares", 1) for t in closed]

        by_reason = {}
        for t in closed:
            r = t.get("reason", "기타")
            by_reason.setdefault(r, []).append(
                (t["exit_price"] - t["buy_price"]) / t["buy_price"])

        lines = [
            f"📊 <b>실거래 분석 요약</b>",
            f"━━━━━━━━━━━━━━━━━━",
            f"총 거래: {len(closed)}건",
            f"승률: {len(wins)/len(closed):.1%}",
            f"평균 수익: {sum(rets)/len(rets):+.2%}",
            f"총 손익: {sum(pnls):+,.0f}원",
            f"",
            f"📋 <b>청산 이유별 성과</b>",
        ]
        for reason, rs in by_reason.items():
            w = sum(1 for r in rs if r > 0)
            lines.append(
                f"  {reason}: {len(rs)}건 | "
                f"승률 {w/len(rs):.0%} | "
                f"평균 {sum(rs)/len(rs):+.2%}")

        cfg = C
        lines += [
            f"",
            f"⚙️ <b>현재 파라미터</b>",
            f"  ATR 중소형: {cfg.get('ATR_MULT_SMALL',2.0):.1f}×",
            f"  트레일링 시작: {cfg.get('TRAIL_ACTIVATE',0.07):.0%}",
            f"  고정 익절: {cfg.get('TAKE_PROFIT_FIXED',0.15):.0%}",
            f"  켈리 비율: {cfg.get('KELLY_MAX_FRACTION',0.25):.0%}",
        ]
        tg_btn("\n".join(lines),
               [[{"text": "⚡ 최적화 적용",   "callback_data": "opt_apply"},
                 {"text": "🔙 돌아가기",       "callback_data": "optimizer"}]])

    # ════════════════════════════════════════════
    # 투자 모드 전환 / 비상정지
    # ════════════════════════════════════════════

    def _check_connection(self):
        """🔍 연결 확인 — 현재 모의/실계좌 접속 상태 및 예수금 조회"""
        kw = kiwoom()
        if not kw:
            tg("❌ 키움 클라이언트 연결 실패\nkiwoom_client.py를 확인해주세요.")
            return

        mode_icon = "🔵" if kw._mock else "🟢"
        mode_str  = "모의투자" if kw._mock else "실제투자(실계좌)"
        host_str  = kw._host
        account   = kw._account or "계좌번호 없음"

        # 토큰 발급 확인
        token_ok = kw._ensure_token()
        token_str = "✅ 정상" if token_ok else "❌ 실패"

        # 예수금 조회 (실제 API 호출)
        deposit = 0
        deposit_str = "조회 실패"
        try:
            deposit = kw.get_deposit()
            deposit_str = f"{deposit:,}원" if deposit > 0 else "0원 (장마감 또는 잔고없음)"
        except Exception as e:
            deposit_str = f"오류: {str(e)[:40]}"

        # 잔고 조회
        balance = []
        try:
            balance = kw.get_balance()
        except Exception:
            pass

        msg = (
            f"{mode_icon} <b>키움 연결 확인</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📡 모드: <b>{mode_str}</b>\n"
            f"🏦 계좌: {account}\n"
            f"🌐 서버: {host_str}\n"
            f"🔑 토큰: {token_str}\n"
            f"💰 예수금: {deposit_str}\n"
        )
        if balance:
            msg += f"\n📦 <b>보유종목 ({len(balance)}개)</b>\n"
            for b in balance[:5]:
                sign = "+" if b["pnl"] >= 0 else ""
                msg += (f"• {b['name']} {b['qty']}주 "
                        f"{sign}{b['pnl_pct']:.1f}%\n")
            if len(balance) > 5:
                msg += f"  ... 외 {len(balance)-5}개\n"
        else:
            msg += "\n📦 보유종목 없음\n"

        tg(msg)

    def _trading_real(self):
        """🟢 실제투자 실행 — 모의 → 실계좌 전환"""
        import os
        global EMERGENCY_STOP
        EMERGENCY_STOP = False  # 비상정지 해제

        env_path = _get_env_path()
        _set_env_value(env_path, "KIWOOM_MOCK", "false")

        # 싱글턴 리셋 → 다음 호출 시 실계좌로 재연결
        import kiwoom_client as _kc
        _kc._client = None

        # 실계좌 예수금 + 보유평가금 조회 → TOTAL_CAPITAL 자동 동기화
        _deposit_str = "조회 실패"
        _balance_str = ""
        _sync_str    = ""
        try:
            _kw = kiwoom()
            if _kw:
                _dep = _kw.get_deposit()
                _bal = _kw.get_balance()
                _eval_total = sum(b.get("eval_amt", 0) for b in _bal)
                _total = _dep + _eval_total
                _deposit_str = f"{_dep:,.0f}원"
                _balance_str = (f"📦 보유평가금: {_eval_total:,.0f}원\n"
                                f"💰 총 자산: {_total:,.0f}원")
                # TOTAL_CAPITAL 자동 동기화 (실계좌 총자산 기준)
                if _total > 0:
                    _old_cap = C.get("TOTAL_CAPITAL", 0)
                    _new_cap = round(_total, -4)
                    _save_cfg_direct("TOTAL_CAPITAL", _new_cap)
                    globals()["C"] = load_config()
                    _sync_str = (f"\n🔄 운용자본 자동 동기화\n"
                                 f"  {_old_cap:,.0f}원 → <b>{_new_cap:,.0f}원</b>")
                    log.info(f"[실계좌 전환] TOTAL_CAPITAL 동기화: {_old_cap:,.0f} → {_new_cap:,.0f}")
        except Exception as _e:
            log.warning(f"실계좌 예수금 조회 실패: {_e}")

        tg_btn(
            "🟢 <b>실제투자 모드로 전환했어요!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚠️ 지금부터 모든 매수·매도가\n"
            "<b>실계좌</b>에 실제 주문으로 전송됩니다.\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<b>✅ 실계좌 잔고 확인</b>\n"
            f"💵 주문가능 예수금: {_deposit_str}\n"
            f"{_balance_str}"
            f"{_sync_str}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔴 중단하려면 비상정지 버튼을 누르세요.",
            [[{"text": "🔴 비상정지",      "callback_data": "emergency_stop"},
              {"text": "🏠 메인 메뉴",     "callback_data": "menu"}]]
        )

    def _trading_mock(self):
        """🔵 모의투자 전환 — 실계좌 → 모의 복귀"""
        env_path = _get_env_path()
        _set_env_value(env_path, "KIWOOM_MOCK", "true")

        import kiwoom_client as _kc
        _kc._client = None

        # 모의계좌 예수금 + 보유평가금 조회 → TOTAL_CAPITAL 자동 동기화
        _deposit_str = "조회 실패"
        _balance_str = ""
        _sync_str    = ""
        try:
            _kw = kiwoom()
            if _kw:
                _dep = _kw.get_deposit()
                _bal = _kw.get_balance()
                _eval_total = sum(b.get("eval_amt", 0) for b in _bal)
                _total = _dep + _eval_total
                _deposit_str = f"{_dep:,.0f}원"
                _balance_str = (f"📦 보유평가금: {_eval_total:,.0f}원\n"
                                f"💰 총 자산: {_total:,.0f}원")
                # TOTAL_CAPITAL 자동 동기화 (모의계좌 총자산 기준)
                if _total > 0:
                    _old_cap = C.get("TOTAL_CAPITAL", 0)
                    _new_cap = round(_total, -4)
                    _save_cfg_direct("TOTAL_CAPITAL", _new_cap)
                    globals()["C"] = load_config()
                    _sync_str = (f"\n🔄 운용자본 자동 동기화\n"
                                 f"  {_old_cap:,.0f}원 → <b>{_new_cap:,.0f}원</b>")
                    log.info(f"[모의 전환] TOTAL_CAPITAL 동기화: {_old_cap:,.0f} → {_new_cap:,.0f}")
        except Exception as _e:
            log.warning(f"모의계좌 예수금 조회 실패: {_e}")

        tg_btn(
            "🔵 <b>모의투자 모드로 전환했어요!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "✅ 지금부터 모든 주문이 모의계좌로 전송됩니다.\n"
            "실계좌에는 영향이 없어요.\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<b>✅ 모의계좌 잔고 확인</b>\n"
            f"💵 주문가능 예수금: {_deposit_str}\n"
            f"{_balance_str}"
            f"{_sync_str}",
            [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
        )

    def _emergency_stop(self):
        """🔴 비상정지 — 모든 자동 주문 즉시 중단"""
        global EMERGENCY_STOP
        EMERGENCY_STOP = True
        tg_btn(
            "🔴 <b>비상정지 완료!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "✅ 모든 자동 매수·매도 주문이 중단됐어요.\n"
            "보유종목은 그대로 유지됩니다.\n\n"
            "⚠️ 재개하려면 메인 메뉴에서\n"
            "🟢실제투자 또는 🔵모의투자를 선택하세요.",
            [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]]
        )

    # ════════════════════════════════════════════
    # 유니버스 추가·제거 (텍스트 전용)
    # ════════════════════════════════════════════
    def _add(self, ticker_raw: str):
        ticker = ticker_raw.zfill(6)
        if ticker in self.monitor.universe:
            tg(f"ℹ️ {resolve_name(ticker)}은(는) 이미 관심 종목에 있어요."); return
        name = resolve_name(ticker)
        self.monitor.universe[ticker] = name
        save_universe(self.monitor.universe)
        tg(f"➕ 관심 종목 추가: <b>{name}</b>\n현재 {len(self.monitor.universe)}개 관찰 중")

    def _remove(self, ticker_raw: str):
        ticker = ticker_raw.zfill(6)
        if ticker in self.monitor.positions:
            tg("❌ 보유 중인 종목은 제거할 수 없어요.\n먼저 매도를 완료해주세요."); return
        name = self.monitor.universe.pop(ticker, resolve_name(ticker))
        save_universe(self.monitor.universe)
        tg(f"➖ 관심 종목 제거: <b>{name}</b>\n현재 {len(self.monitor.universe)}개 관찰 중")

class EdgeMonitor:
    def __init__(self):
        self.positions     = load_positions()
        self.universe      = load_universe()
        self.regime        = "SIDE"
        self.last_hash     = ""
        self.vol_alerted   = set()
        self.prev_edge     = {}
        self.today_alerts  = 0
        self.today_exited       = set()
        self.last_offhours_hash = ""
        self.prev_regime        = "SIDE"
        self.consec_loss        = 0
        self.consec_win         = 0   # 연속 수익 추적
        self._circuit_active    = False  # ㊱ 서킷브레이커 상태
        self._weekly_trend_cache = {}   # FIX-2: 주봉 추세 캐시 {ticker: bool}
        # 시작 시 이름 전체 캐시
        for tk, nm in self.universe.items():
            if nm and nm != tk: _name_cache[tk] = nm
        for tk, info in self.positions.items():
            nm = info.get("name", "")
            if nm and nm != tk: _name_cache[tk] = nm
        log.info(f"  유니버스 {len(self.universe)}개 / 보유 {len(self.positions)}개")

    def update_regime(self):
        new_regime = calc_regime_from_kospi()
        log.info(f"  📡 국면: {new_regime}")

        # 국면 전환 감지 알람
        if new_regime != self.prev_regime:
            old_thr  = REGIME_EDGE_THRESHOLD.get(self.prev_regime, 0.60)
            new_thr  = REGIME_EDGE_THRESHOLD.get(new_regime, 0.60)
            old_cap  = C.get(f"EXPOSURE_CAP_{self.prev_regime}", 0.70)
            new_cap  = C.get(f"EXPOSURE_CAP_{new_regime}", 0.70)
            icons    = {"BULL": "📈 상승장", "SIDE": "➡️ 보합장", "BEAR": "📉 하락장"}
            old_desc = icons.get(self.prev_regime, self.prev_regime)
            new_desc = icons.get(new_regime, new_regime)

            if new_regime == "BEAR":
                action = (f"🚨 <b>주의가 필요해요!</b>\n"
                          f"  • 앞으로 주식이 전반적으로 내릴 수 있어요\n"
                          f"  • AI가 더 까다롭게 종목을 고를 거예요\n"
                          f"    (기준: {old_thr:.0%} → {new_thr:.0%}으로 강화)\n"
                          f"  • 투자 금액도 줄이는 게 안전해요\n"
                          f"    (권장 비중: {old_cap:.0%} → {new_cap:.0%})\n"
                          f"\n"
                          f"💡 지금 당장 다 팔 필요는 없지만\n"
                          f"   손절 가격을 한 번 더 확인해두세요")
            elif new_regime == "BULL":
                action = (f"✅ <b>좋은 신호예요!</b>\n"
                          f"  • 주식이 전반적으로 오르는 시기예요\n"
                          f"  • AI 추천 기준이 완화돼요\n"
                          f"    (기준: {old_thr:.0%} → {new_thr:.0%})\n"
                          f"  • 투자 비중을 늘려도 좋아요\n"
                          f"    (권장 비중: {old_cap:.0%} → {new_cap:.0%})")
            else:
                action = (f"ℹ️ 방향이 불확실한 시기예요\n"
                          f"  신중하게 접근하는 게 좋아요")

            tg(f"🔔 <b>시장 분위기가 바뀌었어요!</b>\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"{old_desc}  →  <b>{new_desc}</b>\n"
               f"\n"
               f"이게 무슨 뜻이냐면:\n"
               f"{action}")
            # 보유 종목 AI점수 영향 분석
            if self.positions:
                hold_impact = []
                for _tk, _info in self.positions.items():
                    _nm  = _info.get("name", resolve_name(_tk))
                    _df  = get_ohlcv(_tk, days=60)
                    if _df is None: continue
                    _ka  = fetch_kind_sentiment(_tk)
                    _eg  = calculate_edge_v27(_df, _ka, _tk)
                    _thr = REGIME_EDGE_THRESHOLD.get(new_regime, 0.60)
                    _ok  = "✅" if _eg >= _thr else "⚠️"
                    _bp  = float(_info.get("buy_price", 0))
                    _cp  = get_current_price(_tk)
                    _ret = (_cp - _bp) / _bp if _bp > 0 and _cp > 0 else 0
                    hold_impact.append(
                        f"  {_ok} {_nm}: AI {int(_eg*100)}점 "
                        f"(기준 {int(_thr*100)}점) | {_ret:+.2%}"
                    )
                if hold_impact:
                    tg(
                        f"📋 <b>국면 전환 후 보유 종목 영향</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        + "\n".join(hold_impact) +
                        f"\n━━━━━━━━━━━━━━━━━━\n"
                        f"✅ 기준 이상 → 보유 유지 적합\n"
                        f"⚠️ 기준 미달 → 매도 검토 필요"
                    )

            log.info(f"  🔔 국면 전환: {self.prev_regime} → {new_regime}")

        self.prev_regime = new_regime
        self.regime      = new_regime

    def do_refresh_universe(self):
        if not is_trading_day():
            log.info("📅 오늘은 휴장일 — 유니버스 갱신 스킵")
            return
        self.universe = refresh_universe(self.positions)
        self.vol_alerted.clear()
        self.today_exited.clear()   # 날짜 바뀌면 재진입 차단 초기화

        # ── 캐시 Purge: 유니버스+보유에 없는 종목만 선택 삭제 ──
        # invalidate_cache() 전체 삭제 대신 미사용 종목만 제거하여
        # 보유 종목 데이터는 유지 → 다음 check_holdings에서 API 재호출 불필요
        active_tickers = set(self.universe.keys()) | set(self.positions.keys())
        stale_ohlcv    = [tk for tk in list(_ohlcv_cache.keys())
                          if tk not in active_tickers]
        for tk in stale_ohlcv:
            _ohlcv_cache.pop(tk, None)
            _foreign_net_cache.pop(tk, None)  # 외국인 순매수 캐시도 함께 정리

        # edge_cache TTL 만료 항목 정리 (id 기반이라 종목별 삭제 불필요)
        purged_edge = _purge_edge_cache()

        total_purged = len(stale_ohlcv) + purged_edge
        if total_purged:
            log.info(f"🧹 캐시 정리: ohlcv {len(stale_ohlcv)}개 + "
                     f"edge {purged_edge}개 제거 "
                     f"(활성 {len(active_tickers)}개 유지)")

    def _log_exit(self, ticker: str, info: dict,
                  exit_price: float, reason: str):
        buy_price  = float(info.get("buy_price", 0))
        shares     = int(info.get("shares", 0))
        amount     = buy_price * shares
        entry_date = info.get("entry_date", "")
        hold_days  = ((date.today() - date.fromisoformat(entry_date)).days
                      if entry_date else 0)
        # 수수료/세금 반영 실질 손익
        _buy_amt   = buy_price * shares
        _sell_amt  = exit_price * shares
        _commission= (_buy_amt + _sell_amt) * COMMISSION_RATE
        _tax       = _sell_amt * TAX_RATE
        pnl        = (_sell_amt - _buy_amt) - _commission - _tax
        ret        = pnl / _buy_amt if _buy_amt > 0 else 0
        _cluster_name = get_cluster_name(ticker)
        append_trade_log({
            "action":     "sell",
            "ticker":     ticker,
            "name":       info.get("name", ticker),
            "buy_price":  buy_price,
            "sell_price": exit_price,
            "shares":     shares,
            "amount":     amount,
            "date":       str(date.today()),   # api_performance equity_curve용
            "entry_date": entry_date,
            "exit_date":  str(date.today()),
            "exit_price": exit_price,
            "hold_days":   hold_days,
            "ret":         round(ret, 4),
            "pnl":         round(pnl, 0),
            "reason":      reason,
            "regime":      getattr(self, "regime", "SIDE"),
            "edge_at_exit": info.get("last_edge", 0),
            "cluster":     _cluster_name,
            "atr_mult_orig": get_atr_mult_rt(_cluster_name),
            "carry_over":   False,
            "trail_active": bool(info.get("trail_active", False)),
        })
        self.today_exited.add(ticker)   # ③ 당일 재진입 차단

        # ── 키움 자동 실주문 + 체결 대기 알림 ───────────────
        if not EMERGENCY_STOP:
            kw = kiwoom()
            if kw:
                _mode   = "모의" if kw._mock else "실계좌"
                _shares = int(info.get("shares", 0))
                _bp     = float(info.get("buy_price", 0))
                _pnl    = (exit_price - _bp) * _shares if _bp > 0 else 0
                _ret    = (exit_price - _bp) / _bp if _bp > 0 else 0
                _name   = info.get("name", ticker)
                if _shares > 0:
                    _res = kw.sell(ticker, _shares, exit_price, order_type="3")  # 시장가
                    if _res.get("success"):
                        _dash_alert(
                            f"자동매도 접수: {_name} | {reason} | {_ret:+.2%}",
                            kind="sell", ticker=ticker
                        )
                        tg(f"📨 [{_mode}] 자동매도 접수 → 체결 대기 중...\n종목: {_name} | {reason}")
                        _notify_on_fill(
                            _res.get("order_no", ""), ticker, _name,
                            action="sell", qty=_shares, price=exit_price,
                            buy_price=_bp, reason=reason
                        )
                    else:
                        tg(f"⚠️ [{_mode}] 자동매도 실패: {_res.get('error','')}\n종목: {_name}")
        # ── 포지션 삭제 및 저장 ─────────────────────────
        self.positions.pop(ticker, None)
        save_positions(self.positions)

    # ── 보유 종목 체크 (1분, 장중) ──────────────────────
    def check_holdings(self):
        """보유 종목 손절·트레일링·익절·타임스탑 1분 체크"""
        if not is_market_hour():
            return
        if not self.positions:
            return
        alerts = []
        for ticker, info in list(self.positions.items()):
            name   = info.get("name", resolve_name(ticker))
            df     = get_ohlcv(ticker, days=30)
            cp     = get_current_price(ticker)
            if cp <= 0 and df is not None:
                cp = float(df["종가"].iloc[-1])
            if cp <= 0: continue
            buy_p  = float(info.get("buy_price", cp))
            shares = int(info.get("shares", 0))
            ret    = (cp - buy_p) / buy_p if buy_p > 0 else 0
            atr    = calc_atr(df) if df is not None else cp * 0.02
            dyn_sl = calc_dynamic_sl(atr, cp, ticker, self.regime)
            # [C-2/C-3 수정] atr_alerted / trail_alerted 회복 시 자동 리셋
            # 가격이 손절선 위로 회복되면 alerted 초기화 → 다음 손절 사이클 알림 재활성화
            if info.get("atr_alerted") and ret > dyn_sl + 0.01:
                info.pop("atr_alerted", None)
                info.pop("sl_alert_time", None)
                info.pop("sl_followup_sent", None)
            # 트레일링이 비활성 상태로 돌아오면 alerted 초기화 (신규 트레일링 사이클 대비)
            if info.get("trail_alerted") and not info.get("trail_active"):
                info.pop("trail_alerted", None)
            # [BUG-4 수정] sl_warn 회복 리셋 — 손절가 접근 경보 이후 가격 회복 시 초기화
            # 미리셋 시 다음 접근에서 경보가 영구적으로 발송되지 않는 문제 방지
            _sl_warn_key = f"sl_warn_{ticker}"
            if info.get(_sl_warn_key):
                # [BUG-FIX] cp*(1+dyn_sl)*1.02 는 항상 cp 미만 → 조건 항상 True → 매분 리셋 스팸
                # 수정: ret(매수가 기준 수익률) vs dyn_sl 직접 비교
                # ret가 손절 임계치보다 3% 이상 회복됐을 때만 리셋
                if ret > dyn_sl + 0.03:
                    info.pop(_sl_warn_key, None)
            # ── 미매도 후속 분석 ─────────────────────────
            # 손절/트레일링 알림 후 아직 보유 중이면, N분 뒤 추세 재분석
            _sl_at = info.get("sl_alert_time")
            if _sl_at and not info.get("sl_followup_sent"):
                _elapsed_min = (datetime.now() - _sl_at).total_seconds() / 60
                _delay = C.get("SL_FOLLOWUP_DELAY_MIN", 10)
                if _elapsed_min >= _delay:
                    _al_price = info.get("sl_alert_price", buy_p)
                    _al_type  = info.get("sl_alert_type", "손절")
                    _chg = (cp - _al_price) / _al_price if _al_price > 0 else 0
                    _pnl_now = (cp - buy_p) * shares
                    # 최근 거래량 분석
                    _vol_ratio = 1.0
                    if df is not None and len(df) >= 20:
                        _vol_avg = df["거래량"].iloc[-20:].mean()
                        _vol_now = df["거래량"].iloc[-1]
                        _vol_ratio = _vol_now / _vol_avg if _vol_avg > 0 else 1.0
                    if _chg < -0.01:
                        # Case 1: 추가 하락 중
                        _capital_floor = C.get("TOTAL_CAPITAL", 10_000_000) * C.get("CAPITAL_FLOOR_RATIO", 0.70)
                        _advice = (
                            f"⏰ <b>{name}, {_al_type} 알림 이후 상태예요</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"{_al_type} 알림 가격: {_al_price:,.0f}원\n"
                            f"지금 가격: {cp:,.0f}원 ({_chg:+.1%} 추가 하락)\n"
                            f"현재 손익: {_pnl_now:+,.0f}원 ({ret:+.2%})\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"📉 <b>계속 떨어지고 있어요</b>\n"
                            f"   더 기다릴수록 손실이 커질 수 있어요\n"
                            f"\n"
                            f"💡 <b>지금이라도 매도하는 게 안전해요</b>\n"
                            f"\n"
                            f"👉 매도하려면 /sell\n"
                            f"\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"🛡️ <b>바빠서 지금 대응이 어려우시다면</b>\n"
                            f"  걱정 마세요. 시스템이 계속 지키고 있어요:\n"
                            f"  · 1분마다 손절선 자동 체크 중\n"
                            f"  · 추가 매수는 이미 차단된 상태\n"
                            f"  · 자본 하한선 {_capital_floor:,.0f}원은 절대 보호\n"
                            f"  · 금요일에 전체 종목 정리 판단 드려요"
                        )
                    elif _chg > 0.005:
                        # Case 2: 반등 중
                        _advice = (
                            f"⏰ <b>{name}, {_al_type} 알림 이후 상태예요</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"{_al_type} 알림 가격: {_al_price:,.0f}원\n"
                            f"지금 가격: {cp:,.0f}원 ({_chg:+.1%} 반등)\n"
                            f"현재 손익: {_pnl_now:+,.0f}원 ({ret:+.2%})\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"📈 <b>조금 올라오고 있어요</b>\n"
                            f"   지금 매도하면 손실을 줄일 수 있어요\n"
                            f"\n"
                            f"💡 <b>반등할 때 매도하는 게 유리해요</b>\n"
                            f"   다시 떨어질 수도 있거든요\n"
                            f"\n"
                            f"👉 매도하려면 /sell\n"
                            f"\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"🛡️ <b>지금 바로 대응이 어려워도 괜찮아요</b>\n"
                            f"  시스템이 계속 모니터링하고 있어요.\n"
                            f"  반등이 더 이어지면 트레일링이 수익을 지켜줘요."
                        )
                    else:
                        # Case 3: 횡보
                        _vol_txt = "거래량이 많아서 방향이 곧 정해질 수 있어요" if _vol_ratio > 1.5 else "거래량도 적어서 당분간 움직임이 적을 수 있어요"
                        _advice = (
                            f"⏰ <b>{name}, {_al_type} 알림 이후 상태예요</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"{_al_type} 알림 가격: {_al_price:,.0f}원\n"
                            f"지금 가격: {cp:,.0f}원 (변동 {_chg:+.1%})\n"
                            f"현재 손익: {_pnl_now:+,.0f}원 ({ret:+.2%})\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"↔️ <b>큰 변동 없이 멈춰 있어요</b>\n"
                            f"   {_vol_txt}\n"
                            f"\n"
                            f"💡 <b>손절 기준을 넘은 상태이므로</b>\n"
                            f"   <b>매도를 권장해요</b>\n"
                            f"\n"
                            f"👉 매도하려면 /sell\n"
                            f"\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"🛡️ <b>확인이 늦어져도 시스템이 지키고 있어요</b>\n"
                            f"  다음 체크까지 1분마다 자동 모니터링 중이에요."
                        )
                    tg(_advice)
                    info["sl_followup_sent"] = True
                    log.info(f"[후속분석] {name} {_al_type} 후 {_elapsed_min:.0f}분 경과 → {_chg:+.1%}")
            # ② 수익 구간별 알림 (익절 통합)
            alerted_steps = info.get("alerted_steps", [])
            for step in C["PROFIT_ALERT_STEPS"]:
                if ret >= step and step not in alerted_steps:
                    pnl = (cp - buy_p) * shares
                    is_target = step >= C["TAKE_PROFIT_FIXED"]
                    next_steps = [s for s in C["PROFIT_ALERT_STEPS"] if s > step]
                    next_target = next_steps[0] if next_steps else C["TAKE_PROFIT_FIXED"]
                    if is_target:
                        action_line = (f"✅ 목표 수익률 도달! 익절을 고려해보세요\n"
                                       f"   지금 팔면 {pnl:+,.0f}원을 확정할 수 있어요\n"
                                       f"   더 오를 수 있지만 언제든 내릴 수 있어요")
                    else:
                        action_line = f"💡 수익이 나고 있어요! 다음 목표: +{next_target:.0%}"
                    trail_hint = (
                        "\n🔺 트레일링이 활성화돼 수익을 자동으로 지키고 있어요"
                        if info.get("trail_active") else
                        f"\n💡 +{C['TRAIL_ACTIVATE']:.0%} 이상이면 자동 추적이 시작돼요"
                    )
                    alerts.append(
                        f"🎉 <b>{name} 수익 중!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📈 수익률: +{ret:.2%}\n"
                        f"💵 번 돈: {pnl:+,.0f}원\n"
                        f"\n"
                        f"산 가격:   {buy_p:,.0f}원\n"
                        f"지금 가격: {cp:,.0f}원\n"
                        f"보유 주식: {shares:,}주\n"
                        f"\n"
                        f"{action_line}"
                        f"{trail_hint}"
                    )
                    alerted_steps.append(step)
            info["alerted_steps"] = alerted_steps
            # 트레일링 (trail_alerted = 이미 알림 발송됨 → 매분 반복 방지)
            trail_exit, trail_reason = update_trailing(
                info, cp, atr, self.regime)
            if trail_exit and not info.get("trail_alerted"):
                peak_p   = float(info.get("peak_price", cp))
                peak_ret = (peak_p - buy_p) / buy_p if buy_p > 0 else 0
                pnl      = (cp - buy_p) * shares
                alerts.append(
                    f"🔴 <b>{name} 고점에서 내려왔어요</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"고점 대비 일정 비율 하락해서\n"
                    f"자동 매도 신호가 발생했어요\n"
                    f"\n"
                    f"최고점:    {peak_p:,.0f}원  (최고 수익 +{peak_ret:.2%})\n"
                    f"지금 가격:  {cp:,.0f}원\n"
                    f"지금 수익: {pnl:+,.0f}원 ({ret:+.2%})\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"💡 수익이 날 때 파는 거예요\n"
                    f"   손실이 아니에요!\n"
                    f"   지금 팔면 {pnl:+,.0f}원 확정이에요"
                )
                info["trail_alerted"] = True   # 알림 반복 방지
                info["sl_alert_time"] = datetime.now()
                info["sl_alert_price"] = cp
                info["sl_alert_type"] = "트레일링스탑"
                info.pop("sl_followup_sent", None)
                self._log_exit(ticker, info, cp, "트레일링스탑")
                self.consec_loss  = 0
                self.consec_win   = getattr(self, "consec_win", 0) + 1
                if self.consec_win >= 3:
                    tg(
                        f"🎊 <b>{self.consec_win}연속 수익 중이에요!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"최근 {self.consec_win}번 거래 모두 수익으로 끝났어요 👏\n"
                        f"전략이 잘 맞고 있어요!\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"💡 연속 수익에 과신하지 않고\n"
                        f"   원칙대로 손절·익절 기준을 지켜주세요"
                    )
                continue
            # ATR 손절
            # [BUG-FIX] sl_price_now = cp*(1+dyn_sl) → |dyn_sl|>5% 시 접근 경보 영구 미발동
            # 수정: buy_p 기준 절대 손절가로 계산 (동적 dyn_sl을 매수가에 적용)
            sl_price_now = buy_p * (1 + dyn_sl)
            if np.isnan(sl_price_now) or sl_price_now <= 0:
                sl_price_now = buy_p * 0.93
            # ㊳ 타임스탑 체크 (ATR/트레일링 미발동 상태에서 장기 무변동 시)
            if not info.get("trail_active") and not info.get("atr_alerted"):
                _entry_ts = info.get("entry_date", "")
                _hold_ts  = ((date.today() - date.fromisoformat(_entry_ts)).days
                             if _entry_ts else 0)
                _ts_days  = C.get("TIME_STOP_DAYS", 15)
                _ts_thr   = C.get("TIME_STOP_THRESHOLD", 0.02)
                if (C.get("TIME_STOP_ENABLED", True)
                        and _hold_ts >= _ts_days
                        and abs(ret) <= _ts_thr
                        and not info.get("timestop_alerted")):
                    pnl_ts = (cp - buy_p) * shares
                    alerts.append(
                        f"\u23f1\ufe0f <b>{name}, {_hold_ts}일째 움직임이 없어요</b>\n"
                        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                        f"산 지 {_hold_ts}일이 지났는데\n"
                        f"수익률이 {ret:+.2%}로 거의 변동이 없어요\n\n"
                        f"\U0001f4ca 현재 상태\n"
                        f"   산 가격: {buy_p:,.0f}원 \u2192 지금: {cp:,.0f}원\n"
                        f"   손익: {pnl_ts:+,.0f}원\n"
                        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                        f"\U0001f4a1 <b>이런 경우 팔고 다른 종목으로 갈아타는 게</b>\n"
                        f"   <b>더 수익이 날 수 있어요</b>\n\n"
                        f"\U0001f449 매도하려면 /sell 을 눌러주세요"
                    )
                    info["timestop_alerted"] = True
                    self._log_exit(ticker, info, cp, "타임스탑")
                    continue  # 포지션 삭제됨 → 이하 처리 skip
            if ticker not in self.positions:
                continue      # 타임스탑으로 삭제된 경우
            if ret <= dyn_sl and not info.get("atr_alerted"):
                pnl = (cp - buy_p) * shares
                alerts.append(
                    f"🔴 <b>{name} 손절 가격 도달!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"지금 바로 매도를 고려하세요\n"
                    f"\n"
                    f"현재 가격:  {cp:,.0f}원\n"
                    f"산 가격:    {buy_p:,.0f}원\n"
                    f"손실 금액: {pnl:+,.0f}원 ({ret:.2%})\n"
                    f"보유 주식: {shares:,}주\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📝 AI가 판단한 최대 허용 손실에 도달했어요\n"
                    f"   더 기다리면 손실이 더 커질 수 있어요"
                )
                info["atr_alerted"] = True   # 알림 반복 방지
                info["sl_alert_time"] = datetime.now()
                info["sl_alert_price"] = cp
                info["sl_alert_type"] = "ATR손절"
                info.pop("sl_followup_sent", None)
                self._log_exit(ticker, info, cp, "ATR손절")
                self.consec_win  = 0
                self.consec_loss = getattr(self, "consec_loss", 0) + 1
                if self.consec_loss >= 2:
                    tg(f"🚨 <b>연속으로 손절이 났어요 ({self.consec_loss}회 연속)</b>\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"최근 {self.consec_loss}번의 거래에서 모두 손실로 끝났어요\n"
                       f"\n"
                       f"이럴 때는 잠깐 쉬는 게 좋아요\n"
                       f"  • 시장이 전략과 맞지 않는 시기일 수 있어요\n"
                       f"  • 당분간 새로운 종목 매수를 줄여보세요\n"
                       f"  • 지금 보유 중인 종목 손절가를 재확인하세요\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"💡 연속 손절은 운이 나쁜 게 아니라\n"
                       f"   시장 흐름이 바뀌었다는 신호일 수 있어요")
                    self.today_alerts += 1
                continue  # 포지션 삭제됨 → 이하 처리 skip
            if ticker not in self.positions:
                continue  # ATR손절로 삭제된 경우
            # ── 원칙2: 최대 보유일 경고 ──────────────────────────
            # FIX-3: 타임스탑 이미 발동된 종목은 MAX_HOLD 경고 skip (알림 중복 방지)
            _entry_d  = info.get("entry_date", "")
            _hold_d   = ((date.today() - date.fromisoformat(_entry_d)).days
                         if _entry_d else 0)
            _max_hold = C.get("MAX_HOLD_DAYS", 5)
            if (_hold_d >= _max_hold - 1
                    and not info.get("max_hold_warned")
                    and not info.get("timestop_alerted")
                    and C.get("FRIDAY_FORCE_EXIT", True)):
                _pnl_h = (cp - buy_p) * shares
                alerts.append(
                    f"⏰ <b>{name} 보유 {_hold_d}일 — 마감 임박!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"투자원칙: 이번 주 안에 정리\n\n"
                    f"현재: {cp:,.0f}원  손익: {_pnl_h:+,.0f}원 ({ret:+.2%})\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"💡 금요일 15:20에 최종 알림이 와요"
                )
                info["max_hold_warned"] = True
            # ── last_edge 갱신 (옵티마이저 이월 시뮬레이션용) ──
            # [C-1 수정] elif → if 블록 내부로 통합
            # 이전: elif df is not None → 위 if가 True면 영구 미실행
            # AI점수 경보 / 손절가 접근 경보 모두 독립 if로 분리
            if df is not None:
                _ka_le   = fetch_kind_sentiment(ticker)
                _edge_le = calculate_edge_v27(df, _ka_le, ticker)
                info["last_edge"] = round(_edge_le, 4)
                # ── AI 점수 급락 매도 경보 (SELL_EDGE_THRESHOLD) ──
                # 백테스트와 동일: edge < SELL_EDGE_THRESHOLD 시 보유 의미 없음
                # 이미 계산된 _edge_le 재사용 → API 중복 호출 방지
                edge_now = _edge_le
                sell_thr = C.get("SELL_EDGE_THRESHOLD", 0.30)
                if edge_now < sell_thr and not info.get("sell_edge_alerted"):
                    pnl_now = (cp - buy_p) * shares
                    alerts.append(
                        f"📉 <b>{name} AI 점수 급락 주의!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"AI 점수가 {int(edge_now*100)}점으로 떨어졌어요\n"
                        f"(기준선: {int(sell_thr*100)}점)\n"
                        f"\n"
                        f"현재 가격: {cp:,.0f}원\n"
                        f"현재 손익: {pnl_now:+,.0f}원 ({ret:+.2%})\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"💡 AI가 이 종목의 매력을 낮게 봐요\n"
                        f"   손절선 위라도 매도를 고려해보세요\n"
                        f"   (강제 매도 아님 — 참고용 경보예요)"
                    )
                    info["sell_edge_alerted"] = True
                elif edge_now >= sell_thr:
                    info.pop("sell_edge_alerted", None)  # 점수 회복 시 초기화
            # ── 손절가 95% 접근 사전 경보 ── (독립 if로 분리)
            if cp <= sl_price_now * 1.05 and cp > sl_price_now:
                approach_pct = (cp - sl_price_now) / sl_price_now
                warned_key   = f"sl_warn_{ticker}"
                if not info.get(warned_key):
                    pnl_now = (cp - buy_p) * shares
                    alerts.append(
                        f"⚠️ <b>{name} 주의!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"손절 가격에 가까워지고 있어요\n"
                        f"\n"
                        f"현재 가격:  {cp:,.0f}원\n"
                        f"손절 가격:  {sl_price_now:,.0f}원  ← 이 가격이면 팔아야 해요\n"
                        f"남은 거리:  {cp - sl_price_now:,.0f}원  (약 {approach_pct:.1%})\n"
                        f"\n"
                        f"지금 손익: {pnl_now:+,.0f}원 ({ret:.2%})\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"💡 지금 당장 팔 필요는 없지만\n"
                        f"   트레이딩 앱에서 {sl_price_now:,.0f}원으로\n"
                        f"   스탑로스를 설정해두면 자동으로 보호돼요"
                    )
                    info[warned_key] = True
            # 고정 익절 — 수익 구간 알람에 통합됨
            elif (not info.get("trail_active")
                  and ret >= C["TAKE_PROFIT_FIXED"]
                  and C["TAKE_PROFIT_FIXED"] not in info.get("alerted_steps", [])):
                pass  # 위 수익 구간 알람에서 처리됨
            # 거래량 급증 (보유 정보 포함)
            if df is not None and ticker not in self.vol_alerted:
                surge = check_vol_surge(df, ticker, name, held_info=info)
                if surge:
                    alerts.append(surge)
                    self.vol_alerted.add(ticker)
        # ㊱ 서킷브레이커: 당일 전체 평가손 체크
        if C.get("CIRCUIT_BREAKER_ENABLED", True):
            _total_inv = sum(float(i.get("buy_price",0)) * int(i.get("shares",0))
                             for i in self.positions.values())
            _total_val = 0
            for _tk, _inf in self.positions.items():
                _cp2 = get_current_price(_tk)
                if _cp2 > 0:
                    _total_val += _cp2 * int(_inf.get("shares", 0))
            if _total_inv > 0:
                _dd_now = (_total_val - _total_inv) / _total_inv
                if _dd_now <= C.get("DAILY_DRAWDOWN_LIMIT", -0.05):
                    if not self._circuit_active:
                        self._circuit_active = True
                        tg("🚨 <b>오늘은 주식을 새로 사지 않아요!</b>\n"
                           f"━━━━━━━━━━━━━━━━━━\n"
                           f"보유 종목 전체의 오늘 손실이 {_dd_now:.1%}에요\n"
                           f"하루에 {C.get('DAILY_DRAWDOWN_LIMIT', -0.05):.0%} 넘게 떨어지면\n"
                           f"안전을 위해 자동으로 매수를 멈춰요\n\n"
                           f"📌 지금 갖고 있는 종목은 그대로 유지돼요\n"
                           f"   (손절가에 닿으면 평소처럼 알려드려요)\n\n"
                           f"⏰ 내일 아침에 자동으로 다시 정상화돼요\n\n"
                           f"━━━━━━━━━━━━━━━━━━\n"
                           f"🛡️ <b>바쁘거나 확인이 어려워도 걱정 마세요</b>\n"
                           f"  ✅ 손절선은 1분마다 자동 체크 중이에요\n"
                           f"  ✅ 추가 매수는 이미 차단되었어요\n"
                           f"  ✅ 자본의 70%는 절대 보호돼요\n"
                           f"  ✅ 금요일에 전체 정리 판단을 해드려요\n\n"
                           f"💬 <b>지금 당장 아무것도 안 해도 괜찮아요</b>\n"
                           f"   시스템이 계속 지켜보고 있어요")
        save_positions(self.positions)
        # 포트폴리오 리스크 (1일 1회만 발송)
        _risk_key = f"_portfolio_risk_{date.today()}"
        if not getattr(self, _risk_key, False):
            risk_alerts = check_portfolio_risk(self.positions, self.regime)
            if risk_alerts:
                alerts.extend(risk_alerts)
                setattr(self, _risk_key, True)
        for alert in alerts:
            # 알림 종류 분류 (대시보드 연동)
            _ak = ("sell"    if any(k in alert for k in ["매도", "손절", "청산", "타임스탑"])
                   else "buy"  if any(k in alert for k in ["매수", "추가매수"])
                   else "warning")
            _dash_alert(alert, kind=_ak)
            tg(alert); self.today_alerts += 1; time.sleep(0.3)
    # ── 유니버스 스캔 (5분, 장중) ──────────────────
    def scan_universe(self, force_notify: bool = False):
        if not is_market_hour() and not force_notify:
            return
        now          = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows         = []
        regime_emoji = {"BULL":"📈","SIDE":"➡️","BEAR":"📉"}.get(
            self.regime, "❓")
        # 보유 종목 현황
        for ticker, info in self.positions.items():
            name  = info.get("name", resolve_name(ticker))
            cp    = get_current_price(ticker)
            buy_p = float(info.get("buy_price", 0))
            shares = int(info.get("shares", 0))
            ret   = (cp - buy_p) / buy_p if buy_p > 0 and cp > 0 else 0
            df    = get_ohlcv(ticker, days=60)
            kind_adj = fetch_kind_sentiment(ticker)
            edge  = calculate_edge_v27(df, kind_adj, ticker) if df is not None else 0.5
            tm    = " 🔺" if info.get("trail_active") else ""
            rows.append([now, "보유", name, f"{cp:,.0f}", f"{ret:+.2f}%", edge])

            # ── ③ 타임스탑 임박 알림 (D-3) ──────────────────
            if C.get("TIME_STOP_ENABLED", True) and not info.get("timestop_alerted"):
                _ts_days  = C.get("TIME_STOP_DAYS", 15)
                _ts_thr   = C.get("TIME_STOP_THRESHOLD", 0.02)
                _entry    = info.get("entry_date", "")
                try:
                    _hold = (date.today() - date.fromisoformat(_entry)).days if _entry else 0
                except Exception:
                    _hold = 0
                _days_left = _ts_days - _hold
                if (2 <= _days_left <= 3
                        and abs(ret) <= _ts_thr
                        and not info.get("ts_imminent_alerted")):
                    tg(f"⏱ <b>타임스탑 임박: {name}</b>\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"보유 {_hold}일째 — {_days_left}일 후 타임스탑 도달\n"
                       f"현재 수익률: {ret:+.2%} (기준: ±{_ts_thr:.1%} 이내)\n\n"
                       f"📌 지금 추이를 지켜보고\n"
                       f"   {_ts_days}일이 되면 자동 매도 검토됩니다.")
                    info["ts_imminent_alerted"] = True

            # ── ④ Edge 급락 경고 ─────────────────────────────
            _prev_edge_val = self.prev_edge.get(ticker, None)
            _curr_edge_int = round(edge * 100)
            # [v40.0 BUG-FIX] float 오염 보정 (구버전 scan_universe가 0.xx로 저장한 경우)
            if _prev_edge_val is not None and isinstance(_prev_edge_val, float) and _prev_edge_val < 2.0:
                _prev_edge_val = round(_prev_edge_val * 100)
            if (_prev_edge_val is not None
                    and _prev_edge_val - _curr_edge_int >= 15
                    and not info.get("edge_drop_alerted")):
                tg(f"📉 <b>Edge 급락 경고: {name}</b>\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"Edge: {_prev_edge_val}점 → {_curr_edge_int}점 "
                   f"({_curr_edge_int - _prev_edge_val:+d}점)\n"
                   f"현재 수익률: {ret:+.2%}\n\n"
                   f"💡 매도의견을 확인해보세요.")
                info["edge_drop_alerted"] = True
            elif (_prev_edge_val is not None
                    and _curr_edge_int - _prev_edge_val >= 10
                    and info.get("edge_drop_alerted")):
                info.pop("edge_drop_alerted", None)   # 회복 시 리셋
            self.prev_edge[ticker] = _curr_edge_int
        # 유니버스 스캔 → 추천 (③ 당일 청산 종목 제외)
        held   = set(self.positions.keys())
        scored = []
        # STEP3: 경제이벤트 플래그 루프 밖 사전계산
        _econ_today_dt = date.today()
        _econ_list_cached = C.get("ECON_EVENTS_2025_2026", [])
        def __try_parse_date(s):
            try: return date.fromisoformat(s)
            except: return None
        _econ_today_flag = _econ_today_dt in [
            __d for __s in _econ_list_cached
            for __d in [__try_parse_date(__s)] if __d
        ]
        for ticker, name in self.universe.items():
            if ticker in held: continue
            if ticker in self.today_exited: continue   # ③ 재진입 차단
            df = get_ohlcv(ticker, days=60)
            if df is None or len(df) < 20: continue
            time.sleep(0.15)   # [IP 차단 방지] 종목 간 150ms 간격
            # [New-C] 신호 생성: 확정봉 데이터만 사용 (장중 미완성봉 배제)
            df_signal = get_closed_df(df)
            if df_signal is None or len(df_signal) < 20: continue
            kind_adj        = fetch_kind_sentiment(ticker)
            edge            = calculate_edge_v27(df_signal, kind_adj, ticker)
            cp              = float(df["종가"].iloc[-1])   # 표시용 현재가는 원본 df (최신값)
            slip_ok, exp, req = check_slippage_filter(df_signal, ticker)
            # ⑦ Edge 급등 + 매수 타이밍 통합
            # [v40.0 BUG-FIX] prev_edge 단위 통일: check_holdings(정수) ↔ scan_universe(float) 교차오염 방지
            # prev_edge[ticker]는 항상 정수(100배) 형태로 읽고 씀
            edge_int       = round(edge * 100)
            prev_int       = self.prev_edge.get(ticker, edge_int)
            # prev가 float(0.xx)로 오염된 경우 자동 보정
            if isinstance(prev_int, float) and prev_int < 2.0:
                prev_int = round(prev_int * 100)
            edge_surge_int = edge_int - prev_int
            if edge_surge_int >= round(C["EDGE_SURGE_THRESHOLD"] * 100) and slip_ok:
                guide_s    = calc_entry_guide(df_signal, ticker, self.regime)
                entry_str  = (f"{guide_s['entry_low']:,.0f} ~ {guide_s['entry_high']:,.0f}원"
                              if guide_s else f"{cp:,.0f}원")
                target_str = f"{guide_s['target']:,.0f}원" if guide_s else "-"
                sl_str     = f"{guide_s['sl_price']:,.0f}원" if guide_s else "-"
                tg(f"🚀 <b>{name} AI가 주목하기 시작했어요!</b>\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"🤖 AI 점수: {prev_int}점 → {edge_int}점 (▲{edge_surge_int}점 급등)\n"
                   f"\n"
                   f"지금이 매수 타이밍일 수 있어요\n"
                   f"💰 사기 좋은 가격: {entry_str}\n"
                   f"🎯 목표 가격: {target_str}\n"
                   f"🛑 손절 가격: {sl_str}  (이 가격엔 팔아야 해요)\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"💡 AI 점수가 갑자기 오른 건\n"
                   f"   수급·기술·모멘텀이 동시에 좋아졌다는 신호예요")
                self.today_alerts += 1
            # [v40.0 BUG-FIX] prev_edge 정수(100배)로 저장 통일
            self.prev_edge[ticker] = edge_int
            # 거래량 급증 (미보유 종목 — held_info 없음)
            if ticker not in self.vol_alerted:
                surge_msg = check_vol_surge(df_signal, ticker, name)
                if surge_msg:
                    tg(surge_msg)
                    self.vol_alerted.add(ticker)
                    self.today_alerts += 1
            # ㉝ RSI 다이버전스 감점
            if df_signal is not None and len(df_signal) > 40:  # FIX-1: RSI rolling(20)+rolling(14) 유효값 확보
                _rsi = 100 - (100 / (1 + df_signal["종가"].diff().clip(lower=0).rolling(14).mean() /
                       (-df_signal["종가"].diff().clip(upper=0)).rolling(14).mean().replace(0, float("nan"))))
                _price_high = df_signal["종가"].rolling(20).max().iloc[-1] == df_signal["종가"].iloc[-1]
                _rsi_dec = False
                if len(_rsi.dropna()) > 1:
                    _rsi_dec = float(_rsi.iloc[-1]) < float(_rsi.rolling(20).max().iloc[-1])
                if _price_high and _rsi_dec:
                    edge -= C.get("RSI_DIVERGENCE_PENALTY", 0.08)
            # ㉞ 섹터 로테이션 보너스/감점
            _sec = get_sector_for_ticker_rt(ticker)
            # 간이 섹터 모멘텀: 유니버스에서 같은 섹터 종목 평균 edge
            _sec_edges = []
            for _st, _sn in self.universe.items():
                if get_sector_for_ticker_rt(_st) == _sec and _st != ticker:
                    _se = self.prev_edge.get(_st, 50)  # [v40.0] 정수(100배) 기준, 기본값 50
                    # float 오염 보정
                    if isinstance(_se, float) and _se < 2.0:
                        _se = round(_se * 100)
                    _sec_edges.append(_se)
            if _sec_edges:
                _sec_avg = sum(_sec_edges) / len(_sec_edges)
                # [v40.0] 정수(100배) 기준 비교: 60 = 0.60, 40 = 0.40
                if _sec_avg > 60:
                    edge += C.get("SECTOR_MOMENTUM_BONUS", 0.05)
                elif _sec_avg < 40:
                    edge -= C.get("SECTOR_MOMENTUM_PENALTY", 0.03)
            thr = get_regime_threshold(self.regime)
            # ㊶ 경제 이벤트 당일 커트라인 상향 (STEP3: 루프 밖 _econ_today_flag 참조)
            if _econ_today_flag:
                thr += C.get("ECON_EVENT_EDGE_UPLIFT", 0.10)
            # ㊱ 서킷브레이커 (당일 전체 평가 -5% 초과 시 추천 중단)
            if C.get("CIRCUIT_BREAKER_ENABLED", True) and hasattr(self, "_circuit_active") and self._circuit_active:
                continue
            # ㊴ 섹터 집중도 제한
            if C.get("SECTOR_LIMIT_ENABLED", True) and _sec != "기타":
                _sec_count = sum(1 for _ht, _hi in self.positions.items()
                                 if get_sector_for_ticker_rt(_ht) == _sec)
                _sec_max = C.get("SECTOR_MAX_POSITIONS", 2)
                if _sec_count >= _sec_max:
                    continue  # 섹터 한도 초과 → 추천 제외
            # ㉟ 멀티 타임프레임 필터 (FIX-2: 캐시 참조 → 연산 제거)
            if C.get("WEEKLY_TREND_REQUIRED", True):
                _wt_ok = self._weekly_trend_cache.get(ticker, True)
                if not _wt_ok:
                    continue  # 주봉 하락추세 → 추천 제외
            if edge >= thr and slip_ok:
                guide = calc_entry_guide(df_signal, ticker, self.regime)
                scored.append({
                    "ticker": ticker, "name": name,
                    "edge": edge, "price": cp,
                    "expected": exp, "required": req,
                    "guide": guide,
                    "df": df_signal,   # 추천 상세 표시용도 — 확정봉 기준 유지
                })
        scored.sort(key=lambda x: x["edge"], reverse=True)
        top5 = scored[:5]
        for i, s in enumerate(top5):
            rows.append([now, f"추천{i+1}", s["name"],
                         f"{s['price']:,.0f}", "-", s["edge"], s["ticker"]])
        # 스마트 알림
        raw_str  = "".join(r[3] for r in rows if r[1]=="보유")
        cur_hash = hashlib.md5(raw_str.encode()).hexdigest()
        if force_notify or cur_hash != self.last_hash:
            hold_rows = [r for r in rows if r[1]=="보유"]
            r_plain = _regime_plain(self.regime)
            # 시장 국면 쉬운 설명
            _regime_easy = {
                "BULL": "📈 지금 주식시장이 올라가는 중이에요",
                "SIDE": "➡️ 지금 주식시장이 별로 안 움직이고 있어요",
                "BEAR": "📉 지금 주식시장이 내려가는 중이에요",
            }.get(self.regime, "")
            msg = (f"🤖 <b>AI 현황 리포트</b>\n"
                   f"{now[:16]}\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"{_regime_easy}\n"
                   f"━━━━━━━━━━━━━━━━━━\n")
            if hold_rows:
                msg += "<b>📌 지금 갖고 있는 주식</b>\n"
                for r in hold_rows:
                    tm = " 🔺" if any(
                        info.get("name","") == r[2] and info.get("trail_active")
                        for info in self.positions.values()) else ""
                    r_icon3 = "✅" if "+" in str(r[4]) else "🔴"
                    s_int = int(float(str(r[5]))*100) if r[5] else 0
                    _score_comment = ("🔥 지금 아주 좋아요" if s_int >= 70
                                      else "👍 괜찮아요" if s_int >= 55
                                      else "⚠️ 주의가 필요해요")
                    msg += f"• {r[2]}  {r_icon3}{r[4]}{tm}\n"
                    msg += f"  AI점수 {s_int}점 — {_score_comment}\n"
            else:
                msg += "💵 지금 갖고 있는 주식이 없어요\n"
            if top5:
                msg += "\n<b>🤖 AI가 지금 주목하는 종목 TOP 5</b>\n"
                msg += "(아직 사지 않은 종목 중 가장 좋아 보이는 것들이에요)\n"
                for i, s in enumerate(top5):
                    g = s.get("guide")
                    entry_str  = (f"{g['entry_low']:,.0f}~{g['entry_high']:,.0f}원"
                                  if g else f"{s['price']:,.0f}원")
                    target_str = f"{g['target']:,.0f}원" if g else "-"
                    sl_str     = f"{g['sl_price']:,.0f}원" if g else "-"
                    _score_int = int(s['edge']*100)
                    msg += (f"\n{i+1}. <b>{s['name']}</b>  AI {_score_int}점\n"
                            f"   💰 이 가격대에 사면 좋아요: {entry_str}\n"
                            f"   🎯 이 가격이 되면 팔아요: {target_str}\n"
                            f"   🛑 이 가격 아래로 내려가면 손절: {sl_str}\n")
            # ── 교체 의견: 보유 종목보다 추천 종목이 훨씬 나을 때 ──
            if top5 and self.positions:
                switch_msgs = []
                for held_tk, held_info in self.positions.items():
                    held_df   = get_ohlcv(held_tk, days=60)
                    held_name = held_info.get("name", resolve_name(held_tk))
                    for cand in top5[:3]:
                        sv = calc_switch_value(
                            held_info, held_df, held_tk,
                            cand, cand.get("df"), self.regime
                        )
                        if sv.get("worth_switch"):
                            sell_s  = sv.get("sell_shares", 0)
                            buy_s   = sv.get("buy_shares", 0)
                            label   = sv.get("ratio_label", "일부")
                            reason  = sv.get("ratio_reason", "")
                            sell_a  = sv.get("sell_amt", 0)
                            buy_a   = sv.get("buy_amt", 0)
                            switch_msgs.append(
                                f"🔄 <b>종목 교체를 고려해보세요</b>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"지금 갖고 있는 것보다\n"
                                f"더 좋은 종목을 AI가 발견했어요\n"
                                f"\n"
                                f"AI 점수 비교:\n"
                                f"  {held_name}: {int(sv['held_edge']*100)}점  →  {cand['name']}: {int(sv['cand_edge']*100)}점\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"📤 {held_name} <b>{label} 매도</b>\n"
                                f"   {sell_s:,}주  /  약 {sell_a:,.0f}원\n"
                                f"\n"
                                f"📥 {cand['name']} 매수\n"
                                f"   사기 좋은 가격: {sv['entry_str']}\n"
                                f"   약 {buy_s:,}주 살 수 있어요\n"
                                f"   🎯 목표 가격: {sv['target_str']}\n"
                                f"   🛑 손절 가격: {sv['sl_str']}\n"
                                f"\n"
                                f"💡 {reason}"
                            )
                if switch_msgs:
                    msg += "\n━━━━━━━━━━━━━━━━━━\n"
                    msg += "\n".join(switch_msgs)
            tg(msg, silent=(not force_notify))
            # 대시보드 알림 연동 — 매수 추천 종목 저장
            for s in rows:
                if str(s[1]).startswith("추천"):   # "추천1" ~ "추천5"
                    _dash_alert(f"매수 추천: {s[2]} (Edge {float(s[5]):.2f})",
                                kind="buy", ticker=s[6] if len(s) > 6 else "")
            self.last_hash = cur_hash
    # ── 장 외 간단 체크 ───────────────────────────
    def offhours_check(self):
        """
        실행 조건:
          ① 장 중이 아닐 것
          ② 보유 종목이 있을 것
          ③ 장 종료 이후(15:35~)에만 전송 — 개장 전 새벽·오전 스팸 방지
          ④ 이전 전송과 내용이 달라졌을 때만 전송 — 변화 없으면 침묵
        """
        if is_market_hour() or not self.positions:
            return
        # 장 시작 전(00:00~15:34)은 전송하지 않음
        # → 새벽에 30분마다 동일 메시지가 반복되는 문제 방지
        now_hhmm = datetime.now().strftime("%H:%M")
        if now_hhmm < "15:35":
            return
        lines = [f"💤 <b>현재 보유 현황</b>  (장 마감 후)\n"
                 f"🕐 {datetime.now().strftime('%H:%M')} 기준"]
        for ticker, info in self.positions.items():
            name  = info.get("name", resolve_name(ticker))
            buy_p = float(info.get("buy_price", 0))
            # 장 외 시간 실시간 가격 조회 시 0원 반환 문제 방지
            # → ohlcv_cache 마지막 종가 우선 사용, 없으면 매수가로 표시
            cp = 0.0
            cached = _ohlcv_cache.get(ticker)
            if cached and cached["df"] is not None and len(cached["df"]) > 0:
                cp = float(cached["df"]["종가"].iloc[-1])
            if cp <= 0:
                cp = buy_p   # 마지막 수단: 매수가 표시 (수익률 0%)
            ret    = (cp - buy_p) / buy_p if buy_p > 0 else 0
            tm     = " 🔺" if info.get("trail_active") else ""
            r_icon = "✅" if ret >= 0 else "🔴"
            price_note = " (전일 종가)" if cp == buy_p else ""
            lines.append(f"  • {name}  {r_icon} {ret:+.2%}"
                         f"  {cp:,.0f}원{price_note}{tm}")
        # 내용 해시 비교 — 변화 없으면 전송 안 함
        content = "\n".join(lines[1:])   # 시간 제외하고 비교
        cur_hash = hashlib.md5(content.encode()).hexdigest()
        if cur_hash == self.last_offhours_hash:
            log.debug("[장외체크] 변화 없음 — 전송 스킵")
            return
        self.last_offhours_hash = cur_hash
        tg("\n".join(lines), silent=True)
    # ── 일간 결산 리포트 (15:35 통합) ────────────
    def monthly_report(self):
        """매월 마지막 거래일 15:35 — 월간 손익 리포트"""
        if not is_trading_day():
            return
        # 이번 달 마지막 거래일 여부 확인
        today = date.today()
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        # 이번 달 남은 거래일이 없으면 마지막 거래일
        remaining = [d for d in range(today.day + 1, last_day + 1)
                     if date(today.year, today.month, d).weekday() < 5]
        if remaining:
            return   # 아직 거래일 남음
        log.info("📅 월간 리포트 발송")
        logs = load_trade_log()
        m_start = str(date(today.year, today.month, 1))
        monthly = [t for t in logs
                   if t.get("exit_date", "") >= m_start
                   and t.get("exit_price", 0) > 0]
        if not monthly:
            tg(f"📅 <b>{today.month}월 마감</b>\n이번 달 완료된 거래가 없어요.")
            return
        p = calc_performance(monthly)
        w_icon = "✅" if p["win_rate"] >= 0.5 else "🔴"
        pnl_icon = "📈" if p["total_pnl"] >= 0 else "📉"
        # 종목별 집계
        ticker_pnl = {}
        for t in monthly:
            nm = t.get("name", t.get("ticker",""))
            ticker_pnl[nm] = ticker_pnl.get(nm, 0) + t.get("pnl", 0)
        top3 = sorted(ticker_pnl.items(), key=lambda x: x[1], reverse=True)[:3]
        bot3 = sorted(ticker_pnl.items(), key=lambda x: x[1])[:3]
        top_str = "\n".join(f"  {nm}: {pnl:+,.0f}원" for nm, pnl in top3 if pnl > 0)
        bot_str = "\n".join(f"  {nm}: {pnl:+,.0f}원" for nm, pnl in bot3 if pnl < 0)
        msg = (
            f"📅 <b>{today.year}년 {today.month}월 월간 리포트</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 거래 {p['count']}회  {w_icon} 승률 {p['win_rate']:.1%}\n"
            f"⏱ 평균 보유: {p['avg_days']:.1f}일\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{pnl_icon} <b>월간 손익: {p['total_pnl']:+,.0f}원</b>\n"
            f"   평균 수익률: {p['avg_ret']:+.2%}\n"
            f"   (수수료/세금 반영)\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
        if top_str:
            msg += f"🏆 수익 TOP\n{top_str}\n"
        if bot_str:
            msg += f"💔 손실\n{bot_str}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n💪 다음 달도 원칙대로!"
        tg(msg)

    def daily_backup(self):
        """매일 15:40 핵심 데이터 자동 백업"""
        if not is_trading_day():
            return
        import shutil
        today_s = str(date.today())
        backup_dir = Path(__file__).parent / "backup"
        backup_dir.mkdir(exist_ok=True)
        backed = []
        # 백업 대상
        targets = [
            (TRADE_DB_FILE,   f"trade_history_{today_s}.db"),
            (TRADE_LOG_FILE,  f"trade_log_{today_s}.json"),
            (POSITIONS_FILE,  f"positions_{today_s}.json"),
            (CONFIG_FILE,     f"config_{today_s}.json"),
        ]
        for src, dst_name in targets:
            if src.exists():
                dst = backup_dir / dst_name
                shutil.copy2(src, dst)
                backed.append(src.name)
        # 30일 초과 백업 자동 삭제
        cutoff = date.today() - timedelta(days=30)
        for f in backup_dir.glob("*"):
            try:
                f_date = date.fromisoformat(f.stem.split("_")[-1])
                if f_date < cutoff:
                    f.unlink()
            except Exception:
                pass
        log.info(f"[백업] {', '.join(backed)} → backup/")

    def close_report(self):
        if not is_trading_day():
            return
        log.info("📊 일간 결산 리포트")
        now         = datetime.now().strftime("%Y/%m/%d")
        regime_icon = {"BULL": "📈", "SIDE": "➡️", "BEAR": "📉"}.get(self.regime, "")
        regime_name = {"BULL": "상승장", "SIDE": "보합장", "BEAR": "하락장"}.get(self.regime, "")
        total_pnl  = 0
        total_eval = 0
        # 요일 + 남은 거래일 컨텍스트
        _wd_names = {0:"월",1:"화",2:"수",3:"목",4:"금"}
        _wd_today = date.today().weekday()
        _wd_str   = _wd_names.get(_wd_today, "")
        _remain   = get_remaining_trading_days()
        if _wd_today == 4:
            _day_ctx = "📅 오늘이 이번 주 마지막 거래일이에요"
        elif _wd_today == 3:
            _day_ctx = "⚠️ 내일(금요일)이 이번 주 마지막 거래일이에요 — 정리 준비하세요"
        else:
            _day_ctx = f"📅 {_wd_str}요일 | 이번 주 남은 거래일: {_remain}일"
        _regime_easy2 = {
            "BULL": "📈 오늘 시장 분위기: 상승장",
            "SIDE": "➡️ 오늘 시장 분위기: 횡보장 (크게 안 움직임)",
            "BEAR": "📉 오늘 시장 분위기: 하락장",
        }.get(self.regime, "")
        msg = (f"🌙 <b>오늘 하루 마감 정리</b>  |  {now}\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"{_regime_easy2}\n"
               f"{_day_ctx}\n")
        if self.positions:
            msg += "\n<b>📌 오늘 내 주식 성적표</b>\n"
            for ticker, info in self.positions.items():
                name   = info.get("name", resolve_name(ticker))
                buy_p  = float(info.get("buy_price", 0))
                shares = int(info.get("shares", 0))
                cached = _ohlcv_cache.get(ticker)
                cp = (float(cached["df"]["종가"].iloc[-1])
                      if cached and cached.get("df") is not None
                      and len(cached["df"]) > 0 else buy_p)
                ret    = (cp - buy_p) / buy_p if buy_p > 0 else 0
                pnl    = (cp - buy_p) * shares
                eval_v = cp * shares
                total_pnl  += pnl
                total_eval += eval_v
                df_sl    = get_ohlcv(ticker, days=30)
                atr      = calc_atr(df_sl) if df_sl is not None else cp * 0.02
                dyn_sl   = calc_dynamic_sl(atr, cp, ticker, self.regime)
                # [v40.0 BUG-FIX] 표시 손절가를 실제 트리거와 동일하게 매수가 기준으로 통일
                _sl_base_cr = buy_p if buy_p > 0 else cp
                sl_price = round(_sl_base_cr * (1 + dyn_sl), -1)
                if np.isnan(sl_price) or sl_price <= 0:
                    sl_price = round(_sl_base_cr * 0.93, -1)
                r_icon = "✅" if ret >= 0 else "🔴"
                tm_str = "  🔺수익 추적 중" if info.get("trail_active") else ""
                _ret_comment = ("수익 중이에요 👍" if ret > 0
                                else "손실 중이에요 😥" if ret < 0
                                else "본전이에요")
                msg += (f"\n📌 <b>{name}</b>{tm_str}\n"
                        f"   {buy_p:,.0f}원에 샀는데 → 오늘 {cp:,.0f}원이에요\n"
                        f"   {r_icon} {_ret_comment} ({ret:+.2%}, {pnl:+,.0f}원)\n"
                        f"   🛑 이 가격 밑으로 내려가면 자동 매도: <b>{sl_price:,.0f}원</b>\n")
            tot_icon = "✅" if total_pnl >= 0 else "🔴"
            msg += (f"━━━━━━━━━━━━━━━━━━\n"
                    f"{tot_icon} 오늘 총 손익: <b>{total_pnl:+,.0f}원</b>\n"
                    f"💼 지금 내 주식 총 가치: {total_eval:,.0f}원\n")
        else:
            msg += "\n💵 지금 갖고 있는 주식이 없어요\n   내일 AI가 좋은 종목을 찾아드릴게요!\n"
        # 내일 주목 예비
        preview = []
        for ticker, name in list(self.universe.items())[:15]:
            if ticker in self.positions: continue
            df = get_ohlcv(ticker, days=60)
            if df is None: continue
            edge = calculate_edge_v27(df, 0.0, ticker)
            preview.append((name, edge))
        preview.sort(key=lambda x: -x[1])
        if preview[:3]:
            msg += "\n⭐ <b>내일 AI가 주목하는 종목</b>\n"
            msg += "(내일 사면 좋을 수도 있는 후보예요)\n"
            for i, (nm, eg) in enumerate(preview[:3], 1):
                _eg_int = int(eg*100)
                _eg_comment = "🔥 아주 좋음" if _eg_int >= 70 else "👍 좋음"
                msg += f"  {i}. {nm}  {_eg_int}점 {_eg_comment}\n"
        msg += "\n💡 내일 오전 8시 40분에 더 자세한 정보가 와요"
        # ── 미대응 안심 리포트 ─────────────────────
        # 장중 손절/트레일링 알림이 있었는데 아직 보유 중인 종목이 있으면
        # "대응 못 해도 괜찮다"는 안심 메시지 추가 발송
        _unacted = []
        for _tk, _inf in self.positions.items():
            if _inf.get("sl_followup_sent") or _inf.get("atr_alerted") or _inf.get("trail_alerted"):
                _nm = _inf.get("name", resolve_name(_tk))
                _bp = float(_inf.get("buy_price", 0))
                _cp = get_current_price(_tk)
                if _cp <= 0: _cp = _bp
                _ret = (_cp - _bp) / _bp if _bp > 0 else 0
                _unacted.append((_nm, _ret))
        if _unacted:
            _capital = C.get("TOTAL_CAPITAL", 10_000_000)
            _floor = _capital * C.get("CAPITAL_FLOOR_RATIO", 0.70)
            _wd_today2 = date.today().weekday()
            _fri_left = 4 - _wd_today2 if _wd_today2 < 4 else 0
            _safe_msg = (
                f"\n\n🛡️ <b>오늘 알림에 대응하지 못하셨나요?</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"괜찮아요. 시스템이 하루종일 지켜봤어요.\n\n"
                f"📋 <b>미대응 종목 {len(_unacted)}개</b>\n"
            )
            for _nm, _ret in _unacted:
                _safe_msg += f"  · {_nm}: {_ret:+.2%}\n"
            _safe_msg += (
                f"\n🔒 <b>지금도 작동 중인 안전장치</b>\n"
                f"  ✅ 추가 매수: 서킷브레이커가 이미 차단했어요\n"
                f"  ✅ 자본 보호: 최소 {_floor:,.0f}원은 절대 보존돼요\n"
                f"  ✅ 내일도 1분마다 자동 체크를 이어가요\n"
            )
            if _fri_left > 0:
                _safe_msg += f"  ✅ 금요일까지 {_fri_left}일 남았어요 — 금요일에 전체 정리 판단\n"
            else:
                _safe_msg += f"  ✅ 오늘이 금요일이에요 — 주간 리포트에서 종목별 정리/이월 안내\n"
            _safe_msg += (
                f"\n💬 <b>급락장에서 가장 나쁜 선택은 패닉셀이에요</b>\n"
                f"  시장은 항상 회복했어요. 규칙대로 가면 됩니다.\n"
                f"  시간이 되실 때 천천히 확인하세요."
            )
            tg(_safe_msg)
        tg_btn(msg, [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]])
        # ── 오늘 체결내역 요약 (SQLite) ───────────
        _summary = db_daily_summary()
        if _summary["buy_count"] > 0 or _summary["sell_count"] > 0:
            _pnl_icon = "✅" if _summary["total_pnl"] >= 0 else "🔴"
            _trade_msg = (
                f"📋 <b>오늘 체결내역</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🟢 매수: {_summary['buy_count']}건\n"
                f"🔴 매도: {_summary['sell_count']}건\n"
            )
            if _summary["sell_count"] > 0:
                _trade_msg += (
                    f"{_pnl_icon} 실현손익: {_summary['total_pnl']:+,.0f}원\n"
                    f"🏆 승률: {_summary['win_rate']:.1%}"
                )
            tg(_trade_msg)
        self.today_alerts = 0
    # ── ⑧ 주간 성과 집계 (금요일 15:35) ─────────
    def weekly_report(self):
        """㊵ 주간 성과 분석 리포트 (강화판)"""
        if date.today().weekday() != 4:   # 금요일만
            return
        log.info("📅 주간 성과 집계")
        logs       = load_trade_log()
        week_start = date.today() - timedelta(days=4)
        this_week  = [t for t in logs
                      if t.get("exit_date","") >= str(week_start)
                      and t.get("exit_price", 0) > 0]
        week_perf  = calc_performance(this_week)
        total_perf = calc_performance(logs)
        # 다음주 주목 예비 (Edge 상위 3)
        preview = []
        for ticker, name in list(self.universe.items())[:15]:
            if ticker in self.positions: continue
            df = get_ohlcv(ticker, days=60)
            if df is None: continue
            edge = calculate_edge_v27(df, 0.0, ticker)
            preview.append((name, edge))
        preview.sort(key=lambda x: -x[1])
        regime_emoji = {"BULL":"📈","SIDE":"➡️","BEAR":"📉"}.get(
            self.regime, "❓")
        msg = (f"📅 <b>주간 성과 리포트</b>\n"
               f"{week_start} ~ {date.today()}\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"<b>📅 이번 주 성적표</b>\n"
               f"  거래: {week_perf['count']}회 | "
               f"승률: {week_perf['win_rate']:.1%}\n"
               f"  평균수익: {week_perf['avg_ret']:+.2%} | "
               f"주간손익: {week_perf['total_pnl']:+,.0f}원\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"<b>📊 전체 누적 성과</b>\n"
               f"  총 {total_perf['count']}회 | "
               f"승률 {total_perf['win_rate']:.1%}\n"
               f"  누적손익: {total_perf['total_pnl']:+,.0f}원\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"{regime_emoji} 현재 {self.regime}국면\n")
        # 이월 종목 요약
        _this_mon_s = str(date.today() - timedelta(days=date.today().weekday()))  # weekday 기반 (공휴일 대응)
        carry_over  = {tk: info for tk, info in self.positions.items()
                       if info.get("entry_date","") < _this_mon_s}
        cleared     = len([t for t in this_week])  # 이번 주 청산
        if carry_over:
            msg += f"\n📌 <b>다음 주 이월 종목: {len(carry_over)}개</b>\n"
            for tk, info in carry_over.items():
                nm   = info.get("name", resolve_name(tk))
                bp   = float(info.get("buy_price",0))
                cp   = get_current_price(tk)
                if cp <= 0: cp = bp
                ret  = (cp-bp)/bp if bp > 0 else 0
                _ok, _reason = is_friday_hold_ok(tk, info, cp)
                _tag = "✅ 보유유지" if _ok else "⚠️ 다음주 정리"
                msg += f"  {_tag} | {nm}  {ret:+.2%}\n"
        if preview[:3]:
            msg += "\n⭐ <b>다음주 미리 볼 종목</b>\n"
            for nm, eg in preview[:3]:
                msg += f"  ⭐ {nm}: {eg:.3f}점\n"
        # ── ① 모의 vs 실계좌 비교 리포트 ──────────────────
        try:
            import sqlite3 as _sq3
            _con = _sq3.connect(Path("trade_history.db"))
            _con.row_factory = _sq3.Row
            _all_rows = [dict(r) for r in _con.execute(
                "SELECT * FROM trades WHERE action='sell' ORDER BY date"
            ).fetchall()]
            _con.close()

            _wk_s = str(week_start)
            _mock_week = [r for r in _all_rows if r.get("mode")=="mock" and r.get("date","")>=_wk_s]
            _real_week = [r for r in _all_rows if r.get("mode")=="real" and r.get("date","")>=_wk_s]
            _mock_all  = [r for r in _all_rows if r.get("mode")=="mock"]
            _real_all  = [r for r in _all_rows if r.get("mode")=="real"]

            def _stats(rows):
                if not rows: return {"count":0,"wins":0,"win_rate":0,"total_pnl":0}
                wins = sum(1 for r in rows if r.get("pnl",0)>0)
                return {"count":len(rows),"wins":wins,
                        "win_rate":wins/len(rows),"total_pnl":sum(r.get("pnl",0) for r in rows)}

            _mw = _stats(_mock_week); _rw = _stats(_real_week)
            _ma = _stats(_mock_all);  _ra = _stats(_real_all)

            if _mock_all or _real_all:
                _cmp_msg = ("━━━━━━━━━━━━━━━━━━\n"
                            "⚖️ <b>모의 vs 실계좌 비교</b>\n"
                            f"{'항목':<8} {'🔵모의':>10} {'🟢실계좌':>10}\n"
                            f"{'이번주손익':<6} {_mw['total_pnl']:>+10,.0f} {_rw['total_pnl']:>+10,.0f}\n"
                            f"{'이번주승률':<6} {_mw['win_rate']:>10.1%} {_rw['win_rate']:>10.1%}\n"
                            f"{'누적손익':<6} {_ma['total_pnl']:>+10,.0f} {_ra['total_pnl']:>+10,.0f}\n"
                            f"{'누적승률':<6} {_ma['win_rate']:>10.1%} {_ra['win_rate']:>10.1%}\n"
                            f"{'거래횟수':<6} {_ma['count']:>10}회 {_ra['count']:>10}회\n")
                # gap 분석
                _pnl_gap = _ra['total_pnl'] - _ma['total_pnl']
                _wr_gap  = _ra['win_rate'] - _ma['win_rate']
                _gap_txt = (f"📐 실계좌 - 모의: 손익 {_pnl_gap:+,.0f}원 | 승률 {_wr_gap:+.1%}\n"
                            if (_mock_all and _real_all) else "")
                tg(_cmp_msg + _gap_txt)
        except Exception as _e:
            log.warning(f"모의vs실계좌 리포트 오류: {_e}")

        # ── ② 슬리피지 주간 경고 ────────────────────────────
        try:
            import sqlite3 as _sq3b
            _con2 = _sq3b.connect(Path("trade_history.db"))
            _con2.row_factory = _sq3b.Row
            _buy_rows = [dict(r) for r in _con2.execute(
                "SELECT * FROM trades WHERE action='buy' AND date>=? ORDER BY date",
                (str(week_start),)
            ).fetchall()]
            _con2.close()
            _slip_vals = []
            for _br in _buy_rows:
                try:
                    _df_sl = get_ohlcv(_br["ticker"], days=60)
                    if _df_sl is None or len(_df_sl) < 2: continue
                    import pandas as _pd2
                    _df_sl.index = _pd2.to_datetime(_df_sl.index)
                    _prior = _df_sl[_df_sl.index < _pd2.to_datetime(_br["date"])]
                    if len(_prior) == 0: continue
                    _sig_p = float(_prior["종가"].iloc[-1])
                    if _sig_p > 0:
                        _slip_vals.append((_br["price"] - _sig_p) / _sig_p)
                except Exception:
                    continue
            if _slip_vals:
                _avg_slip = sum(_slip_vals) / len(_slip_vals)
                if abs(_avg_slip) > 0.003:   # 0.3% 초과 시 경고
                    tg(f"⚠️ <b>슬리피지 경고</b>\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"이번 주 평균 슬리피지: {_avg_slip:+.3%}\n"
                       f"매수 {len(_slip_vals)}건 기준\n\n"
                       f"{'📈 시장가 주문이 너무 높게 체결되고 있어요.' if _avg_slip > 0 else '✅ 유리하게 체결되고 있어요.'}\n"
                       f"{'지정가 매수나 분할 매수를 고려해보세요.' if _avg_slip > 0.005 else ''}")
        except Exception as _e2:
            log.warning(f"슬리피지 경고 오류: {_e2}")

        tg_btn(msg, [[ {"text": "🏠 메인 메뉴", "callback_data": "menu"}]])
        # ── 월 1회 자동 최적화 (매월 마지막 금요일) ─────────
        today     = date.today()
        next_fri  = today + timedelta(days=7)
        if next_fri.month != today.month:   # 이번달 마지막 금요일
            self._run_auto_optimizer()
    # ── 자동 최적화 실행 ─────────────────────────────
    # ── 원칙1+2: 월요일 자본 재계산 + 새 주 시작 알림 (08:35) ──────────
    def daily_capital_sync(self):
        """
        매일 08:35 키움 잔고(예수금+보유평가금) → TOTAL_CAPITAL 자동 동기화
        모의 모드: 모의계좌 기준 / 실계좌 모드: 실계좌 기준
        키움 조회 실패 시 calc_effective_capital 폴백
        """
        global C
        if not is_trading_day():
            return
        old_cap = C.get("TOTAL_CAPITAL", 10_000_000)
        _kiwoom_cap = 0
        _mode_label = "알수없음"
        try:
            _kw = kiwoom()
            if _kw:
                _dep = _kw.get_deposit()
                _bal = _kw.get_balance()
                _eval_total = sum(b.get("eval_amt", 0) for b in _bal)
                _kiwoom_cap = _dep + _eval_total
                _mode_label = "모의계좌" if _kw._mock else "실계좌"
                log.info(f"[자본동기화] 키움 {_mode_label}: {_kiwoom_cap:,.0f}원 "
                         f"(예수금 {_dep:,.0f} + 평가금 {_eval_total:,.0f})")
        except Exception as _e:
            log.warning(f"[자본동기화] 키움 조회 실패 → calc_effective_capital 폴백: {_e}")

        if _kiwoom_cap > 0:
            new_cap = round(max(_kiwoom_cap, old_cap * C.get("CAPITAL_FLOOR_RATIO", 0.70)), -4)
        else:
            new_cap = calc_effective_capital(self.positions)
            new_cap = round(max(new_cap, old_cap * C.get("CAPITAL_FLOOR_RATIO", 0.70)), -4)

        if new_cap != old_cap:
            _save_cfg_direct("TOTAL_CAPITAL", new_cap)
            C = load_config()
            pnl_str = f"{new_cap - old_cap:+,.0f}원"
            log.info(f"[자본동기화] {old_cap:,.0f} → {new_cap:,.0f} ({pnl_str})")

    def monday_reset(self):
        """
        투자원칙 1: 전주 총자산(현금+평가금)을 새 TOTAL_CAPITAL로 갱신
        투자원칙 2: 새 주 시작 메시지 발송
        실행시각: 매주 월요일 08:35 (장 시작 전)
        """
        global C   # [수정] C 사용 전 global 선언 (Python: global은 함수 첫 사용 전에 위치해야 함)
        if not is_trading_day() or date.today().weekday() != 0:
            return
        if not C.get("WEEKLY_CAPITAL_RESET", True):
            return
        log.info("🗓️ 월요일 자본 재계산")
        _pre_cap = C.get("TOTAL_CAPITAL", 10_000_000)   # sync 전 자본 기억
        self.daily_capital_sync()   # 키움 잔고 동기화 (매일 08:35 공통 함수)
        C = load_config()
        new_cap = C.get("TOTAL_CAPITAL", _pre_cap)      # sync 후 갱신된 자본
        old_cap = _pre_cap                               # 전주 기준 자본
        pnl   = new_cap - old_cap
        icon  = "📈" if pnl >= 0 else "📉"
        ret_s = f"{pnl/old_cap:+.2%}" if old_cap > 0 else "+0.00%"
        # 전주 성적
        logs    = load_trade_log()
        w_start = str(date.today() - timedelta(days=7))
        lw      = [t for t in logs
                   if t.get("exit_date", "") >= w_start
                   and t.get("exit_price", 0) > 0]
        lw_p    = calc_performance(lw)
        regime_e = {"BULL": "📈", "SIDE": "➡️", "BEAR": "📉"}.get(self.regime, "❓")
        tg(
            f"🗓️ <b>새로운 한 주 시작!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>📊 전주 성적표</b>\n"
            f"  거래 {lw_p['count']}회  |  승률 {lw_p['win_rate']:.0%}\n"
            f"  평균 수익: {lw_p['avg_ret']:+.2%}\n"
            f"  주간 손익: {lw_p['total_pnl']:+,.0f}원\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{icon} <b>이번 주 운용 자본</b>\n"
            f"  {old_cap:,.0f}원  →  <b>{new_cap:,.0f}원</b> ({ret_s})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{regime_e} 현재 {self.regime}국면\n"
            f"💪 이번 주도 원칙대로 시작해요!\n"
            f"   (이번 주 보유 종목은 금요일 전에 정리)"
        )
    # ── 원칙2: 목요일 사전 정리 경보 (15:00) ────────────────────────────
    # ── 수요일 중간 점검 (15:35) ────────────────────────────
    def wednesday_midcheck(self):
        """주간 중반 성적 + 보유 현황 요약 (수요일 장마감 후)"""
        if not is_trading_day() or date.today().weekday() != 2:
            return
        log.info("📊 수요일 중간 점검")
        # 이번 주 월요일부터 오늘까지 거래 성적
        logs      = load_trade_log()
        _this_mon = date.today() - timedelta(days=date.today().weekday())  # 이번 주 월요일 (weekday 기반)
        this_week = [t for t in logs
                     if t.get("exit_date", "") >= str(_this_mon)
                     and t.get("exit_price", 0) > 0]
        wp = calc_performance(this_week)
        regime_e = {"BULL":"📈","SIDE":"➡️","BEAR":"📉"}.get(self.regime,"❓")
        _remaining = get_remaining_trading_days()   # 공휴일 포함 동적 계산
        msg = (
            f"📊 <b>주간 중간 점검</b> (수요일 기준)\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{regime_e} {self.regime}국면  |  이번 주 남은 거래일: <b>{_remaining}일</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>📅 이번 주 성적 (월~수)</b>\n"
            f"  거래: {wp['count']}회  |  승률: {wp['win_rate']:.0%}\n"
            f"  평균 수익: {wp['avg_ret']:+.2%}\n"
            f"  누적 손익: {wp['total_pnl']:+,.0f}원\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
        if self.positions:
            msg += "<b>📌 현재 보유 종목</b>\n"
            for ticker, info in self.positions.items():
                name  = info.get("name", resolve_name(ticker))
                buy_p = float(info.get("buy_price", 0))
                shares= int(info.get("shares", 0))
                cp    = get_current_price(ticker)
                if cp <= 0: cp = buy_p
                ret   = (cp - buy_p) / buy_p if buy_p > 0 else 0
                pnl   = (cp - buy_p) * shares
                tm    = " 🔺" if info.get("trail_active") else ""
                icon  = "✅" if ret >= 0 else "🔴"
                # 이번 주 진입 여부
                _entry  = info.get("entry_date","")
                _this_m = str(date.today() - timedelta(days=date.today().weekday()))
                _tag    = " [이월]" if _entry < _this_m else ""
                msg += (
                    f"  {icon} <b>{name}</b>{tm}{_tag}\n"
                    f"     {ret:+.2%}  ({pnl:+,.0f}원)\n"
                )
            msg += (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💡 이번 주 남은 거래일: 목·금\n"
                f"   금요일까지 원칙에 따라 정리해요\n"
                f"   (수익+AI점수 양호 시 이월 가능)"
            )
        else:
            msg += "💵 현재 보유 종목 없음\n"
        tg_btn(msg, [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]])
    def thursday_warning(self):
        """
        투자원칙 2: 목요일 15:00 — 미청산 종목 사전 경보
        내일(금요일)이 마감일임을 알리고 종목별 상태 요약
        """
        if not is_trading_day() or date.today().weekday() != 3:
            return
        if not self.positions or not C.get("FRIDAY_FORCE_EXIT", True):
            return
        log.info("⚠️ 목요일 사전 정리 경보")
        lines = [
            "⚠️ <b>내일(금요일)이 마감일이에요!</b>",
            "━━━━━━━━━━━━━━━━━━",
            "투자원칙: 매주 금요일까지 전 종목 정리\n",
            "현재 보유 종목:",
        ]
        for ticker, info in self.positions.items():
            name   = info.get("name", resolve_name(ticker))
            buy_p  = float(info.get("buy_price", 0))
            shares = int(info.get("shares", 0))
            cp     = get_current_price(ticker)
            if cp <= 0: cp = buy_p
            ret  = (cp - buy_p) / buy_p if buy_p > 0 else 0
            pnl  = (cp - buy_p) * shares
            icon = "✅" if ret >= 0 else "🔴"
            if info.get("timestop_alerted"):
                advice = "⏱️ 타임스탑 발동됨 — 즉시 매도 권장"
            elif info.get("trail_active"):
                advice = "🔺 트레일링 중 — 트레일링 발동 시 청산"
            elif ret >= C.get("TAKE_PROFIT_FIXED", 0.15):
                advice = "🎯 목표 달성 — 내일 오전 매도 권장"
            elif ret < 0:
                advice = "⚠️ 손실 중 — 손절선 확인 후 정리"
            else:
                advice = "💡 내일 장 중 적절한 시점에 정리"
            lines.append(
                f"\n📌 <b>{name}</b>\n"
                f"   {icon} {ret:+.2%}  ({pnl:+,.0f}원)\n"
                f"   {advice}"
            )
        lines += [
            "━━━━━━━━━━━━━━━━━━",
            "⏰ 내일 15:20까지 정리 완료해주세요",
            "   15:20에 미청산 종목 최종 알림이 와요",
        ]
        tg_btn("\n".join(lines), [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]])
    # ── 원칙2: 금요일 강제 청산 최종 알림 (15:20) ───────────────────────
    def friday_force_exit(self):
        """
        투자원칙 2: 금요일 15:20 — 미청산 종목 최종 경보 + 매도 버튼 제공
        장마감(15:30) 10분 전에 발송
        """
        if not is_trading_day() or date.today().weekday() != 4:
            return
        if not C.get("FRIDAY_FORCE_EXIT", True):
            return
        log.info("🚨 금요일 강제 청산 최종 알림")
        if not self.positions:
            tg(
                "✅ <b>이번 주 모든 종목 정리 완료!</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "완벽해요 👏\n"
                "다음 주 월요일 08:35에\n"
                "새 자본금과 함께 새롭게 시작해요 💪"
            )
            return
        # ── 수정된 원칙2: 보유 유지 / 청산 분류 ──
        hold_tickers   = {}   # 보유 유지 (수익+AI점수 양호)
        exit_tickers   = {}   # 청산 필요
        for ticker, info in self.positions.items():
            cp = get_current_price(ticker)
            if cp <= 0: cp = float(info.get("buy_price", 0))
            ok, reason = is_friday_hold_ok(ticker, info, cp)
            if ok:
                hold_tickers[ticker] = (info, cp, reason)
            else:
                exit_tickers[ticker] = (info, cp, reason)
        # ── 청산 필요 종목 알림 ──
        if exit_tickers:
            lines = [
                "🚨 <b>마감 10분 전! 청산이 필요한 종목이 있어요</b>",
                "━━━━━━━━━━━━━━━━━━",
                "지금 바로 매도 주문 넣어주세요:\n",
            ]
            total_pnl = 0
            for ticker, (info, cp, reason) in exit_tickers.items():
                name  = info.get("name", resolve_name(ticker))
                buy_p = float(info.get("buy_price", 0))
                shares= int(info.get("shares", 0))
                ret   = (cp - buy_p) / buy_p if buy_p > 0 else 0
                pnl   = (cp - buy_p) * shares
                total_pnl += pnl
                icon = "✅" if ret >= 0 else "🔴"
                lines.append(
                    f"{icon} <b>{name}</b>  {ret:+.2%}  ({pnl:+,.0f}원)\n"
                    f"   └ {reason}"
                )
            lines += [
                "━━━━━━━━━━━━━━━━━━",
                f"예상 손익: <b>{total_pnl:+,.0f}원</b>",
                "⏰ 장마감까지 10분! 지금 매도해주세요",
            ]
            tg("\n".join(lines))
        # ── 보유 유지 종목 알림 (+ 주말 갭 리스크 경고) ──
        if hold_tickers:
            lines = [
                "✅ <b>보유 유지 종목 (원칙2 예외)</b>",
                "━━━━━━━━━━━━━━━━━━",
                "수익 중 + AI점수 양호 → 시스템 매도 신호까지 보유:\n",
            ]
            for ticker, (info, cp, reason) in hold_tickers.items():
                name  = info.get("name", resolve_name(ticker))
                buy_p = float(info.get("buy_price", 0))
                shares= int(info.get("shares", 0))
                ret   = (cp - buy_p) / buy_p if buy_p > 0 else 0
                pnl   = (cp - buy_p) * shares
                df_h  = get_ohlcv(ticker, days=30)
                atr   = calc_atr(df_h) if df_h is not None else cp * 0.02
                dyn_sl= calc_dynamic_sl(atr, cp, ticker, self.regime)
                # [v40.0 BUG-FIX] 표시 손절가를 실제 트리거와 동일하게 매수가 기준으로 통일
                _sl_base_ff = buy_p if buy_p > 0 else cp
                sl_p  = round(_sl_base_ff * (1 + dyn_sl), -1)
                lines.append(
                    f"🔺 <b>{name}</b>  {ret:+.2%}  ({pnl:+,.0f}원)\n"
                    f"   └ {reason}\n"
                    f"   🛑 손절가: {sl_p:,.0f}원 (주말 후 월요일 설정 필수)"
                )
            lines += [
                "━━━━━━━━━━━━━━━━━━",
                "⚠️ <b>주말 갭 리스크 주의</b>",
                "  주말 사이 예상치 못한 악재 발생 시",
                "  월요일 시가에 갭하락이 반영될 수 있어요",
                "  → 월요일 08:40 아침 보고에서 재확인해드려요",
            ]
            tg("\n".join(lines))
        # ── 전체 정리 완료 시 ──
        if not exit_tickers and not hold_tickers:
            tg(
                "✅ <b>이번 주 모든 종목 정리 완료!</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "완벽해요 👏\n"
                "다음 주 월요일 08:35에\n"
                "새 자본금과 함께 새롭게 시작해요 💪"
            )
    def _run_auto_optimizer(self, dry_run: bool = False):
        """
        실거래 결과 분석 → 파라미터 자동 최적화
        dry_run=True 이면 미리보기만 (실제 파일 미수정)
        """
        import threading
        # [Issue-8 수정] sys.argv 전역 변조 동시성 문제 방지를 위한 Lock
        _argv_lock = getattr(self, "_optimizer_argv_lock", None)
        if _argv_lock is None:
            self._optimizer_argv_lock = threading.Lock()
            _argv_lock = self._optimizer_argv_lock
        def _run():
            try:
                log.info("🤖 자동 최적화 시작")
                tg("🤖 <b>월간 자동 최적화 시작...</b>\n실거래 데이터를 분석하고 있어요")
                # opt.py(기본) 또는 edge_optimizer.py 중 존재하는 파일 사용
                opt_file = Path(__file__).parent / "opt.py"
                if not opt_file.exists():
                    opt_file = Path(__file__).parent / "edge_optimizer.py"
                if not opt_file.exists():
                    tg("❌ opt.py 파일이 없어요\n같은 폴더에 놓아주세요")
                    return
                import importlib.util
                import sys as _sys
                spec = importlib.util.spec_from_file_location("optimizer", opt_file)
                opt  = importlib.util.module_from_spec(spec)
                # [Issue-8 수정] sys.argv 임계구역 — Lock 보호 + 복원 보장
                with _argv_lock:
                    _orig_argv = _sys.argv[:]           # 원본 보존
                    try:
                        if dry_run:
                            _sys.argv = [_sys.argv[0]]  # --apply 없이 → DRY_RUN=True
                        else:
                            _sys.argv = [_sys.argv[0], "--apply", "--tg"]
                        spec.loader.exec_module(opt)    # ← 모듈 수준 argv 읽기 완료 후 즉시 복원
                    finally:
                        _sys.argv = _orig_argv          # 반드시 원복 (예외 발생 시에도)
                trades = opt.load_trades()
                if not trades:
                    tg("⚠️ 분석할 거래 데이터가 없어요\n거래가 쌓이면 자동으로 실행돼요")
                    return
                stats        = opt.calc_stats(trades)
                diagnose_sug = opt.diagnose(stats)
                # BUG-D 수정: current_cfg 로드를 grid_search 전으로 이동
                current_cfg  = json.loads(CONFIG_FILE.read_text(encoding="utf-8")) \
                               if CONFIG_FILE.exists() else {}
                grid_result  = opt.grid_search(trades, stats, current_cfg) if len(trades) >= 5 else {}
                updates      = opt.merge_recommendations(grid_result, diagnose_sug, current_cfg)
                updates      = {k: v for k, v in updates.items()
                                if v is not None and current_cfg.get(k) != v}
                if not updates:
                    tg("✅ <b>자동 최적화 완료</b>\n현재 설정이 이미 최적 상태예요!")
                    return
                if not dry_run:
                    # config.json 업데이트
                    prev_cfg  = opt.update_config(updates)
                    bt_changed = opt.update_backtest_source(updates)
                    # 전역 C 즉시 반영
                    global C
                    C = load_config()
                    report = opt.build_report(stats, updates, prev_cfg,
                                              bt_changed, diagnose_sug)
                    tg(report)
                    log.info(f"✅ 자동 최적화 완료: {len(updates)}개 파라미터 변경")
                else:
                    # 미리보기
                    lines = ["🔍 <b>최적화 미리보기</b>",
                             f"━━━━━━━━━━━━━━━━━━",
                             f"분석 거래: {len(trades)}건",
                             f"승률: {stats.get('win_rate',0):.1%}",
                             "",
                             "변경 예정 파라미터:"]
                    for k, v in updates.items():
                        old = current_cfg.get(k)
                        lines.append(f"  {k}: {old} → {v}")
                    lines += ["", "✅ 적용하려면 텔레그램에서\n[최적화 적용] 버튼을 눌러주세요"]
                    tg("\n".join(lines))
            except Exception as e:
                log.error(f"자동 최적화 오류: {e}")
                tg(f"❌ 자동 최적화 중 오류 발생\n{str(e)[:100]}")
        threading.Thread(target=_run, daemon=True).start()
    # ── 아침 전략 보고 ────────────────────────────
    def morning_report(self):
        # ㊱ 서킷브레이커 매일 해제 + 해제 알림
        if getattr(self, '_circuit_active', False):
            self._circuit_active = False   # ✅ 매일 아침 서킷브레이커 자동 해제
            tg("✅ <b>다시 정상 운영이에요!</b>\n"
               "━━━━━━━━━━━━━━━━━━\n"
               "어제는 보유 종목이 많이 떨어져서\n"
               "안전을 위해 매수를 멈췄었어요\n\n"
               "오늘부터 다시 좋은 종목이 나오면\n"
               "매수 추천을 보내드릴게요 💪")
        # FIX-2: 주봉 추세 캐시 갱신 (하루 1회, 아침에 계산)
        self._weekly_trend_cache = {}
        for ticker in self.universe:
            try:
                df = get_ohlcv(ticker, days=90)
                if df is not None and len(df) > 50:
                    _weekly = df["종가"].resample("W-FRI").last().dropna()
                    if len(_weekly) > 10:
                        _wma = _weekly.rolling(10).mean()
                        self._weekly_trend_cache[ticker] = (
                            float(_weekly.iloc[-1]) > float(_wma.iloc[-1]))
                    else:
                        self._weekly_trend_cache[ticker] = True  # 데이터 부족 → 통과
                else:
                    self._weekly_trend_cache[ticker] = True
            except Exception:
                self._weekly_trend_cache[ticker] = True
        log.info(f"  주봉추세 캐시 갱신: {sum(self._weekly_trend_cache.values())}"
                 f"/{len(self._weekly_trend_cache)} 상승추세")
        # FIX-4: 유니버스 vs SECTOR_MAP 동기화 검증
        _unmapped = [tk for tk in self.universe
                     if get_sector_for_ticker_rt(tk) == "기타"]
        if len(_unmapped) > len(self.universe) * 0.5:
            log.warning(f"⚠️ SECTOR_MAP 미등록 종목 과다: {len(_unmapped)}/{len(self.universe)}")
            tg(f"⚠️ <b>종목 분류 업데이트가 필요해요</b>\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"관심 종목 {len(self.universe)}개 중 {len(_unmapped)}개의\n"
               f"업종 분류가 안 돼 있어요\n\n"
               f"같은 업종에 너무 몰아서 사지 않도록\n"
               f"자동으로 관리하고 있는데\n"
               f"분류가 안 된 종목이 많으면 이 기능이 약해져요\n\n"
               f"📌 소스코드의 SECTOR_MAP_RT에\n"
               f"   새 종목의 업종을 추가해주세요\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"미등록: {', '.join(_unmapped[:5])}{'...' if len(_unmapped) > 5 else ''}")
        log.info("🌅 아침 전략 보고")
        self.update_regime()
        regime_emoji = {"BULL":"📈","SIDE":"➡️","BEAR":"📉"}.get(self.regime,"❓")
        now_str      = datetime.now().strftime("%m/%d %H:%M")
        # ── ① 보유 종목 손절가 안내 ──────────────────────────
        _tp = _fetch_naver_realtime("005930")
        _src_txt = (f"🟢 네이버 실시간 ({_tp:,.0f}원)" if _tp > 0
                    else "🟡 FDR 일봉 (장 시작 후 실시간 전환)")
        # STEP2-A: 경제이벤트 캘린더 알림
        _today_mr = date.today()
        _tomorrow_mr = _today_mr + timedelta(days=1)
        _econ_mr = C.get("ECON_EVENTS_2025_2026", [])
        def __try_parse_date(s):
            try: return date.fromisoformat(s)
            except: return None
        _econ_dates = [__d for __s in _econ_mr for __d in [__try_parse_date(__s)] if __d]
        _econ_today    = _today_mr    in _econ_dates
        _econ_tomorrow = _tomorrow_mr in _econ_dates
        if _econ_today:
            tg("🔴 <b>오늘 중요한 경제 발표가 있어요!</b>\n"
               "━━━━━━━━━━━━━━━━━━\n"
               "미국 금리/물가/고용 관련 발표가 있는 날이에요\n"
               "이런 날은 주가가 크게 출렁일 수 있어요\n\n"
               "📌 오늘 AI가 하는 일\n"
               "   더 확실한 종목만 추천해요\n"
               "   (추천 기준을 평소보다 높였어요)\n\n"
               "💡 갖고 있는 종목의 손절가를 꼭 확인하세요!")
        elif _econ_tomorrow:
            tg("⚠️ <b>내일 중요한 경제 발표가 있어요</b>\n"
               "━━━━━━━━━━━━━━━━━━\n"
               "내일 미국 금리/물가/고용 관련 발표가 있어요\n\n"
               "💡 오늘 주식을 새로 사려면 신중하게!\n"
               "   내일 발표 후 주가가 크게 움직일 수 있어요\n"
               "   이미 갖고 있는 종목은 걱정 안 해도 돼요")
        if self.positions:
            msg  = (f"🌅 <b>장 시작 전 체크리스트</b>\n"
                    f"{regime_emoji} {self.regime}국면  |  {now_str}\n"
                    f"{_src_txt}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"<b>🛑 오늘 스탑로스 설정가</b>\n"
                    f"(트레이딩 시스템에 아래 가격으로 스탑로스 설정해두세요)\n\n")
            for ticker, info in self.positions.items():
                name   = info.get("name", resolve_name(ticker))
                buy_p  = float(info.get("buy_price", 0))
                shares = int(info.get("shares", 0))
                df     = get_ohlcv(ticker, days=30)
                cp_cached = 0.0
                cached = _ohlcv_cache.get(ticker)
                if cached and cached["df"] is not None:
                    cp_cached = float(cached["df"]["종가"].iloc[-1])
                cp = cp_cached if cp_cached > 0 else buy_p
                atr      = calc_atr(df) if df is not None else cp * 0.02
                dyn_sl   = calc_dynamic_sl(atr, cp, ticker, self.regime)
                # [v40.0 BUG-FIX] 표시 손절가를 실제 트리거와 동일하게 매수가 기준으로 통일
                _sl_base_mr = buy_p if buy_p > 0 else cp
                sl_price = round(_sl_base_mr * (1 + dyn_sl), -1)
                if np.isnan(sl_price) or sl_price <= 0:
                    sl_price = round(_sl_base_mr * 0.93, -1)
                ret      = (cp - buy_p) / buy_p if buy_p > 0 else 0
                pnl      = (cp - buy_p) * shares
                r_icon   = "✅" if ret >= 0 else "🔴"
                trail_str = " 🔺트레일링 중" if info.get("trail_active") else ""
                # 이월 종목 판단 (지난 주 매수)
                _entry = info.get("entry_date", "")
                _today = date.today()
                # 이번 주 월요일 계산
                _this_monday = _today - timedelta(days=_today.weekday())
                _is_carry = (_entry < str(_this_monday)) if _entry else False
                _carry_tag = " <b>[이월]</b>" if _is_carry else ""
                # 이월 종목 안내 (금요일 판단은 금요일 실시간으로 is_friday_hold_ok 실행)
                _hold_hint = ""
                if _is_carry:
                    _hold_hint = (
                        f"\n   📌 이월 종목 — 이번 주 내 정리 예정"
                        f"\n   (금요일 15:20 AI점수 기준으로 자동 판단)"
                    )
                msg += (f"📌 <b>{name}</b>{trail_str}{_carry_tag}\n"
                        f"   산 가격: {buy_p:,.0f}원  현재: {cp:,.0f}원\n"
                        f"   {r_icon} 수익률: {ret:+.2%}  ({pnl:+,.0f}원)\n"
                        f"   🛑 스탑로스 설정가: <b>{sl_price:,.0f}원</b> "
                        f"({dyn_sl:.1%}){_hold_hint}\n\n")
            tg_btn(msg, [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]])
        # ── ② 오늘 주목 종목 (AI점수 + 매수 적정가) ──────────
        self.scan_universe(force_notify=True)
        watch = []
        for ticker, name in self.universe.items():
            df = get_ohlcv(ticker, days=60)
            if df is None: continue
            if ticker in self.positions: continue
            time.sleep(0.15)   # [IP 차단 방지] 종목 간 150ms 간격
            # [New-C] 아침 보고도 확정봉 기준 — 08:40 실행이라 장 전이지만 방어적으로 적용
            df_signal       = get_closed_df(df)
            if df_signal is None or len(df_signal) < 20: continue
            kind_adj        = fetch_kind_sentiment(ticker)
            edge            = calculate_edge_v27(df_signal, kind_adj, ticker)
            slip_ok, exp, _ = check_slippage_filter(df_signal, ticker)
            if edge >= 0.70 and slip_ok:
                guide = calc_entry_guide(df_signal, ticker, self.regime)
                split_label = ""
                for step in C["SPLIT_BUY_STEPS"]:
                    if edge >= step["edge"]:
                        split_label = step["label"]
                watch.append((name, ticker, edge, exp, kind_adj, split_label, guide))
        if watch:
            watch.sort(key=lambda x: -x[2])
            msg = (f"⭐ <b>오늘 AI 주목 종목</b>\n"
                   f"{regime_emoji} {self.regime}국면\n"
                   f"━━━━━━━━━━━━━━━━━━\n")
            for nm, tk, eg, exp, kadj, slbl, g in watch[:5]:
                kind_str  = f" 공시{kadj:+.2f}" if kadj != 0 else ""
                split_str = f" [{slbl}]" if slbl else ""
                entry_str  = (f"{g['entry_low']:,.0f}~{g['entry_high']:,.0f}원"
                              if g else "-")
                target_str = f"{g['target']:,.0f}원" if g else "-"
                sl_str     = f"{g['sl_price']:,.0f}원" if g else "-"
                msg += (f"\n⭐ <b>{nm}</b>  {int(eg*100)}점{kind_str}{split_str}\n"
                        f"   💰 매수 적정가: {entry_str}\n"
                        f"   🎯 목표가: {target_str}\n"
                        f"   🛑 손절가: {sl_str}\n")
            tg_btn(msg, [[{"text": "🏠 메인 메뉴", "callback_data": "menu"}]])
# ══════════════════════════════════════════════════
# 실행 진입점
# ══════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("=" * 55)
    log.info("  🚀 Edge Score v40.0 통합 엔진 가동")
    log.info("=" * 55)
    monitor = EdgeMonitor()
    monitor.update_regime()
    # ── 데이터 소스 진단 ─────────────────────────
    def _diagnose_data_sources():
        status, test_tk = [], "005930"
        kiwoom_ok = fdr_ok = naver_ok = False
        # ① 키움 현재가
        try:
            kw = kiwoom()
            if kw:
                _kp = kw.get_price(test_tk)
                if _kp and _kp > 0:
                    kiwoom_ok = True
                    status.append(f"✅ 키움 실시간 ({_kp:,}원)")
                else:
                    status.append("⚠️ 키움 실시간 (장 외 또는 접속 불가)")
            else:
                status.append("⚠️ 키움 (클라이언트 미연결)")
        except Exception:
            status.append("❌ 키움 (오류)")
        # ② FDR 일봉
        if FDR_OK:
            try:
                raw = fdr.DataReader(test_tk, (date.today()-timedelta(days=10)).strftime("%Y-%m-%d"))
                if raw is not None and len(raw) >= 3:
                    fdr_ok = True; status.append("✅ FDR (일봉 폴백)")
                else: status.append("⚠️ FDR (데이터 부족)")
            except: status.append("❌ FDR (오류)")
        else: status.append("❌ FDR (미설치)")
        # ③ 네이버
        try:
            p = _fetch_naver_realtime(test_tk)
            if p > 0: naver_ok = True; status.append(f"✅ 네이버 실시간 ({p:,.0f}원, 폴백)")
            else: status.append("⚠️ 네이버 실시간 (장 외 또는 접속 불가)")
        except: status.append("❌ 네이버 실시간 (오류)")
        status.append("✅ pykrx (폴백)" if PYKRX_OK else "⚠️ pykrx (미설치)")
        status.append("✅ yfinance (최종 폴백)" if YF_OK else "⚠️ yfinance (미설치)")
        primary = ("키움(실시간)" if kiwoom_ok
                   else "네이버(실시간)" if naver_ok
                   else "FDR(일봉)" if fdr_ok
                   else "폴백 모드")
        return status, primary, naver_ok, fdr_ok
    data_status, primary_source, naver_live, fdr_live = _diagnose_data_sources()
    log.info(f"📡 데이터 소스: {primary_source}")
    for s in data_status: log.info(f"  {s}")
    # 텔레그램 명령어 수신
    commander = TelegramCommander(monitor)
    commander.start()
    # ⑦ 네트워크 모니터 (복구 시 보유 종목 즉시 체크)
    net_monitor = NetworkMonitor(on_recover=lambda: monitor.scan_universe(force_notify=False))
    net_monitor.start()
    # ⑧ 웹 대시보드 API 서버 (선택적 — Flask 설치 시 활성)
    try:
        from dashboard_api import start_dashboard
        _dash_port = C.get("DASHBOARD_PORT", 5000)
        start_dashboard(monitor, port=_dash_port)
    except ImportError:
        log.info("ℹ️ 대시보드 비활성 (flask 미설치 — pip install flask flask-cors)")
    # ── 재시작 감지 ────────────────────────────────────────────
    _shutdown_file = Path(__file__).parent / "last_shutdown.txt"
    _restart_flag  = ""
    try:
        if _shutdown_file.exists():
            _last_ts = _shutdown_file.read_text().strip()
            _last_dt = datetime.fromisoformat(_last_ts)
            _gap_min = (datetime.now() - _last_dt).total_seconds() / 60
            if _gap_min > 30:   # 30분 이상 공백 → 비정상 종료로 판단
                _restart_flag = (f"\n⚠️ <b>비정상 재시작 감지</b>\n"
                                 f"   마지막 정상 종료: {_last_ts[:16]}\n"
                                 f"   공백: {int(_gap_min)}분")
            else:
                _restart_flag = f"\n🔄 정상 재시작 ({_last_ts[:16]})"
        else:
            _restart_flag = "\n🆕 최초 가동"
    except Exception:
        pass

    # ── 가동 메시지 최우선 발송 ──────────────────────────────────
    src_lines = "\n".join(f"  {s}" for s in data_status)
    tg(
        f"🚀 <b>Edge Score v40.0 가동</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>데이터 소스 진단</b>\n"
        f"{src_lines}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 유니버스: {len(monitor.universe)}개\n"
        f"⏰ {C['HOLD_CHECK_MIN']}분(보유) / {C['SCAN_CHECK_MIN']}분(스캔)\n"
        f"📅 공휴일 자동 스킵\n"
        f"🛡 ATR손절 + 트레일링 + 슬리피지필터\n"
        f"📢 수익구간알림 + 당일재진입차단\n"
        f"🧮 켈리공식 + 분할매수가이드\n"
        f"🌐 네트워크 복구 자동 체크\n"
        f"{'🟢 실제투자 모드' if _os_tg.getenv('KIWOOM_MOCK','true').lower()=='false' else '🔵 모의투자 모드'}\n"
        f"📱 명령어: /help"
        f"{_restart_flag}"
    )
    # ── 스케줄 ──────────────────────────────────
    schedule.every(C["HOLD_CHECK_MIN"]).minutes.do(monitor.check_holdings)
    schedule.every(C["SCAN_CHECK_MIN"]).minutes.do(monitor.scan_universe)
    schedule.every(30).minutes.do(monitor.update_regime)
    schedule.every(30).minutes.do(monitor.offhours_check)
    schedule.every().day.at("08:30").do(monitor.do_refresh_universe)
    schedule.every().day.at("08:40").do(monitor.morning_report)
    schedule.every().day.at("15:30").do(monitor.close_report)
    schedule.every().day.at("15:35").do(monitor.weekly_report)
    schedule.every().day.at("08:34").do(monitor.monday_reset)   # [BUG-FIX] 08:35 daily_capital_sync 이전 실행 → _pre_cap 전주 자본 정확히 캡처
    schedule.every().day.at("08:35").do(monitor.daily_capital_sync)
    schedule.every().day.at("15:00").do(monitor.thursday_warning)
    schedule.every().day.at("15:20").do(monitor.friday_force_exit)
    schedule.every().day.at("15:35").do(monitor.wednesday_midcheck)
    schedule.every().day.at("15:35").do(monitor.monthly_report)
    schedule.every().day.at("15:40").do(monitor.daily_backup)
    log.info("스케줄:")
    log.info(f"  {C['HOLD_CHECK_MIN']}분   → 보유 체크 (장중·거래일만)")
    log.info(f"  {C['SCAN_CHECK_MIN']}분   → 유니버스 스캔 (장중·거래일만)")
    log.info("  30분  → 국면갱신 / 장외체크")
    log.info("  08:30 → 유니버스 자동 갱신")
    log.info("  08:40 → 아침 전략 보고")
    log.info("  15:30 → 장 마감 리포트")
    log.info("  15:35 → 주간 성과 집계 (금요일만)")
    # 첫 보고 — 백그라운드 스레드로 (크래시 방지)
    threading.Thread(target=monitor.scan_universe,
                     kwargs={"force_notify": True}, daemon=True).start()
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        # 정상/비정상 상관없이 종료 시각 기록 (재시작 감지용)
        try:
            _sd_file = Path(__file__).parent / "last_shutdown.txt"
            _sd_file.write_text(datetime.now().isoformat())
            log.info("종료 시각 기록 완료")
        except Exception:
            pass