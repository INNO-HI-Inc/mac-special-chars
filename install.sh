#!/bin/sh
# Hammerspoon 팔레트 설치: 파일 복사 + init.lua에 require 추가
set -e
HS_DIR="$HOME/.hammerspoon"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HS_DIR"
cp "$SCRIPT_DIR/hammerspoon/special_chars.lua" "$HS_DIR/"
cp "$SCRIPT_DIR/hammerspoon/special_chars_palette.html" "$HS_DIR/"
# 내 서명 파일: 개인정보이므로 최초 1회만 예시를 복사(기존 파일은 덮어쓰지 않음)
SIG="$HS_DIR/special_chars_signatures.json"
[ -f "$SIG" ] || cp "$SCRIPT_DIR/hammerspoon/signatures.example.json" "$SIG"
INIT="$HS_DIR/init.lua"
touch "$INIT"
grep -q 'require("special_chars")' "$INIT" || printf '\nrequire("special_chars")\n' >> "$INIT"
echo "설치 완료 — Hammerspoon을 (재)시작하면 ⌥ + Space 로 팔레트가 열립니다."
echo "내 서명은 $SIG 를 편집하거나, 웹 치트시트에서 '팔레트로 내보내기'로 교체하세요."
