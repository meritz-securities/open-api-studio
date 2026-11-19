"""안전 기본값이 회귀하지 않게 잠근다.

모의계좌가 없다. 앱키에 묶인 계좌는 언제나 실계좌다. 이 저장소는 AI 에이전트가
그대로 실행할 수 있는 예제와 스킬을 동봉하므로, 기본값이 유일한 완충재다.

여기서 보는 것은 셋이다.
  ① 아무것도 설정하지 않으면 조회 전용인가
  ② 빈 값·공백·알아볼 수 없는 값에서 안전한 쪽으로 떨어지는가
  ③ 게이트가 도구 계층이 아니라 라이브러리(ApiClient.call) 안에 있는가
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MERITZ_CATALOG",
                      str(ROOT / "meritz_studio" / "data" / "catalog.json"))
os.environ.setdefault("MERITZ_NO_ENV_FILE", "1")
sys.path.insert(0, str(ROOT))

from meritz_studio.core import safety  # noqa: E402
from meritz_studio.core.catalog import load_catalog  # noqa: E402
from meritz_studio.core.client import ApiClient, MeritzError  # noqa: E402
from meritz_studio.core.config import Settings, settings  # noqa: E402
from meritz_studio.core.safety import is_state_changing  # noqa: E402

CAT = load_catalog()
ORDER = CAT.get("orders_buy")
QUOTE = CAT.get("market_prices")


@pytest.fixture(autouse=True)
def memory_store(monkeypatch, tmp_path):
    """CLI 가 끼운 파일 저장소가 남지 않게 한다."""
    monkeypatch.setenv("MERITZ_STATE_DIR", str(tmp_path))
    safety.set_confirm_store(safety._MemoryStore())


# ------------------------------------------------- 안전 스위치 기본값
def test_default_is_read_only(monkeypatch):
    monkeypatch.delenv("MERITZ_READ_ONLY", raising=False)
    assert settings().read_only is True


def test_dataclass_default_is_read_only():
    """환경변수를 거치지 않고 Settings 를 직접 만들어도 닫혀 있어야 한다."""
    assert Settings().read_only is True


@pytest.mark.parametrize("value", ["", "   ", "yes please", "참", "1 "])
def test_unreadable_switch_value_falls_back_to_safe(monkeypatch, value):
    """안전 스위치가 오타 하나로 열리면 안 된다."""
    monkeypatch.setenv("MERITZ_READ_ONLY", value)
    assert settings().read_only is True, f"{value!r} 에서 열렸다"


def test_env_can_open_orders(monkeypatch):
    """명시적으로 열 수는 있어야 한다 — 그렇지 않으면 주문을 쓸 수 없다."""
    monkeypatch.setenv("MERITZ_READ_ONLY", "0")
    assert settings().read_only is False


# ------------------------------------------------- 주문 경로 게이트
def test_orders_are_blocked_in_read_only():
    c = ApiClient(Settings(app_key="k", app_secret="s", read_only=True))
    with pytest.raises(MeritzError) as e:
        c.call(ORDER, {})
    assert e.value.code == "READ_ONLY"


def test_orders_need_a_confirm_token_even_from_the_library():
    """게이트는 라이브러리 계층에 있어야 한다.

    도구 계층에만 두면 ApiClient 를 직접 임포트해 쓰는 코드에서 주문이
    무확인으로 나간다.
    """
    c = ApiClient(Settings(app_key="k", app_secret="s", read_only=False))
    with pytest.raises(MeritzError) as e:
        c.call(ORDER, _order_body())
    assert e.value.code == "NEEDS_CONFIRMATION"
    assert "confirm_token" in (e.value.body or {})


def test_a_valid_token_passes_the_gate():
    s = Settings(app_key="k", app_secret="s", read_only=False)
    c = ApiClient(s)
    body = ORDER.body_params(_order_body())
    pv = safety.preview(ORDER, body, s.base_url, s.app_key)
    # 게이트만 본다 — 통과하면 예외가 없다. 전송은 하지 않는다.
    c.require_confirmation(ORDER, {**_order_body(),
                                   "confirm_token": pv["confirm_token"]})


def test_the_token_is_single_use():
    s = Settings(app_key="k", app_secret="s", read_only=False)
    c = ApiClient(s)
    params = _order_body()
    pv = safety.preview(ORDER, ORDER.body_params(params), s.base_url, s.app_key)
    params["confirm_token"] = pv["confirm_token"]
    c.require_confirmation(ORDER, params)
    with pytest.raises(MeritzError) as e:
        c.require_confirmation(ORDER, params)
    assert e.value.code == "NEEDS_CONFIRMATION"


def test_queries_do_not_need_a_token():
    c = ApiClient(Settings(app_key="k", app_secret="s", read_only=True))
    c.require_confirmation(QUOTE, {"iscd": "005930"})


def _order_body() -> dict:
    return {"iscd": "A005930", "odqt": "1", "oder_unpr": "50000",
            "oder_cls_code": "01", "oder_cond_cls_code": "0",
            "orgl_oder_no": "0", "whol_rctf_cncl_yn": "N",
            "warn_cnfr_yn": "N", "exch_kind_code": "01"}


def test_token_revoke_is_gated_but_issue_is_not():
    """토큰 폐기는 조회 전용에서 막혀야 한다.

    같은 앱키로 발급된 토큰은 하나뿐이라, 폐기하면 다른 프로세스·세션이
    쓰던 토큰까지 끊긴다. oauth2 카테고리를 통째로 면제했더니 시험 삼아
    부를 수 있는 자리가 열려 있었다. 발급은 모든 호출의 전제라 면제를
    유지한다.
    """
    assert is_state_changing(CAT.get("oauth2_revoke")) is True
    assert is_state_changing(CAT.get("oauth2_token")) is False


# ------------------------------------------------------------- paginate()
#
# 여기가 틀리면 건수가 조용히 모자라게 돌아온다. 합계로 쓰면 틀린 수치가
# 그대로 화면에 나가는데, 예외도 오류 코드도 없어 알아챌 방법이 없다.
class _FakeClient:
    """호출 순서대로 미리 정한 응답을 돌려준다. 네트워크를 쓰지 않는다."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.requests = []

    def call(self, api, params, **kw):
        self.requests.append(dict(params))
        return self.pages[min(len(self.requests) - 1, len(self.pages) - 1)]


def _page(rows, rsp_cd, key=None):
    body = {"rsp_cd": rsp_cd, "data": rows}
    if key is not None:
        body["tr_cont_key"] = key
    return {"ok": True, "body": body}


def test_paginate_walks_until_the_server_stops():
    from meritz_studio.core.client import PAGE_MORE, paginate

    api = CAT.get("transactions")
    client = _FakeClient([_page([{"n": 1}], PAGE_MORE, "K1"),
                          _page([{"n": 2}], PAGE_MORE, "K2"),
                          _page([{"n": 3}], "0000")])
    out = paginate(client, api, {"from": "20260101"})
    assert out["pages"] == 3
    assert [r["n"] for r in out["rows"]] == [1, 2, 3]
    assert out["truncated"] is False


def test_paginate_sends_the_continuation_key_untouched():
    """키에 붙어 오는 오른쪽 공백을 잘라내면 서버가 다른 구간을 준다."""
    from meritz_studio.core.client import PAGE_MORE, paginate

    api = CAT.get("transactions")
    client = _FakeClient([_page([{"n": 1}], PAGE_MORE, "ABC   "),
                          _page([{"n": 2}], "0000")])
    paginate(client, api, {"from": "20260101"})
    assert client.requests[1]["tr_cont_key"] == "ABC   "
    assert client.requests[1]["tr_cont"] == "1"


def test_paginate_stops_when_the_key_never_changes():
    """같은 키를 다시 보내면 같은 구간이 영원히 돌아온다."""
    from meritz_studio.core.client import PAGE_MORE, paginate

    api = CAT.get("transactions")
    client = _FakeClient([_page([{"n": 1}], PAGE_MORE, "SAME")] * 5)
    out = paginate(client, api, {"from": "20260101"})
    assert out["pages"] == 2, "키가 그대로면 두 번째에서 멈춰야 합니다"
    assert out["truncated"] is True
    assert out["note"], "끝까지 받지 못했으면 이유를 남겨야 합니다"


def test_paginate_marks_truncated_at_the_page_limit():
    from meritz_studio.core.client import PAGE_MORE, paginate

    api = CAT.get("transactions")
    pages = [_page([{"n": i}], PAGE_MORE, f"K{i}") for i in range(10)]
    client = _FakeClient(pages)
    out = paginate(client, api, {"from": "20260101"}, max_pages=3)
    assert out["pages"] == 3
    assert out["truncated"] is True


def test_paginate_refuses_apis_that_do_not_support_it():
    """명세에 tr_cont 가 있어도 다음 구간이 오지 않는 API 가 있다."""
    from meritz_studio.core.client import MeritzError, paginate

    client = _FakeClient([_page([], "0000")])
    with pytest.raises(MeritzError) as e:
        paginate(client, CAT.get("market_investors"), {})
    assert e.value.code == "PAGING_UNSUPPORTED"
    assert client.requests == [], "지원하지 않는 API 는 호출조차 하지 않아야 합니다"
