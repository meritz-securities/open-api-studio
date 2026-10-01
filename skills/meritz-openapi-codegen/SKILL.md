---
name: meritz-openapi-codegen
description: 메리츠증권 Open API 를 호출하는 파이썬 코드를 만든다. "메리츠 API 호출 코드 짜줘", "현재가 조회 파이썬 예제", "실시간 체결 구독 코드", "주문 넣는 코드 만들어줘", "write Meritz API client code" 처럼 실행이 아니라 코드가 필요할 때 쓴다. REST 62건과 실시간 13건 전부를 다룬다. 실제로 호출해 결과를 보려면 meritz-openapi-trading 을 쓴다.
metadata:
  version: 0.2.3
  author: 메리츠증권
---

# 메리츠증권 Open API — 호출 코드 작성

호출 코드를 만든다. **실행하지 않는다.** 실행이 필요하면
`meritz-openapi-trading` 스킬로 넘긴다.

## 원칙

1. **명세에 있는 것만 쓴다.** 파라미터·경로·`tr_cd` 를 지어내지 않는다
2. **응답을 검사하는 코드를 함께 낸다.** HTTP 200 만 보고 성공으로 처리하지 않는다
3. **주문 코드에는 경고 확인 흐름을 반드시 넣는다** (아래)
4. API별 응답 처리 참고사항이 있다 — `references/corrections.md` 를 먼저 본다

## 작업 순서

1. **API 찾기** — `references/apis.json` 또는 `meritz api list -q <키워드>`
2. **명세 확인** — `meritz api show <api_type>` 으로 필수 항목·코드값을 본다
3. **코드 생성** — 아래 형태를 따른다
4. **주의사항 주석** — 정정 대상이면 그 사실을 코드 주석에 남긴다

| 파일 | 언제 |
|---|---|
| `references/apis.json` | api_type·필수 파라미터 기계 조회 |
| `references/corrections.md` | **API별 응답 처리 참고사항** |
| `references/errors.md` | 응답 코드 판정 |
| `references/api-catalog.md` | 75건 전체 목록 |
| `references/glossary.md` | 응답 필드 한/영 |

## 인증

토큰은 `POST /oauth2/token` 으로 받고, 만료 전까지 재사용한다.
**요청마다 새로 받지 않는다.**

요청 본문은 **form 인코딩**이다. JSON 이 아니다.

```python
requests.post(f"{BASE_URL}/oauth2/token",
              data={"grant_type": "client_credentials",
                    "client_id": APP_KEY, "client_secret": APP_SECRET,
                    "scope": "login"},
              headers={"content-type": "application/x-www-form-urlencoded"})
# 응답의 access_token 과 expires_in(초) 을 쓴다. 보통 12시간이다.
```

호출 헤더에 **`mac_address` 가 빠지면 `IGW50024` 로 거절된다.** 12자리 대문자 16진수다.

```python
headers = {
    "authorization": f"Bearer {token}",
    "content-type": "application/json; charset=utf-8",
    "mac_address": mac_address(),      # uuid.getnode() 를 12자리 16진수로
    "tr_id": api_tr_id,
}
```

토큰이 폐기되면 `rsp_cd` 가 `EGW00121` 로 온다. 캐시를 버리고 한 번 다시 받아 재시도한다.

WebSocket 은 **접속이 아니라 구독 메시지에서** 인증한다.
`{"header": {"token": f"Bearer {token}", "tr_type": "1"}, "body": {"tr_cd": ..., "tr_key": ...}}`

## 응답 판정 — 이 순서를 지킨다

```
1) HTTP 200 인가                     아니면 실패
2) 주문이면 warn_cls_code 부터        경고면 접수 안 된 것이다
3) rsp_cd 가 읽히는가
     성공 코드면 성공, 아니면 업무 오류
4) 읽히지 않는다면
     알려진 손상 API 인가 (corrections.md)
       아니면 실패로 처리한다 — 모르는 손상을 성공으로 넘기지 않는다
       맞으면 데이터가 비지 않았을 때만 통과시키되 "검증되지 않음"을 표시한다
```

성공 코드는 `0000`·`0001`·`5762`·`5766`·`5820`·`5822`. `5762` 는 다음 페이지가
있다는 뜻이고 `5820`·`5822` 는 보통 자료 없음이다 — **전부 오류가 아니다.**
(`5822` 는 빈 기간을 조회했을 때 온다.)
다만 **`5820` 으로 자료 유무를 판정하지 않는다.** 담보 조회·종목별 실현손익·해외
실현손익은 자료를 담은 채로도 `5820` 을 보낸다. **`data` 가 비었는지로 가른다.**

**"값이 있으면 성공"으로 판정하지 않는다.** 게이트웨이는 조회가 빗나가도
시장명·거래정지여부 같은 상수 필드를 채워 보낸다. 종목코드·종목명처럼
**조회 결과가 되돌아오는 필드**가 비었는지를 본다.

## 주문 코드 — 경고 확인 흐름 (빠뜨리면 안 된다)

응답에 `warn_cls_code` 가 있고 그 값이 `0` 이 아니면 **주문이 접수되지 않은 것이다.**
`rsp_cd` 가 `0001` 이고 메시지가 "주문이 완료되었습니다" 여도 마찬가지다.
**값 목록으로 판정하지 않는다 — `0` 만 접수다.**

```python
# 재전송(warn_cnfr_yn="Y")으로 풀리는 값. 국내와 해외는 코드 체계가 다르다.
RESEND_OK = {
    "domestic": frozenset("134679acdfg"),
    "overseas": frozenset("13"),          # 1 경고 · 3 미국 PTP 과세 확인
}

def check_not_accepted(row, scheme="domestic"):
    code = str(row.get("warn_cls_code", "")).strip()
    if not code or code == "0":
        return                                  # 접수됐다
    # 여기 오면 접수되지 않았다.
    if code in RESEND_OK[scheme]:
        # 경고 문구를 사용자에게 보이고 동의를 받은 뒤,
        # 같은 주문에 warn_cnfr_yn="Y" 를 더해 다시 보내야 접수된다.
        raise MeritzWarning(row.get("warn_msg"), resendable=True)
    # 국내 2·5·8·b·e·h, 해외 2 등 — 재전송해도 접수되지 않는다.
    raise MeritzWarning(row.get("warn_msg"), resendable=False)
```

`scheme` 은 경로로 가른다 — `"/overseas/" in api["path"]` 이면 `"overseas"`.

이 검사를 `rsp_cd` 성공 반환보다 **먼저** 둔다. 뒤에 두면 영영 안 걸린다.

생성하는 주문 코드에는 **사용자 확인 단계를 남겨 둔다.** 함수가 인자만 받고
바로 전송하는 형태로 만들지 않는다.

## 연속 조회

목록 API 는 `tr_cont` / `tr_cont_key` 로 이어 받는다.

**두 값은 쿼리스트링에 넣는다.** 헤더에만 실으면 두 번째 페이지가
`5822`(자료 없음)로 와서 조용히 1페이지에서 끝난다.

```python
params = {...}
while True:
    result = fetch(**params)
    rows += result.get("data") or []
    if result.get("rsp_cd") != "5762":       # 5766·5820·5822 면 끝이다
        break
    params = dict(params, tr_cont="1",
                  tr_cont_key=result.get("tr_cont_key", ""))
    if len(rows) > 100000:                   # 서버가 같은 키를 계속 주는 경우를 막는다
        break
```

`tr_cont_key` 는 오른쪽에 공백이 붙어 올 때가 있다. **자르지 말고 그대로 넘긴다.**

## 초당 호출 한도

API 마다 초당 10건이다. 넘기면 **HTTP 500** 과 함께 `rsp_cd` 가 `EGW00200` 으로 온다.
목록을 순회하는 코드에는 호출 간격을 두거나 재시도를 넣는다.

## 서버

기본은 **운영**(`https://openapi.imeritz.com:9443`)이다.
개발로 붙이려면 `MERITZ_BASE_URL` 과 `MERITZ_WS_URL` 을 **둘 다** 바꾼다.
하나만 바꾸면 토큰은 개발에서 받고 구독은 운영으로 나간다.

## 하지 말 것

- 앱키·시크릿을 코드에 적지 않는다. 환경변수로 읽는다
- 계좌 파라미터(`acno`·`asno`·`acnt_pwd`)를 넣지 않는다. 앱키에 묶여 있다
- 예제라도 **실행되는 주문 코드를 확인 없이** 내놓지 않는다
- 명세에 없는 필드를 응답에서 꺼내 쓰지 않는다
