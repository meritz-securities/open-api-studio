"""배포물에는 운영 기준만 들어간다.

개발 서버 주소가 한 번이라도 다시 섞여 들어오면 여기서 걸린다.
카탈로그를 다시 크롤하면 `domain.dev` 가 그대로 따라 들어오기 때문에
사람 눈으로 잡는 대신 기본 실행에 넣는다 (slow 마커를 붙이지 않는다).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEEDLE = "dev" + "api"          # 이 파일 자신이 걸리지 않게 나눠 쓴다
SELF = Path(__file__).name
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache",
             ".ruff_cache", ".mypy_cache", "node_modules", "dist", "build"}


def _tracked_text_files() -> list[Path]:
    """커밋 대상 파일만 본다 — 무시되는 산출물은 배포되지 않는다."""
    r = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout:
        names = [n for n in r.stdout.split("\0") if n]
        return [ROOT / n for n in names]
    # git 이 없는 환경(설치본 검사 등)에서는 트리를 직접 훑는다.
    out = []
    for p in ROOT.rglob("*"):
        if p.is_file() and not (SKIP_DIRS & set(p.relative_to(ROOT).parts)):
            out.append(p)
    return out


def test_no_dev_server_reference_anywhere():
    hits = []
    for p in _tracked_text_files():
        if p.name == SELF or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue        # 바이너리는 대상이 아니다
        for i, line in enumerate(text.splitlines(), 1):
            if NEEDLE in line:
                hits.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:120]}")
    assert not hits, (
        "개발 서버 주소가 배포물에 들어 있습니다. 운영 기준만 담아야 합니다:\n"
        + "\n".join(hits))
