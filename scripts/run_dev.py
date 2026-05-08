from __future__ import annotations

import os
import socket
import shutil
import subprocess
import sys
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def candidate_python_paths() -> list[Path]:
    candidates: list[Path] = []
    explicit = os.getenv("BACKEND_PYTHON")
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(Path(sys.executable))

    path_python = shutil.which("python")
    if path_python:
        candidates.append(Path(path_python))

    if os.name == "nt":
        try:
            output = subprocess.check_output(["where.exe", "python"], text=True, stderr=subprocess.DEVNULL)
            candidates.extend(Path(line.strip()) for line in output.splitlines() if line.strip())
        except Exception:
            pass
        candidates.extend(
            [
                Path(r"E:\anaconda3\python.exe"),
                Path(r"C:\ProgramData\anaconda3\python.exe"),
                Path(r"C:\ProgramData\miniconda3\python.exe"),
            ]
        )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate.exists():
            continue
        key = str(candidate.resolve()).lower() if os.name == "nt" else str(candidate.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def python_supports_backend(python: Path) -> tuple[bool, str]:
    command = [
        str(python),
        "-c",
        (
            "import sys; "
            "sys.exit('Python >= 3.11 is required') if sys.version_info < (3, 11) else None; "
            f"sys.path.insert(0, {str(SRC)!r}); "
            "import fastapi, uvicorn, sqlglot, dotenv; "
            "import evosql_platform.app.main"
        ),
    ]
    try:
        subprocess.check_output(command, cwd=ROOT, text=True, stderr=subprocess.STDOUT)
        return True, ""
    except subprocess.CalledProcessError as exc:
        return False, (exc.output or str(exc)).strip()
    except Exception as exc:
        return False, str(exc)


def choose_backend_python() -> Path:
    failures: list[str] = []
    for python in candidate_python_paths():
        ok, error = python_supports_backend(python)
        if ok:
            return python
        failures.append(f"{python} -> {error.splitlines()[-1] if error else 'unknown error'}")

    details = "\n".join(f"  - {failure}" for failure in failures)
    raise SystemExit(
        "No Python interpreter with working backend dependencies was found.\n"
        "Tried:\n"
        f"{details}\n"
        "Set BACKEND_PYTHON to a working python.exe or install requirements in your current environment."
    )


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
    backend_python = choose_backend_python()
    if backend_python.resolve() != Path(sys.executable).resolve():
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC)
        env["HOST"] = host
        env["PORT"] = str(port)
        env["RELOAD"] = "1" if reload_enabled else "0"
        print(f"Current Python is not usable for the backend; switching to {backend_python}")
        raise SystemExit(subprocess.call([str(backend_python), str(__file__)], cwd=ROOT, env=env))

    print(f"Starting dev server on http://{host}:{port} (reload={'on' if reload_enabled else 'off'})")
    print(f"Python: {sys.executable}")
    run_options = {
        "host": host,
        "port": port,
        "reload": reload_enabled,
        "app_dir": str(SRC),
    }
    if reload_enabled:
        run_options["reload_dirs"] = [str(ROOT)]
    uvicorn.run("evosql_platform.app.main:app", **run_options)
