#!/bin/bash
cd "$(dirname "$0")"

echo "📦 변경된 파일 확인 중..."
git status --short

echo ""
read -p "커밋 메시지 (엔터 = 날짜/시간 자동): " MSG

if [ -z "$MSG" ]; then
    MSG="update $(date '+%Y-%m-%d %H:%M')"
fi

git add .
git commit -m "$MSG"
git push

echo ""
echo "✅ GitHub 업로드 완료!"
