"""설치된 패키지만으로 첫 명령이 도는지 본다.

개발 환경 변수를 걷어내고 확인한다.
"""
import json
import os
import subprocess
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "meritz_studio" / "data"


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """휠을 만들어 빈 가상환경에 깔고 그 meritz 경로를 돌려준다."""
    env_dir = tmp_path_factory.mktemp("venv")
    venv.create(env_dir, with_pip=True)
    bin_dir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    pip = bin_dir / "pip"
    r = subprocess.run([str(pip), "install", "--quiet", str(ROOT)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        pytest.fail(f"pip install 실패:\n{r.stdout}\n{r.stderr}")
    return bin_dir / "meritz"


def _run(meritz, *args):
    # 개발 환경 변수를 걷어내야 설치본만으로 도는지 알 수 있다.
    env = {k: v for k, v in os.environ.items()
           if k not in ("MERITZ_CATALOG", "PYTHONPATH")}
    return subprocess.run([str(meritz), *args], capture_output=True, text=True, env=env)


@pytest.mark.slow
def test_wheel_builds_and_installs(installed):
    assert installed.is_file(), "meritz 명령이 설치되지 않았습니다"


@pytest.mark.slow
def test_installed_cli_finds_the_catalog(installed):
    """동봉 데이터를 찾지 못하면 첫 명령이 실패한다."""
    r = _run(installed, "api", "list", "--json")
    assert r.returncode == 0, f"exit={r.returncode}\n{r.stderr}"
    # 건수를 박아 두지 않는다. 54 를 박아 둔 탓에 카탈로그가 75건이 된 뒤로
    # 이 검사가 계속 실패했고, slow 마커로 CI 에서 빠져 있어 아무도 몰랐다.
    # 보려는 것은 «건수가 몇인가» 가 아니라 «동봉 카탈로그를 통째로 찾았는가» 다.
    expected = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    assert len(json.loads(r.stdout)) == expected["counts"]["total"]


@pytest.mark.slow
def test_installed_cli_shows_corrections(installed):
    # 대상 API 를 이름으로 박아 두지 않는다 — 정정 항목이 줄어드는 것은 정상이다.
    # ovs_market_prices 를 박아 둔 탓에, 포털이 그 항목을 고친 뒤 이 검사가 깨졌다.
    fixes = json.loads((DATA / "corrections.json").read_text(encoding="utf-8"))
    catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    known = {a["key"] for a in catalog["apis"]}
    keys = [k for c in (fixes.get("corrections") or [])
            for k in c.get("keys", []) if k in known]
    assert keys, "정정 항목이 하나도 없습니다 — corrections.json 을 확인하세요"
    r = _run(installed, "api", "show", keys[0])
    assert r.returncode == 0, r.stderr
    assert "응답 처리 참고사항" in r.stdout


@pytest.mark.slow
def test_installed_cli_blocks_orders_on_call(installed):
    """게이트가 설치본에서도 살아 있어야 한다."""
    r = _run(installed, "call", "orders_buy")
    assert r.returncode != 0
    assert "상태를 바꾸는 요청" in (r.stdout + r.stderr)
