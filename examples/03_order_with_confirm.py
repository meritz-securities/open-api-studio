"""주문 — 확인 없이는 전송되지 않는 형태.

이 예제는 **그대로 실행해도 주문이 나가지 않는다.** send() 를 호출하려면
호출하는 쪽이 사용자 동의를 받아 confirm_token 을 넘겨야 한다.
주문 코드를 이 모양으로 만드는 이유는, 인자만 받고 바로 전송하는 함수는
실수 한 번으로 주문이 나가기 때문이다.

주문·환전은 MERITZ_READ_ONLY=0 으로 열어야 나간다. 기본값은 조회 전용이다.
"""
from meritz_studio.core import safety
from meritz_studio.core.catalog import load_catalog
from meritz_studio.core.client import ApiClient
from meritz_studio.core.config import settings

# 주문이 접수되지 않았는데 성공처럼 보이는 유일한 경로다.
#
# 판정은 값 목록이 아니라 "0 인가" 로 한다 — warn_cls_code 가 있고 0 이 아니면
# 접수되지 않은 것이다. 아래는 그중 재전송(warn_cnfr_yn="Y")으로 풀리는 값이고,
# 국내와 해외는 코드 체계가 달라 공용으로 쓰지 않는다.
RESEND_OK = {
    "domestic": frozenset("134679acdfg"),
    "overseas": frozenset("13"),          # 1 경고 · 3 미국 PTP 과세 확인
}


class OrderNotAccepted(RuntimeError):
    """접수되지 않은 주문. resendable 이면 동의 후 재전송으로 풀린다."""

    def __init__(self, message, *, code="", resendable=False):
        super().__init__(message)
        self.code, self.resendable = code, resendable


def preview(api, body):
    s = settings()
    # 앱키까지 넘긴다 — 계좌를 정하는 것이 앱키다.
    return safety.preview(api, body, s.base_url, s.app_key)


def send(api, body, confirm_token):
    """확인 게이트는 ApiClient.call() 안에 있다. 여기서 따로 검사하지 않는다 —
    토큰은 1회용이라 두 번 보면 두 번째가 실패한다. 토큰이 없거나 맞지 않으면
    call() 이 MeritzError(code="NEEDS_CONFIRMATION") 를 올린다.
    """
    s = settings()
    res = ApiClient(s).call(api, {**body, "confirm_token": confirm_token})
    if not res["ok"]:
        raise RuntimeError(f"{res.get('error')}: {res.get('message')}")

    # rsp_cd 성공보다 warn_cls_code 를 먼저 본다. 뒤에 두면 영영 안 걸린다.
    check_not_accepted(res.get("body"), warn_scheme(api))
    return res


def warn_scheme(api) -> str:
    """코드 체계는 국내와 해외가 다르다. 경로로 가른다."""
    path = (api.get("path") if isinstance(api, dict) else getattr(api, "path", "")) or ""
    return "overseas" if "/overseas/" in path else "domestic"


def check_not_accepted(body, scheme="domestic"):
    """warn_cls_code 가 0 이 아니면 접수되지 않은 것이다.

    응답은 단건 dict 일 수도 배열일 수도 있고 최상위에 올 수도 있다.
    한 형태만 보면 나머지에서 조용히 새어 나간다.
    """
    if not isinstance(body, dict):
        return
    data = body.get("data")
    rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
    for row in list(rows) + [body]:
        if not isinstance(row, dict) or "warn_cls_code" not in row:
            continue
        code = str(row.get("warn_cls_code", "")).strip()
        if not code or code == "0":
            continue                            # 접수됐다
        msg = row.get("warn_msg") or "주문이 접수되지 않았습니다."
        if code in RESEND_OK[scheme]:
            raise OrderNotAccepted(
                f"{msg}\n사용자 동의를 받은 뒤 warn_cnfr_yn='Y' 를 더해 "
                f"다시 보내야 접수됩니다.", code=code, resendable=True)
        raise OrderNotAccepted(
            f"{msg}\n재전송해도 접수되지 않습니다(warn_cls_code={code}). "
            f"사유를 확인하십시오.", code=code, resendable=False)


if __name__ == "__main__":
    cat = load_catalog()
    api = cat.get("orders_buy")
    body = {"iscd": "A005930", "odqt": "1", "oder_unpr": "50000",
            "oder_cls_code": "01", "oder_cond_cls_code": "0",
            "orgl_oder_no": "0", "whol_rctf_cncl_yn": "N",
            "warn_cnfr_yn": "N", "exch_kind_code": "01"}

    pv = preview(api, body)
    print("보낼 내용:", pv["will_send"])
    print(pv["note"])
    print("\n전송하지 않았습니다. 사용자 동의를 받은 뒤")
    print(f"  send(api, body, {pv['confirm_token']!r})")
