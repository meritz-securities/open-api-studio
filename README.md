# 메리츠증권 Open API Studio

> 현재 베타 서비스 기간입니다.

[개발자 포털](https://openapi.imeritz.com) · [API 신청](https://openapi.imeritz.com/api-apply) · [API 문서](https://openapi.imeritz.com/apiservice) · [문의](https://openapi.imeritz.com/qna)

[![test](https://github.com/meritz-securities/open-api-studio/actions/workflows/test.yml/badge.svg)](https://github.com/meritz-securities/open-api-studio/actions/workflows/test.yml) [![python](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/downloads/) [![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

터미널에서 메리츠증권 Open API를 찾고, 명세를 보고, 호출하는 `meritz` 명령입니다.
AI 에이전트용 스킬 2종과 파이썬 예제 4종이 함께 들어 있습니다.
기본값은 조회 전용이고, 주문·환전은 `MERITZ_READ_ONLY=0`으로 두셔야 열립니다.

앱키(App Key)와 시크릿(App Secret)은 [개발자 포털](https://openapi.imeritz.com)에서
발급받으십시오. 앱키에는 계좌가 묶입니다. 요청에 계좌번호를 넣지 않아도 그 계좌가
조회되고, 주문도 그 계좌로 나갑니다.

## 설치와 첫 호출

[uv](https://docs.astral.sh/uv/)가 필요합니다 (`brew install uv`).

| 방법 | 명령 |
|---|---|
| 내려받지 않고 그때그때 | `uvx --from git+https://github.com/meritz-securities/open-api-studio meritz doctor` |
| 설치해 두고 쓰기 | `uv tool install git+https://github.com/meritz-securities/open-api-studio` |
| 실시간(`meritz ws`)까지 | `uv tool install "git+https://github.com/meritz-securities/open-api-studio[realtime]"` |

`pip install git+…` 으로도 설치됩니다. `websocket-client`는 선택 항목이라, `realtime`
없이 설치하시면 `meritz ws`가 종료 코드 `2`로 멈춥니다. 앱키를 넣고 점검합니다.

```bash
export MERITZ_APP_KEY=발급받은_앱키
export MERITZ_APP_SECRET=발급받은_시크릿
meritz doctor
```

```
  서버      prod  https://openapi.imeritz.com:9443
  자격증명  있음      조회전용  예
  카탈로그  75건  (기준 2026-09-22)
발급 성공  eyJhbGciOiJI…  (prod · https://openapi.imeritz.com:9443)
```

여기서 걸리는 게 없으면 준비가 끝난 것입니다.

## 명령

```bash
meritz api list -q 잔고                   # 한글로 찾으셔도 됩니다
meritz api show market_prices             # 필수 항목·코드값·응답 필드
meritz call deposit                       # 조회
meritz order orders_buy -p iscd=A005930 …  # 주문 — 미리보기만, 전송하지 않습니다
meritz ws ws_stck_cntg --tr-key 005930    # 실시간 (realtime 설치 필요)
meritz token                              # 접근토큰이 발급되는지만 확인
```

종료 코드는 `0` 성공 / `2` 사용법 오류 / `3` 실패 / `4` 확인 필요 / `5` 주문 미접수입니다.
스크립트에서 결과를 판정하실 때 쓰시면 됩니다.

## 주문은 두 단계입니다

`--confirm` 없이 실행하면 전송하지 않고 보낼 내용과 확인 토큰만 보여 줍니다.
토큰은 한 번만 쓸 수 있고 180초 뒤 만료되며, 요청 값이나 대상 서버가 바뀌면 무효가 됩니다.
`--confirm <토큰>`을 붙여 다시 실행해야 나갑니다.

주문 응답이 성공으로 와도 `data.warn_cls_code`가 `0`이 아니면 아직 접수되지 않은 상태입니다.
CLI가 이를 실패로 처리하고 종료 코드 `5`와 함께 재전송 가능 여부를 안내합니다.

이 장치는 실수를 막기 위한 것이지, 사람이 내용을 확인했다는 증거는 아닙니다. 게이트는
`ApiClient.call()` 에 있어, `meritz` 명령으로 내시든 같은 패키지의 클라이언트를
파이썬에서 직접 부르시든 똑같이 걸립니다.
한계는 [DISCLAIMER.md](DISCLAIMER.md)에 적어 두었습니다.

## 예제와 스킬

조회·연속조회·주문·실시간 예제 네 개가 [`examples/`](examples/README.md)에 있습니다.
그대로 실행되는 코드이고, 주문 예제는 미리보기까지만 합니다.

스킬은 에이전트가 이 API를 제대로 쓰도록 안내하는 문서 묶음입니다. 조회·주문용
[`meritz-openapi-trading`](skills/meritz-openapi-trading/SKILL.md)과 코드 생성용
[`meritz-openapi-codegen`](skills/meritz-openapi-codegen/SKILL.md) 두 개가 있고,
`meritz skills install` 로 `~/.claude/skills` 에 설치됩니다(`--tool claude-desktop`
`--to <경로>` `--force`). 스킬이 참고하는 문서는 `python3 build_skills.py`로 만듭니다.

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `MERITZ_APP_KEY` / `MERITZ_APP_SECRET` | — | 포털에서 발급 |
| `MERITZ_BASE_URL` | `https://openapi.imeritz.com:9443` | REST 호출 대상 |
| `MERITZ_WS_URL` | `wss://openapi.imeritz.com:29443/websocket` | 실시간 접속점 |
| `MERITZ_READ_ONLY` | `1` | 기본이 조회 전용입니다. 주문·환전까지 쓰시려면 `0` |
| `MERITZ_TIMEOUT` | `15` | 요청 제한시간(초) |
| `MERITZ_STATE_DIR` | `~/.meritz` | 확인 토큰을 두는 곳. 접근토큰은 디스크에 쓰지 않습니다 |

`MERITZ_BASE_URL`을 바꾸실 때는 `MERITZ_WS_URL`도 함께 바꾸십시오. 한쪽만 바꾸면
토큰과 실시간 구독이 서로 다른 서버로 나갑니다. 동봉 카탈로그 대신 다른 파일을 쓰시려면
`MERITZ_CATALOG`에 경로를 주십시오.

저장소 루트나 패키지 폴더의 `.env`를 읽어 들입니다(`MERITZ_NO_ENV_FILE=1`이면 읽지
않습니다). 이미 설정된 환경변수가 우선합니다. `.env`는 `.gitignore`에 있습니다.

## 저장소가 네 개입니다

| 하고 싶으신 일 | 여기로 |
|---|---|
| 터미널에서 조회·주문하기 | **이 저장소** |
| 파이썬으로 직접 호출해 보기 | [open-api](https://github.com/meritz-securities/open-api) — 실행 예제 |
| AI 클라이언트에 붙이기 | [open-api-mcp](https://github.com/meritz-securities/open-api-mcp) — MCP 서버 |
| 호출 코드를 받아 쓰기 | [open-api-codegen-mcp](https://github.com/meritz-securities/open-api-codegen-mcp) — MCP 서버 |

## 개발

```bash
pip install -e ".[realtime]" pytest
pytest tests/ -q            # 앱키·네트워크 없이 돕니다
pytest tests/ -q -m ""      # 설치 검증까지 (네트워크 필요)
```

기여 방법은 [CONTRIBUTING.md](CONTRIBUTING.md)에 있습니다.


## 사용 전 확인해 주세요

- 대상 서버는 운영이 기본값이고, 앱키에 연결된 계좌는 실계좌입니다. 모의계좌는 없습니다
- 기본값은 조회 전용입니다. 주문·환전은 `MERITZ_READ_ONLY=0`으로 두셔야 열립니다
- 확인 절차는 실수를 막기 위한 것이지, 사람이 내용을 확인했다는 증거는 아닙니다
- 동봉한 스킬로 AI 에이전트에 붙여 쓰시면 조회 결과가 그 AI 서비스로 전송되며,
  해당 서비스의 데이터 처리 정책이 적용됩니다
- 앱키와 시크릿을 저장소에 커밋하지 말아 주세요
- [DISCLAIMER.md](DISCLAIMER.md)를 꼭 읽어 주세요

## 라이선스

MIT — [LICENSE](LICENSE)

문의는 개발자 포털을 이용해 주세요.
