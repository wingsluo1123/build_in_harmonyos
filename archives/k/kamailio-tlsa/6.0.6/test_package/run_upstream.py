"""Run two upstream core cases with documented launch and CLI adaptations."""
import argparse
import json
import os
import pwd
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

subprocess._USE_POSIX_SPAWN = False
parser = argparse.ArgumentParser()
parser.add_argument("--host", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
source = Path(__file__).resolve().parent
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
results = []
for case in ("1", "18"):
    run = Path(tempfile.mkdtemp(prefix=case + "-", dir=output))
    shutil.copytree(source / "upstream", run, dirs_exist_ok=True)
    shutil.copytree(source / "upstream_support", run / "include")
    if case == "18":
        # OHOS app UIDs have no passwd entry; toybox id -u/-g can fail
        # despite the numeric identity being available from POSIX get*id.
        script = run / "18.sh"
        text = script.read_text().replace("$(id -u)", str(os.getuid()))
        text = text.replace("$(id -g)", str(os.getgid()))
        try:
            pwd.getpwuid(os.getuid())
        except KeyError:
            # App sandbox UID has no account entry. Retain the same actual
            # identity; account-switching coverage is explicitly excluded.
            text = text.replace(f" -u {os.getuid()} -g {os.getgid()}", "")
        # The upstream script disables TCP with -T, then configures its
        # children with -N: the same-version parser rejects this conflict.
        script.write_text(text.replace("-T -N 0", "-N 1"))
    common = run / "include/common"
    # Keep the original scripts in the source tree. Runtime copies adapt
    # the launch environment and 18.sh's obsolete CLI argument explicitly.
    launcher = run / "launch.sh"
    launcher.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " "
                        + shlex.quote(str(source / "upstream_launcher.py")) + ' "$@"\n')
    launcher.chmod(0o700)
    with common.open("a") as file:
        file.write("\nBIN=" + shlex.quote(str(launcher)) + "\n")
    env = os.environ.copy()
    env["TLSA_CORE"] = str(args.host.resolve() / "kamailio")
    env["TLSA_UPSTREAM_RUN"] = str(run)
    try:
        result = subprocess.run([shutil.which("bash"), str(run / (case + ".sh"))],
                                cwd=run, env=env, capture_output=True, text=True, timeout=30)
        (run / "stdout.log").write_text(result.stdout)
        (run / "stderr.log").write_text(result.stderr)
        passed = result.returncode == 0 and (run / "owned-process.json").is_file()
        if case == "18":
            negative = subprocess.run([env["TLSA_CORE"], "-f", "-", "-T", "-N", "0", "-c"],
                                      input="debug=0\nrequest_route { ; }\n",
                                      capture_output=True, text=True, timeout=10)
            (run / "invalid-N0.log").write_text(negative.stdout + negative.stderr)
            passed = passed and negative.returncode != 0 and "could not configure TCP children" in negative.stderr
            results.append({"name": "conflicting TCP disable/children options rejected", "exit_code": negative.returncode,
                            "pass": negative.returncode != 0 and "could not configure TCP children" in negative.stderr,
                            "kind": "added negative assertion"})
        results.append({"upstream": case + ".sh", "exit_code": result.returncode,
                        "pass": passed, "adaptation": "foreground supervisor; private loopback port"})
    finally:
        owned = run / "owned-process.json"
        if owned.is_file():
            pid = json.loads(owned.read_text())["pid"]
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
(output / "results.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
raise SystemExit(0 if len(results) == 3 and all(item["pass"] for item in results) else 1)
