#!/bin/sh
# Hammerspoon 팔레트 설치: 파일 복사 + init.lua에 require 추가
#
# 덮어쓰기 전에 기존 파일을 backup/ 으로 백업하고, 다른 빌드(인감·서명 포함
# build_local.py 등)가 설치돼 있으면 멈춘다. FORCE=1 로 강제할 수 있다.
set -eu

HS_DIR="$HOME/.hammerspoon"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP="$HS_DIR/backup"
LUA="$SCRIPT_DIR/hammerspoon/special_chars.lua"
PAL="$SCRIPT_DIR/hammerspoon/special_chars_palette.html"
PAL_LOCAL="$SCRIPT_DIR/hammerspoon/special_chars_palette.local.html"

for f in "$LUA" "$PAL"; do
  [ -f "$f" ] || { echo "오류: $f 없음 — 먼저 python3 scripts/build.py 를 실행하세요" >&2; exit 1; }
done

mkdir -p "$HS_DIR"

# --- 다른 빌드 덮어쓰기 방지 ---------------------------------------------
# build_local.py(인감·서명 포함)는 같은 파일에 쓰기 때문에, 그대로 덮으면
# 인감·서명 기능이 조용히 사라진다.
if [ -f "$HS_DIR/special_chars.lua" ] \
   && grep -q "special_chars_signatures.json" "$HS_DIR/special_chars.lua" 2>/dev/null \
   && ! grep -q "special_chars_signatures.json" "$LUA" 2>/dev/null; then
  echo "────────────────────────────────────────────────────────" >&2
  echo "멈춤: 지금 설치된 팔레트는 인감·서명이 포함된 로컬 빌드입니다." >&2
  echo "      (~/특수문자-단축키-로컬/build_local.py 로 만든 것)" >&2
  echo "" >&2
  echo "이 스크립트로 덮어쓰면 인감·서명 기능이 사라집니다." >&2
  echo "서명 텍스트는 entries.local.json 으로 옮길 수 있습니다." >&2
  echo "" >&2
  echo "그래도 덮어쓰려면:  FORCE=1 ./install.sh" >&2
  echo "────────────────────────────────────────────────────────" >&2
  [ "${FORCE:-0}" = "1" ] || exit 1
  echo "FORCE=1 — 계속합니다." >&2
fi

# --- 백업 ----------------------------------------------------------------
stamp="$(date +%Y%m%d-%H%M%S)"
backed=0
for name in special_chars.lua special_chars_palette.html special_chars_palette.local.html; do
  if [ -f "$HS_DIR/$name" ]; then
    mkdir -p "$BACKUP"
    cp "$HS_DIR/$name" "$BACKUP/$name.$stamp"
    backed=$((backed + 1))
  fi
done
if [ "$backed" -gt 0 ]; then
  echo "백업: $BACKUP (${backed}개, $stamp)"
fi

# --- 설치 ----------------------------------------------------------------
cp "$LUA" "$HS_DIR/"
cp "$PAL" "$HS_DIR/"

# 로컬 전용 팔레트가 있으면 함께 설치 (개인 항목 포함, 저장소에는 없음)
if [ -f "$PAL_LOCAL" ]; then
  cp "$PAL_LOCAL" "$HS_DIR/"
  echo "로컬 전용 팔레트 설치됨 (개인 항목 포함)"
else
  rm -f "$HS_DIR/special_chars_palette.local.html"
fi

# --- init.lua (멱등) ------------------------------------------------------
INIT="$HS_DIR/init.lua"
touch "$INIT"
if grep -q 'require("special_chars")' "$INIT"; then
  :
else
  printf '\n-- 특수문자 팔레트 (⌥+Space)\nrequire("special_chars")\n' >> "$INIT"
  echo "init.lua에 require 추가"
fi

echo "설치 완료 — Hammerspoon을 (재)시작하면 팔레트가 열립니다."
echo "되돌리려면: ./uninstall.sh"
