# 설치와 설정

## 설치

`meritz` 명령은 저장소에서 바로 설치한다. PyPI 에는 올라가 있지 않다.

```bash
# 계속 쓸 때 — 실시간(meritz ws)까지 쓰려면 [realtime] 을 붙인다
uv tool install "git+https://github.com/meritz-securities/open-api-studio[realtime]"

# 한 번만 써 볼 때 — 내려받지 않고 그때그때 실행한다
uvx --from git+https://github.com/meritz-securities/open-api-studio meritz doctor
```

[uv](https://docs.astral.sh/uv/) 가 필요하다 (`brew install uv`).
uv 를 쓸 수 없으면 `pip install "git+https://github.com/meritz-securities/open-api-studio[realtime]"`.

`websocket-client` 는 선택 항목이다. `[realtime]` 없이 설치하면 `meritz ws` 가
종료 코드 `2` 로 멈춘다 — 이때는 다시 설치하게 안내한다.

저장소를 고칠 목적의 편집 설치(`pip install -e`)는 CONTRIBUTING.md 를 본다.

## 앱키

메리츠증권 Open API 포털에서 발급받는다.

```bash
export MERITZ_APP_KEY=발급받은_앱키
export MERITZ_APP_SECRET=발급받은_시크릿
```

`.env` 파일에 적어도 된다 — 저장소 루트의 `.env` 를 자동으로 읽고, 이미 설정된
환경변수는 덮지 않는다. **저장소에 커밋하지 않는다.**

## 서버

기본은 운영이다.

| 변수 | 기본값 |
|---|---|
| `MERITZ_BASE_URL` | `https://openapi.imeritz.com:9443` |
| `MERITZ_WS_URL` | `wss://openapi.imeritz.com:29443/websocket` |

다른 서버로 붙이려면 **둘 다** 바꾼다. 하나만 바꾸면 토큰과 구독이
서로 다른 서버로 나간다.

## 안전 스위치

| 변수 | 뜻 |
|---|---|
| `MERITZ_READ_ONLY` | 기본 `1` — 조회 전용. `0` 으로 두어야 주문·환전이 열린다 |
| `MERITZ_STATE_DIR` | 확인 토큰 저장 위치 (기본 `~/.meritz`). 접근토큰은 디스크에 쓰지 않는다 |
| `MERITZ_CATALOG` | 동봉 카탈로그 대신 쓸 `catalog.json` 경로 |
| `MERITZ_NO_ENV_FILE=1` | `.env` 를 읽지 않는다 |

## 확인

```bash
meritz doctor
```

서버·자격증명·카탈로그·토큰 발급까지 한 번에 점검한다.
토큰 발급만 확인하려면 `meritz token`.

## 안 될 때

| 증상 | 원인 |
|---|---|
| `MERITZ_APP_KEY … 필요합니다` | 환경변수 미설정 |
| `meritz ws` 가 종료 코드 `2` | `websocket-client` 없음. `[realtime]` 로 다시 설치한다 |
| 토큰 발급 실패 (`EGW00002`) | 서버측 문제다. 앱키를 다시 입력하게 하지 않는다 |
| `카탈로그를 찾을 수 없습니다` | 설치가 깨졌다. 재설치하거나 `MERITZ_CATALOG` 로 경로 지정 |
