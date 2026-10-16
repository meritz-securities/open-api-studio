"""현재가 한 종목 조회 — 가장 짧은 예제.

  export MERITZ_APP_KEY=... MERITZ_APP_SECRET=...
  python examples/01_quote.py 005930
"""
import sys

from meritz_studio.core.catalog import load_catalog
from meritz_studio.core.client import ApiClient, MeritzError
from meritz_studio.core.config import settings

iscd = sys.argv[1] if len(sys.argv) > 1 else "005930"
cat = load_catalog()
api = cat.get("market_prices")

try:
    res = ApiClient(settings()).call(api, {"mrkt_div_code": "J", "iscd": iscd})
except MeritzError as e:
    raise SystemExit(f"호출 실패: {e}") from None

# ok 판정은 client 가 한다. HTTP 200 만 보고 성공으로 넘기지 않는다.
if not res["ok"]:
    raise SystemExit(f"{res.get('error')}: {res.get('message')}")

body = res.get("body")
if not isinstance(body, dict):
    raise SystemExit(f"JSON 이 아닌 응답입니다: {str(body)[:200]}")
data = body.get("data") or {}
# 필드명은 meritz api show market_prices 로 확인한다. 현재가는 stck_prpr 다.
print(f"{data.get('kor_isnm') or iscd}  {data.get('stck_prpr')}원  "
      f"전일대비 {data.get('prdy_vrss')} ({data.get('prdy_ctrt')}%)")

if res.get("verified") is False:
    print("\n※ 이 API 는 응답 코드가 손상돼 옵니다. 값은 정상이지만 "
          "업무 성공 여부는 검증되지 않았습니다.")
