#!/bin/bash
# Edge Score v39.2 무중단 실행 스크립트

# 부팅 직후 시스템 준비 대기 (30초)
sleep 30

cd /Users/jeongsanghyeon/Desktop/edgescore

# Dashboard.jsx → App.jsx 자동 동기화 (fswatch)
echo "🔄 Dashboard 자동 동기화 시작..."
SRC="/Users/jeongsanghyeon/Desktop/edgescore/Dashboard.jsx"
DST="/Users/jeongsanghyeon/Desktop/edgescore/edge-dashboard/src/App.jsx"

# 최초 1회 즉시 복사
cp "$SRC" "$DST"
echo "✅ Dashboard.jsx → App.jsx 초기 복사 완료"

# fswatch로 변경 감지 → 자동 복사 (백그라운드)
nohup bash -c "
  fswatch -o \"$SRC\" | while read; do
    cp \"$SRC\" \"$DST\"
    echo \"[$(date '+%H:%M:%S')] Dashboard.jsx 변경 감지 → App.jsx 자동 반영\"
  done
" > /tmp/dashboard_sync.log 2>&1 &
echo "👀 Dashboard 파일 감시 중 (로그: /tmp/dashboard_sync.log)"

# 대시보드 프론트엔드 시작
echo "🖥️ 대시보드 프론트엔드 시작..."
cd /Users/jeongsanghyeon/Desktop/edgescore/edge-dashboard
nohup /opt/homebrew/bin/npm run dev -- --host > /dev/null 2>&1 &
cd /Users/jeongsanghyeon/Desktop/edgescore

while true
do
    # 재시작 전 잔여 프로세스 정리 (5000 포트 충돌 방지)
    pkill -f dashboard_api 2>/dev/null
    sleep 1

    echo "============================================================"
    echo "🚀 [$(date '+%Y년 %m월 %d일 %A %H시 %M분 %S초 KST')] Edge Score 엔진 기동 시작..."
    echo "============================================================"

    /opt/homebrew/bin/python3.11 rt.py

    echo "⚠️ [$(date '+%Y년 %m월 %d일 %A %H시 %M분 %S초 KST')] 엔진 중단 감지! 5초 후 자동으로 다시 시작합니다..."
    sleep 5
done