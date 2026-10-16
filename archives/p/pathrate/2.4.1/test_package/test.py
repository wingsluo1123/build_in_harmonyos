"""Installed CLI and complete paced-loopback capacity measurement."""

import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time


def program(name):
    executable = shutil.which(name)
    assert executable and Path(executable).is_file(), f"missing installed {name}"
    return executable


def check_help():
    for name in ("pathrate_snd", "pathrate_rcv"):
        result = subprocess.run([program(name), "-h"], capture_output=True,
                                text=True, timeout=10)
        assert f"{name} options" in result.stdout + result.stderr, (
            name, result.returncode, result.stdout, result.stderr)
    print("PASS: both installed programs display their own options", flush=True)


def check_capacity_loopback():
    assert os.uname().sysname == "HarmonyOS", "requires a HarmonyOS PC"
    storage = Path("/storage/Users/currentUser")
    assert storage.is_dir(), "HarmonyOS PC user storage is unavailable"
    shim = Path(__file__).with_name("pace_udp.so").resolve()
    assert shim.is_file(), "UDP pacing shim was not built"

    with tempfile.TemporaryDirectory(prefix="pathrate-f-", dir=storage) as work:
        sender_log_path = Path(work) / "sender.log"
        with sender_log_path.open("w+") as sender_log:
            sender_env = os.environ.copy()
            sender_env["LD_PRELOAD"] = str(shim)
            sender = subprocess.Popen([program("pathrate_snd"), "-q"],
                                      cwd=work, env=sender_env,
                                      stdout=sender_log, stderr=subprocess.STDOUT)
            try:
                time.sleep(1)
                assert sender.poll() is None, "sender exited before receiver connected"
                receiver = subprocess.run(
                    [program("pathrate_rcv"), "-s", "127.0.0.1", "-Q"],
                    cwd=work, capture_output=True, text=True, timeout=600)
                output = receiver.stdout + receiver.stderr
                assert receiver.returncode == 0, output
                assert "Requested Quick Termination" in output, output
                match = re.search(
                    r"Final capacity estimate\s*:\s*([0-9.]+)\s+(\w+)\s+to\s+([0-9.]+)\s+(\w+)",
                    output)
                assert match, output
                low, high = float(match[1]), float(match[3])
                assert all(map(math.isfinite, (low, high))) and 0 < low <= high, output
                assert match[2] == match[4], output
                print(f"PASS: HarmonyOS paced UDP loopback estimated "
                      f"{low:g}–{high:g} {match[2]}", flush=True)
            finally:
                sender.terminate()
                try:
                    sender.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    sender.kill()
                    sender.wait(timeout=5)
                sender_log.seek(0)
                print("Sender log:\n" + sender_log.read(), flush=True)


if __name__ == "__main__":
    check_help()
    check_capacity_loopback()
