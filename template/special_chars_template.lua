-- ============================================================
-- 특수문자 팔레트  (기본 ⌥ + Space) — 버튼 그리드 + 키보드 커서
--   클릭 = 커서 위치에 입력 + 복사 · ⌘클릭 = 복사만
--   ⇧클릭 = 연속 입력(안 닫힘) · ⌃클릭 = 즐겨찾기
--   검색: 이름 · 단축어 · 초성 · 영문 별칭 · U+코드 / Esc = 닫기
-- 설정은 config.json / config.local.json 에서 바꾸고 재빌드하세요.
-- UI 수정: template/palette_template.html (재빌드 시 덮어써짐)
-- ============================================================

local CFG = hs.json.decode([[@@CONFIG@@]]) or {}
local PAL = CFG.palette or {}
local INP = CFG.input or {}
local PRIV = CFG.privacy or {}
local DISP = CFG.display or {}
local VERSION = "@@VERSION@@"

local CHAR_COUNT = 0        -- loadHtml에서 실제 버튼 수로 채워진다

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
local STATE_KEY = "specialchars.state"
local SCHEMA_KEY = "specialchars.schema"

-- 설정 마이그레이션 (#73) — 저장 구조가 바뀌어도 예전 값이 깨지지 않게
local SCHEMA = 2
local function migrate()
  local have = hs.settings.get(SCHEMA_KEY) or 1
  if have >= SCHEMA then return end
  local st = hs.settings.get(STATE_KEY)
  if type(st) ~= "table" then st = {} end
  st.fav = st.fav or {}
  st.collapsed = st.collapsed or {}
  st.history = st.history or {}
  hs.settings.set(STATE_KEY, st)
  hs.settings.set(SCHEMA_KEY, SCHEMA)
end
migrate()

local MAX_RECENT = PAL.maxRecent or 10

-- 최근 기록. 개인 항목은 옵션에 따라 남기지 않는다 (#70,71)
local function remember(ch, cat)
  if cat == "personal" and PRIV.excludePersonalFromRecent ~= false then return end
  local out = { ch }
  for _, v in ipairs(hs.settings.get(RECENT_KEY) or {}) do
    if v ~= ch and #out < MAX_RECENT then out[#out + 1] = v end
  end
  hs.settings.set(RECENT_KEY, out)
  local counts = hs.settings.get(COUNT_KEY) or {}
  counts[ch] = (counts[ch] or 0) + 1
  hs.settings.set(COUNT_KEY, counts)
end

-- 자주 쓰는 항목 (#48,72)
local function topChars(n)
  local counts = hs.settings.get(COUNT_KEY) or {}
  local arr = {}
  for ch, c in pairs(counts) do arr[#arr + 1] = { ch = ch, c = c } end
  table.sort(arr, function(a, b)
    if a.c == b.c then return a.ch < b.ch end
    return a.c > b.c
  end)
  local out = {}
  for i = 1, math.min(n or 12, #arr) do out[i] = arr[i].ch end
  return out
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
  -- 버튼마다 정확히 한 번 나오는 표식으로 센다.
  -- ('class="g' 로 세면 내부의 gc/gs span까지 잡혀 3배가 된다)
  local _, n = s:gsub('role="gridcell"', '')
  CHAR_COUNT = n
  return s
end

local wv = nil
local shown = false
local prevWin = nil
local escHotkey
local focusChecker

-- 팔레트를 띄울 화면: 마우스 커서가 있는 모니터 (#64), 아니면 마지막 화면 (#65)
local LASTSCREEN_KEY = "specialchars.lastscreen"
local function targetScreen()
  if DISP.followMouse ~= false then
    local ok, scr = pcall(function() return hs.mouse.getCurrentScreen() end)
    if ok and scr then return scr end
  end
  local id = hs.settings.get(LASTSCREEN_KEY)
  if id then
    for _, s in ipairs(hs.screen.allScreens()) do
      if s:id() == id then return s end
    end
  end
  return hs.screen.mainScreen()
end

local function paletteRect()                                    -- 크기 설정 (#66)
  local scr = targetScreen():frame()
  local w = math.min(PAL.width or 760, scr.w * 0.92)
  local h = math.min(PAL.height or 660, scr.h * 0.9)
  return { x = scr.x + (scr.w - w) / 2, y = scr.y + (scr.h - h) / 2.3, w = w, h = h }
end

local FADE = (DISP.fade ~= false) and 0.08 or 0                  -- 페이드 (#68)

local function hidePalette(refocus)
  if escHotkey then escHotkey:disable() end
  if focusChecker then focusChecker:stop(); focusChecker = nil end
  if wv and shown then
    wv:hide(FADE)
    shown = false
  end
  if refocus and prevWin then prevWin:focus() end
end

escHotkey = hs.hotkey.new({}, "escape", function() hidePalette(true) end)

-- 입력: 짧으면 키스트로크, 길면 붙여넣기가 훨씬 안정적이다 (#61,62,63,69)
local PASTE_MIN = INP.pasteThreshold or 4
local DELAY = INP.inputDelay or 0.15

local function charLen(s)
  local ok, n = pcall(function() return utf8.len(s) end)
  if ok and n then return n end
  return #s
end

local function typeText(s, restorePrev)
  local prevClip = restorePrev and hs.pasteboard.getContents() or nil
  local ok
  if charLen(s) >= PASTE_MIN then
    hs.pasteboard.setContents(s)
    ok = pcall(function() hs.eventtap.keyStroke({ "cmd" }, "v") end)
  else
    ok = pcall(function() hs.eventtap.keyStrokes(s) end)
  end
  if not ok then
    hs.alert.show("입력 실패 — 손쉬운 사용 권한을 확인하세요", 2)   -- (#69)
    return
  end
  if prevClip ~= nil then
    hs.timer.doAfter(0.45, function() hs.pasteboard.setContents(prevClip) end)
  end
end

local uc = hs.webview.usercontent.new("palette")
uc:setCallback(function(msg)
  local b = msg.body or {}

  if b.action == "pick" and type(b.char) == "string" and #b.char > 0 then
    remember(b.char, b.cat)
    if b.cmd then                                   -- ⌘ = 복사만
      hs.pasteboard.setContents(b.char)
      hidePalette(true)
      hs.alert.show(b.char .. "  복사됨 (입력 안 함)", 0.7)
      return
    end
    if b.keep then                                  -- ⇧ = 연속 입력, 안 닫힘
      local restore = INP.restoreClipboard ~= false
      if prevWin then prevWin:focus() end
      hs.timer.doAfter(DELAY, function()
        typeText(b.char, restore)
        if wv and shown then
          local win = wv:hswindow()
          if win then win:focus() end
        end
      end)
      return
    end
    hs.pasteboard.setContents(b.char)               -- 기본 = 입력 + 복사
    hidePalette(false)
    if prevWin then prevWin:focus() end
    hs.timer.doAfter(DELAY, function() typeText(b.char, false) end)

  elseif b.action == "copyName" and type(b.name) == "string" then   -- ⌥Enter (#36)
    hs.pasteboard.setContents(b.name)

  elseif b.action == "state" then                   -- 즐겨찾기·접힘·테마 등 영속화
    if type(b.state) == "table" then hs.settings.set(STATE_KEY, b.state) end

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

local function showPalette(opts)
  opts = opts or {}
  prevWin = hs.window.frontmostWindow()
  local scr = targetScreen()
  hs.settings.set(LASTSCREEN_KEY, scr:id())
  wv:frame(paletteRect())

  local st = hs.settings.get(STATE_KEY) or {}
  wv:evaluateJavaScript("window.setState && setState(" .. hs.json.encode(st) .. ")")
  wv:evaluateJavaScript("window.setRecent && setRecent(" ..
    hs.json.encode(hs.settings.get(RECENT_KEY) or {}) .. ")")
  wv:evaluateJavaScript("window.setTop && setTop(" .. hs.json.encode(topChars(12)) .. ")")

  wv:show(FADE)
  shown = true
  escHotkey:enable()
  -- 팔레트는 borderless floating이라 포커스를 잃어도 떠 있는다.
  -- 그 상태로 두면 Esc 핫키가 다른 앱의 Esc까지 가로채므로, 포커스가 떠나면 닫는다.
  if focusChecker then focusChecker:stop(); focusChecker = nil end
  -- 데모·문서 촬영용(noAutoHide)일 때는 감시 타이머만 걸지 않는다.
  -- 아래 포커스·검색창 초기화는 두 경우 모두 필요하다.
  if not opts.noAutoHide then
    focusChecker = hs.timer.doEvery(0.4, function()
      if not shown then return end
      local pw = wv and wv:hswindow()
      local fw = hs.window.focusedWindow()
      if pw and fw and fw:id() ~= pw:id() then hidePalette(false) end
    end)
  end

  hs.timer.doAfter(0.08, function()
    local win = wv:hswindow()
    if win then win:focus() end
    wv:evaluateJavaScript("window.resetAndFocus && resetAndFocus()")
  end)
end

-- 핫키 커스터마이즈 (#67)
local HOT = CFG.hotkey or {}
local MODS = HOT.mods or { "alt" }
local KEY = HOT.key or "space"
hs.hotkey.bind(MODS, KEY, function()
  if shown then hidePalette(true) else showPalette({}) end
end)

-- 터미널 검증용:
--   hs -c "SpecialChars.probe()" && sleep 1 && hs -c "print(hs.settings.get('specialchars.probe'))"
SpecialChars = {
  version = VERSION,
  count = function() return CHAR_COUNT end,
  show = function() showPalette({}) end,
  -- 자동 닫기 없이 띄운다 (시연·문서 촬영). 닫기는 SpecialChars.hide()
  demo = function() showPalette({ noAutoHide = true }) end,
  hide = function() hidePalette(true) end,
  isShown = function() return shown end,
  reload = function()                                -- (#74)
    hidePalette(false)
    if wv then wv:delete() end
    buildWebview()
    return CHAR_COUNT
  end,
  stats = function(n)                                -- (#72)
    local counts = hs.settings.get(COUNT_KEY) or {}
    local arr = {}
    for ch, c in pairs(counts) do arr[#arr + 1] = { char = ch, count = c } end
    table.sort(arr, function(a, b) return a.count > b.count end)
    local out = {}
    for i = 1, math.min(n or 10, #arr) do out[i] = arr[i] end
    return out
  end,
  resetState = function()
    hs.settings.set(STATE_KEY, {})
    hs.settings.set(RECENT_KEY, {})
    hs.settings.set(COUNT_KEY, {})
    return "초기화됨"
  end,
  probe = function()
    wv:evaluateJavaScript("document.querySelectorAll('button.g').length", function(res)
      hs.settings.set("specialchars.probe", res)
    end)
  end,
}
