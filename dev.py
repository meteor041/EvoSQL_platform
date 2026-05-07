from __future__ import annotations

import os
import signal
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
SRC = ROOT / "src"
NPM = "npm.cmd" if os.name == "nt" else "npm"


def can_bind(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
    except OSError:
        return False
    finally:
        sock.close()
    return True


def choose_port(host: str) -> int:
    requested = int(os.getenv("PORT", "8000"))
    for port in (requested, 8001, 8010, 8080, 8765, 9000):
        if can_bind(host, port):
            return port
    raise SystemExit("No available backend port found. Try setting PORT=8001.")


def candidate_python_paths() -> list[str]:
    candidates: list[str] = []
    explicit = os.getenv("BACKEND_PYTHON")
    if explicit:
        candidates.append(explicit)
    candidates.append(sys.executable)

    path_python = shutil.which("python")
    if path_python:
        candidates.append(path_python)

    if os.name == "nt":
        try:
            output = subprocess.check_output(["where.exe", "python"], text=True, stderr=subprocess.DEVNULL)
            candidates.extend(line.strip() for line in output.splitlines() if line.strip())
        except Exception:
            pass
        candidates.extend(
            [
                r"E:\anaconda3\python.exe",
                r"C:\ProgramData\anaconda3\python.exe",
                r"C:\ProgramData\miniconda3\python.exe",
            ]
        )

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(Path(candidate))
        key = normalized.lower() if os.name == "nt" else normalized
        if key not in seen and Path(normalized).exists():
            seen.add(key)
            unique.append(normalized)
    return unique


def python_supports_backend(python: str) -> bool:
    command = [
        python,
        "-c",
        (
            "import sys; "
            "sys.exit(1) if sys.version_info < (3, 10) else None; "
            f"sys.path.insert(0, {str(SRC)!r}); "
            "import fastapi, pydantic_core, uvicorn; "
            "import evosql_platform.app.main"
        ),
    ]
    try:
        subprocess.check_call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def choose_backend_python() -> str:
    for python in candidate_python_paths():
        if python_supports_backend(python):
            return python
    raise SystemExit(
        "No Python interpreter with backend dependencies was found. "
        "Install requirements or set BACKEND_PYTHON to a working python.exe."
    )


def ensure_frontend_deps() -> None:
    if (FRONTEND / "node_modules").exists():
        return
    print("frontend/node_modules not found. Running npm install...")
    subprocess.check_call([NPM, "install"], cwd=FRONTEND)


def start_process(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(command, cwd=cwd, env=env)


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            process.terminate()
        process.wait(timeout=5)
    except Exception:
        process.kill()


def main() -> int:
    host = os.getenv("HOST", "127.0.0.1")
    port = choose_port(host)
    backend_python = choose_backend_python()

    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(SRC)
    backend_env["HOST"] = host
    backend_env["PORT"] = str(port)
    backend_env.setdefault("RELOAD", "0")

    frontend_env = os.environ.copy()
    frontend_env["VITE_API_TARGET"] = f"http://{host}:{port}"

    ensure_frontend_deps()

    print(f"Backend:  http://{host}:{port}")
    print("Frontend: http://127.0.0.1:5173")
    print(f"Python:   {backend_python}")
    print("Press Ctrl+C to stop both services.")

    backend = start_process(
        [
            backend_python,
            "-m",
            "uvicorn",
            "evosql_platform.app.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        ROOT,
        backend_env,
    )
    time.sleep(1)
    frontend = start_process([NPM, "run", "dev", "--", "--host", "127.0.0.1"], FRONTEND, frontend_env)

    try:
        while True:
            backend_code = backend.poll()
            frontend_code = frontend.poll()
            if backend_code is not None:
                stop_process(frontend)
                return backend_code
            if frontend_code is not None:
                stop_process(backend)
                return frontend_code
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping services...")
        stop_process(frontend)
        stop_process(backend)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
