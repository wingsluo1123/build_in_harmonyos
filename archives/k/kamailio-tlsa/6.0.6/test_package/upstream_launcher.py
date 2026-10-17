"""Foreground/loopback launcher for adapted upstream startup shell tests."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

subprocess._USE_POSIX_SPAWN = False
arguments = sys.argv[1:]
filtered = []
i = 0
while i < len(arguments):
    if arguments[i] == "-l":
        i += 2  # Replace the upstream default port with a task-private port.
    else:
        filtered.append(arguments[i])
        i += 1
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
output = Path(os.environ["TLSA_UPSTREAM_RUN"])
with (output / "server.log").open("w") as log:
    process = subprocess.Popen(
        [os.environ["TLSA_CORE"], *filtered, "-DD", "-E", "-l", f"127.0.0.1:{port}"],
        stdout=log, stderr=log, start_new_session=True,
    )
(output / "owned-process.json").write_text(json.dumps({"pid": process.pid, "port": port}))
time.sleep(1)
if process.poll() is not None:
    raise SystemExit(process.returncode or 1)
raise SystemExit(0)
