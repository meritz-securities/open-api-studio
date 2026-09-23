"""meritz — 메리츠증권 Open API 명령줄 도구.

판정·안전 규칙은 이 파일에 없다. core 패키지가 담당한다.
CLI 가 하는 일은 인자를 모으고, 결과를 사람이 읽게 찍고, 종료코드를 정하는 것뿐이다.

종료코드
  0  성공          2  사용법 오류        3  업무 오류·호출 실패
  4  확인 필요(미리보기까지만 진행됨)
  5  주문 미접수(경고 확인 후 재전송 필요)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from . import __version__
from .confirm_store import FileConfirmStore, state_dir
from .core import safety
from .core.catalog import load_catalog
from .core.client import ApiClient, MeritzError, TokenManager
from .core.config import settings
from .core.search import CATEGORY_KO
from .core.search import search as search_apis

safety.set_confirm_store(FileConfirmStore())

EXIT_OK, EXIT_USAGE, EXIT_FAIL, EXIT_CONFIRM = 0, 2, 3, 4
EXIT_ORDER_REJECTED = 5      # 전송은 됐으나 접수되지 않았다 — 재전송이 필요하다


# ------------------------------------------------------------------ 출력
def out(obj: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))
    else:
        print(obj if isinstance(obj, str) else
              json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def err(msg: str) -> None:
    print(msg, file=sys.stderr)


def kv(pairs: list[str]) -> dict:
    """-p 이름=값 을 모은다. 값에 = 가 들어가도 첫 = 에서만 자른다."""
    d: dict[str, str] = {}
    for item in pairs or []:
        if "=" not in item:
            raise SystemExit(f"-p 는 이름=값 형식입니다: {item!r}")
        k, v = item.split("=", 1)
        k = k.strip()
        if not k:
            raise SystemExit(f"파라미터 이름이 비었습니다: {item!r}")
        if k in d:
            raise SystemExit(f"같은 파라미터를 두 번 넘겼습니다: {k}")
        d[k] = v
    return d


def need_api(cat, key: str):
    api = cat.get(key)
    if api:
        return api
    hits = search_apis(cat, key)[:5]
    tip = ("\n비슷한 것: " + ", ".join(h["api_type"] for h in hits)) if hits else ""
    raise SystemExit(f"모르는 api_type 입니다: {key}{tip}\n"
                     f"  meritz api list --query <키워드> 로 찾으세요.")


# ------------------------------------------------------------------ api
def cmd_api_list(a, cat) -> int:
    items = search_apis(cat, a.query or "", a.category) if (a.query or a.category) else [
        {"api_type": x.key, "name": x["name"], "category": x["category"],
         "method": x["method"], "path": x["path"], "protocol": x["protocol"]}
        for x in cat]
    if a.state_changing:
        items = [i for i in items if safety.is_state_changing(cat.get(i["api_type"]))]
    if a.read_only:
        items = [i for i in items if not safety.is_state_changing(cat.get(i["api_type"]))]
    if a.json:
        out(items, True)
        return EXIT_OK
    if not items:
        print("해당하는 API 가 없습니다.")
        return EXIT_OK
    for i in items:
        api = cat.get(i["api_type"])
        mark = "[!] " if safety.is_state_changing(api) else "    "
        proto = "WS  " if api.is_websocket else f"{api['method']:<4}"
        print(f"{mark}{i['api_type']:<28} {proto} {i['name']}")
    print(f"\n{len(items)}건  ([!] = 상태를 바꾸는 요청)")
    return EXIT_OK


def cmd_api_show(a, cat) -> int:
    api = need_api(cat, a.api_type)
    if a.json:
        out({"api": api.raw, "corrections": cat.corrections_for(api.key)}, True)
        return EXIT_OK
    print(f"{api.key}  —  {api['name']}")
    cate = api["category"]
    print(f"  분류   {CATEGORY_KO.get(cate, cate)}")
    if api.is_websocket:
        print(f"  방식   WebSocket · tr_cd={api['tr_id']}")
    else:
        print(f"  호출   {api['method']} {api['path']}")
        print(f"  tr_id  {api['tr_id']}")
    if safety.is_state_changing(api):
        print("  [!] 상태를 바꾸는 요청입니다. meritz order 로만 실행되며 확인이 필요합니다.")
    if api["description"]:
        print()
        for para in clean(api["description"]).splitlines():
            for line in _fold(para, 80):
                print(f"  {line}")
    req = api.params
    if req:
        print("\n요청 파라미터")
        for p in req:
            flag = "필수" if p.get("required") else "선택"
            print(f"  {flag}  {p['name']:<26} {p.get('name_ko') or ''}")
            for para in clean(p.get("description") or "").splitlines():
                for line in _fold(para, 74):
                    print(f"          {line}")
    # 응답 필드 설명이 없으면 조회 결과가 숫자 뭉치로만 보인다.
    res = [f for f in (api.get("response") or {}).get("body", [])
           if f["name"] not in ("data", "rsp_cd", "rsp_msg", "tr_cont", "tr_cont_key")]
    if res:
        shown = res if a.all else res[:12]
        print(f"\n응답 필드 ({len(res)}개)")
        for f in shown:
            print(f"  {f['name']:<26} {f.get('name_ko') or ''}")
            for para in clean(f.get("description") or "").splitlines():
                for line in _fold(para, 74):
                    print(f"          {line}")
        if len(shown) < len(res):
            print(f"  … 외 {len(res) - len(shown)}개. 전부 보려면 --all")

    for c in cat.corrections_for(api.key):
        print(f"\n* 응답 처리 참고사항 — {c.get('kind')}")
        if c.get("working_example"):
            print(f"   적용 예시: {c['working_example']}")
        if c.get("if_you_follow_the_portal"):
            print(f"   일반적인 처리 방식으로 호출하면: {c['if_you_follow_the_portal']}")
        # 원인만 찍고 끝내면 무엇을 해야 하는지 알 수 없다. 해결 방법을 반드시 붙인다.
        if c.get("workaround"):
            print(f"   이렇게 하십시오: {c['workaround']}")
        if c.get("caution"):
            print(f"   주의: {c['caution']}")
    return EXIT_OK


_TAGS = re.compile(r"<br\s*/?>|</?p>", re.I)
_ANY_TAG = re.compile(r"<[^>]+>")


def clean(text: str) -> str:
    """포털 설명에 섞인 HTML 을 사람이 읽을 문장으로 되돌린다."""
    t = _TAGS.sub("\n", text or "")
    t = _ANY_TAG.sub("", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    lines = [ln.strip() for ln in t.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def _fold(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ call
def _client(s, cat) -> ApiClient:
    degraded = {k for c in (cat.corrections.get("corrections") or []) if c.get("degraded")
                for k in c.get("keys", [])}
    return ApiClient(s, degraded_keys=degraded)


def cmd_call(a, cat) -> int:
    api = need_api(cat, a.api_type)
    if api.is_websocket:
        raise SystemExit(f"{api.key} 는 WebSocket 입니다. meritz ws {api.key} 를 쓰세요.")
    if safety.is_state_changing(api):
        raise SystemExit(
            f"{api.key} 는 상태를 바꾸는 요청이라 call 로는 실행하지 않습니다.\n"
            f"  meritz order {api.key} ... 를 쓰세요 (미리보기 후 확인).")
    s = settings()
    params = kv(a.param)
    for k in ("tr_cont", "tr_cont_key"):
        v = getattr(a, k)
        if v:
            params[k] = v
    try:
        res = _client(s, cat).call(api, params)
    except MeritzError as e:
        err(f"실패: {e}")
        if e.code:
            err(f"  코드 {e.code}")
        return EXIT_FAIL
    if not res.get("ok") and not a.json:
        # core 가 만든 사유를 버리면 0 으로 가득한 응답만 보고 이유를 알 수 없다.
        err(f"{res.get('error')} — {res.get('message') or ''}".rstrip(" —"))
        if res.get("note"):
            err(f"  {res['note']}")
    # 실패 응답의 본문은 게이트웨이가 돌려준 원문일 수 있다(프록시 HTML 등).
    # 중간 장비 이름과 내부 주소가 섞여 나오므로 사람용 출력에서는 뺀다.
    body = res.get("body")
    if not res.get("ok") and not isinstance(body, (dict, list)):
        body = None
    out(res if a.json else body, a.json)
    if not a.json and res.get("ok"):
        if res.get("warning"):
            err(f"\n[주의] {res['warning']}")
        if res.get("note"):
            err(f"\n{res['note']}")
    return EXIT_OK if res.get("ok") else EXIT_FAIL


# ------------------------------------------------------------------ order
def cmd_order(a, cat) -> int:
    api = need_api(cat, a.api_type)
    if not safety.is_state_changing(api):
        raise SystemExit(f"{api.key} 는 조회입니다. meritz call 을 쓰세요.")
    s = settings()
    if s.read_only:
        out(safety.blocked(api), a.json)
        return EXIT_FAIL
    params = kv(a.param)
    problems = ApiClient.validate(api, params)
    if problems:
        err("요청이 명세와 다릅니다:")
        for p in problems:
            err(f"  - {p}")
            # 값이 정해져 있는 필수 항목은 무엇을 넣어야 하는지까지 알려준다.
            name = p.rsplit(":", 1)[-1].split("(")[0].strip()
            hint = _fixed_value_hint(api, name)
            if hint:
                err(f"      → {hint}")
        err(f"\n  meritz api show {api.key} 로 필수 항목을 확인하세요.")
        return EXIT_USAGE
    body = api.body_params(params)

    if not a.confirm:
        # 앱키까지 지문에 넣는다 — CLI 는 미리보기와 전송이 다른 프로세스라
        # 그 사이 앱키(=계좌)가 바뀌면 확인한 것과 다른 계좌로 나간다.
        pv = safety.preview(api, body, s.base_url, s.app_key)
        if a.json:
            out(pv, True)
        else:
            print("전송하지 않았습니다. 아래 내용을 확인하세요.\n")
            print(f"  {pv['will_send']['method']} {pv['will_send']['url']}")
            print(f"  tr_id {pv['will_send']['tr_id']}")
            print("  본문")
            for k, v in body.items():
                p = api.param(k) or {}
                print(f"    {k:<24} {v!r}   {p.get('name_ko') or ''}")
            print(f"\n  {pv['note']}")
            print(f"\n실제로 보내려면 {pv['expires_in_sec']}초 안에")
            print(f"  meritz order {api.key} … --confirm {pv['confirm_token']}")
        return EXIT_CONFIRM

    # 확인 게이트는 ApiClient.call() 안에 있다. 여기서 따로 검사하지 않는다 —
    # 토큰은 1회용이라 두 번 보면 두 번째가 실패한다.
    try:
        res = _client(s, cat).call(api, {**params, "confirm_token": a.confirm})
    except MeritzError as e:
        if e.code == "NEEDS_CONFIRMATION":
            err(f"전송하지 않았습니다: {e}")
            return EXIT_CONFIRM
        err(f"실패: {e}")
        return EXIT_FAIL
    if res.get("error") == "ORDER_NOT_ACCEPTED":
        # 데이터보다 먼저 찍는다 — 뒤에 두면 스크롤에 묻힌다.
        err(f"[!] {res['message']}\n")
    # 실패 응답의 본문은 게이트웨이가 돌려준 원문일 수 있다(프록시 HTML 등).
    # 중간 장비 이름과 내부 주소가 섞여 나오므로 사람용 출력에서는 뺀다.
    body = res.get("body")
    if not res.get("ok") and not isinstance(body, (dict, list)):
        body = None
    out(res if a.json else body, a.json)
    # 판정은 core 가 한다 — --json 이든 아니든 같은 결론이 나와야 한다.
    if res.get("error") == "ORDER_NOT_ACCEPTED":
        return EXIT_ORDER_REJECTED
    if not a.json and res.get("note"):
        err(f"\n{res['note']}")
    return EXIT_OK if res.get("ok") else EXIT_FAIL


def _fixed_value_hint(api, name: str) -> str | None:
    """설명에 "…을 넣습니다" 로 값이 못박힌 필수 항목을 그대로 안내한다.

    신규 주문의 orgl_oder_no·whol_rctf_cncl_yn 처럼, 필수지만 값이 정해진
    항목이 있다. 이름만 보고는 왜 필요한지 알 수 없어 막히기 쉽다.
    """
    p = api.param(name) or {}
    d = clean(p.get("description") or "")
    # \b 를 쓰면 안 된다 — "0을" 처럼 뒤에 한글이 붙으면 단어 경계가 서지 않는다.
    m = re.search(r'("[^"]{1,12}"|(?<![0-9A-Za-z])[0-9]{1,3}(?![0-9]))\s*을?를?\s*넣습니다', d)
    return d if m else None



# ------------------------------------------------------------------ skills
_SKILL_HOMES = {
    "claude-code": "~/.claude/skills",
    "claude-desktop": "~/Library/Application Support/Claude/skills",
}


def _bundled_skills() -> list:
    """패키지에 동봉된 스킬 폴더. 저장소에서 실행할 때도 찾는다."""
    import pathlib
    here = pathlib.Path(__file__).resolve().parent
    for base in (here / "skills", here.parent / "skills"):
        if base.is_dir():
            return sorted(p for p in base.iterdir() if (p / "SKILL.md").is_file())
    return []


def cmd_skills(a, cat) -> int:
    import pathlib
    import shutil

    found = _bundled_skills()
    if not found:
        err("동봉된 스킬을 찾지 못했습니다. 저장소에서 실행하거나 다시 설치해 주세요.")
        return EXIT_FAIL

    if a.sub == "list":
        for p in found:
            print(f"  {p.name}")
        print("\n설치하려면  meritz skills install")
        return EXIT_OK

    target = pathlib.Path(a.to or _SKILL_HOMES.get(a.tool, "~/.claude/skills")).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    for src in found:
        dst = target / src.name
        if dst.exists() and not a.force:
            print(f"  건너뜀 {src.name} — 이미 있습니다 (--force 로 덮어씁니다)")
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"  설치 {src.name}")
    print(f"\n위치 {target}")
    print("에이전트를 다시 시작하면 스킬이 잡힙니다.")
    return EXIT_OK


# ------------------------------------------------------------------ ws
def cmd_ws(a, cat) -> int:
    api = need_api(cat, a.api_type)
    if not api.is_websocket:
        raise SystemExit(f"{api.key} 는 WebSocket 이 아닙니다. meritz call 을 쓰세요.")
    try:
        import websocket  # noqa: F401
    except ImportError:
        raise SystemExit(
            "websocket-client 가 필요합니다:  pip install websocket-client") from None
    import websocket as ws

    s = settings()
    token = TokenManager(s).get()
    # token 은 "Bearer " 를 붙이고 body 는 평면이다.
    # 인증은 접속이 아니라 이 구독 메시지에서 이뤄진다.
    body = {"tr_cd": api["tr_id"]}
    if a.tr_key:
        body["tr_key"] = a.tr_key
    sub = {"header": {"token": f"Bearer {token}", "tr_type": "1"}, "body": body}
    # HTTP 읽기 타임아웃을 그대로 쓰면 거래가 뜸한 종목에서 스트림이 끊긴다.
    # 유휴 대기는 별도 값으로 둔다 (--idle, 0 이면 무한 대기).
    try:
        conn = ws.create_connection(s.ws_url,
                                    timeout=(a.idle if a.idle > 0 else None))
    except Exception as e:
        # 대개 MERITZ_BASE_URL 만 바꾸고 MERITZ_WS_URL 을 안 바꾼 경우다.
        # 토큰은 한 서버에서 받고 구독은 다른 서버로 나간다.
        err(f"실시간 접속 실패: {s.ws_url} — {type(e).__name__}. "
            "MERITZ_BASE_URL 을 바꾸셨다면 MERITZ_WS_URL 도 함께 바꾸십시오.")
        return EXIT_FAIL
    conn.send(json.dumps(sub))
    got = 0
    try:
        while a.count == 0 or got < a.count:
            try:
                msg = conn.recv()
            except ws.WebSocketTimeoutException:
                err(f"{a.idle}초 동안 수신이 없습니다. 장 시간과 tr_key 를 확인하세요.")
                break
            except ws.WebSocketConnectionClosedException:
                err("연결이 끊겼습니다. 이 도구는 재연결하지 않습니다.")
                return EXIT_FAIL
            except OSError as e:
                err(f"수신 중 오류: {e}")
                return EXIT_FAIL
            if not msg:
                continue
            try:
                d = json.loads(msg)
            except ValueError:
                print(msg)
                continue
            head = d.get("header") or {}
            if "rsp_cd" in head or "rt_cd" in head:      # 구독 응답(ACK)
                code = head.get("rsp_cd") or head.get("rt_cd")
                msg = head.get("rsp_msg") or ""
                if code not in ("00000", "0000"):
                    err(f"구독 실패 {api['tr_id']}: {code} {msg}")
                    return EXIT_FAIL
                err(f"구독 완료 — {api['tr_id']}  {msg}")
                continue
            if "rsp_cd" in d and "body" not in d:        # 봉투 없이 오는 오류
                err(f"구독 실패 {api['tr_id']}: {d.get('rsp_cd')} {d.get('rsp_msg') or ''}")
                return EXIT_FAIL
            out(d, a.json)
            got += 1
    except KeyboardInterrupt:
        pass
    finally:
        try:                                   # 구독 해지를 알리고 닫는다
            conn.send(json.dumps({"header": {"tr_type": "2"},
                                  "body": {"tr_cd": api["tr_id"]}}))
        except Exception:
            pass
        conn.close()
    if got == 0:
        return EXIT_FAIL
    return EXIT_OK


# ------------------------------------------------------------------ token / doctor
def cmd_token(a, cat) -> int:
    s = settings()
    try:
        t = TokenManager(s).get()
    except MeritzError as e:
        err(f"토큰 발급 실패: {e}")
        return EXIT_FAIL
    print(f"발급 성공  {t[:12]}…  ({s.env} · {s.base_url})")
    return EXIT_OK


def cmd_doctor(a, cat) -> int:
    s = settings()
    print(f"meritz {__version__}")
    print(f"  서버      {s.env}  {s.base_url}")
    print(f"  WebSocket {s.ws_url}")
    print(f"  자격증명  {'있음' if s.has_credentials else '없음 — MERITZ_APP_KEY/APP_SECRET 필요'}")
    print(f"  조회전용  {'예' if s.read_only else '아니오'}")
    print(f"  상태파일  {state_dir()}")
    print(f"  카탈로그  {len(cat)}건  (기준 {cat.generated or '?'})")
    n = len(cat.corrections.get("corrections") or [])
    print(f"  포털 정정 {n}건" + ("  — meritz api show 에서 해당 API 에 표시됩니다" if n else ""))
    if not s.has_credentials:
        return EXIT_FAIL
    return cmd_token(a, cat)


# ------------------------------------------------------------------ 진입점
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="meritz", description="메리츠증권 Open API 명령줄 도구")
    p.add_argument("--version", action="version", version=f"meritz {__version__}")
    # --json 은 하위 명령 앞뒤 어디에 써도 통하게 한다.
    jsonopt = argparse.ArgumentParser(add_help=False)
    jsonopt.add_argument("--json", action="store_true", help="결과를 JSON 으로 출력")
    p.add_argument("--json", action="store_true", help="결과를 JSON 으로 출력")
    sub = p.add_subparsers(dest="cmd", required=True)

    api = sub.add_parser("api", help="API 목록·명세 확인").add_subparsers(
        dest="sub", required=True)
    ls = api.add_parser("list", help="API 목록", parents=[jsonopt])
    ls.add_argument("--query", "-q", help="검색어 (한글 표현 가능)")
    ls.add_argument("--category", "-c", help="분류로 좁히기")
    ls.add_argument("--state-changing", action="store_true", help="주문·환전만")
    ls.add_argument("--read-only", action="store_true", help="조회만")
    ls.set_defaults(fn=cmd_api_list)
    sh = api.add_parser("show", help="한 API 의 명세", parents=[jsonopt])
    sh.add_argument("api_type")
    sh.add_argument("--all", action="store_true", help="응답 필드를 전부 보여준다")
    sh.set_defaults(fn=cmd_api_show)

    c = sub.add_parser("call", help="조회 API 호출", parents=[jsonopt])
    c.add_argument("api_type")
    c.add_argument("-p", "--param", action="append", metavar="이름=값")
    c.add_argument("--tr-cont", dest="tr_cont", help="연속조회 플래그")
    c.add_argument("--tr-cont-key", dest="tr_cont_key", help="연속조회 키")
    c.set_defaults(fn=cmd_call)

    o = sub.add_parser("order", help="주문·환전 (미리보기 → 확인 → 전송)", parents=[jsonopt])
    o.add_argument("api_type")
    o.add_argument("-p", "--param", action="append", metavar="이름=값")
    o.add_argument("--confirm", metavar="토큰",
                   help="미리보기에서 받은 토큰. 없으면 전송하지 않는다")
    o.set_defaults(fn=cmd_order)

    w = sub.add_parser("ws", help="실시간 구독", parents=[jsonopt])
    w.add_argument("api_type")
    w.add_argument("--tr-key", dest="tr_key", help="종목코드 등 구독 키")
    w.add_argument("--count", type=int, default=10, help="이만큼 받고 끝낸다 (0=계속)")
    w.add_argument("--idle", type=int, default=30, metavar="초",
                   help="이 시간 동안 수신이 없으면 끝낸다 (0=무한 대기)")
    w.set_defaults(fn=cmd_ws)

    sk = sub.add_parser("skills", help="에이전트 스킬 설치").add_subparsers(
        dest="sub", required=True)
    sk.add_parser("list", help="동봉된 스킬 보기").set_defaults(fn=cmd_skills)
    ins = sk.add_parser("install", help="에이전트가 읽는 위치에 복사")
    ins.add_argument("--tool", default="claude-code",
                     choices=sorted(_SKILL_HOMES), help="설치 대상 (기본 claude-code)")
    ins.add_argument("--to", help="직접 경로 지정")
    ins.add_argument("--force", action="store_true", help="이미 있으면 덮어쓴다")
    ins.set_defaults(fn=cmd_skills)

    sub.add_parser("token", help="토큰 발급 확인").set_defaults(fn=cmd_token)
    sub.add_parser("doctor", help="설정·연결 점검").set_defaults(fn=cmd_doctor)
    return p


def _widen_console() -> None:
    """콘솔이 UTF-8 이 아니어도 죽지 않게 한다.

    콘솔이 UTF-8 이 아니면 표식 문자에서 UnicodeEncodeError 가 난다.
    출력이 조금 깨지는 편이 낫다.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _widen_console()
    argv = list(sys.argv[1:] if argv is None else argv)
    # --json 을 하위 명령 앞에 쓰면 서브파서 기본값(False)이 덮어쓴다.
    # 어디에 써도 같은 결과가 나와야 한다.
    top_json = "--json" in argv
    a = build_parser().parse_args(argv)
    if top_json:
        a.json = True
    for k in ("query", "category", "state_changing", "read_only", "param",
              "tr_cont", "tr_cont_key", "confirm", "tr_key", "count", "all",
              "idle", "sub", "tool", "to", "force"):
        if not hasattr(a, k):
            setattr(a, k, None)
    try:
        cat = load_catalog()
    except (FileNotFoundError, ValueError) as e:
        err(str(e))
        return EXIT_FAIL
    try:
        return a.fn(a, cat)
    except MeritzError as e:
        # 파이썬 트레이스백은 고객에게 "도구가 깨졌다" 로 읽히고 내부 경로를 노출한다.
        err(f"실패: {e}")
        if getattr(e, "code", None):
            err(f"  코드 {e.code}")
        return EXIT_FAIL
    except ValueError as e:
        # 환경변수 값이 잘못되면 settings() 가 여기로 올린다. 트레이스백이
        # 나가면 고객에게는 "도구가 깨졌다" 로 읽히고 내부 경로가 드러난다.
        err(f"설정을 읽지 못했습니다: {e}")
        return EXIT_USAGE
    except OSError as e:
        err(f"연결하지 못했습니다: {e}")
        return EXIT_FAIL
    except SystemExit as e:
        if isinstance(e.code, str):
            err(e.code)
            return EXIT_USAGE
        raise
    except KeyboardInterrupt:
        return EXIT_FAIL
