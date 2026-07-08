-- ============================================================
-- 특수문자 팔레트 v6  (⌥ + Space) — 기호·인감이미지·내 서명 클립보드 + 키보드 커서
-- 99개 기호가 한 화면에 버튼으로 깔림. 클릭 = 커서 위치에 입력 + 복사
--   ⌘클릭(또는 검색 후 ⌘Enter) = 복사만
--   검색: 이름 · 단축어 · 초성(ㅂㅈ→별점) / Esc = 닫기
-- 단축키 변경: 아래 hs.hotkey.bind의 {"alt"}, "space" 부분 수정
-- UI 수정: special_chars_palette.html (재빌드 시 덮어써짐)
-- ============================================================

local CHAR_COUNT = 99
local PALETTE_FILE = hs.configdir .. "/special_chars_palette.html"
-- 내 서명: 개인정보이므로 이 파일에만 저장(레포에 커밋 안 됨). JSON 배열 [{name, text}, ...]
local SIG_FILE = hs.configdir .. "/special_chars_signatures.json"
local function loadSignatures()
  local ok, data = pcall(hs.json.read, SIG_FILE)
  if ok and type(data) == "table" then return data end
  return {}
end

-- 인감/도장 이미지: 로컬 폴더에서만 읽음(레포에 커밋 안 됨). 클릭 시 이미지가 클립보드로.
local SEAL_DIR = hs.configdir .. "/seals"
if not hs.fs.attributes(SEAL_DIR) then
  local alt = os.getenv("HOME") .. "/Desktop/인감 모음"
  if hs.fs.attributes(alt) then SEAL_DIR = alt end
end
do
  local cfg = io.open(hs.configdir .. "/special_chars_seals_dir.txt", "r")
  if cfg then local p = cfg:read("*l"); cfg:close(); if p and #p > 0 then SEAL_DIR = p end end
end
local sealPaths = {}
local function loadSeals()
  sealPaths = {}
  local list = {}
  local function scan(dir, cat)
    if not hs.fs.attributes(dir) then return end
    local ok = pcall(function()
      for name in hs.fs.dir(dir) do
        if name:sub(1, 1) ~= "." then
          local full = dir .. "/" .. name
          local attr = hs.fs.attributes(full)
          if attr and attr.mode == "directory" then
            scan(full, name)
          elseif name:lower():match("%.png$") or name:lower():match("%.jpe?g$") then
            local img = hs.image.imageFromPath(full)
            if img then
              local id = tostring(#list + 1)
              sealPaths[id] = full
              local uri = ""
              pcall(function() img:setSize({ w = 128, h = 128 }); uri = img:encodeAsURLString() end)
              list[#list + 1] = { id = id, name = (name:gsub("%.%w+$", "")), cat = cat or "", img = uri }
            end
          end
        end
      end
    end)
    if not ok then return end
  end
  scan(SEAL_DIR, nil)
  return list
end

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
  elseif b.action == "sig" and type(b.text) == "string" and #b.text > 0 then
    hs.pasteboard.setContents(b.text)
    hidePalette(true)
    hs.alert.show((b.name or "서명") .. "  복사됨 · ⌘V로 붙여넣기", 0.9)
  elseif b.action == "seal" and type(b.id) == "string" then
    local path = sealPaths[b.id]
    if path then
      local img = hs.image.imageFromPath(path)
      if img then
        hs.pasteboard.writeObjects(img)
        hidePalette(true)
        hs.alert.show((b.name or "인감") .. " 이미지 복사됨 · ⌘V로 붙여넣기", 0.9)
      end
    end
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
  wv:evaluateJavaScript("window.setSignatures && setSignatures(" .. hs.json.encode(loadSignatures()) .. ")")
  wv:evaluateJavaScript("window.setSeals && setSeals(" .. hs.json.encode(loadSeals()) .. ")")
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
  version = 6,
  show = showPalette,
  hide = function() hidePalette(true) end,
  probe = function()
    wv:evaluateJavaScript("document.querySelectorAll('button.g').length", function(res)
      hs.settings.set("specialchars.probe", res)
    end)
  end,
  probeSig = function()
    wv:evaluateJavaScript("document.querySelectorAll('.sigbtn').length", function(res)
      hs.settings.set("specialchars.sigprobe", res)
    end)
  end,
  probeSeal = function()
    wv:evaluateJavaScript("document.querySelectorAll('.sealbtn').length", function(res)
      hs.settings.set("specialchars.sealprobe", res)
    end)
  end,
}
