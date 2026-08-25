#!/usr/bin/env python3
"""entries.json → plist / 팔레트(lua+html) / 치트시트(index.html) 생성

사용법:
  python3 scripts/build.py            빌드
  python3 scripts/build.py --check    검증만 (파일 안 씀, CI용)
  python3 scripts/build.py --watch    소스 변경 시 자동 재빌드
  python3 scripts/build.py --quiet    요약만 출력

개인정보(연락처 등)는 entries.local.json 에만 두며, 공개 산출물
(entries.json·특수문자_텍스트대치.plist·index.html·팔레트 html)에는
절대 들어가지 않는다. 로컬 항목은 .local. 접미사 산출물에만 병합된다.
"""
import json, plistlib, pathlib, sys, time, html as htmlmod

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT
HS = ROOT / "hammerspoon" / "special_chars.lua"
PALETTE = ROOT / "hammerspoon" / "special_chars_palette.html"
PALETTE_LOCAL = ROOT / "hammerspoon" / "special_chars_palette.local.html"
LOCAL_SRC = ROOT / "entries.local.json"
LOCAL_PLIST = DEST / "특수문자_텍스트대치.local.plist"

ARGS = set(sys.argv[1:])
CHECK = "--check" in ARGS
WATCH = "--watch" in ARGS
QUIET = "--quiet" in ARGS

VERSION = "1.1.0"

# 카테고리: personal을 맨 앞에 둬서 팔레트에서 「최근」 바로 다음에 오게 한다. (#45)
CATS = ["personal", "hanja-classic", "work-units", "punct-modern", "combo"]
CAT_META = {
    "personal": ("개인 — 로컬 전용", "--c4"),
    "hanja-classic": ("한자키 클래식", "--c1"),
    "work-units": ("업무 · 단위 · 번호", "--c2"),
    "punct-modern": ("괄호 · 문장부호 · 맥 키", "--c3"),
    "combo": ("조합", "--c4"),
}
ORDER = {c: i for i, c in enumerate(CATS)}
REQUIRED = ("shortcut", "phrase", "ko_name", "priority", "category")

problems = []
warnings = []


def say(*a):
    if not QUIET:
        print(*a)


def fail(msg):
    problems.append(msg)


def warn(msg):
    warnings.append(msg)


def load_json(path, what):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"{what} 없음: {path}")
    except json.JSONDecodeError as e:
        fail(f"{what} JSON 오류: {e}")
    return None


# ---------------------------------------------------------------- 설정 (#3)
def load_config():
    """config.json(공개 기본값) + config.local.json(개인 재정의)를 병합."""
    base = load_json(ROOT / "config.json", "config.json") or {}
    local_path = ROOT / "config.local.json"
    if local_path.exists():
        over = load_json(local_path, "config.local.json") or {}
        for k, v in over.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                base[k].update(v)
            else:
                base[k] = v
    return base


# ---------------------------------------------------------------- 검증 (#8,9,10)
BAD_CHARS = set(' \t\n"\'\\')


def validate(entries, label, known_shortcuts=()):
    """스키마·형식·중복 검증. 문제는 problems/warnings에 쌓는다."""
    seen = {}
    for i, e in enumerate(entries):
        where = f"{label}[{i}]"
        if not isinstance(e, dict):
            fail(f"{where}: 객체가 아님")
            continue
        missing = [k for k in REQUIRED if k not in e]
        if missing:
            fail(f"{where}: 필수 키 누락 {missing}")
            continue
        sc, ph, nm = e["shortcut"], e["phrase"], e["ko_name"]
        if not isinstance(sc, str) or not isinstance(ph, str) or not isinstance(nm, str):
            fail(f"{where}: shortcut/phrase/ko_name 은 문자열이어야 함")
            continue
        if not isinstance(e["priority"], int):
            fail(f"{where} {sc}: priority 는 정수여야 함")
        if not sc.startswith("ㅁ"):
            fail(f"{where} {sc}: 단축어는 'ㅁ' 로 시작해야 함")
        if len(sc) < 2:
            fail(f"{where} {sc}: 단축어가 너무 짧음")
        if BAD_CHARS & set(sc):
            fail(f"{where} {sc}: 단축어에 공백·따옴표·역슬래시 금지")
        if not ph:
            fail(f"{where} {sc}: phrase 가 비어 있음")
        if not nm:
            warn(f"{where} {sc}: ko_name 이 비어 있음")
        if e["category"] not in ORDER:
            fail(f"{where} {sc}: 알 수 없는 카테고리 '{e['category']}' (가능: {', '.join(CATS)})")
        if "aliases" in e and not (isinstance(e["aliases"], list)
                                  and all(isinstance(x, str) for x in e["aliases"])):
            fail(f"{where} {sc}: aliases 는 문자열 배열이어야 함")
        if sc in seen:
            fail(f"{label}: 단축어 중복 '{sc}' ({seen[sc]}, {i}번)")
        else:
            seen[sc] = i
        if sc in known_shortcuts:
            fail(f"{label}: '{sc}' 가 공개 항목과 충돌")
    # 같은 기호에 단축어가 여럿 (#7) — 의도적일 수 있으므로 경고
    by_phrase = {}
    for e in entries:
        if isinstance(e, dict) and isinstance(e.get("phrase"), str):
            by_phrase.setdefault(e["phrase"], []).append(e["shortcut"])
    for ph, scs in by_phrase.items():
        if len(scs) > 1:
            warn(f"{label}: 같은 기호 '{ph}' 에 단축어 {len(scs)}개 — {', '.join(scs)}")
    return entries


# ---------------------------------------------------------------- 초성·이스케이프
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"


def cho(s):
    out = []
    for ch in s:
        o = ord(ch)
        out.append(CHO[(o - 0xAC00) // 588] if 0xAC00 <= o <= 0xD7A3 else ch)
    return "".join(out)


def att(s):
    return htmlmod.escape(str(s), quote=True)


def codepoints(phrase):
    """검색용 유니코드 코드포인트 문자열. (#22)"""
    return " ".join("U+%04X" % ord(c) for c in phrase)


def build_sections(entry_list):
    out = []
    for c in CATS:
        rows = [e for e in entry_list if e["category"] == c]
        if not rows:
            continue
        title, color = CAT_META[c]
        btns = []
        for e in rows:
            long_cls = " long" if len(e["phrase"]) > 2 else ""
            aliases = " ".join(e.get("aliases", []))
            btns.append(
                f'<button class="g{long_cls}" role="gridcell" '
                f'data-c="{att(e["phrase"])}" data-n="{att(e["ko_name"])}" '
                f'data-s="{att(e["shortcut"])}" data-cho="{att(cho(e["ko_name"]))}" '
                f'data-a="{att(aliases)}" data-u="{att(codepoints(e["phrase"]))}" '
                f'data-cat="{att(c)}" '
                f'aria-label="{att(e["ko_name"])} {att(e["shortcut"])}" '
                f'title="{att(e["ko_name"])} · {att(e["shortcut"])} + 스페이스">'
                f'<span class="gc">{att(e["phrase"])}</span>'
                f'<span class="gs">{att(e["shortcut"][1:])}</span>'
                f'</button>')
        out.append(
            f'<div class="sec" data-cat="{att(c)}">'
            f'<div class="lbl" role="button" tabindex="-1" aria-expanded="true">'
            f'<span class="dot" style="background:var({color})"></span>'
            f'<span class="lbl-t">{att(title)}</span>'
            f'<span class="lbl-n">{len(rows)}</span></div>'
            f'<div class="row" role="row">{"".join(btns)}</div></div>')
    return "".join(out)


# ---------------------------------------------------------------- 변경 요약 (#6)
def summarize_changes(old, new):
    if old is None:
        return None
    o = {e["shortcut"]: e for e in old if isinstance(e, dict) and "shortcut" in e}
    n = {e["shortcut"]: e for e in new}
    added = [k for k in n if k not in o]
    removed = [k for k in o if k not in n]
    changed = [k for k in n if k in o and n[k] != o[k]]
    if not (added or removed or changed):
        return "변경 없음"
    bits = []
    if added:
        bits.append(f"추가 {len(added)} ({', '.join(sorted(added)[:5])}{'…' if len(added) > 5 else ''})")
    if removed:
        bits.append(f"삭제 {len(removed)} ({', '.join(sorted(removed)[:5])}{'…' if len(removed) > 5 else ''})")
    if changed:
        bits.append(f"수정 {len(changed)} ({', '.join(sorted(changed)[:5])}{'…' if len(changed) > 5 else ''})")
    return " · ".join(bits)


# ---------------------------------------------------------------- 빌드 본체
def build():
    problems.clear()
    warnings.clear()

    cfg = load_config()
    entries = load_json(ROOT / "entries.json", "entries.json")
    if entries is None:
        return report(None)
    old_entries = list(entries)

    validate(entries, "entries.json")
    public_shortcuts = {e["shortcut"] for e in entries
                        if isinstance(e, dict) and isinstance(e.get("shortcut"), str)}

    local_entries = []
    if LOCAL_SRC.exists():
        local_entries = load_json(LOCAL_SRC, "entries.local.json") or []
        validate(local_entries, "entries.local.json", public_shortcuts)

    if problems:
        return report(None)

    entries.sort(key=lambda e: (ORDER[e["category"]], e["priority"], e["shortcut"]))
    all_entries = sorted(entries + local_entries,
                         key=lambda e: (ORDER[e["category"]], e["priority"], e["shortcut"]))

    change = summarize_changes(old_entries, entries)

    if CHECK:
        return report({"공개": len(entries), "로컬": len(local_entries), "변경": change}, wrote=False)

    cfg_json = json.dumps(cfg, ensure_ascii=False)

    # 1. plist (#75,76,82)
    def dump_plist(path, rows):
        with open(path, "wb") as f:
            plistlib.dump([{"phrase": e["phrase"], "shortcut": e["shortcut"]} for e in rows], f)

    dump_plist(DEST / "특수문자_텍스트대치.plist", entries)
    if local_entries:
        dump_plist(LOCAL_PLIST, all_entries)
        warn("텍스트 대치에는 .local.plist 하나만 등록하세요. "
             "공개 plist와 둘 다 등록하면 항목이 중복됩니다.")
    elif LOCAL_PLIST.exists():
        LOCAL_PLIST.unlink()

    # 2. entries.json 정규화 재기록
    (DEST / "entries.json").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 3. 팔레트 html
    tpl = (ROOT / "template" / "palette_template.html").read_text(encoding="utf-8")

    def render(rows):
        return (tpl.replace("@@SECTIONS@@", build_sections(rows))
                   .replace("@@CONFIG@@", cfg_json)
                   .replace("@@VERSION@@", VERSION))

    PALETTE.write_text(render(entries), encoding="utf-8")
    if local_entries:
        PALETTE_LOCAL.write_text(render(all_entries), encoding="utf-8")
    elif PALETTE_LOCAL.exists():
        PALETTE_LOCAL.unlink()

    # 4. lua
    lua = (ROOT / "template" / "special_chars_template.lua").read_text(encoding="utf-8")
    HS.parent.mkdir(exist_ok=True)
    HS.write_text(lua.replace("@@CONFIG@@", cfg_json).replace("@@VERSION@@", VERSION),
                  encoding="utf-8")

    # 5. 치트시트
    sheet = (ROOT / "template" / "cheatsheet_template.html").read_text(encoding="utf-8")
    html_out = (sheet.replace("__DATA__", json.dumps(entries, ensure_ascii=False))
                     .replace("@@VERSION@@", VERSION))
    (DEST / "index.html").write_text(html_out, encoding="utf-8")
    (DEST / "치트시트.html").write_text(html_out, encoding="utf-8")

    return report({"공개": len(entries), "로컬": len(local_entries), "변경": change})


# ---------------------------------------------------------------- 출력 (#11,14)
OUTPUTS = ["entries.json", "특수문자_텍스트대치.plist", "특수문자_텍스트대치.local.plist",
           "index.html", "치트시트.html",
           "hammerspoon/special_chars.lua",
           "hammerspoon/special_chars_palette.html",
           "hammerspoon/special_chars_palette.local.html"]


def report(stats, wrote=True):
    for w in warnings:
        say(f"  경고: {w}")
    if problems:
        for p in problems:
            print(f"  오류: {p}", file=sys.stderr)
        print(f"실패: 오류 {len(problems)}건", file=sys.stderr)
        return 1
    if stats:
        line = f"OK: 공개 {stats['공개']}개"
        if stats["로컬"]:
            line += f" + 로컬 {stats['로컬']}개 (공개 산출물에는 제외)"
        if stats.get("변경"):
            line += f" · {stats['변경']}"
        say(line)
    if wrote:
        say("생성:")
        for rel in OUTPUTS:                      # 결정론적 순서 (#14)
            p = ROOT / rel
            if p.exists():
                say(f"  {rel} ({p.stat().st_size:,} bytes)")
    else:
        say("검증만 수행 (파일 안 씀)")
    return 0


# ---------------------------------------------------------------- watch (#5)
WATCH_FILES = ["entries.json", "entries.local.json", "config.json", "config.local.json",
               "template/palette_template.html", "template/special_chars_template.lua",
               "template/cheatsheet_template.html"]


def stamps():
    out = {}
    for rel in WATCH_FILES:
        p = ROOT / rel
        out[rel] = p.stat().st_mtime if p.exists() else None
    return out


if __name__ == "__main__":
    code = build()
    if WATCH:
        print("watch 중 — 종료는 Ctrl+C")
        last = stamps()
        try:
            while True:
                time.sleep(0.7)
                cur = stamps()
                if cur != last:
                    last = cur
                    print(f"\n[{time.strftime('%H:%M:%S')}] 변경 감지 — 재빌드")
                    build()
        except KeyboardInterrupt:
            print("\nwatch 종료")
    sys.exit(code)
