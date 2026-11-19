"""CLI 계약. 네트워크 없이 확인할 수 있는 것을 지킨다."""
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MERITZ_CATALOG", str(ROOT / "meritz_studio" / "data" / "catalog.json"))
os.environ.setdefault("MERITZ_NO_ENV_FILE", "1")

from meritz_studio import cli  # noqa: E402
from meritz_studio.core import safety  # noqa: E402
from meritz_studio.core.catalog import load_catalog  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("MERITZ_STATE_DIR", str(tmp_path))
    # 기본값은 조회 전용이다. 이 파일은 확인 게이트 자체를 확인하므로
    # 주문을 열어 둔 상태에서 돌린다. 기본값 검증은 아래 전용 테스트가 한다.
    monkeypatch.setenv("MERITZ_READ_ONLY", "0")
    from meritz_studio.confirm_store import FileConfirmStore
    safety.set_confirm_store(FileConfirmStore(tmp_path / "pending.json"))


@pytest.fixture(scope="module")
def cat():
    return load_catalog()


# --------------------------------------------------------------- 인자 파싱
def test_param_requires_name_equals_value():
    with pytest.raises(SystemExit):
        cli.kv(["iscd"])


def test_param_keeps_equals_inside_value():
    assert cli.kv(["q=a=b"]) == {"q": "a=b"}


def test_duplicate_param_is_rejected():
    """같은 이름을 두 번 넘기면 어느 쪽이 갈지 알 수 없다 — 조용히 덮지 않는다."""
    with pytest.raises(SystemExit):
        cli.kv(["odqt=1", "odqt=100"])


def test_empty_param_name_is_rejected():
    with pytest.raises(SystemExit):
        cli.kv(["=5"])


def test_json_flag_works_after_subcommand():
    a = cli.build_parser().parse_args(["call", "deposit", "--json"])
    assert a.json is True


# --------------------------------------------------------------- 게이트
def test_call_refuses_state_changing(cat, capsys):
    with pytest.raises(SystemExit) as e:
        cli.cmd_call(cli.build_parser().parse_args(["call", "orders_buy"]), cat)
    assert "order" in str(e.value)


def test_order_refuses_read_only_api(cat):
    with pytest.raises(SystemExit) as e:
        cli.cmd_order(cli.build_parser().parse_args(["order", "deposit"]), cat)
    assert "조회" in str(e.value)


def test_call_refuses_websocket(cat):
    ws = cat.websockets()[0]
    with pytest.raises(SystemExit) as e:
        cli.cmd_call(cli.build_parser().parse_args(["call", ws.key]), cat)
    assert "WebSocket" in str(e.value)


def test_unknown_api_type_suggests_alternatives(cat):
    with pytest.raises(SystemExit) as e:
        cli.need_api(cat, "잔고")
    assert "api list" in str(e.value)


# --------------------------------------------------------------- 확인 토큰
def _order_args(**kw):
    p = ["order", "fx_exchanges"]
    for k, v in kw.items():
        p += ["-p", f"{k}={v}"]
    return cli.build_parser().parse_args(p)


FX = dict(mnec_clcd="1", wncr_amt="0", frcr_amt="10",
          exrt_stnd_time="100000", iqry_exrt="1400", crcd="USD")


def test_preview_does_not_send_and_returns_confirm_exit(cat, capsys):
    code = cli.cmd_order(_order_args(**FX), cat)
    assert code == cli.EXIT_CONFIRM
    assert "전송하지 않았습니다" in capsys.readouterr().out


def test_forged_token_is_rejected(cat, capsys):
    cli.cmd_order(_order_args(**FX), cat)
    a = _order_args(**FX)
    a.confirm = "0" * 16
    assert cli.cmd_order(a, cat) == cli.EXIT_CONFIRM
    assert "유효하지" in capsys.readouterr().err


def test_changed_body_invalidates_token(cat, capsys):
    cli.cmd_order(_order_args(**FX), cat)
    token = _token_from(capsys)
    changed = dict(FX, frcr_amt="99999")
    a = _order_args(**changed)
    a.confirm = token
    assert cli.cmd_order(a, cat) == cli.EXIT_CONFIRM
    assert "다릅니다" in capsys.readouterr().err


def test_token_survives_a_new_process_view(cat, capsys, tmp_path):
    """미리보기와 전송이 다른 프로세스여도 토큰이 살아 있어야 한다."""
    cli.cmd_order(_order_args(**FX), cat)
    token = _token_from(capsys)
    from meritz_studio.confirm_store import FileConfirmStore
    fresh = FileConfirmStore(tmp_path / "pending.json")
    assert fresh.get(token) is not None


def test_state_file_is_not_world_readable(cat, capsys, tmp_path):
    cli.cmd_order(_order_args(**FX), cat)
    _token_from(capsys)
    mode = (tmp_path / "pending.json").stat().st_mode & 0o077
    assert mode == 0, "주문 내용을 담은 파일이 다른 사용자에게 열려 있습니다"


def _token_from(capsys) -> str:
    out = capsys.readouterr().out
    line = [x for x in out.splitlines() if "--confirm" in x][0]
    return line.split("--confirm")[1].strip()


def test_missing_required_is_usage_error(cat, capsys):
    a = cli.build_parser().parse_args(["order", "fx_exchanges", "-p", "crcd=USD"])
    assert cli.cmd_order(a, cat) == cli.EXIT_USAGE
    assert "필수 파라미터 누락" in capsys.readouterr().err


# --------------------------------------------------------------- 표시
def test_show_strips_html_from_description():
    assert "<br" not in cli.clean('실시간<br/>지연')
    assert cli.clean("a<br/>b") == "a\nb"


def test_show_marks_state_changing(cat, capsys):
    cli.cmd_api_show(cli.build_parser().parse_args(["api", "show", "orders_buy"]), cat)
    assert "상태를 바꾸는" in capsys.readouterr().out


def test_show_surfaces_portal_corrections(cat, capsys):
    """포털 예시를 그대로 쓰면 실패하는 API 는 명세를 볼 때 알려야 한다.

    대상 API 를 이름으로 박아 두지 않는다. 2026-09-11 재검증에서 포털이 고친
    항목을 corrections.json 에서 빼자 ovs_market_plrices 를 박아 둔 이 검사가
    깨졌다 — 정정 목록이 줄어드는 것은 정상이므로, 지금 남아 있는 항목 중
    아무거나 골라 «표시가 되는가» 만 본다.
    """
    keys = [k for c in (cat.corrections.get("corrections") or [])
            for k in c.get("keys", []) if cat.get(k) is not None]
    assert keys, "정정 항목이 하나도 없습니다 — corrections.json 을 확인하세요"
    cli.cmd_api_show(cli.build_parser().parse_args(["api", "show", keys[0]]), cat)
    assert "응답 처리 참고사항" in capsys.readouterr().out


def test_list_state_changing_matches_safety(cat, capsys):
    cli.cmd_api_list(
        cli.build_parser().parse_args(["api", "list", "--state-changing", "--json"]), cat)
    keys = {i["api_type"] for i in json.loads(capsys.readouterr().out)}
    assert keys == {a.key for a in cat if safety.is_state_changing(a)}
    assert keys, "상태변경 API 가 하나도 안 잡히면 게이트가 죽은 것이다"


def test_fixed_value_hint_covers_new_order_fields(cat):
    """신규 주문의 필수지만 값이 정해진 항목은 무엇을 넣을지까지 알려야 한다."""
    api = cat.get("orders_buy")
    for name in ("orgl_oder_no", "whol_rctf_cncl_yn"):
        hint = cli._fixed_value_hint(api, name)
        assert hint, f"{name} 안내가 나오지 않습니다"
        assert "넣습니다" in hint


def test_fixed_value_hint_is_silent_when_value_is_not_fixed(cat):
    assert cli._fixed_value_hint(cat.get("orders_buy"), "iscd") is None


# --------------------------------------------------------------- 예제
def test_examples_use_only_declared_field_names(cat):
    """예제가 없는 필드를 읽으면 화면에 None 이 찍힌다.

    예제는 고객이 가장 먼저 복사해 가는 코드다. 여기서 틀린 필드명이
    나가면 그대로 퍼진다.
    """
    import ast
    import re as _re

    examples = sorted((ROOT / "examples").glob("*.py"))
    assert examples, "예제가 하나도 없습니다"

    declared = set()
    for api in cat:
        for sec in ("request", "response"):
            groups = api.get(sec) or {}
            for lst in (groups.values() if isinstance(groups, dict) else []):
                # 필드 목록이 아닌 절은 건너뛴다.
                #   response.containers 는 {"data": {...}} 형태의 매핑이라
                #   그대로 순회하면 문자열 키가 나와 f["name"] 에서 터진다.
                if not isinstance(lst, list):
                    continue
                declared |= {f["name"] for f in lst if isinstance(f, dict)}
    # 봉투 키는 필드가 아니다.
    declared |= {"data", "rsp_cd", "rsp_msg", "tr_cont", "tr_cont_key",
                 "header", "body", "input"}

    snake = _re.compile(r"^[a-z][a-z0-9_]{3,}$")
    for path in examples:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # 응답을 담은 이름에서 꺼내는 것만 본다 —
            # cat.get("market_prices") 같은 카탈로그 조회는 필드가 아니다.
            recv = getattr(node.func, "value", None) if isinstance(
                getattr(node, "func", None), ast.Attribute) else None
            recv_name = recv.id if isinstance(recv, ast.Name) else ""
            if recv_name not in ("data", "body", "row", "d", "b", "head", "msg"):
                continue
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get" and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                name = node.args[0].value
                if snake.match(name) and name not in declared:
                    pytest.fail(f"{path.name}: 카탈로그에 없는 필드 {name!r} 를 읽습니다")


# --------------------------------------------------------------- 주문 미접수
_WARNED = {
    "rsp_cd": "0001", "rsp_msg": "주문이 완료되었습니다.",
    "data": {"oder_no": 140, "warn_cls_code": "c",
             "warn_msg": "위탁증거금 부족 종목입니다."},
}


@pytest.fixture
def sent(monkeypatch, cat):
    """전송 단계를 가로챈다 — 무엇이 어디로 나갔는지 본다. 실제로 보내지 않는다."""
    seen = {}

    def fake_call(self, api, params):
        from meritz_studio.core.client import ApiClient
        # 게이트를 건너뛰지 않는다. 가짜가 게이트까지 흉내 내면,
        # 게이트가 빠져도 이 시험은 통과해 버린다.
        self.require_confirmation(api, params)
        seen["api"] = api.key
        seen["base_url"] = self.s.base_url
        seen["params"] = dict(params)
        return ApiClient.judge(api, 200, seen.get("reply", _WARNED),
                               self.s.base_url + api["path"])

    monkeypatch.setattr("meritz_studio.core.client.ApiClient.call", fake_call)
    return seen


def _confirmed_order(cat, capsys, **kw):
    cli.cmd_order(_order_args(**FX), cat)
    token = _token_from(capsys)
    a = _order_args(**FX)
    a.confirm = token
    for k, v in kw.items():
        setattr(a, k, v)
    return a


@pytest.mark.parametrize("as_json", [False, True], ids=["사람용", "--json"])
def test_unaccepted_order_is_never_reported_as_success(cat, capsys, sent, as_json):
    """--json 에서도 접수되지 않은 주문은 실패로 보고돼야 한다."""
    a = _confirmed_order(cat, capsys, json=as_json)
    code = cli.cmd_order(a, cat)
    captured = capsys.readouterr()
    assert code == cli.EXIT_ORDER_REJECTED, "성공 종료코드로 나갑니다"
    assert "접수되지 않았습니다" in captured.err
    assert "warn_cnfr_yn" in captured.err
    if as_json:
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert payload["error"] == "ORDER_NOT_ACCEPTED"
        assert "주문이 접수됐습니다" not in json.dumps(payload, ensure_ascii=False)


def test_order_sends_to_the_server_shown_in_the_preview(cat, capsys, sent, monkeypatch):
    """미리보기 서버와 전송 서버가 다르면 거절해야 한다."""
    monkeypatch.setenv("MERITZ_BASE_URL", "https://example.invalid:9443")
    a = _confirmed_order(cat, capsys)
    cli.cmd_order(a, cat)
    assert sent.get("base_url") == "https://example.invalid:9443"


def test_token_from_another_server_is_rejected(cat, capsys, sent, monkeypatch):
    monkeypatch.setenv("MERITZ_BASE_URL", "https://example.invalid:9443")
    a = _confirmed_order(cat, capsys)
    monkeypatch.delenv("MERITZ_BASE_URL")           # 기본값 = 운영
    assert cli.cmd_order(a, cat) == cli.EXIT_CONFIRM
    assert "sent" not in sent or not sent, "전송 단계까지 갔습니다"


def test_token_cannot_be_computed_without_a_preview():
    """미리보기를 건너뛰고 토큰을 지어낼 수 없어야 한다."""
    from meritz_studio.core.safety import _fingerprint
    body, base = {"odqt": "9999"}, "https://openapi.imeritz.com:9443"
    guess = _fingerprint("orders_buy", body, base)
    assert safety.check_confirm("orders_buy", body, guess, base) is not None

    real = safety.issue_confirm_token("orders_buy", body, base)
    assert real != guess, "토큰이 지문 그대로면 계산해서 만들 수 있습니다"
    assert safety.check_confirm("orders_buy", body, real, base) is None


def test_output_survives_a_narrow_console(cat, capsys, monkeypatch):
    """콘솔이 UTF-8 이 아니어도 출력이 깨질지언정 죽지 않아야 한다."""
    cli.cmd_api_list(cli.build_parser().parse_args(
        ["api", "list", "--state-changing"]), cat)
    text = capsys.readouterr().out
    text.encode("cp949", errors="strict")     # 예외가 나면 실패


def test_concurrent_previews_do_not_lose_tokens(tmp_path, monkeypatch):
    """동시에 발급한 토큰이 서로를 덮어쓰지 않아야 한다."""
    import threading

    from meritz_studio.confirm_store import FileConfirmStore
    store = FileConfirmStore(tmp_path / "pending.json")
    safety.set_confirm_store(store)

    tokens, errors = [], []

    def issue(i):
        try:
            tokens.append(safety.issue_confirm_token("orders_buy", {"n": i}, "https://x"))
        except Exception as e:            # 잠금 도입으로 새 예외가 나면 잡는다
            errors.append(e)

    threads = [threading.Thread(target=issue, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert len(tokens) == 50
    survived = [t for t in tokens if store.get(t) is not None]
    assert len(survived) == 50, f"{50 - len(survived)}건이 사라졌습니다"


def test_lock_file_is_not_world_readable(tmp_path):
    from meritz_studio.confirm_store import FileConfirmStore
    store = FileConfirmStore(tmp_path / "pending.json")
    store.put("t", "f", 9e9)
    if store.lock_path.exists():
        assert store.lock_path.stat().st_mode & 0o077 == 0


# --------------------------------------------------------------- 스킬 설치
def test_bundled_skills_are_found():
    """설치된 패키지에서도 스킬을 찾아야 한다. 못 찾으면 install 이 무용지물이다."""
    found = cli._bundled_skills()
    names = {p.name for p in found}
    assert names == {"meritz-openapi-codegen", "meritz-openapi-trading"}, names


def test_skills_install_copies_and_is_idempotent(tmp_path, capsys):
    a = cli.build_parser().parse_args(
        ["skills", "install", "--to", str(tmp_path)])
    assert cli.cmd_skills(a, None) == cli.EXIT_OK
    for name in ("meritz-openapi-codegen", "meritz-openapi-trading"):
        assert (tmp_path / name / "SKILL.md").is_file()

    # 두 번째는 덮어쓰지 않는다 — 사용자가 고친 스킬을 날리면 안 된다
    cli.cmd_skills(a, None)
    assert "건너뜀" in capsys.readouterr().out


def test_skills_install_force_overwrites(tmp_path):
    a = cli.build_parser().parse_args(
        ["skills", "install", "--to", str(tmp_path), "--force"])
    cli.cmd_skills(a, None)
    marker = tmp_path / "meritz-openapi-trading" / "SKILL.md"
    marker.write_text("고쳐 둔 내용", encoding="utf-8")
    cli.cmd_skills(a, None)
    assert marker.read_text(encoding="utf-8") != "고쳐 둔 내용"


# ------------------------------------------- 주문 미접수 판정 (보류값이 새지 않게)
#
# 문서·스킬·예제가 한때 "11개 목록에 걸릴 때만 미접수" 로 적혀 있었다.
# 그 목록은 **재전송하면 풀리는 값**이라 보류·거절값(국내 2·5·8·b·e·h, 해외 2)이
# 성공으로 통과했다. 판정 기준은 목록이 아니라 "0 인가" 다.
from meritz_studio.core.client import _RESEND_OK, _warn_scheme, _warning_row  # noqa: E402

_HOLD = {"domestic": list("258beh"), "overseas": ["2", "4", "9"]}


def _order_body(code):
    return {"rsp_cd": "0001", "rsp_msg": "주문이 완료되었습니다.",
            "data": {"oder_no": 140, "warn_cls_code": code,
                     "warn_msg": "확인이 필요합니다."}}


@pytest.mark.parametrize("scheme", ["domestic", "overseas"])
@pytest.mark.parametrize("code", ["0"])
def test_warn_zero_is_accepted(scheme, code):
    assert _warning_row(_order_body(code), scheme) is None


@pytest.mark.parametrize("scheme,code", [(s, c) for s, v in _HOLD.items() for c in v])
def test_hold_codes_are_not_accepted_and_not_resendable(scheme, code):
    """보류·거절값. 재전송해도 접수되지 않으므로 성공으로 넘기면 안 된다."""
    row = _warning_row(_order_body(code), scheme)
    assert row is not None, f"{scheme} {code!r} 가 성공으로 새어 나갑니다"
    assert row[0] == code
    assert row[2] is False, f"{scheme} {code!r} 는 재전송으로 풀리지 않습니다"


@pytest.mark.parametrize("scheme,code",
                         [(s, c) for s, v in _RESEND_OK.items() for c in sorted(v)])
def test_resendable_codes_are_not_accepted_but_resendable(scheme, code):
    row = _warning_row(_order_body(code), scheme)
    assert row is not None and row[2] is True


def test_overseas_does_not_borrow_domestic_codes():
    """국내·해외는 코드 체계가 다르다. 국내 목록을 해외에 쓰면 오판한다."""
    for code in sorted(_RESEND_OK["domestic"] - _RESEND_OK["overseas"]):
        row = _warning_row(_order_body(code), "overseas")
        assert row is not None and row[2] is False, f"해외 {code!r}"


@pytest.mark.parametrize("shape", ["top", "list"])
def test_warning_is_caught_in_every_response_shape(shape):
    """단건 dict·배열·최상위 — 한 형태만 보면 나머지에서 샌다."""
    warn = {"warn_cls_code": "2", "warn_msg": "보류"}
    body = {"rsp_cd": "0001", **({"data": [warn]} if shape == "list" else warn)}
    assert _warning_row(body, "domestic") is not None


def test_warn_scheme_follows_the_path():
    assert _warn_scheme({"path": "/overseas/order/v1/orders"}) == "overseas"
    assert _warn_scheme({"path": "/domestic/order/v1/orders"}) == "domestic"


def test_example_order_code_rejects_hold_codes():
    """examples/03 은 에이전트가 베끼는 코드다 — 여기서 새면 실계좌로 샌다."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_ex03", ROOT / "examples" / "03_order_with_confirm.py")
    ex = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ex)

    ex.check_not_accepted(_order_body("0"), "domestic")        # 접수 — 통과해야 한다
    for code in _HOLD["domestic"]:
        with pytest.raises(ex.OrderNotAccepted) as e:
            ex.check_not_accepted(_order_body(code), "domestic")
        assert e.value.resendable is False
    with pytest.raises(ex.OrderNotAccepted) as e:
        ex.check_not_accepted(_order_body("c"), "domestic")
    assert e.value.resendable is True
    with pytest.raises(ex.OrderNotAccepted) as e:
        ex.check_not_accepted(_order_body("2"), "overseas")
    assert e.value.resendable is False


# ------------------------------------------------- 안전 스위치 기본값
def test_default_is_read_only(monkeypatch):
    """아무것도 설정하지 않으면 주문이 나가지 않아야 한다.

    이 저장소는 CLI 와 함께 AI 에이전트용 스킬을 동봉한다. 명령을 치는 것이
    늘 사람이라고 볼 수 없고, 모의계좌가 없어 앱키에 묶인 계좌는 언제나
    실계좌다. 기본값이 유일한 완충재라 회귀하면 안 된다.
    """
    from meritz_studio.core.config import settings

    monkeypatch.delenv("MERITZ_READ_ONLY", raising=False)
    assert settings().read_only is True


@pytest.mark.parametrize("value", ["", "  ", "yes please", "참"])
def test_unreadable_switch_value_falls_back_to_safe(monkeypatch, value):
    """안전 스위치가 오타 하나로 열리면 안 된다."""
    from meritz_studio.core.config import settings

    monkeypatch.setenv("MERITZ_READ_ONLY", value)
    assert settings().read_only is True


def test_switch_opens_only_when_said_so(monkeypatch):
    from meritz_studio.core.config import settings

    monkeypatch.setenv("MERITZ_READ_ONLY", "0")
    assert settings().read_only is False
