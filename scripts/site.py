#!/usr/bin/env python3
"""GitHub Pages 배포용 정적 사이트를 _site/ 에 조립한다.

  _site/index.html       랜딩 (다운로드 + 설치 안내)  ← template/landing_template.html
  _site/cheatsheet.html  치트시트                     ← index.html (build.py 산출물)
  _site/mac-special-chars.plist   텍스트 대치 파일    ← 특수문자_텍스트대치.plist
  _site/palette.png      팔레트 스크린샷              ← docs/palette.png

사용법:
  python3 scripts/site.py            _site/ 생성
  python3 scripts/site.py --check    검증만 (파일 안 씀, CI용)

build.py 를 먼저 돌려야 한다. 개인 항목(.local. 산출물)은 절대 복사하지 않는다.
"""
import json, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
CHECK = "--check" in sys.argv[1:]

PLIST_SRC = ROOT / "특수문자_텍스트대치.plist"
PLIST_OUT = "mac-special-chars.plist"      # URL은 ASCII, 저장될 이름은 download 속성으로 한글
FALLBACK_REPO = "https://github.com/INNO-HI-Inc/mac-special-chars"

# 데모에 쓸 단축어 — entries.json 에 없으면 빌드를 멈춘다 (동기화 보증)
DEMO_SHORTCUTS = ["ㅁ별", "ㅁ참고", "ㅁ1", "ㅁ제곱미터", "ㅁ하트", "ㅁ낫표"]
PREVIEW_MAX = 24

problems = []


def fail(msg):
    problems.append(msg)


def repo_url():
    """CI에서는 GITHUB_REPOSITORY, 로컬에서는 git remote 를 쓴다."""
    import os
    slug = os.environ.get("GITHUB_REPOSITORY")
    if slug:
        return f"https://github.com/{slug}"
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return FALLBACK_REPO
    url = re.sub(r"^git@github\.com:", "https://github.com/", url)
    return re.sub(r"\.git$", "", url) or FALLBACK_REPO


def version():
    """build.py 의 VERSION 하나가 유일한 출처 (README 참고)."""
    src = (ROOT / "scripts" / "build.py").read_text(encoding="utf-8")
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', src, re.M)
    if not m:
        fail("scripts/build.py 에서 VERSION 을 찾지 못함")
        return "0.0.0"
    return m.group(1)


def sub_once(text, old, new, what):
    """정확히 1번만 치환 — 템플릿이 바뀌어 앵커가 사라지면 조용히 넘어가지 않는다."""
    if text.count(old) != 1:
        fail(f"{what}: 앵커를 {text.count(old)}번 찾음 (1번이어야 함)")
        return text
    return text.replace(old, new)


def main():
    # --- 입력 확인 -------------------------------------------------------
    need = [ROOT / "entries.json", ROOT / "index.html", PLIST_SRC,
            ROOT / "docs" / "palette.png", ROOT / "template" / "landing_template.html"]
    for p in need:
        if not p.exists():
            fail(f"{p.relative_to(ROOT)} 없음 — 먼저 python3 scripts/build.py 를 실행하세요")
    if problems:
        return report()

    entries = json.loads((ROOT / "entries.json").read_text(encoding="utf-8"))
    by_shortcut = {e["shortcut"]: e for e in entries}
    ver = version()
    repo = repo_url()

    # 개인 항목이 공개 entries.json 에 섞이지 않았는지 (build.py 와 중복 방어)
    if any(e.get("category") == "personal" for e in entries):
        fail("entries.json 에 personal 항목이 있음 — 사이트에 올리면 안 됩니다")

    # --- 데모 · 미리보기 데이터 -----------------------------------------
    demo = []
    for sc in DEMO_SHORTCUTS:
        e = by_shortcut.get(sc)
        if not e:
            fail(f"데모 단축어 {sc} 가 entries.json 에 없음")
            continue
        demo.append({"s": e["shortcut"], "p": e["phrase"]})

    preview = [{"s": e["shortcut"], "p": e["phrase"], "n": e["ko_name"]}
               for e in entries if e.get("priority", 9) <= 1][:PREVIEW_MAX]
    if len(preview) < 12:
        fail(f"미리보기 항목이 {len(preview)}개뿐 — priority 1 항목을 확인하세요")

    if problems:
        return report()

    # --- 랜딩 ------------------------------------------------------------
    landing = (ROOT / "template" / "landing_template.html").read_text(encoding="utf-8")
    kb = max(1, round(PLIST_SRC.stat().st_size / 1024))
    landing = (landing
               .replace("@@COUNT@@", str(len(entries)))
               .replace("@@VERSION@@", ver)
               .replace("@@PLIST_KB@@", str(kb))
               .replace("@@PLIST@@", PLIST_OUT)
               .replace("@@REPO@@", repo)
               .replace("__PREVIEW__", json.dumps(preview, ensure_ascii=False))
               .replace("__DEMO__", json.dumps(demo, ensure_ascii=False)))
    for left in re.findall(r"@@[A-Z_]+@@|__[A-Z]+__", landing):
        fail(f"랜딩에 치환되지 않은 자리표시자: {left}")

    # --- 치트시트: 랜딩으로 돌아가는 링크만 덧댄다 -----------------------
    sheet = (ROOT / "index.html").read_text(encoding="utf-8")
    sheet = sub_once(
        sheet,
        '<div class="eyebrow">윈도우 ㅁ+한자 대신, 맥에서</div>',
        '<div class="eyebrow">윈도우 ㅁ+한자 대신, 맥에서 · '
        '<a href="./" style="color:var(--accent);font-weight:700;text-decoration:none">설치 안내 →</a></div>',
        "치트시트 back-link")

    if problems:
        return report()
    if CHECK:
        print(f"검증 통과 — 기호 {len(entries)}개 · v{ver} · {repo}")
        print("  (--check 이므로 _site/ 는 만들지 않았습니다)")
        return 0

    # --- 쓰기 ------------------------------------------------------------
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    (SITE / "index.html").write_text(landing, encoding="utf-8")
    (SITE / "cheatsheet.html").write_text(sheet, encoding="utf-8")
    shutil.copy2(PLIST_SRC, SITE / PLIST_OUT)
    shutil.copy2(ROOT / "docs" / "palette.png", SITE / "palette.png")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    # 개인 항목이 실수로 딸려오지 않았는지 최종 확인 — 파일명과 내용 둘 다
    named = [p.name for p in SITE.rglob("*") if ".local." in p.name]
    if named:
        fail(f"_site 에 로컬 전용 파일이 섞임: {named}")
    local_src = ROOT / "entries.local.json"
    if local_src.exists():
        secrets = [e["phrase"] for e in json.loads(local_src.read_text(encoding="utf-8"))
                   if e.get("phrase")]
        for f in sorted(SITE.rglob("*")):
            if not f.is_file():
                continue
            blob = f.read_bytes().decode("utf-8", "ignore")
            for sec in secrets:
                if sec and sec in blob:
                    fail(f"_site/{f.name} 에 개인 값이 들어감: {sec[:6]}…")
    if problems:
        shutil.rmtree(SITE)          # 새는 사이트는 남기지 않는다
        return report()

    print(f"_site/ 생성 — 기호 {len(entries)}개 · v{ver}")
    for p in sorted(SITE.iterdir()):
        print(f"  {p.name} ({p.stat().st_size:,} bytes)")
    print(f"미리보기: python3 -m http.server -d _site 8080")
    return 0


def report():
    for p in problems:
        print(f"  오류: {p}", file=sys.stderr)
    print(f"실패: 오류 {len(problems)}건", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
