#!/usr/bin/env python3
"""entries.json → plist / 팔레트(lua+html) / 치트시트(index.html) 생성"""
import json, plistlib, pathlib, sys, html as htmlmod

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT
HS = ROOT / "hammerspoon" / "special_chars.lua"
PALETTE = ROOT / "hammerspoon" / "special_chars_palette.html"

entries = json.loads((ROOT / "entries.json").read_text())

# --- 검증 ---
shortcuts = [e["shortcut"] for e in entries]
dups = {s for s in shortcuts if shortcuts.count(s) > 1}
if dups:
    sys.exit(f"FATAL: 단축어 중복 {dups}")
bad = [e for e in entries if not e["shortcut"].startswith("ㅁ") or not e["phrase"]]
if bad:
    sys.exit(f"FATAL: 형식 오류 {bad}")
cats = ["hanja-classic", "work-units", "punct-modern", "combo"]
order = {c: i for i, c in enumerate(cats)}
entries.sort(key=lambda e: (order.get(e["category"], 9), e["priority"]))
print(f"OK: {len(entries)}개 항목, 중복 없음")

DEST.mkdir(exist_ok=True)

# --- 1. plist ---
plist_data = [{"phrase": e["phrase"], "shortcut": e["shortcut"]} for e in entries]
with open(DEST / "특수문자_텍스트대치.plist", "wb") as f:
    plistlib.dump(plist_data, f)

# --- 2. entries.json ---
(DEST / "entries.json").write_text(
    json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

# --- 3a. 팔레트 HTML (버튼 그리드) ---
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
def cho(s):
    out = []
    for ch in s:
        o = ord(ch)
        out.append(CHO[(o - 0xAC00) // 588] if 0xAC00 <= o <= 0xD7A3 else ch)
    return "".join(out)

cat_meta = {
    "hanja-classic": ("한자키 클래식", "--c1"),
    "work-units": ("업무 · 단위 · 번호", "--c2"),
    "punct-modern": ("괄호 · 문장부호 · 맥 키", "--c3"),
    "combo": ("조합", "--c4"),
}
def att(s):
    return htmlmod.escape(str(s), quote=True)

sections_html = []
for c in cats:
    rows = [e for e in entries if e["category"] == c]
    if not rows:
        continue
    title, color = cat_meta[c]
    btns = []
    for e in rows:
        long_cls = " long" if len(e["phrase"]) > 2 else ""
        btns.append(
            f'<button class="g{long_cls}" data-c="{att(e["phrase"])}" data-n="{att(e["ko_name"])}" '
            f'data-s="{att(e["shortcut"])}" data-cho="{att(cho(e["ko_name"]))}" '
            f'title="{att(e["ko_name"])} · {att(e["shortcut"])} + 스페이스">{att(e["phrase"])}</button>')
    sections_html.append(
        f'<div class="sec"><div class="lbl"><span class="dot" style="background:var({color})"></span>{att(title)}</div>'
        f'<div class="row">{"".join(btns)}</div></div>')
SECTIONS = "".join(sections_html)

palette_html = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><style>
:root {
  --bg: #FFFFFF; --ink: #191F28; --sub: #6B7684; --card: #F2F4F6;
  --line: #E5E8EB; --accent: #3182F6; --seal: #3182F6; --chip: #E8F3FF;
  --c1: #FE9800; --c2: #3182F6; --c3: #02A262; --c4: #9161F1;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #17171C; --ink: #E7E9EC; --sub: #8B95A1; --card: #26262E;
    --line: #32323B; --accent: #4593FC; --seal: #4593FC; --chip: #1B3050;
    --c1: #FFA938; --c2: #4593FC; --c3: #3AC08E; --c4: #A97DF5;
  }
}
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; background: transparent; }
body { font-family: "Apple SD Gothic Neo", -apple-system, sans-serif; color: var(--ink); }
.panel {
  background: var(--bg); border: none; border-radius: 18px;
  margin: 14px; padding: 13px 16px 10px;
  max-height: calc(100% - 28px); overflow-y: auto;
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.38);
}
.top { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.panel::-webkit-scrollbar { width: 10px; }
.panel::-webkit-scrollbar-thumb { background: var(--line); border-radius: 99px; border: 3px solid var(--bg); }
.panel::-webkit-scrollbar-track { background: transparent; }
.stamp {
  width: 30px; height: 30px; flex: none; display: inline-flex;
  align-items: center; justify-content: center;
  border: none; color: var(--seal); border-radius: 9px;
  font-size: 16px; font-weight: 800;
  background: color-mix(in srgb, var(--seal) 12%, transparent);
}
#q {
  flex: 1; font: inherit; font-size: 14px; color: var(--ink);
  background: var(--card); border: none;
  border-radius: 10px; padding: 8px 13px; outline: none; min-width: 120px;
}
#q:focus { box-shadow: 0 0 0 2px var(--accent) inset; }
.hint { font-size: 11px; color: var(--sub); white-space: nowrap; }
#x {
  border: none; background: var(--card); color: var(--sub);
  width: 26px; height: 26px; border-radius: 99px; cursor: pointer;
  font-size: 12px; font-weight: 700; flex: none;
}
.lbl {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 700; color: var(--sub);
  margin: 13px 0 7px; letter-spacing: 0.02em;
}
.lbl .dot { width: 7px; height: 7px; border-radius: 99px; }
.row { display: grid; grid-template-columns: repeat(auto-fill, minmax(46px, 1fr)); gap: 5px; }
button.g {
  font-family: "Apple SD Gothic Neo", "Apple Symbols", sans-serif;
  width: 100%; min-width: 0; height: 44px; font-size: 21px; line-height: 1;
  color: var(--ink); background: var(--card);
  border: none; border-radius: 10px; cursor: pointer;
  padding: 0 6px;
  transition: transform 0.1s ease, background 0.1s ease;
}
button.g:hover { background: var(--chip); }
button.g:active { transform: scale(0.94); }
button.g:focus-visible { outline: 2px solid var(--accent); }
button.g.long { font-size: 12px; letter-spacing: 1px; padding: 0 10px; grid-column: span 3; }
.status {
  margin-top: 11px; padding-top: 8px; border-top: 1px solid var(--line);
  font-size: 12px; color: var(--sub); min-height: 18px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.status b { color: var(--ink); }
.sel { box-shadow: 0 0 0 2px var(--accent); position: relative; z-index: 2; }
button.g.sel { background: var(--chip); }
</style></head>
<body>
<div class="panel">
  <div class="top">
    <span class="stamp">ㅁ</span>
    <input id="q" placeholder="검색: 별, 초성(ㅂㅈ), ㅁ참고…" autocomplete="off" spellcheck="false">
    <span class="hint">←→↑↓ 이동 · Enter 입력 · ⌘=복사만 · Esc 닫기</span>
    <button id="x" title="닫기 (Esc)">✕</button>
  </div>
  <div class="sec" id="recent-sec" hidden>
    <div class="lbl"><span class="dot" style="background:var(--sub)"></span>최근</div>
    <div class="row" id="recent-row"></div>
  </div>
  @@SECTIONS@@
  <div class="status" id="status">기호를 누르면 커서 위치에 바로 입력돼요 · ⌘클릭은 복사만 해요</div>
</div>
<script>
"use strict";
function post(m) {
  try { window.webkit.messageHandlers.palette.postMessage(m); } catch (e) {}
}
function pick(b, cmd) { post({ action: "pick", char: b.dataset.c, cmd: !!cmd }); }
document.addEventListener("click", ev => {
  const b = ev.target.closest("button.g");
  if (b) { pick(b, ev.metaKey); return; }
  if (ev.target.closest("#x")) post({ action: "close" });
});
const statusEl = document.getElementById("status");
document.addEventListener("mouseover", ev => {
  const b = ev.target.closest("button.g");
  if (b) statusEl.innerHTML = "<b>" + b.dataset.c + "</b>  " + b.dataset.n + "  ·  " + b.dataset.s + " + 스페이스";
});
const q = document.getElementById("q");
function visibleButtons() {
  return [...document.querySelectorAll(".sec:not([hidden]) button.g")].filter(b => b.style.display !== "none");
}
function filter() {
  const raw = q.value.trim().toLowerCase();
  const tokens = raw ? raw.split(/\\s+/) : [];
  document.querySelectorAll("button.g").forEach(b => {
    const k = (b.dataset.c + " " + b.dataset.n + " " + b.dataset.s).toLowerCase();
    const hit = !tokens.length || tokens.every(t =>
      k.includes(t) || (/^[ㄱ-ㅎ]+$/.test(t) && b.dataset.cho.includes(t)));
    b.style.display = hit ? "" : "none";
  });
  document.querySelectorAll(".sec").forEach(sec => {
    if (sec.id === "recent-sec" && sec.hidden) return;
    const any = [...sec.querySelectorAll("button.g")].some(b => b.style.display !== "none");
    sec.style.display = any ? "" : "none";
  });
  refreshSel();
}
q.addEventListener("input", filter);
// ---- 키보드 커서: 파란 테두리로 현재 위치, 방향키 이동, Enter 입력 ----
let sel = null;
function focusables() {
  return [...document.querySelectorAll(".sec:not([hidden]) button.g")]
    .filter(el => el.offsetParent !== null && el.style.display !== "none");
}
function setSel(el) {
  if (sel && sel !== el) sel.classList.remove("sel");
  sel = el || null;
  if (sel) { sel.classList.add("sel"); sel.scrollIntoView({ block: "nearest" }); }
}
function refreshSel() {
  const items = focusables();
  if (!items.length) { if (sel) { sel.classList.remove("sel"); sel = null; } return; }
  if (!sel || !items.includes(sel)) setSel(items[0]);
}
function colsOf(el) {
  const grid = el.parentElement;
  if (!grid) return 1;
  const kids = [...grid.children].filter(c => c.offsetParent !== null && c.style.display !== "none");
  if (!kids.length) return 1;
  const top0 = kids[0].offsetTop; let n = 0;
  for (const k of kids) { if (k.offsetTop === top0) n++; else break; }
  return Math.max(1, n);
}
function navSel(dir) {
  const items = focusables();
  if (!items.length) return;
  let i = sel ? items.indexOf(sel) : -1;
  if (i < 0) { setSel(items[0]); return; }
  let ni = i;
  if (dir === "right") ni = i + 1;
  else if (dir === "left") ni = i - 1;
  else if (dir === "down") ni = i + colsOf(items[i]);
  else if (dir === "up") ni = i - colsOf(items[i]);
  if (ni < 0) ni = 0;
  if (ni >= items.length) ni = items.length - 1;
  setSel(items[ni]);
}
function activate(el, cmd) {
  if (!el) return;
  if (el.matches("button.g")) pick(el, cmd);
  else el.click();
}
document.addEventListener("keydown", ev => {
  if (ev.isComposing || ev.keyCode === 229) return;
  if (ev.key === "Escape") { ev.preventDefault(); post({ action: "close" }); return; }
  if (ev.key === "Enter") { ev.preventDefault(); activate(sel || focusables()[0], ev.metaKey); return; }
  if (ev.key === "ArrowRight") { ev.preventDefault(); navSel("right"); return; }
  if (ev.key === "ArrowLeft") { ev.preventDefault(); navSel("left"); return; }
  if (ev.key === "ArrowDown") { ev.preventDefault(); navSel("down"); return; }
  if (ev.key === "ArrowUp") { ev.preventDefault(); navSel("up"); return; }
});
window.setRecent = function (chars) {
  const sec = document.getElementById("recent-sec");
  const row = document.getElementById("recent-row");
  row.innerHTML = "";
  const seen = new Set();
  (chars || []).slice(0, 10).forEach(ch => {
    if (seen.has(ch)) return;
    seen.add(ch);
    const src = [...document.querySelectorAll(".sec:not(#recent-sec) button.g")].find(b => b.dataset.c === ch);
    if (src) row.appendChild(src.cloneNode(true));
  });
  sec.hidden = row.children.length === 0;
  refreshSel();
};
window.resetAndFocus = function () {
  q.value = "";
  filter();
  q.focus();
};
</script>
</body></html>
"""
PALETTE.write_text(palette_html.replace("@@SECTIONS@@", SECTIONS), encoding="utf-8")

# --- 3b. Hammerspoon Lua (v4: webview 버튼 그리드) ---
lua_template = r"""-- ============================================================
-- 특수문자 팔레트 v5  (⌥ + Space) — 버튼 그리드 + 키보드 커서
-- 99개 기호가 한 화면에 버튼으로 깔림. 클릭 = 커서 위치에 입력 + 복사
--   ⌘클릭(또는 검색 후 ⌘Enter) = 복사만
--   검색: 이름 · 단축어 · 초성(ㅂㅈ→별점) / Esc = 닫기
-- 단축키 변경: 아래 hs.hotkey.bind의 {"alt"}, "space" 부분 수정
-- UI 수정: special_chars_palette.html (재빌드 시 덮어써짐)
-- ============================================================

local CHAR_COUNT = @@COUNT@@
local PALETTE_FILE = hs.configdir .. "/special_chars_palette.html"

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
"""
HS.parent.mkdir(exist_ok=True)
HS.write_text(lua_template.replace("@@COUNT@@", str(len(entries))), encoding="utf-8")

# --- 5. 치트시트 HTML ---
tpl = (ROOT / "template" / "cheatsheet_template.html").read_text(encoding="utf-8")
html_out = tpl.replace("__DATA__", json.dumps(entries, ensure_ascii=False))
(DEST / "index.html").write_text(html_out, encoding="utf-8")
(DEST / "치트시트.html").write_text(html_out, encoding="utf-8")

print("생성 완료:")
for p in sorted(DEST.iterdir()):
    print(f"  {p.name} ({p.stat().st_size:,} bytes)")
for p in (HS, PALETTE):
    print(f"  {p} ({p.stat().st_size:,} bytes)")
