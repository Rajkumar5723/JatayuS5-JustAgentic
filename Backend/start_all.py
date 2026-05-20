"""
start_all.py
=============
Launch all 5 Hiresy backend microservices in one command.

Usage:
    python start_all.py           # start all services
    python start_all.py --reload  # start with hot-reload (dev mode)

Press Ctrl+C to stop all services gracefully.
"""
from __future__ import annotations
import argparse
import os
import signal
import subprocess
import sys
import time

# Ensure Backend/ is on the path so core.config is importable
_backend = os.path.dirname(os.path.abspath(__file__))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from core.config import settings

SERVICES = [
    {
        "name":   "Main API",
        "module": "services.main_api.app:app",
        "port":   settings.PORT_MAIN,
        "color":  "\033[94m",   # blue
    },
    {
        "name":   "Evaluator",
        "module": "services.evaluator.app:app",
        "port":   settings.PORT_EVAL,
        "color":  "\033[92m",   # green
    },
    {
        "name":   "Shortlisting Test",
        "module": "services.shortlisting_test.app:app",
        "port":   settings.PORT_TEST,
        "color":  "\033[93m",   # yellow
    },
    {
        "name":   "Coding Round",
        "module": "services.coding_test.app:app",
        "port":   settings.PORT_CODING,
        "color":  "\033[95m",   # magenta
    },
    {
        "name":   "Live HR",
        "module": "services.live_hr.app:app",
        "port":   settings.PORT_LIVEHR,
        "color":  "\033[96m",   # cyan
    },
]

RESET = "\033[0m"
BOLD  = "\033[1m"


def _banner():
    print(f"\n{BOLD}{'─'*55}")
    print("  Hiresy Backend — All Services")
    print(f"{'─'*55}{RESET}")
    for svc in SERVICES:
        print(f"  {svc['color']}●{RESET} {svc['name']:25s} → http://localhost:{svc['port']}")
    print(f"{BOLD}{'─'*55}{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="Start all Hiresy backend services")
    parser.add_argument("--reload", action="store_true", help="Enable hot-reload (dev mode)")
    args = parser.parse_args()

    _banner()

    procs: list[subprocess.Popen] = []

    for svc in SERVICES:
        cmd = [
            sys.executable, "-m", "uvicorn",
            svc["module"],
            "--host", "0.0.0.0",
            "--port", str(svc["port"]),
        ]
        if args.reload:
            cmd.append("--reload")

        print(f"  Starting {svc['color']}{svc['name']}{RESET} on port {svc['port']}...")
        proc = subprocess.Popen(
            cmd,
            cwd=_backend,
            env={**os.environ, "PYTHONPATH": _backend},
        )
        procs.append(proc)
        time.sleep(0.4)   # stagger startup slightly

    print(f"\n{BOLD}All services started.{RESET} Press Ctrl+C to stop.\n")

    def _shutdown(sig, frame):
        print(f"\n{BOLD}Shutting down all services...{RESET}")
        for proc in procs:
            try:
                proc.terminate()
            except Exception:
                pass
        for proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Keep alive
    while True:
        time.sleep(1)
        # Restart crashed services
        for i, proc in enumerate(procs):
            if proc.poll() is not None:
                svc = SERVICES[i]
                print(f"  {svc['color']}⚠ {svc['name']} crashed (exit {proc.returncode}) — restarting...{RESET}")
                cmd = [
                    sys.executable, "-m", "uvicorn",
                    svc["module"],
                    "--host", "0.0.0.0",
                    "--port", str(svc["port"]),
                ]
                if args.reload:
                    cmd.append("--reload")
                procs[i] = subprocess.Popen(
                    cmd, cwd=_backend,
                    env={**os.environ, "PYTHONPATH": _backend},
                )


if __name__ == "__main__":
    main()
