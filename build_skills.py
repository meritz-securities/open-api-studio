"""스킬이 읽는 참조 문서를 카탈로그에서 생성한다.

여기서 만드는 것은
전부 catalog.json / corrections.json 에서 나오고, 손으로 쓰는 것은
SKILL.md 와 errors.md 처럼 카탈로그에 없는 지식뿐이다.

  python3 build_skills.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "meritz_studio" / "data"
SKILLS = ROOT / "skills"
NAMES = ["meritz-openapi-codegen", "meritz-openapi-trading"]

sys.path.insert(0, str(ROOT))
from meritz_studio.core.safety import is_state_changing  # noqa: E402

_TAG = re.compile(r"<[^>]+>")


def clean(t: str) -> str:
    t = re.sub(r"<br\s*/?>", " ", t or "")
    t = _TAG.sub("", t).replace("&nbsp;", " ").replace("&amp;", "&")
    return " ".join(t.split())


def load():
    cat = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    fixes = json.loads((DATA / "corrections.json").read_text(encoding="utf-8"))
    return cat, fixes


def api_catalog_md(cat, fixes) -> str:
    L = [f"# API 목록 ({len(cat['apis'])}건)", "",
         f"개발자 포털 기준 명세다. 기준일 {cat.get('generated', '?')} · 출처 {cat.get('source', '')}",
         "", "`⚠` 는 상태를 바꾸는 요청이다 — 미리보기와 사용자 확인 없이 실행하지 않는다.", ""]
    rest = [a for a in cat["apis"] if a["protocol"] != "WEBSOCKET"]
    ws = [a for a in cat["apis"] if a["protocol"] == "WEBSOCKET"]
    by_cat: dict[str, list] = {}
    for a in rest:
        by_cat.setdefault(a["category"], []).append(a)
    for c, items in by_cat.items():
        L += [f"## {c}", "", "| api_type | 호출 | 이름 |", "|---|---|---|"]
        for a in items:
            m = "⚠ " if is_state_changing(a) else ""
            L.append(f"| `{a['key']}` | {a['method']} {a['path']} | {m}{a['name']} |")
        L.append("")
    L += ["## 실시간 (WebSocket)", "",
          "접속점은 하나다. 무엇을 받을지는 구독 메시지의 `tr_cd` 가 정한다.", "",
          "| api_type | tr_cd | 이름 |", "|---|---|---|"]
    for a in ws:
        L.append(f"| `{a['key']}` | `{a['tr_id']}` | {a['name']} |")
    return "\n".join(L) + "\n"


def corrections_md(fixes) -> str:
    L = ["# API별 응답 처리 참고사항", "",
         "API 호출 결과를 해석하고 요청을 구성할 때 참고할 사항을 정리합니다.",
         "실제 이용 시에는 개발자 포털의 최신 명세와 API별 권한을 확인하십시오.", ""]
    for c in fixes.get("corrections", []):
        L += [f"## {c.get('kind')}", "",
              "대상: " + ", ".join(f"`{k}`" for k in c.get("keys", [])), ""]
        # 찍을 칸을 여기서 지정한다. corrections.json 에 새 칸이 생겨도
        # 여기 없으면 나가지 않는다 — 감사 기록(note_*·verified 등)이 고객
        # 문서로 렌더링돼 나간 적이 있어, 기본을 차단으로 둔다.
        #
        # actual(무엇이 다른가)과 workaround(그래서 어떻게 하나)가 빠지면
        # 스킬을 읽는 에이전트가 대응을 알 수 없다. 둘은 반드시 찍는다.
        for label, key in (("증상", "symptom"),
                           ("명세상 안내", "portal_example"), ("응답 동작", "actual"),
                           ("적용 예시", "working_example"),
                           ("일반적인 처리 방식으로 호출하면", "if_you_follow_the_portal"),
                           ("이렇게 하십시오", "workaround"),
                           ("주의", "caution")):
            if c.get(key):
                L.append(f"- **{label}** — {c[key]}")
        # workaround 가 이미 같은 말을 하고 있으면 덧붙이지 않는다.
        if c.get("degraded") and not c.get("workaround"):
            L.append("- **주의** — 이 API 는 `rsp_cd` 로 성공을 판정할 수 없습니다. "
                     "data 가 있으면 정상으로 보십시오.")
        L.append("")
    return "\n".join(L) + "\n"


def glossary_md(cat) -> str:
    terms: dict[str, tuple[str, set]] = {}
    for a in cat["apis"]:
        for sec in ("request", "response"):
            groups = a.get(sec) or {}
            for lst in (groups.values() if isinstance(groups, dict) else []):
                # 필드 목록이 아닌 절은 건너뛴다.
                #   response.containers 는 {"data": {...}} 형태의 매핑이라
                #   그대로 순회하면 문자열 키가 나와 .get 에서 터진다.
                if not isinstance(lst, list):
                    continue
                for f in lst:
                    if not isinstance(f, dict):
                        continue
                    ko = (f.get("name_ko") or "").strip()
                    if not ko:
                        continue
                    cur = terms.setdefault(f["name"], (ko, set()))
                    cur[1].add(ko)
    L = ["# 응답 필드 용어", "",
         "응답은 영문 약어로 온다. 사용자에게 설명할 때 한글명을 붙인다.",
         "같은 이름에 한글명이 둘 이상이면 API 마다 뜻이 갈린다는 뜻이니 "
         "`meritz api show` 로 해당 API 의 설명을 확인한다.", "",
         "| 필드 | 한글명 |", "|---|---|"]
    for name in sorted(terms):
        kos = sorted(terms[name][1])
        L.append(f"| `{name}` | {' · '.join(kos)} |")
    return "\n".join(L) + "\n"


def apis_json(cat) -> str:
    """스킬이 기계적으로 읽는 축약본. 설명 전문은 meritz api show 로 본다."""
    out = []
    for a in cat["apis"]:
        out.append({
            "api_type": a["key"], "name": a["name"], "category": a["category"],
            "protocol": a["protocol"], "method": a["method"], "path": a["path"],
            "tr_id": a["tr_id"], "state_changing": is_state_changing(a),
            "params": [{"name": p["name"], "name_ko": p.get("name_ko"),
                        "required": bool(p.get("required")),
                        "description": clean(p.get("description") or "")[:400]}
                       for p in (a.get("request") or {}).get("params", [])],
        })
    return json.dumps({"generated": cat.get("generated"), "apis": out},
                      ensure_ascii=False, indent=1) + "\n"



def sync_skill_counts(cat):
    """SKILL.md 안의 건수를 카탈로그에 맞춘다.

    SKILL.md 는 손으로 쓰는 문서라 카탈로그가 늘어도 숫자가 따라오지 않는다.
    실제로 REST 가 41→62 로 늘었는데 설명문이 41 에 머물러 있었다.
    """
    rest = sum(1 for a in cat["apis"] if a.get("protocol") != "WEBSOCKET")
    ws = len(cat["apis"]) - rest
    changed = []
    for skill in NAMES:
        f = SKILLS / skill / "SKILL.md"
        if not f.exists():
            continue
        t = old = f.read_text(encoding="utf-8")
        t = re.sub(r"REST\s*\d+\s*건", f"REST {rest}건", t)
        t = re.sub(r"실시간\s*\d+\s*건", f"실시간 {ws}건", t)
        t = re.sub(r"\d+건 전체 목록", f"{rest + ws}건 전체 목록", t)
        if t != old:
            f.write_text(t, encoding="utf-8")
            changed.append(skill)
    return changed


def render() -> dict[str, str]:
    """생성할 내용을 파일로 쓰지 않고 돌려준다.

    테스트가 «지금 돌리면 같은 것이 나오는가» 를 확인할 때 쓴다. 예전에는
    테스트가 생성기를 실행해 작업트리를 덮어쓴 뒤 비교했다. 낡은 생성물이
    커밋돼 있어도 파일만 조용히 바뀌고 통과하는, 검사가 아니라 갱신이었다.
    """
    cat, fixes = load()
    return {
        "api-catalog.md": api_catalog_md(cat, fixes),
        "corrections.md": corrections_md(fixes),
        "glossary.md": glossary_md(cat),
        "apis.json": apis_json(cat),
    }


def main() -> int:
    cat, fixes = load()
    touched = sync_skill_counts(cat)
    files = render()
    for skill in NAMES:
        d = SKILLS / skill / "references"
        d.mkdir(parents=True, exist_ok=True)
        for name, body in files.items():
            (d / name).write_text(body, encoding="utf-8")
    print(f"생성 완료 — 스킬 {len(NAMES)}개 × {len(files)}개 문서 "
          f"(API {len(cat['apis'])}건 · 정정 {len(fixes.get('corrections', []))}건)")
    if touched:
        print("  SKILL.md 건수 갱신: " + ", ".join(touched))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
