# 예제

전부 실제로 도는 코드입니다. 앱키를 먼저 설정하십시오.

```bash
export MERITZ_APP_KEY=발급받은_앱키
export MERITZ_APP_SECRET=발급받은_시크릿

python3 01_quote.py
```

| 파일 | 내용 |
|---|---|
| [`01_quote.py`](01_quote.py) | 현재가 조회 — 응답 판정까지 |
| [`02_paging.py`](02_paging.py) | 연속 조회 (`rsp_cd`=`5762`) |
| [`03_order_with_confirm.py`](03_order_with_confirm.py) | 주문 — 확인 없이는 전송되지 않는 형태 |
| [`04_realtime.py`](04_realtime.py) | 실시간 체결 구독 |

`03`은 그대로 실행해도 주문이 나가지 않습니다. 미리보기까지만 합니다.

대상 서버는 운영이 기본값입니다. 바꾸실 때는 `MERITZ_BASE_URL`과 `MERITZ_WS_URL`을
함께 바꾸십시오. 앱키에 연결된 계좌는 실계좌입니다.
