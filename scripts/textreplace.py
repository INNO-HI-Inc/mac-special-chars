#!/usr/bin/env python3
"""macOS 텍스트 대치 도우미 — 지금 등록된 항목과 우리 plist를 비교/백업한다.

  python3 scripts/textreplace.py --status    등록 현황 + 우리 plist와 비교
  python3 scripts/textreplace.py --diff      어긋난 항목 전체 목록
  python3 scripts/textreplace.py --backup    현재 등록분을 백업 파일로 저장
  python3 scripts/textreplace.py --stats     우리 plist 통계

시스템에 '쓰지는' 않는다. macOS는 텍스트 대치를 자체 DB로 관리하고 iCloud로
동기화하기 때문에, 바깥에서 밀어 넣으면 동기화가 깨질 수 있다. 등록은
시스템 설정에 plist를 드래그하는 방식(사람이 직접)만 지원한다.
"""
import json, plistlib, pathlib, subprocess, sys, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUB = ROOT / "특수문자_텍스트대치.plist"
LOC = ROOT / "특수문자_텍스트대치.local.plist"
BACKUP_DIR = ROOT / "docs" / "backup"

ARGS = set(sys.argv[1:]) or {"--status"}


TR_DB = pathlib.Path.home() / "Library" / "KeyboardServices" / "TextReplacements.db"


def system_items_db():
    """최신 macOS의 실제 저장소(CoreData sqlite). iCloud 동기화 대상."""
    if not TR_DB.exists():
        return None
    try:
        out = subprocess.run(
            ["sqlite3", "-readonly", "-json", str(TR_DB),
             "select ZSHORTCUT as s, ZPHRASE as p from ZTEXTREPLACEMENTENTRY "
             "where coalesce(ZWASDELETED,0)=0;"],
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None
    if not out:
        return []
    try:
        rows = json.loads(out)
    except json.JSONDecodeError:
        return None
    return [(r["s"], r["p"]) for r in rows
            if isinstance(r, dict) and r.get("s") and r.get("p") is not None]


def system_items():
    """현재 등록된 텍스트 대치 목록 [(shortcut, phrase)].
    DB를 우선 읽고(권위), 실패하면 NSGlobalDomain으로 넘어간다."""
    db = system_items_db()
    if db is not None:
        return db
    try:
        out = subprocess.run(["defaults", "export", "-g", "-"],
                             capture_output=True, check=True).stdout
        d = plistlib.loads(out)
    except Exception as e:
        print(f"시스템 설정을 읽지 못했습니다: {e}", file=sys.stderr)
        return None
    items = d.get("NSUserDictionaryReplacementItems") or []
    out = []
    for it in items:
        if isinstance(it, dict) and "replace" in it and "with" in it:
            out.append((str(it["replace"]), str(it["with"])))
    return out


def ours(path):
    if not path.exists():
        return []
    data = plistlib.loads(path.read_bytes())
    return [(x["shortcut"], x["phrase"]) for x in data]


def pick_source():
    """로컬 plist가 있으면 그쪽이 기준(개인 항목 포함)."""
    return (LOC, "로컬(.local)") if LOC.exists() else (PUB, "공개")


def cmd_stats():
    for path, label in ((PUB, "공개"), (LOC, "로컬")):
        if not path.exists():
            continue
        rows = ours(path)
        longest = max(rows, key=lambda r: len(r[1]), default=("", ""))
        print(f"[{label}] {path.name}")
        print(f"  항목 {len(rows)}개 · {path.stat().st_size:,} bytes")
        print(f"  가장 긴 값: {longest[0]} ({len(longest[1])}자)")
        dup = {}
        for sc, ph in rows:
            dup.setdefault(ph, []).append(sc)
        multi = {k: v for k, v in dup.items() if len(v) > 1}
        if multi:
            print(f"  같은 값에 단축어 여럿: {len(multi)}건 — "
                  + ", ".join(f"{k}({'/'.join(v)})" for k, v in list(multi.items())[:3]))


def cmd_backup():
    sys_items = system_items()
    if sys_items is None:
        return 1
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    p = BACKUP_DIR / f"textreplace-{stamp}.json"
    p.write_text(json.dumps([{"shortcut": s, "phrase": w} for s, w in sys_items],
                            ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"백업 {len(sys_items)}개 → {p.relative_to(ROOT)}")
    print("주의: 이 백업에는 개인 항목이 포함될 수 있습니다. git에 올리지 마세요.")
    return 0


def cmd_compare(verbose):
    sys_items = system_items()
    if sys_items is None:
        return 1
    path, label = pick_source()
    mine = ours(path)
    if not mine:
        print(f"기준 plist가 없습니다 — 먼저 python3 scripts/build.py")
        return 1

    sysmap = dict(sys_items)
    mymap = dict(mine)
    mine_sc = set(mymap)

    missing = sorted(mine_sc - set(sysmap))                       # 등록 안 됨
    mismatch = sorted(s for s in mine_sc & set(sysmap) if sysmap[s] != mymap[s])
    extra_ours = sorted(s for s in set(sysmap) - mine_sc if s.startswith("ㅁ"))

    print(f"시스템 등록: {len(sys_items)}개 (그중 ㅁ단축어 "
          f"{sum(1 for s, _ in sys_items if s.startswith('ㅁ'))}개)")
    print(f"기준 plist : {path.name} [{label}] {len(mine)}개")
    print()
    ok = not (missing or mismatch)
    print(f"  {'✅' if not missing else '❌'} 미등록 {len(missing)}개")
    print(f"  {'✅' if not mismatch else '❌'} 값 불일치 {len(mismatch)}개")
    print(f"  {'·' if not extra_ours else '⚠️'} 시스템에만 있는 ㅁ항목 {len(extra_ours)}개")

    if verbose:
        def show(title, keys, fmt):
            if not keys:
                return
            print(f"\n[{title}]")
            for k in keys[:40]:
                print("  " + fmt(k))
            if len(keys) > 40:
                print(f"  … 외 {len(keys) - 40}개")
        show("미등록", missing, lambda k: f"{k} → {mymap[k]}")
        show("값 불일치", mismatch, lambda k: f"{k}  시스템:{sysmap[k]}  plist:{mymap[k]}")
        show("시스템에만 있음", extra_ours, lambda k: f"{k} → {sysmap[k]}")

    if not ok:
        print(f"\n등록 방법: 시스템 설정 → 키보드 → 텍스트 대치 를 열고")
        print(f"  {path}")
        print("  를 목록 안으로 드래그하세요.")
        if LOC.exists():
            print("  ※ .local 쪽 하나만 드래그하세요. 공개 plist까지 넣으면 중복됩니다.")
    return 0


if __name__ == "__main__":
    code = 0
    if "--stats" in ARGS:
        cmd_stats()
    elif "--backup" in ARGS:
        code = cmd_backup()
    else:
        code = cmd_compare("--diff" in ARGS)
    sys.exit(code)
