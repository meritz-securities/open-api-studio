"""프로세스를 넘어가는 확인 토큰 저장소.

CLI 는 미리보기와 전송이 서로 다른 프로세스다. 메모리 저장소를 그대로 쓰면
토큰이 매번 사라져 전송이 영영 안 되거나, 반대로 검증을 건너뛰게 만들기 쉽다.
그래서 파일에 담되 **규칙은 core.safety 에 그대로 둔다** — 여기서 하는 일은
담아 두는 것뿐이고, 무엇이 유효한지는 판단하지 않는다.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path

try:
    import fcntl
except ImportError:          # 윈도우
    fcntl = None


def state_dir() -> Path:
    d = Path(os.environ.get("MERITZ_STATE_DIR") or (Path.home() / ".meritz"))
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    # mode 는 새로 만들 때만 적용된다 — 이미 있는 디렉터리는 그대로 넓게 열려 있다.
    try:
        if d.stat().st_mode & 0o077:
            d.chmod(0o700)
    except OSError:
        pass
    return d


class FileConfirmStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (state_dir() / "pending.json")
        self.lock_path = self.path.with_suffix(".lock")

    @contextlib.contextmanager
    def _locked(self):
        """읽고-고쳐-쓰는 동안 다른 프로세스를 막는다.

        잠금이 없으면 동시에 발급된 토큰이 서로를 덮어쓴다. 사용자가 화면에서
        본 토큰이 전송할 때 "만료됐습니다" 로 거절된다.

        fcntl 이 없는 환경(윈도우)에서는 잠금 없이 진행한다. 그쪽에서는
        동시 실행이 드물고, 잠그지 못한다고 멈추는 것이 더 나쁘다.
        """
        if fcntl is None:
            yield
            return
        with open(self.lock_path, "w") as fh:
            try:
                os.chmod(self.lock_path, 0o600)
            except OSError:
                pass
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def _read(self) -> dict:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return raw if isinstance(raw, dict) else {}

    def _write(self, d: dict) -> None:
        # 주문 내용을 담은 파일이므로 다른 사용자가 읽지 못하게 한다.
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".pending-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except BaseException:
            os.unlink(tmp)
            raise

    def get(self, token: str):
        with self._locked():
            e = self._read().get(token)
        if not isinstance(e, list) or len(e) != 2:
            return None
        return (str(e[0]), float(e[1]))

    def put(self, token: str, fingerprint: str, expires_at: float) -> None:
        with self._locked():
            d = self._read()
            d[token] = [fingerprint, expires_at]
            self._write(d)

    def pop(self, token: str) -> None:
        with self._locked():
            d = self._read()
            if d.pop(token, None) is not None:
                self._write(d)

    def purge(self, now: float) -> None:
        with self._locked():
            d = self._read()
            live = {k: v for k, v in d.items()
                    if isinstance(v, list) and len(v) == 2 and float(v[1]) >= now}
            if len(live) != len(d):
                self._write(live)
