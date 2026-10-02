"""문서에 적힌 건수·api_type 이 카탈로그와 어긋나지 않아야 한다."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / "skills").iterdir())
CATALOG = json.loads((ROOT / "meritz_studio" / "data" / "catalog.json")
                     .read_text(encoding="utf-8"))
KEYS = {a["key"] for a in CATALOG["apis"]}
N_REST = sum(1 for a in CATALOG["apis"] if a["protocol"] != "WEBSOCKET")
N_WS = len(CATALOG["apis"]) - N_REST


def test_two_skills_exist():
    assert [p.name for p in SKILLS] == [
        "meritz-openapi-codegen", "meritz-openapi-trading"]


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_has_frontmatter_with_name_and_description(skill):
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), "프론트매터가 없습니다"
    head = text.split("---")[1]
    assert re.search(r"^name:\s*\S+", head, re.M)
    desc = re.search(r"^description:\s*(.+)", head, re.M)
    assert desc and len(desc.group(1)) > 80, "설명이 짧으면 트리거되지 않습니다"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_references_exist(skill):
    for name in ("api-catalog.md", "apis.json", "corrections.md",
                 "errors.md", "glossary.md", "setup.md"):
        assert (skill / "references" / name).is_file(), f"{name} 누락"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_api_counts_match_catalog(skill):
    """문서에 적힌 건수가 카탈로그와 다르면 안 된다."""
    text = "\n".join(p.read_text(encoding="utf-8")
                     for p in [skill / "SKILL.md"] + list((skill / "references").glob("*.md")))
    for n in re.findall(r"(\d+)\s*개?\s*API", text) + re.findall(r"API\s*(\d+)\s*건", text):
        assert int(n) in (len(KEYS), N_REST, N_WS), \
            f"{skill.name}: 문서의 {n} 이 카탈로그(총 {len(KEYS)}·REST {N_REST}·실시간 {N_WS})와 다릅니다"
    for n in re.findall(r"REST\s*(\d+)건", text):
        assert int(n) == N_REST
    for n in re.findall(r"실시간\s*(\d+)건", text):
        assert int(n) == N_WS


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_mentions_no_unknown_api_type(skill):
    """스킬이 없는 api_type 을 예시로 들면 에이전트가 그대로 따라 한다."""
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for m in re.finditer(r"meritz (?:call|order|ws|api show) ([a-z][a-z0-9_]+)", text):
        assert m.group(1) in KEYS, f"없는 api_type: {m.group(1)}"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_carries_the_warning_flow(skill):
    """접수되지 않은 주문을 성공으로 보고하지 않게 하는 유일한 장치다."""
    text = "\n".join(p.read_text(encoding="utf-8")
                     for p in [skill / "SKILL.md"] + list((skill / "references").glob("*.md")))
    assert "warn_cls_code" in text
    assert "warn_cnfr_yn" in text


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_judges_by_zero_not_by_a_code_list(skill):
    """판정 기준은 "0 인가" 다.

    11개 목록으로 판정한다고 적으면 보류값(국내 2·5·8·b·e·h, 해외 2)이
    성공으로 통과한다. 그 목록은 **재전송하면 풀리는 값**일 뿐이다.
    """
    text = "\n".join(p.read_text(encoding="utf-8")
                     for p in [skill / "SKILL.md"] + list((skill / "references").glob("*.md")))
    assert '`0` 이 아니면' in text or 'code != "0"' in text, \
        f"{skill.name}: '0 이 아니면 미접수' 라는 판정 기준이 없습니다"
    assert "재전송" in text, f"{skill.name}: 재전송으로 풀리는 값이라는 설명이 없습니다"
    assert "재전송해도" in text, \
        f"{skill.name}: 재전송해도 풀리지 않는 값에 대한 안내가 없습니다"
    assert "overseas" in text or "해외" in text, f"{skill.name}: 국내·해외 구분이 없습니다"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_success_codes_match_the_client(skill):
    """문서의 "성공으로 보는 코드" 표가 OK_CODES 와 어긋나면 오판을 가르친다."""
    import re as _re

    from meritz_studio.core.client import OK_CODES
    text = (skill / "references" / "errors.md").read_text(encoding="utf-8")
    body = text.split("## 성공으로 보는 코드", 1)[1].split("###", 1)[0]
    listed = {m for m in _re.findall(r"^\| `(\d{4,5})`", body, _re.M)}
    assert listed - {"00000"} == OK_CODES, \
        f"{skill.name}: 문서 {sorted(listed)} vs OK_CODES {sorted(OK_CODES)}"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_generated_references_are_current(skill):
    """지금 생성기를 돌리면 나올 내용과 같아야 한다.

    파일을 건드리지 않고 대조한다. 예전에는 build_skills.py 를 실제로 실행해
    작업트리를 덮어쓴 뒤 비교했다 — 낡은 생성물이 커밋돼 있어도 파일만 조용히
    바뀌고 통과하는, 검사가 아니라 갱신이었다.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_skills", ROOT / "build_skills.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    stale = [name for name, body in mod.render().items()
             if (skill / "references" / name).read_text(encoding="utf-8") != body]
    assert not stale, f"생성물이 낡았습니다: {stale} — python3 build_skills.py 를 돌리세요"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_examples_use_the_right_symbol_format(skill):
    """시세는 005930, 주문은 A005930 이다. 에이전트는 예시를 그대로 베낀다."""
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for m in re.finditer(r"meritz (call|order) (\w+)[^\n]*?-p iscd=(\S+)", text):
        kind, key, value = m.groups()
        api = next(a for a in CATALOG["apis"] if a["key"] == key)
        desc = next(p.get("description") or ""
                    for p in api["request"]["params"] if p["name"] == "iscd")
        if "모두 받" in desc or "모두 허용" in desc:
            continue        # 6자리·A+6자리 둘 다 받는 API — 어느 쪽이든 맞다 (2026-09-11 명세 보정)
        wants_prefix = 'A005930' in desc
        assert value.startswith("A") == wants_prefix, (
            f'{key}: iscd={value} — 명세는 {"A + 6자리" if wants_prefix else "6자리"} 를 요구합니다')
