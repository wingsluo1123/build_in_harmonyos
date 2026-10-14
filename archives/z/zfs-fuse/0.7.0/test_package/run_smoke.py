#!/usr/bin/env python3
"""zfs-fuse package smoke test (invoked via self.run from conanfile.py).

Executes the packaged binaries for real (R34: no print-only stub):
  1. zpool list CLI load smoke (daemonless, informational).
  2. Full user-space pool cycle under the zfs-fuse daemon:
     start daemon -> zpool create (file vdev) -> zfs list -> zdb -l label
     parse -> zpool destroy -> stop daemon.

Also re-emits the HMBS_UPSTREAM_TEST_RESULT marker persisted by the recipe's
build() into <package>/res/upstream_test_result.json, so upstream evidence
survives Conan cache hits ("Already installed!").

Usage: run_smoke.py <bin_dir>
"""

import json
import os
import subprocess
import sys
import tempfile
import time


def _writable_tmp():
    # [readonly_tmp]: HarmonyOS PC has read-only /tmp.
    for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
        val = (os.environ.get(key, "") or "").strip()
        if not val:
            continue
        try:
            os.makedirs(val, exist_ok=True)
            probe = os.path.join(val, ".hmbs-write-probe")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("ok")
            os.unlink(probe)
            return val
        except OSError:
            continue
    fallback = os.path.join(os.getcwd(), "_tmp")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def _find_upstream_evidence(base):
    for root, _dirs, files in os.walk(base):
        if "upstream_test_result.json" in files:
            return os.path.join(root, "upstream_test_result.json")
    return None


def main(bin_dir):
    for tool in ("zfs-fuse", "zpool", "zfs", "zdb", "ztest"):
        path = os.path.join(bin_dir, tool)
        if not (os.path.isfile(path) and os.path.getsize(path) > 0):
            print("HMBS_TEST_RESULT=" + json.dumps({
                "status": "failed", "framework": "package-smoke",
                "discovered": 1, "executed": 0, "passed": 0, "failed": 1,
                "skipped": 0,
                "notes": ["missing binary: %s" % tool]}))
            return 2
    tmp = _writable_tmp()
    run_dir = tempfile.mkdtemp(prefix="zfsfuse-test-", dir=tmp)
    os.makedirs(os.path.join(run_dir, "mnt"), exist_ok=True)
    env = dict(os.environ)
    env["ZFS_SOCK_DIR"] = run_dir
    env["ZPOOL_CACHE_DIR"] = run_dir
    env["ZFS_LOCK_DIR"] = run_dir
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")

    executed = 0
    failed = 0
    notes = []

    # 1) CLI smoke: zpool list before the daemon starts. The daemonless CLI
    # exits 1 ("failed to initialize ZFS library") by design — the load
    # itself is what we verify; the real check runs after daemon-start.
    probe = subprocess.run([os.path.join(bin_dir, "zpool"), "list"],
                           cwd=run_dir, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, encoding="utf-8",
                           errors="replace", timeout=60)
    if probe.returncode == 0:
        executed += 1
        notes.append("zpool-list=ok")
    elif "zpool" in (probe.stdout or "") or "zfs" in (probe.stdout or ""):
        executed += 1
        notes.append("zpool-list=cli-loaded(daemonless rc=%d)"
                     % probe.returncode)
    else:
        failed += 1
        notes.append("zpool-list=failed(rc=%d)" % probe.returncode)

    # 2) full pool cycle under the daemon
    daemon_log = os.path.join(run_dir, "daemon.log")
    with open(daemon_log, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [os.path.join(bin_dir, "zfs-fuse"), "--no-daemon",
             "--no-kstat-mount"],
            cwd=run_dir, env=env, stdout=log, stderr=subprocess.STDOUT)
    daemon_ok = False
    try:
        zpool = os.path.join(bin_dir, "zpool")
        for _ in range(30):
            if proc.poll() is not None:
                break
            probe = subprocess.run([zpool, "list"], cwd=run_dir, env=env,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=30)
            if probe.returncode == 0:
                daemon_ok = True
                break
            time.sleep(1)
        if daemon_ok:
            executed += 1
            notes.append("daemon-start=ok")
        else:
            failed += 1
            notes.append("daemon-start=failed")

        vdev = os.path.join(run_dir, "test.vdev")
        with open(vdev, "wb") as fh:
            fh.write(b"\0" * (64 * 1024 * 1024))
        mk = subprocess.run(
            [zpool, "create", "-m", "none",
             "-R", os.path.join(run_dir, "mnt"), "testpool", vdev],
            cwd=run_dir, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, encoding="utf-8", errors="replace",
            timeout=120)
        if mk.returncode == 0:
            executed += 1
            notes.append("zpool-create=ok")
            ls = subprocess.run([os.path.join(bin_dir, "zfs"), "list"],
                                cwd=run_dir, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, encoding="utf-8",
                                errors="replace", timeout=60)
            if "testpool" in (ls.stdout or ""):
                executed += 1
                notes.append("zfs-list=ok")
            else:
                failed += 1
                notes.append("zfs-list=failed")
            lb = subprocess.run([os.path.join(bin_dir, "zdb"), "-l", vdev],
                                cwd=run_dir, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, encoding="utf-8",
                                errors="replace", timeout=60)
            if "name: 'testpool'" in (lb.stdout or ""):
                executed += 1
                notes.append("zdb-label=ok")
            else:
                failed += 1
                notes.append("zdb-label=failed")
            de = subprocess.run([zpool, "destroy", "-f", "testpool"],
                                cwd=run_dir, env=env,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=120)
            if de.returncode == 0:
                executed += 1
                notes.append("zpool-destroy=ok")
            else:
                failed += 1
                notes.append("zpool-destroy=failed(rc=%d)" % de.returncode)
        else:
            failed += 1
            notes.append("zpool-create=failed: %s"
                         % (mk.stdout or "").strip().splitlines()[-1:])
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=30)
        except Exception:
            proc.kill()

    # re-emit upstream evidence from the package
    evidence = _find_upstream_evidence(os.path.dirname(bin_dir.rstrip("/")))
    if evidence:
        try:
            with open(evidence, "r", encoding="utf-8") as fh:
                marker = json.load(fh)
            line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker)
            print(line, flush=True)
        except Exception as exc:
            print("WARN: upstream evidence unreadable: %r" % exc, flush=True)
    else:
        print("WARN: upstream_test_result.json not shipped in package",
              flush=True)

    status = "passed" if failed == 0 and executed > 0 else "failed"
    marker = {
        "status": status,
        "framework": "package-smoke",
        "command": "zpool list + daemon zpool create/zfs list/zdb -l/destroy",
        "discovered": executed + failed,
        "executed": executed,
        "passed": executed,
        "failed": failed,
        "skipped": 0,
        "notes": notes,
    }
    line = "HMBS_TEST_RESULT=%s" % json.dumps(marker)
    print(line, flush=True)
    sys.stdout.flush()
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
