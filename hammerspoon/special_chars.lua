-- ============================================================
-- 특수문자 팔레트 v5  (⌥ + Space) — 버튼 그리드 + 키보드 커서
-- 99개 기호가 한 화면에 버튼으로 깔림. 클릭 = 커서 위치에 입력 + 복사
--   ⌘클릭(또는 검색 후 ⌘Enter) = 복사만
--   검색: 이름 · 단축어 · 초성(ㅂㅈ→별점) / Esc = 닫기
-- 단축키 변경: 아래 hs.hotkey.bind의 {"alt"}, "space" 부분 수정
-- UI 수정: special_chars_palette.html (재빌드 시 덮어써짐)
-- ============================================================

local CHAR_COUNT = 0  -- loadHtml에서 실제 버튼 수로 채워진다
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
  local _, n = s:gsub('class="g', '')
  CHAR_COUNT = n
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

-- Esc는 웹뷰 JS에 맡기지 않고 네이티브 핫키로 잡는다.
-- 한글 IME가 켜져 있으면 검색창의 Esc를 IME가 조합 취소로 먼저 먹어서
-- webview의 keydown 핸들러까지 도달하지 못한다. (팔레트는 열릴 때 검색창에 포커스)
local escHotkey
local focusChecker

local function hidePalette(refocus)
  if escHotkey then escHotkey:disable() end
  if focusChecker then focusChecker:stop(); focusChecker = nil end
  if wv and shown then
    wv:hide()
    shown = false
  end
  if refocus and prevWin then prevWin:focus() end
end

escHotkey = hs.hotkey.new({}, "escape", function() hidePalette(true) end)

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
  escHotkey:enable()
  -- 팔레트는 borderless floating이라 포커스를 잃어도 떠 있는다.
  -- 그 상태로 두면 Esc 핫키가 다른 앱의 Esc까지 가로채므로, 포커스가 떠나면 닫는다.
  if focusChecker then focusChecker:stop() end
  focusChecker = hs.timer.doEvery(0.4, function()
    if not shown then return end
    local pw = wv and wv:hswindow()
    local fw = hs.window.focusedWindow()
    if pw and fw and fw:id() ~= pw:id() then hidePalette(false) end
  end)
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
  count = function() return CHAR_COUNT end,
  version = 5,
  show = showPalette,
  hide = function() hidePalette(true) end,
  probe = function()
    wv:evaluateJavaScript("document.querySelectorAll('button.g').length", function(res)
      hs.settings.set("specialchars.probe", res)
    end)
  end,
}
