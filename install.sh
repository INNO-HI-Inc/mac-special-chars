#!/bin/sh
# Hammerspoon 팔레트 설치: 파일 복사 + init.lua에 require 추가
set -e
HS_DIR="$HOME/.hammerspoon"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HS_DIR"
cp "$SCRIPT_DIR/hammerspoon/special_chars.lua" "$HS_DIR/"
cp "$SCRIPT_DIR/hammerspoon/special_chars_palette.html" "$HS_DIR/"
INIT="$HS_DIR/init.lua"
touch "$INIT"
grep -q 'require("special_chars")' "$INIT" || printf '\nrequire("special_chars")\n' >> "$INIT"
echo "설치 완료 — Hammerspoon을 (재)시작하면 ⌥ + Space 로 팔레트가 열립니다."
