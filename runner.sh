#!/bin/bash
# Edge Score v40.0 무중단 실행 스크립트

# ── 로그 설정 ────────────────────────────────────────────────
LOG_DIR="/Users/jeongsanghyeon/Desktop/edgescore/logs"
mkdir -p "$LOG_DIR"
RUNNER_LOG="$LOG_DIR/runner.log"
RT_LOG="$LOG_DIR/rt.log"
exec >> "$RUNNER_LOG" 2>&1   # runner.sh 자신의 stdout/stderr도 로그 저장

echo "============================================================"
echo "🚀 [$(date '+%Y-%m-%d %H:%M:%S')] runner.sh 시작"
echo "============================================================"

# ── 종료 시 백그라운드 프로세스 정리 (trap) ──────────────────
_FSWATCH_PID=""
_NPM_PID=""

cleanup() {
    echo "⛔ [$(date '+%H:%M:%S')] runner.sh 종료 — 백그라운드 프로세스 정리 중..."
    [ -n "$_FSWATCH_PID" ] && kill "$_FSWATCH_PID" 2>/dev/null && echo "  fswatch (PID $_FSWATCH_PID) 종료"
    [ -n "$_NPM_PID" ]     && kill "$_NPM_PID"     2>/dev/null && echo "  npm     (PID $_NPM_PID) 종료"
    # 5000 포트 잔여 프로세스 정리
    lsof -ti:5000 | xargs kill -9 2>/dev/null
    echo "✅ 정리 완료"
    exit 0
}
trap cleanup SIGTERM SIGINT SIGHUP

# ── 부팅 직후 시스템 준비 대기 ──────────────────────────────
echo "⏳ 시스템 준비 대기 (30초)..."
sleep 30

cd /Users/jeongsanghyeon/Desktop/edgescore

# ── Dashboard.jsx → App.jsx 자동 동기화 (fswatch) ───────────
SRC="/Users/jeongsanghyeon/Desktop/edgescore/Dashboard.jsx"
DST="/Users/jeongsanghyeon/Desktop/edgescore/edge-dashboard/src/App.jsx"

echo "🔄 Dashboard 자동 동기화 시작..."

# 기존 fswatch 프로세스 중복 방지
pkill -f "fswatch.*Dashboard.jsx" 2>/dev/null

# 최초 1회 즉시 복사
cp "$SRC" "$DST" && echo "✅ Dashboard.jsx → App.jsx 초기 복사 완료"

# fswatch로 변경 감지 → 자동 복사 (백그라운드)
nohup bash -c "
  fswatch -o \"$SRC\" | while read; do
    cp \"$SRC\" \"$DST\"
    echo \"[\$(date '+%H:%M:%S')] Dashboard.jsx 변경 감지 → App.jsx 자동 반영\"
  done
" > /tmp/dashboard_sync.log 2>&1 &
_FSWATCH_PID=$!
echo "👀 Dashboard 파일 감시 중 (PID $_FSWATCH_PID, 로그: /tmp/dashboard_sync.log)"

# ── 대시보드 프론트엔드 시작 (중복 방지) ─────────────────────
echo "🖥️ 대시보드 프론트엔드 시작..."

# 이미 실행 중인 npm dev 프로세스 종료
pkill -f "npm run dev" 2>/dev/null
sleep 1

cd /Users/jeongsanghyeon/Desktop/edgescore/edge-dashboard
nohup /opt/homebrew/bin/npm run dev -- --host >> "$LOG_DIR/npm.log" 2>&1 &
_NPM_PID=$!
echo "✅ npm dev 시작 (PID $_NPM_PID)"
cd /Users/jeongsanghyeon/Desktop/edgescore

# ── 메인 루프: rt.py 무중단 재시작 ──────────────────────────
while true
do
    # 재시작 전 5000번 포트 강제 해제 (이전 rt.py의 dashboard API 서버 잔여)
    lsof -ti:5000 | xargs kill -9 2>/dev/null
    sleep 1

    echo "============================================================"
    echo "🚀 [$(date '+%Y-%m-%d %H:%M:%S')] Edge Score v40.0 엔진 기동"
    echo "============================================================"

    # rt.py 실행 (stdout/stderr 로그 저장 + 터미널 동시 출력)
    /opt/homebrew/bin/python3.11 rt.py 2>&1 | tee -a "$RT_LOG"

    EXIT_CODE=${PIPESTATUS[0]}
    echo "⚠️ [$(date '+%Y-%m-%d %H:%M:%S')] 엔진 중단 감지 (exit=$EXIT_CODE) — 5초 후 재시작..."
    sleep 5
done
