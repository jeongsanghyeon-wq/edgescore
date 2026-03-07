# ═══════════════════════════════════════════════════════════════
# kiwoom_client.py  — 키움 REST API 클라이언트 v1.3
# 공식 문서 기준 엔드포인트/API ID
#   토큰발급  : POST /oauth2/token          (au10001)
#   현재가    : POST /api/dostk/stkinfo     (ka10001)  → cur_prc
#   일봉조회  : POST /api/dostk/chart       (ka10081)  → stk_dt_pole_chart_qry[]
#   매수주문  : POST /api/dostk/ordr        (kt10000)
#   매도주문  : POST /api/dostk/ordr        (kt10001)
#   예수금    : POST /api/dostk/acnt        (kt00001)  → ord_alow_amt
#   잔고      : POST /api/dostk/acnt        (kt00004)  → stk_acnt_evlt_prst[]
# ═══════════════════════════════════════════════════════════════

import os
import threading
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional

# ── .env 로드 (항상 스크립트 위치 기준) ──────────────────────
def _load_env():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())

_load_env()
# ──────────────────────────────────────────────────────────────

log = logging.getLogger("kiwoom_client")

REAL_HOST = "https://api.kiwoom.com"
MOCK_HOST = "https://mockapi.kiwoom.com"


class KiwoomClient:
    """키움 REST API 클라이언트 (모의/실계좌 통합)"""

    def __init__(self):
        self._mock: bool = os.getenv("KIWOOM_MOCK", "true").lower() == "true"

        if self._mock:
            self._app_key    = os.getenv("KIWOOM_MOCK_APP_KEY", "")
            self._app_secret = os.getenv("KIWOOM_MOCK_APP_SECRET", "").strip()
            self._account    = os.getenv("KIWOOM_MOCK_ACCOUNT", "")
            self._host       = MOCK_HOST
        else:
            self._app_key    = os.getenv("KIWOOM_REAL_APP_KEY", "")
            self._app_secret = os.getenv("KIWOOM_REAL_APP_SECRET", "").strip()
            self._account    = os.getenv("KIWOOM_REAL_ACCOUNT", "")
            self._host       = REAL_HOST

        self._token: str = ""
        self._token_expires: datetime = datetime.min
        self._lock = threading.Lock()

        mode = "[모의]" if self._mock else "[실계좌]"
        log.info(f"KiwoomClient 초기화 {mode} host={self._host}")

    # ══════════════════════════════════════════════════════════
    # ① 토큰 관리
    # ══════════════════════════════════════════════════════════

    def _issue_token(self) -> bool:
        url = self._host + "/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "appkey":     self._app_key,
            "secretkey":  self._app_secret,
        }
        try:
            r = requests.post(url, json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
            self._token = data.get("token", "")
            expires_dt = data.get("token_expired", "")
            if expires_dt:
                try:
                    self._token_expires = datetime.strptime(expires_dt, "%Y-%m-%d %H:%M:%S")
                    self._token_expires -= timedelta(hours=1)
                except Exception:
                    self._token_expires = datetime.now() + timedelta(hours=23)
            else:
                self._token_expires = datetime.now() + timedelta(hours=23)
            log.info(f"[키움] 토큰 발급 성공 (만료: {self._token_expires})")
            return bool(self._token)
        except Exception as e:
            log.error(f"[키움] 토큰 발급 실패: {e}")
            return False

    def _ensure_token(self) -> bool:
        with self._lock:
            if not self._token or datetime.now() >= self._token_expires:
                return self._issue_token()
            return True

    def _headers(self, api_id: str) -> dict:
        return {
            "Content-Type":  "application/json;charset=UTF-8",
            "authorization": f"Bearer {self._token}",
            "api-id":        api_id,
        }

    def _post(self, endpoint: str, api_id: str, payload: dict) -> Optional[dict]:
        if not self._ensure_token():
            log.error("[키움] 토큰 없음")
            return None
        url = self._host + endpoint
        try:
            r = requests.post(url, headers=self._headers(api_id),
                              json=payload, timeout=10)
            if r.status_code == 429:
                raise Exception(f"429 rate limit: {r.text[:100]}")
            if r.status_code == 200:
                data = r.json()
                # return_code:5 = API 호출 한도 초과 (429와 동일 처리)
                if data.get("return_code") == 5:
                    raise Exception(f"429 rate limit: {data.get('return_msg','')}")
                return data
            log.error(f"[키움] {api_id} HTTP {r.status_code}: {r.text[:200]}")
            return None
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e):
                raise  # 상위에서 처리하도록 re-raise
            log.error(f"[키움] {api_id} 오류: {e}")
            return None

    # ══════════════════════════════════════════════════════════
    # ③ 현재가 조회  ka10001 → /api/dostk/stkinfo
    #    응답 필드: cur_prc (현재가, 부호 포함 문자열)
    # ══════════════════════════════════════════════════════════

    def get_price(self, ticker: str) -> int:
        """현재가 조회 (실패 시 0)"""
        data = self._post("/api/dostk/stkinfo", "ka10001", {"stk_cd": ticker})
        if data and data.get("return_code") == 0:
            try:
                raw = str(data.get("cur_prc", "0"))
                return abs(int(raw.replace(",", "").replace("+", "").replace("-", "")))
            except Exception as e:
                log.warning(f"[키움] 현재가 파싱 오류 {ticker}: {e}")
        return 0

    # ══════════════════════════════════════════════════════════
    # ④ 매수 주문  kt10000 → /api/dostk/ordr
    # ══════════════════════════════════════════════════════════

    def buy(self, ticker: str, qty: int, price: int = 0,
            order_type: str = "3") -> dict:
        """
        매수 주문
        order_type: '3'=시장가(기본), '0'=보통(지정가)
        """
        payload = {
            "dmst_stex_tp": "KRX",
            "stk_cd":       ticker,
            "ord_qty":      str(int(qty)),
            "ord_uv":       str(int(price)) if price > 0 else "",  # float→int: "48500.0"→"48500"
            "trde_tp":      order_type,
            "cond_uv":      "",
        }
        data = self._post("/api/dostk/ordr", "kt10000", payload)
        mode = "[모의]" if self._mock else "[실계좌]"
        if data and data.get("return_code") == 0:
            ord_no = data.get("ord_no", "")
            log.info(f"[키움] {mode} 매수주문 성공 | {ticker} {qty}주 | 주문번호:{ord_no}")
            return {"success": True, "order_no": ord_no, "ticker": ticker, "qty": qty}
        msg = data.get("return_msg", "응답없음") if data else "응답없음"
        log.error(f"[키움] {mode} 매수주문 실패 | {ticker}: {msg}")
        return {"success": False, "error": msg, "ticker": ticker}

    # ══════════════════════════════════════════════════════════
    # ⑤ 매도 주문  kt10001 → /api/dostk/ordr
    # ══════════════════════════════════════════════════════════

    def sell(self, ticker: str, qty: int, price: int = 0,
             order_type: str = "3") -> dict:
        """매도 주문"""
        payload = {
            "dmst_stex_tp": "KRX",
            "stk_cd":       ticker,
            "ord_qty":      str(int(qty)),
            "ord_uv":       str(int(price)) if price > 0 else "",  # float→int: "48500.0"→"48500"
            "trde_tp":      order_type,
            "cond_uv":      "",
        }
        data = self._post("/api/dostk/ordr", "kt10001", payload)
        mode = "[모의]" if self._mock else "[실계좌]"
        if data and data.get("return_code") == 0:
            ord_no = data.get("ord_no", "")
            log.info(f"[키움] {mode} 매도주문 성공 | {ticker} {qty}주 | 주문번호:{ord_no}")
            return {"success": True, "order_no": ord_no, "ticker": ticker, "qty": qty}
        msg = data.get("return_msg", "응답없음") if data else "응답없음"
        log.error(f"[키움] {mode} 매도주문 실패 | {ticker}: {msg}")
        return {"success": False, "error": msg, "ticker": ticker}

    # ══════════════════════════════════════════════════════════
    # ⑥ 예수금 조회  kt00001 → /api/dostk/acnt
    #    qry_tp: '2'=일반조회
    #    응답 필드: ord_alow_amt (주문가능금액)
    # ══════════════════════════════════════════════════════════

    def get_deposit(self) -> int:
        """주문가능 예수금 조회"""
        data = self._post("/api/dostk/acnt", "kt00001", {"qry_tp": "2"})
        if data and data.get("return_code") == 0:
            try:
                raw = str(data.get("ord_alow_amt", "0"))
                return int(raw.replace(",", ""))
            except Exception as e:
                log.warning(f"[키움] 예수금 파싱 오류: {e} | raw={data.get('ord_alow_amt')}")
        return 0

    # ══════════════════════════════════════════════════════════
    # ⑦ 잔고 조회  kt00004 → /api/dostk/acnt
    #    응답: stk_acnt_evlt_prst[] 리스트
    # ══════════════════════════════════════════════════════════

    def get_balance(self) -> list:
        """보유 종목 잔고 조회"""
        payload = {"qry_tp": "0", "dmst_stex_tp": "KRX"}
        data = self._post("/api/dostk/acnt", "kt00004", payload)
        if data and data.get("return_code") == 0:
            holdings = data.get("stk_acnt_evlt_prst", [])
            result = []
            def _int(s):
                v = str(s).replace(",", "").replace("+", "").strip()
                return int(v) if v else 0
            for h in holdings:
                try:
                    result.append({
                        "ticker":     h.get("stk_cd", "").strip().lstrip("A"),
                        "name":       h.get("stk_nm", ""),
                        "qty":        abs(_int(h.get("rmnd_qty", 0))),
                        "buy_price":  abs(_int(h.get("avg_prc", 0))),
                        "eval_price": abs(_int(h.get("cur_prc", 0))),
                        "eval_amt":   abs(_int(h.get("evlt_amt", 0))),
                        "pnl":        _int(h.get("pl_amt", 0)),
                        "pnl_pct":    float(h.get("pl_rt", "0") or "0"),
                    })
                except Exception as ex:
                    log.warning(f"[키움] 잔고 항목 파싱 오류: {ex}")
            return result
        return []

    # ══════════════════════════════════════════════════════════
    # ⑧ 유틸리티 (내부 헬퍼)
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def calc_qty(budget: int, price: int) -> int:
        """예산/가격으로 매수 수량 계산"""
        if price <= 0:
            return 0
        return max(1, budget // price)

    # ══════════════════════════════════════════════════════════
    # ⑨ 일봉 조회  ka10081 → /api/dostk/chart
    #    응답: stk_dt_pole_chart_qry[] 리스트
    #    필드: dt(날짜 YYYYMMDD), opn_prc(시가), high_prc(고가),
    #          low_prc(저가), close_prc(종가), trde_qty(거래량)
    # ══════════════════════════════════════════════════════════

    def get_ohlcv(self, ticker: str, days: int = 100) -> list:
        """
        일봉 OHLCV 조회 (최근 days일치)
        반환: [{"date": "2024-01-02", "open": 70000, "high": 71000,
                "low": 69000, "close": 70500, "volume": 12345678}, ...]
        실패 시 [] 반환
        """
        from datetime import date, timedelta
        end_dt   = date.today().strftime("%Y%m%d")
        # 키움은 최대 조회 건수 제한 있음 → days * 2 요청 후 tail(days)
        start_dt = (date.today() - timedelta(days=int(days * 2))).strftime("%Y%m%d")
        payload  = {
            "stk_cd":      ticker,
            "base_dt":     end_dt,
            "upd_stkpc_tp": "1",   # 수정주가 적용
        }
        data = self._post("/api/dostk/chart", "ka10081", payload)
        if not data:
            return []
        rc = data.get("return_code")
        if rc == 5 or "허용된 요청 개수를 초과" in data.get("return_msg", ""):
            raise Exception(f"429 rate limit: {data.get('return_msg','')}")
        if rc != 0:
            log.debug(f"[키움] ka10081 일봉 실패 | {ticker}: "
                      f"{data.get('return_msg','응답없음')}")
            return []
        rows = data.get("stk_dt_pole_chart_qry", [])
        if not rows:
            return []
        def _v(s):
            return abs(int(str(s).replace(",", "").replace("+", "").replace("-", "") or "0"))
        result = []
        for r in rows:
            try:
                dt_s = str(r.get("dt", ""))
                if len(dt_s) != 8:
                    continue
                date_str = f"{dt_s[:4]}-{dt_s[4:6]}-{dt_s[6:8]}"
                result.append({
                    "date":   date_str,
                    "open":   _v(r.get("opn_prc",   0)),
                    "high":   _v(r.get("high_prc",  0)),
                    "low":    _v(r.get("low_prc",   0)),
                    "close":  _v(r.get("close_prc", 0)),
                    "volume": _v(r.get("trde_qty",  0)),
                })
            except Exception as ex:
                log.debug(f"[키움] 일봉 파싱 오류 {ticker}: {ex}")
        # 날짜 오름차순 정렬 후 최근 days개
        result.sort(key=lambda x: x["date"])
        return result[-days:]

    # ══════════════════════════════════════════════════════════
    # ⑩ 체결 확인  kt00009 → /api/dostk/acnt
    #    cntr_qty(체결수량), cntr_uv(체결단가)
    # ══════════════════════════════════════════════════════════

    def get_order_fill(self, order_no: str, ticker: str) -> Optional[dict]:
        """
        주문번호로 체결 여부 조회
        반환: {"filled": True/False, "cntr_qty": 체결수량, "cntr_uv": 체결단가}
        """
        payload = {
            "ord_dt":       "",
            "stk_bond_tp":  "1",   # 주식
            "mrkt_tp":      "0",   # 전체
            "sell_tp":      "0",   # 전체
            "qry_tp":       "1",   # 체결만
            "stk_cd":       ticker,
            "fr_ord_no":    "",
            "dmst_stex_tp": "KRX",
        }
        data = self._post("/api/dostk/acnt", "kt00009", payload)
        if not data or data.get("return_code") != 0:
            return None

        orders = data.get("acnt_ord_cntr_prst", [])
        for o in orders:
            if str(o.get("ord_no", "")).strip().lstrip("0") == str(order_no).strip().lstrip("0"):
                cntr_qty = int(str(o.get("cntr_qty", "0")).replace(",", "") or "0")
                cntr_uv  = int(str(o.get("cntr_uv",  "0")).replace(",", "") or "0")
                return {
                    "filled":   cntr_qty > 0,
                    "cntr_qty": cntr_qty,
                    "cntr_uv":  cntr_uv,
                    "cntr_tm":  o.get("cntr_tm", ""),
                }
        return {"filled": False, "cntr_qty": 0, "cntr_uv": 0}

    def test_connection(self) -> bool:
        ok = self._issue_token()
        mode = "모의투자" if self._mock else "실계좌"
        print(f"[키움] {mode} 연결 {'성공 ✅' if ok else '실패 ❌'}")
        return ok


# ── 싱글턴 ────────────────────────────────────────────────────
_client = None

def get_client() -> KiwoomClient:
    global _client
    if _client is None:
        _client = KiwoomClient()
    return _client


# ── 단독 실행 테스트 ──────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    client = KiwoomClient()

    print("\n" + "="*55)
    print("  키움 REST API 연결 테스트 v1.3")
    print("="*55)

    print("\n[1] 토큰 발급...")
    if not client.test_connection():
        print("❌ 토큰 발급 실패 — .env 키 확인 필요")
        exit(1)

    print("\n[2] 삼성전자(005930) 현재가...")
    price = client.get_price("005930")
    if price:
        print(f"  ✅ 현재가: {price:,}원")
    else:
        print("  ⚠️  현재가 조회 실패 (장마감 시간이면 정상)")

    print("\n[3] 삼성전자(005930) 일봉 5일...")
    ohlcv = client.get_ohlcv("005930", days=5)
    if ohlcv:
        for row in ohlcv:
            print(f"  {row['date']} | 종가:{row['close']:,} | 거래량:{row['volume']:,}")
    else:
        print("  ⚠️  일봉 조회 실패")

    print("\n[3] 예수금 조회 (kt00001)...")
    deposit = client.get_deposit()
    print(f"  ✅ 주문가능금액: {deposit:,}원")

    print("\n[4] 보유종목 잔고 (kt00004)...")
    balance = client.get_balance()
    if balance:
        for b in balance:
            sign = "+" if b["pnl"] >= 0 else ""
            print(f"  {b['name']}({b['ticker']}) | {b['qty']}주 | "
                  f"평균단가:{b['buy_price']:,} | "
                  f"손익:{sign}{b['pnl']:,}원 ({b['pnl_pct']:.2f}%)")
    else:
        print("  보유종목 없음")

    print("\n" + "="*55)
