#!/bin/sh
# 팔레트 제거: ~/.hammerspoon 에서 파일과 init.lua의 require 줄을 뺀다.
# 개인 데이터(서명 json·seals·최근 기록)는 건드리지 않는다.
set -eu

HS_DIR="$HOME/.hammerspoon"
INIT="$HS_DIR/init.lua"
removed=0

for name in special_chars.lua special_chars_palette.html special_chars_palette.local.html; do
  if [ -f "$HS_DIR/$name" ]; then
    rm -f "$HS_DIR/$name"
    removed=$((removed + 1))
  fi
done

if [ -f "$INIT" ] && grep -q 'require("special_chars")' "$INIT"; then
  tmp="$(mktemp)"
  grep -v 'require("special_chars")' "$INIT" \
    | grep -v '^-- 특수문자 팔레트 (⌥+Space)$' > "$tmp"
  mv "$tmp" "$INIT"
  echo "init.lua에서 require 제거"
fi

echo "제거 완료 (${removed}개 파일). Hammerspoon을 리로드하세요."
echo "백업은 $HS_DIR/backup 에 남아 있습니다."
echo "서명·인감 데이터(special_chars_signatures.json 등)는 그대로 뒀습니다."
