import os
import signal
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTAL_CONFIGS = [
    ("customer", int(os.environ.get("CUSTOMER_PORT", "5001"))),
    ("merchant", int(os.environ.get("MERCHANT_PORT", "5002"))),
    ("admin", int(os.environ.get("ADMIN_PORT", "5003"))),
]

processes = []


def terminate_all(*_args):
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    sys.exit(0)


for role, port in PORTAL_CONFIGS:
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["PORTAL_ROLE"] = role
    env.setdefault("CUSTOMER_PORT", str(PORTAL_CONFIGS[0][1]))
    env.setdefault("MERCHANT_PORT", str(PORTAL_CONFIGS[1][1]))
    env.setdefault("ADMIN_PORT", str(PORTAL_CONFIGS[2][1]))

    process = subprocess.Popen([sys.executable, "app.py", str(port)], cwd=BASE_DIR, env=env)
    processes.append(process)
    print(f"[{role}] http://127.0.0.1:{port}")

signal.signal(signal.SIGINT, terminate_all)
signal.signal(signal.SIGTERM, terminate_all)

try:
    while True:
        exited = [proc for proc in processes if proc.poll() is not None]
        if exited:
            terminate_all()
        time.sleep(1)
except KeyboardInterrupt:
    terminate_all()
