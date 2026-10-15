"""Run all registered Kannel checks with strict results and owned-session cleanup."""
import os
import signal
import subprocess
import sys
from pathlib import Path

root = Path.cwd().resolve()
shell = str(Path(sys.argv[1]).resolve())
home = os.environ.get("CONAN_HOME", "")
if not home or not root.is_relative_to(Path(home).resolve()):
    raise RuntimeError("Task-private Conan home must own the test build")
boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
uid = os.getuid()

def session_members(session, start):
    if Path("/proc/sys/kernel/random/boot_id").read_text().strip() != boot or os.getuid() != uid:
        raise RuntimeError("Test cleanup device identity drift")
    members = {}
    for directory in Path("/proc").iterdir():
        if not directory.name.isdigit():
            continue
        try:
            # OHOS denies reads of foreign /proc files, including PID 1.
            # Check directory ownership first; never inspect foreign sessions.
            try:
                owner_uid = directory.stat().st_uid
            except PermissionError:
                continue  # inaccessible directory is never a signal candidate
            if owner_uid != uid:
                continue
            fields = (directory / "stat").read_text().rsplit(") ", 1)[1].split()
            if int(fields[3]) != session or int(fields[19]) < int(start):
                continue
            if fields[0] == "Z":
                continue  # already exited; nothing can be signalled
            owner = next(line.split()[1:] for line in (directory / "status").read_text().splitlines()
                         if line.startswith("Uid:"))
            if owner != [str(uid)] * 4 or ("CONAN_HOME=" + home).encode() not in (directory / "environ").read_bytes().split(b"\0"):
                raise RuntimeError("Test session has an unowned process; no signal")
            members[int(directory.name)] = fields[19]
        except FileNotFoundError:
            continue
    return members

def cleanup_session(process, start):
    import time
    # A completed upstream shell can leave short-lived shutdown descendants.
    # Give those owned processes a bounded normal-exit grace before signals.
    for _ in range(15):
        if not session_members(process.pid, start):
            return False
        time.sleep(.2)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        members = session_members(process.pid, start)
        for pid, token in members.items():
            if session_members(process.pid, start).get(pid) == token:
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass
        if process.poll() is None:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
        for _ in range(15):
            if not session_members(process.pid, start):
                return bool(members)
            time.sleep(.2)
    raise RuntimeError("Owned check processes remain after cleanup")
checks = sorted([p.with_suffix("") for p in (root / "checks").glob("*.c")])
checks += sorted((root / "checks").glob("*.sh"))
if len(checks) != 14 or not all(p.is_file() for p in checks):
    raise RuntimeError("The complete 14-group upstream check inventory is required")
passed = 0
for check in checks:
    argv = [shell, str(check)] if check.suffix == ".sh" else [str(check)]
    with open(str(check) + ".stdout", "xb") as out, open(str(check) + ".stderr", "xb") as err:
        process = subprocess.Popen(argv, cwd=root, stdout=out, stderr=err,
                                   start_new_session=True)
        start = Path("/proc", str(process.pid), "stat").read_text().rsplit(") ", 1)[1].split()[19]
        try:
            rc = process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            raise RuntimeError("Upstream check timed out: " + check.name)
        finally:
            cleaned = cleanup_session(process, start)
    stderr = Path(str(check) + ".stderr").read_bytes()
    if rc or stderr:
        print(Path(str(check) + ".stdout").read_text(errors="replace"))
        print(stderr.decode(errors="replace"), file=sys.stderr)
        raise RuntimeError("Upstream check failed: {} rc={}".format(check.name, rc))
    passed += 1
    if cleaned:
        print("KANNEL_CHECK_OWNED_CLEANUP " + check.name, flush=True)
    print("KANNEL_UPSTREAM_PASS " + check.name, flush=True)
print("KANNEL_UPSTREAM_RESULT={}/14 PASS".format(passed), flush=True)
