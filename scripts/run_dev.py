from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def can_bind(host: str, port: int) -> tuple[bool, str | None]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
    except OSError as exc:
        return False, f"[WinError {getattr(exc, 'winerror', 'N/A')}] {exc}"
    finally:
        sock.close()
    return True, None


def parse_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {value!r}") from exc


def resolve_bind_target() -> tuple[str, int]:
    requested_host = os.getenv("HOST", "127.0.0.1")
    requested_port = parse_int("PORT", 8000)

    candidates: list[tuple[str, int]] = [(requested_host, requested_port)]
    for port in (8001, 8010, 8080, 8765, 9000):
        if (requested_host, port) not in candidates:
            candidates.append((requested_host, port))
    if requested_host != "0.0.0.0":
        for port in (requested_port, 8001, 8010, 8080, 8765, 9000):
            if ("0.0.0.0", port) not in candidates:
                candidates.append(("0.0.0.0", port))

    failures: list[str] = []
    for host, port in candidates:
        ok, error = can_bind(host, port)
        if ok:
            return host, port
        failures.append(f"{host}:{port} -> {error}")

    joined = "\n".join(f"  - {failure}" for failure in failures)
    raise SystemExit(
        "No local bind target is available for the dev server.\n"
        "Tried:\n"
        f"{joined}\n"
        "This is usually caused by Windows reserved ports, endpoint security, or a local policy.\n"
        "Try a different terminal with admin rights, or inspect excluded port ranges with:\n"
        "  netsh interface ipv4 show excludedportrange protocol=tcp"
    )


if __name__ == "__main__":
    host, port = resolve_bind_target()
    reload_enabled = os.getenv("RELOAD", "1").lower() not in {"0", "false", "no"}
    print(f"Starting dev server on http://{host}:{port} (reload={'on' if reload_enabled else 'off'})")
    uvicorn.run("main:app", host=host, port=port, reload=reload_enabled)
