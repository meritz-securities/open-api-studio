# 설치 (CLI)

`meritz` 명령줄 도구를 설치하고 첫 호출까지 확인합니다. 조회·주문·실시간을 터미널에서 바로 씁니다.

> 요약만 필요하시면 [README 의 설치 표](../README.md#설치와-첫-호출)로 충분합니다. 이 문서는
> 운영체제별 준비·자격증명 영속화·문제 해결까지 자세히 다룹니다.

## 1. 요구사항

- **Python 3.11 이상**
- **[uv](https://docs.astral.sh/uv/)** (Python 설치·실행을 대신 처리합니다. uv 가 Python 도 받아 줍니다)

uv 설치 — [uv 공식 안내](https://docs.astral.sh/uv/getting-started/installation/)를 따르십시오. 대표 방법:

| OS | 설치 |
|---|---|
| macOS | `brew install uv` |
| macOS · Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Windows (PowerShell) | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

설치 후 확인: `uv --version`

## 2. 설치

| 방법 | 명령 | 언제 |
|---|---|---|
| 그때그때 실행 | `uvx --from git+https://github.com/meritz-securities/open-api-studio meritz doctor` | 내려받지 않고 한 번만 |
| 설치해 두기 | `uv tool install git+https://github.com/meritz-securities/open-api-studio` | `meritz` 를 계속 쓰기 |
| 실시간까지 | `uv tool install "git+https://github.com/meritz-securities/open-api-studio[realtime]"` | `meritz ws` 도 쓰기 |

- `pip install git+https://github.com/meritz-securities/open-api-studio` 으로도 설치됩니다.
- **실시간(`meritz ws`)은 `websocket-client` 가 있어야 합니다.** `[realtime]` 없이 설치하면
  `meritz ws` 가 `종료 코드 2`로 멈추며 `pip install websocket-client` 를 안내합니다.
  조회·주문만 쓰시면 기본 설치로 충분합니다.

설치 확인: `meritz --version` → `meritz 0.2.0`

## 3. 앱키와 자격증명

### 앱키 발급
메리츠증권 Open API 포털 [openapi.imeritz.com](https://openapi.imeritz.com) 에서 발급합니다.
**앱키는 발급받은 서버에서만 유효**합니다. 발급처와 다른 서버로 보내면 `EGW00103` 이 납니다.

### 넣는 방법 — 둘 중 하나
**① 환경변수** (현재 셸에만 적용)
```bash
export MERITZ_APP_KEY=발급받은_앱키
export MERITZ_APP_SECRET=발급받은_시크릿
```
새 터미널마다 다시 넣어야 하면, 셸 설정(`~/.zshrc` 등)에 넣거나 아래 `.env` 를 쓰십시오.
Windows PowerShell 은 `$env:MERITZ_APP_KEY="..."` 입니다.

**② `.env` 파일** (영속)
실행 파일 옆(또는 그 상위 폴더)에 `.env` 를 두면 읽습니다. 환경변수가 있으면 환경변수가 이깁니다.
```
MERITZ_APP_KEY=발급받은_앱키
MERITZ_APP_SECRET=발급받은_시크릿
```
`.env` 를 아예 읽지 않게 하려면 `MERITZ_NO_ENV_FILE=1` 을 두십시오.

> 기본 서버는 운영(`https://openapi.imeritz.com:9443`)입니다. 그 밖의 환경변수:
> `MERITZ_CATALOG`(카탈로그 파일 경로), `MERITZ_STATE_DIR`(상태 파일 위치, 기본 `~/.meritz`).

## 4. 점검 — `meritz doctor`

```bash
meritz doctor
```
서버·자격증명·조회전용 여부·카탈로그 건수와 **토큰 발급 성공 여부**를 한 번에 봅니다.

```
meritz 0.2.0
  서버      prod  https://openapi.imeritz.com:9443
  WebSocket wss://openapi.imeritz.com:29443/websocket
  자격증명  있음
  조회전용  예
  상태파일  /Users/<사용자>/.meritz
  카탈로그  82건  (기준 2026-10-02)
  포털 정정 13건  — meritz api show 에서 해당 API 에 표시됩니다
발급 성공  eyJhbGciOiJI…  (prod · https://openapi.imeritz.com:9443)
```
`발급 성공` 줄이 나오면 준비가 끝난 것입니다. `토큰 발급 실패 … EGW00103` 이 나오면
**앱키와 서버가 안 맞는 것**입니다(3번의 발급 서버를 확인하십시오).

## 5. 첫 호출

```bash
meritz api list -q 잔고                 # 한글로 찾습니다
meritz api show valuation               # 필수 항목·코드값·응답 필드
meritz call valuation                   # 조회
meritz token                            # 접근토큰 발급만 확인
```
종료 코드: `0` 성공 · `2` 사용법 오류 · `3` 실패 · `4` 확인 필요 · `5` 주문 미접수.

## 6. 스킬 설치 (선택)

Claude 등 에이전트가 읽는 위치(`~/.claude/skills`)에 사용법 스킬을 복사합니다.
```bash
meritz skills list        # 동봉된 스킬 보기
meritz skills install     # 설치
```

## 7. 업그레이드 · 제거

```bash
uv tool upgrade meritz-openapi-studio                               # 최신으로
uv tool install --force git+https://github.com/meritz-securities/open-api-studio   # 재설치(강제)
uv tool uninstall meritz-openapi-studio                            # 제거
```

## 8. 문제 해결

| 증상 | 원인 · 해결 |
|---|---|
| `uv: command not found` | 1번으로 uv 설치. 설치 후 새 터미널을 여십시오(PATH 반영) |
| `토큰 발급 실패 … EGW00103 유효하지 않은 client_id` | 앱키가 이 서버에서 발급한 것인지 확인하십시오(3번) |
| `토큰 발급 실패 … EGW00002` | 서버측 장애입니다. 앱키 문제가 아니므로 다시 넣지 마십시오 |
| `자격증명  없음 — MERITZ_APP_KEY/APP_SECRET 필요` | 3번처럼 앱키·시크릿을 넣으십시오 |
| `meritz ws` 가 `종료 코드 2` + `websocket-client 가 필요합니다` | 2번의 `[realtime]` 로 설치하거나 `pip install websocket-client` |
| 카탈로그 날짜가 오래됨 | 배포본에 동봉된 기준일입니다. 새 버전을 7번으로 올리면 갱신됩니다 |

> 앱키·시크릿은 민감정보입니다. 화면·로그·저장소에 남기지 마십시오. `.env` 는 버전관리에서 제외하십시오.
