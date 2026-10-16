"""Launch installed sender, run independent compiled client, verify its report."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def main():
    sender_path = shutil.which("pathrate_snd")
    if not sender_path:
        raise RuntimeError("installed sender missing")
    consumer = Path(__file__).with_name("ohos_consumer").resolve()
    # Independent expected output calculated from fixed inputs: 5*256 + 9*1024.
    expected = (
        "pathrate-consumer-v1\nrtt_echoes=10\n"
        "round=41 train=1 packets=5 packet_bytes=256 received_bytes=1280\n"
        "round=42 train=2 packets=9 packet_bytes=1024 received_bytes=9216\n"
        "trains=2 packets=14 received_bytes=10496\n"
    )
    with tempfile.TemporaryDirectory(prefix="pathrate-consumer-f-",
                                     dir="/storage/Users/currentUser") as directory:
        work = Path(directory)
        report = work / "transfer-report.txt"
        with (work / "sender.log").open("w+") as log:
            environment = os.environ.copy()
            environment.pop("LD_PRELOAD", None)
            sender = subprocess.Popen([sender_path, "-q"], cwd=work,
                                      env=environment, stdout=log,
                                      stderr=subprocess.STDOUT)
            try:
                time.sleep(1)
                if sender.poll() is not None:
                    raise RuntimeError("sender exited before consumer connected")
                result = subprocess.run([str(consumer), str(report)], cwd=work,
                                        capture_output=True, text=True, timeout=30,
                                        env=environment)
                print(result.stdout, end="", flush=True)
                if result.returncode:
                    raise RuntimeError(result.stderr)
                if sender.wait(timeout=5) != 0:
                    raise RuntimeError("sender did not complete its session successfully")
                actual = report.read_bytes()
                if actual != expected.encode("ascii"):
                    raise RuntimeError(f"consumer report mismatch: {actual!r}")
                print(actual.decode("ascii"), end="", flush=True)
                print("PASS: independent HarmonyOS C consumer completed TCP/UDP "
                      "session and report matched fixed reference byte-for-byte", flush=True)
            finally:
                if sender.poll() is None:
                    sender.terminate()
                    try:
                        sender.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        sender.kill()
                        sender.wait(timeout=5)
                log.seek(0)
                print("Consumer sender log:\n" + log.read(), flush=True)


if __name__ == "__main__":
    main()
