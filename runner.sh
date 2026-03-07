#!/bin/bash
# EQS V1.0 (Edge Quant Signal) 무중단 실행 스크립트

BASE_DIR="/Users/jeongsanghyeon/Desktop/edgescore"
LOG_DIR="$BASE_DIR/logs"
PYTHON="/opt/homebrew/bin/python3.11"
NPM="/opt/homebrew/bin/npm"

SRC="$BASE_DIR/Dashboard.jsx"
DST="$BASE_DIR/edge-dashboard/src/App.jsx"

# ── 로그 디렉토리 생성 ──────────────────────────────────────
mkdir -p "$LOG_DIR"

# ── [R-2 FIX] 종료 시그널 트랩 — 좀비 프로세스 방지 ───────
cleanup() {
    echo "[$(date '+%H:%M:%S')] 종료 신호 수신 — fswatch·npm 정리 중..."
    pkill -f "fswatch.*Dashboard.jsx" 2>/dev/null
    pkill -f "npm run dev"            2>/dev/null
    exit 0
}
trap cleanup SIGTERM SIGINT SIGHUP EXIT

# 부팅 직후 시스템 준비 대기
sleep 30

cd "$BASE_DIR"

# ── [R-3 FIX] 재시작 시 중복 실행 방지 ─────────────────────
pkill -f "fswatch.*Dashboard.jsx" 2>/dev/null
pkill -f "npm run dev"            2>/dev/null
sleep 1

# ── Dashboard.jsx → App.jsx 자동 동기화 (fswatch) ──────────
echo "🔄 Dashboard 자동 동기화 시작..."

cp "$SRC" "$DST"
echo "✅ Dashboard.jsx → App.jsx 초기 복사 완료"

nohup bash -c "
  fswatch -o \"$SRC\" | while read; do
    cp \"$SRC\" \"$DST\"
    echo \"[\$(date '+%H:%M:%S')] Dashboard.jsx 변경 감지 → App.jsx 자동 반영\"
  done
" >> "$LOG_DIR/dashboard_sync.log" 2>&1 &

echo "👀 Dashboard 파일 감시 중 (로그: $LOG_DIR/dashboard_sync.log)"

# ── 대시보드 프론트엔드 시작 ────────────────────────────────
echo "🖥️ 대시보드 프론트엔드 시작..."
cd "$BASE_DIR/edge-dashboard"
nohup "$NPM" run dev -- --host >> "$LOG_DIR/dashboard_frontend.log" 2>&1 &
cd "$BASE_DIR"

# ── 메인 루프: rt.py 무중단 재시작 ─────────────────────────
while true; do
    lsof -ti:5000 | xargs kill -9 2>/dev/null
    sleep 1

    echo "============================================================" | tee -a "$LOG_DIR/runner.log"
    echo "🚀 [$(date '+%Y년 %m월 %d일 %A %H시 %M분 %S초 KST')] EQS V1.0 엔진 기동 시작..." | tee -a "$LOG_DIR/runner.log"
    echo "============================================================" | tee -a "$LOG_DIR/runner.log"

    # [R-4 FIX] rt.py 출력 → 터미널 + 로그 파일 동시 기록
    "$PYTHON" rt.py 2>&1 | tee -a "$LOG_DIR/rt.log"
    EXIT_CODE=${PIPESTATUS[0]}   # python 종료코드 정확히 캡처 (tee 코드 아님)

    echo "⚠️ [$(date '+%Y년 %m월 %d일 %A %H시 %M분 %S초 KST')] 엔진 중단 감지! (종료코드: $EXIT_CODE) 5초 후 자동으로 다시 시작합니다..." | tee -a "$LOG_DIR/runner.log"
    sleep 5
done
