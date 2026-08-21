#!/usr/bin/env bash
# 把 mp3 上传到 GitHub Release，返回稳定的公开下载 URL（系列性留存的默认免费方案）。
#
# 用法:
#   ./publish_github.sh <mp3文件> <owner/repo> [tag]
#
# 返回: https://github.com/<owner>/<repo>/releases/download/<tag>/<文件名>
set -euo pipefail

FILE="${1:-}"
REPO="${2:-}"
TAG="${3:-episode-$(date +%Y%m%d-%H%M%S)}"

if [ -z "$FILE" ] || [ -z "$REPO" ]; then
  echo "用法: publish_github.sh <mp3文件> <owner/repo> [tag]" >&2
  exit 1
fi
[ -f "$FILE" ] || { echo "文件不存在: $FILE" >&2; exit 1; }

# 需要 gh 已登录
if ! gh auth status >/dev/null 2>&1; then
  echo "请先登录 GitHub：gh auth login" >&2
  exit 1
fi

FILENAME="$(basename "$FILE")"
gh release create "$TAG" "$FILE" \
  --repo "$REPO" \
  --title "播客 $TAG" \
  --notes "由 article-to-podcast 自动生成" >/dev/null

echo "https://github.com/$REPO/releases/download/$TAG/$FILENAME"
