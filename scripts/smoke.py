#!/usr/bin/env python3
"""스모크 테스트 — 빌드 산출물이 온전한지, 개인정보가 새지 않았는지 확인한다.

  python3 scripts/smoke.py

CI나 커밋 전에 돌린다. 실패하면 종료코드 1.
가장 중요한 검사는 '개인 데이터가 공개 산출물에 없는가' 이다.
"""
import json, plistlib, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
fails, checks = [], 0


def ok(cond, label, detail=""):
    global checks
    checks += 1
    if cond:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}" + (f" — {detail}" if detail else ""))
        fails.append(label)


def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


print("[1] 빌드 검증")
r = subprocess.run([sys.executable, "scripts/build.py", "--check"],
                   cwd=ROOT, capture_output=True, text=True)
ok(r.returncode == 0, "build.py --check 통과", r.stderr.strip()[:200])

print("\n[2] 산출물 존재")
required = ["entries.json", "특수문자_텍스트대치.plist", "index.html",
            "hammerspoon/special_chars.lua", "hammerspoon/special_chars_palette.html"]
for rel in required:
    ok((ROOT / rel).exists(), f"{rel} 있음")

print("\n[3] 플레이스홀더 치환")
for rel in ["hammerspoon/special_chars.lua", "hammerspoon/special_chars_palette.html", "index.html"]:
    t = read(rel)
    left = [m for m in ("@@SECTIONS@@", "@@CONFIG@@", "@@VERSION@@", "__DATA__") if m in t]
    ok(not left, f"{rel} 치환 완료", f"남음: {left}")

print("\n[4] 항목 수 일치")
entries = json.loads(read("entries.json") or "[]")
plist = plistlib.loads((ROOT / "특수문자_텍스트대치.plist").read_bytes())
pal = read("hammerspoon/special_chars_palette.html")
btns = len(re.findall(r'role="gridcell"', pal))
ok(len(entries) == len(plist) == btns,
   f"entries={len(entries)} plist={len(plist)} 팔레트={btns}")

print("\n[5] 단축어 규칙")
bad = [e["shortcut"] for e in entries if not e["shortcut"].startswith("ㅁ")]
ok(not bad, "모든 단축어가 ㅁ로 시작", str(bad[:5]))
scs = [e["shortcut"] for e in entries]
ok(len(scs) == len(set(scs)), "단축어 중복 없음")

print("\n[6] 별칭·검색 데이터")
withalias = len(re.findall(r'data-a="[^"]+"', pal))
ok(withalias > len(entries) * 0.8, f"영문 별칭 {withalias}/{len(entries)}개 채워짐")
ok(len(re.findall(r'data-u="U\+', pal)) > 0, "유니코드 코드포인트 있음")
ok(len(re.findall(r'data-cho="', pal)) == len(entries), "초성 데이터 완비")

print("\n[7] 개인정보 격리  ← 가장 중요")
local_path = ROOT / "entries.local.json"
if local_path.exists():
    local = json.loads(local_path.read_text(encoding="utf-8"))
    secrets = [e["phrase"] for e in local if e.get("phrase")]
    public_files = ["entries.json", "index.html", "치트시트.html",
                    "특수문자_텍스트대치.plist", "config.json", "README.md",
                    "hammerspoon/special_chars.lua",
                    "hammerspoon/special_chars_palette.html",
                    "template/palette_template.html",
                    "template/special_chars_template.lua",
                    "scripts/build.py", "entries.local.example.json"]
    leaked = []
    for rel in public_files:
        p = ROOT / rel
        if not p.exists():
            continue
        blob = p.read_bytes().decode("utf-8", "ignore")
        for sec in secrets:
            if sec in blob:
                leaked.append(f"{rel}:{sec[:6]}…")
    ok(not leaked, f"공개 산출물 {len(public_files)}개에 개인 값 없음", str(leaked[:3]))

    # git 추적 여부
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT,
                             capture_output=True, text=True).stdout.split("\n")
    must_ignore = ["entries.local.json", "특수문자_텍스트대치.local.plist",
                   "hammerspoon/special_chars_palette.local.html"]
    bad_tracked = [f for f in must_ignore if f in tracked]
    ok(not bad_tracked, "개인 파일이 git에 추적되지 않음", str(bad_tracked))

    # 커밋 히스토리
    h = subprocess.run(["git", "log", "-p", "--all"], cwd=ROOT,
                       capture_output=True, text=True).stdout
    hist = [s[:6] + "…" for s in secrets if s and s in h]
    ok(not hist, "커밋 히스토리에도 개인 값 없음", str(hist[:3]))
else:
    print("  · entries.local.json 없음 — 개인정보 검사 건너뜀")

print("\n" + "─" * 46)
if fails:
    print(f"실패 {len(fails)}/{checks}: " + ", ".join(fails[:5]))
    sys.exit(1)
print(f"전부 통과 ({checks}개 검사)")
