#!/usr/bin/env python3
"""Exercise all three packaged programs through a real local UDP flow."""

import glob
import math
import os
import pathlib
import shutil
import subprocess
import tempfile
import time


PROGRAMS = ("pathchirp_snd", "pathchirp_rcv", "pathchirp_run")


def program(name):
    path = shutil.which(name)
    assert path and os.path.isfile(path), f"packaged {name} missing from PATH"
    return path


def check_versions():
    for name in PROGRAMS:
        result = subprocess.run([program(name), "-v"], capture_output=True,
                                text=True, timeout=10)
        output = result.stdout + result.stderr
        assert "pathChirp version 2.4.1" in output, (
            name, result.returncode, output)
    print("PASS: all three installed programs report their version", flush=True)


def check_ohos_loopback_storage():
    assert os.uname().sysname == "HarmonyOS", "requires a HarmonyOS PC device"
    user_storage = pathlib.Path("/storage/Users/currentUser")
    assert user_storage.is_dir(), "expected HarmonyOS PC user storage"
    with tempfile.TemporaryDirectory(prefix="pathchirp-d-", dir=user_storage) as work:
        logs = []
        processes = []
        try:
            for name, args in (("pathchirp_snd", ["-U", "28128"]),
                               ("pathchirp_rcv", [])):
                log = open(os.path.join(work, name + ".log"), "w+")
                logs.append(log)
                processes.append(subprocess.Popen([program(name), *args],
                                                  cwd=work, stdout=log,
                                                  stderr=subprocess.STDOUT))
            time.sleep(2)
            for name, proc in zip(PROGRAMS[:2], processes):
                assert proc.poll() is None, f"{name} exited before measurement"
            result = subprocess.run(
                [program("pathchirp_run"), "-S", "127.0.0.1", "-R",
                 "127.0.0.1", "-U", "28128", "-t", "12", "-n", "3",
                 "-l", "0.1", "-u", "1", "-a", "0.1"],
                cwd=work, capture_output=True, text=True, timeout=35)
            assert result.returncode == 0, result.stdout + result.stderr
            assert "Finished Experiment" in result.stdout + result.stderr, (
                result.stdout + result.stderr)
            output_files = glob.glob(os.path.join(work, "*.instbw"))
            assert output_files, "master did not write bandwidth estimates"
            samples = []
            for filename in output_files:
                with open(filename, encoding="ascii") as stream:
                    samples.extend(line.split() for line in stream if line.strip())
            assert samples, "bandwidth estimate file is empty: " + result.stdout + result.stderr
            assert all(len(row) == 2 and math.isfinite(float(row[0])) and math.isfinite(float(row[1])) and float(row[1]) >= 0 for row in samples), samples
            print(f"PASS: HarmonyOS loopback UDP measurement wrote {len(samples)} "
                  "samples in user storage", flush=True)
        finally:
            for proc in processes:
                proc.terminate()
            for proc in processes:
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
            for log in logs:
                log.seek(0)
                print(log.read(), flush=True)
                log.close()


if __name__ == "__main__":
    check_versions()
    check_ohos_loopback_storage()
