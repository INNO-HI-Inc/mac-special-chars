-- ============================================================
-- 특수문자 팔레트 v5  (⌥ + Space) — 버튼 그리드 + 키보드 커서
-- 99개 기호가 한 화면에 버튼으로 깔림. 클릭 = 커서 위치에 입력 + 복사
--   ⌘클릭(또는 검색 후 ⌘Enter) = 복사만
--   검색: 이름 · 단축어 · 초성(ㅂㅈ→별점) / Esc = 닫기
-- 단축키 변경: 아래 hs.hotkey.bind의 {"alt"}, "space" 부분 수정
-- UI 수정: special_chars_palette.html (재빌드 시 덮어써짐)
-- ============================================================

local CHAR_COUNT = 99
-- 로컬 전용 팔레트(.local.html)가 설치돼 있으면 그쪽을 우선 사용한다.
-- 개인 항목은 공개 저장소의 special_chars_palette.html에는 들어가지 않는다.
local function paletteFile()
  local localFile = hs.configdir .. "/special_chars_palette.local.html"
  local f = io.open(localFile, "r")
  if f then f:close(); return localFile end
  return hs.configdir .. "/special_chars_palette.html"
end
local PALETTE_FILE = paletteFile()

local RECENT_KEY = "specialchars.recent"
local COUNT_KEY = "specialchars.counts"
local function remember(ch)
  local out = { ch }
  for _, v in ipairs(hs.settings.get(RECENT_KEY) or {}) do
    if v ~= ch and #out < 10 then out[#out + 1] = v end
  end
  hs.settings.set(RECENT_KEY, out)
  local counts = hs.settings.get(COUNT_KEY) or {}
  counts[ch] = (counts[ch] or 0) + 1
  hs.settings.set(COUNT_KEY, counts)
end

local function loadHtml()
  PALETTE_FILE = paletteFile()
  local f = io.open(PALETTE_FILE, "r")
  if not f then
    hs.alert.show("special_chars_palette.html 없음 — 재빌드 필요")
    return "<html><body>palette missing</body></html>"
  end
  local s = f:read("*a")
  f:close()
  return s
end

local wv = nil
local shown = false
local prevWin = nil

local function paletteRect()
  local scr = hs.screen.mainScreen():frame()
  local w = math.min(760, scr.w * 0.72)
  local h = math.min(660, scr.h * 0.85)
  return { x = scr.x + (scr.w - w) / 2, y = scr.y + (scr.h - h) / 2.3, w = w, h = h }
end

local function hidePalette(refocus)
  if wv and shown then
    wv:hide()
    shown = false
  end
  if refocus and prevWin then prevWin:focus() end
end

local uc = hs.webview.usercontent.new("palette")
uc:setCallback(function(msg)
  local b = msg.body or {}
  if b.action == "pick" and type(b.char) == "string" and #b.char > 0 then
    remember(b.char)
    hs.pasteboard.setContents(b.char)
    if b.cmd then
      hidePalette(true)
      hs.alert.show(b.char .. "  복사됨 (입력 안 함)", 0.7)
      return
    end
    hidePalette(false)
    if prevWin then prevWin:focus() end
    hs.timer.doAfter(0.15, function()
      hs.eventtap.keyStrokes(b.char)
    end)
  elseif b.action == "close" then
    hidePalette(true)
  end
end)

local function buildWebview()
  wv = hs.webview.new(paletteRect(), {}, uc)
  wv:windowStyle({ "borderless" })
  wv:allowTextEntry(true)
  wv:transparent(true)
  wv:shadow(false)
  wv:level(hs.drawing.windowLevels.floating)
  wv:behavior(hs.drawing.windowBehaviors.canJoinAllSpaces)
  wv:html(loadHtml())
end
buildWebview()

local function showPalette()
  prevWin = hs.window.frontmostWindow()
  wv:frame(paletteRect())
  local rec = hs.settings.get(RECENT_KEY) or {}
  wv:evaluateJavaScript("window.setRecent && setRecent(" .. hs.json.encode(rec) .. ")")
  wv:show()
  shown = true
  hs.timer.doAfter(0.08, function()
    local win = wv:hswindow()
    if win then win:focus() end
    wv:evaluateJavaScript("window.resetAndFocus && resetAndFocus()")
  end)
end

hs.hotkey.bind({ "alt" }, "space", function()
  if shown then hidePalette(true) else showPalette() end
end)

-- 터미널 검증용:
--   hs -c "SpecialChars.probe()" && sleep 1 && hs -c "print(hs.settings.get('specialchars.probe'))"
SpecialChars = {
  count = CHAR_COUNT,
  version = 5,
  show = showPalette,
  hide = function() hidePalette(true) end,
  probe = function()
    wv:evaluateJavaScript("document.querySelectorAll('button.g').length", function(res)
      hs.settings.set("specialchars.probe", res)
    end)
  end,
}
