#!/usr/bin/env python3
"""laptop-mode-tools 1.74 consumer test — OHOS smoke verification.

Checks the installed package: bin/laptop_mode exists, is executable, has a
POSIX sh shebang, all shipped scripts pass `bash -n`, `laptop_mode --version`
really executes and reports the expected version (works without an installed
/etc/laptop-mode config thanks to the OHOS runtime-portability patch), the
module/helper/config inventory is complete, and the OHOS-inapplicable
integration components (systemd/udev/init.d/pm-utils/polkit/GUI) are absent.
Exits non-zero on failure.
"""
import os
import subprocess
import sys

EXPECTED_VERSION = "1.74"


def run(cmd, cwd=None):
    env = dict(os.environ)
    if cwd is not None:
        env["PWD"] = cwd
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                          text=True)


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0

    def ok(msg):
        print("[ok] %s" % msg)

    def fail(msg):
        nonlocal failures
        failures += 1
        print("[FAIL] %s" % msg)

    # Assertion 1: main entry point present (L1e sabotage failure point).
    main_script = os.path.join(pkg_root, "bin", "laptop_mode")
    if not os.path.isfile(main_script):
        fail("%s missing" % main_script)
        return 1
    ok("bin/laptop_mode present")

    # Assertion 2: executable bit.
    if os.access(main_script, os.X_OK):
        ok("bin/laptop_mode is executable")
    else:
        fail("bin/laptop_mode is not executable")

    # Assertion 3: POSIX sh shebang.
    with open(main_script, "rt", encoding="utf-8", errors="replace") as f:
        shebang = f.readline().strip()
    if shebang.startswith("#!") and shebang.endswith("/sh"):
        ok("shebang: %s" % shebang)
    else:
        fail("unexpected shebang: %s" % shebang)

    # Assertion 4: --version really executes and reports the version.
    # (Runs the script with /bin/sh; no /etc/laptop-mode config needed.)
    r = run(["/bin/sh", main_script, "--version"], cwd=pkg_root)
    if r.returncode == 0 and "Laptop Mode Tools %s" % EXPECTED_VERSION in \
            (r.stdout + r.stderr):
        ok("--version reports Laptop Mode Tools %s" % EXPECTED_VERSION)
    else:
        fail("--version failed: rc=%d out=%r err=%r"
             % (r.returncode, r.stdout[-200:], r.stderr[-200:]))

    # Assertion 5: --help lists the subcommands.
    r = run(["/bin/sh", main_script, "--help"], cwd=pkg_root)
    if r.returncode == 0 and "status" in (r.stdout + r.stderr):
        ok("--help lists subcommands")
    else:
        fail("--help failed: rc=%d" % r.returncode)

    # Assertion 6: bash -n syntax check across the shipped scripts.
    bash = os.environ.get("BASH") or "/data/service/hnp/bin/bash"
    bad = []
    targets = []
    for rel in ("bin/laptop_mode", "bin/lm-profiler", "bin/lm-syslog-setup"):
        targets.append(os.path.join(pkg_root, rel))
    for group in ("modules", "module-helpers"):
        d = os.path.join(pkg_root, "usr/share/laptop-mode-tools", group)
        if os.path.isdir(d):
            targets += [os.path.join(d, f) for f in sorted(os.listdir(d))]
    if not targets:
        fail("no module/helper scripts found in package")
    for t in targets:
        if os.path.exists(t):
            r = run([bash, "-n", t])
            if r.returncode != 0:
                bad.append(t)
    if bad:
        fail("bash -n failed for: %s" % ", ".join(bad))
    else:
        ok("bash -n passed for %d scripts" % len(targets))

    # Assertion 7: module/helper/config inventory complete.
    modules_dir = os.path.join(pkg_root, "usr/share/laptop-mode-tools/modules")
    helpers_dir = os.path.join(pkg_root, "usr/share/laptop-mode-tools/module-helpers")
    conf_dir = os.path.join(pkg_root, "etc/laptop-mode/conf.d")
    n_modules = len(os.listdir(modules_dir)) if os.path.isdir(modules_dir) else 0
    n_helpers = len(os.listdir(helpers_dir)) if os.path.isdir(helpers_dir) else 0
    n_conf = (len([f for f in os.listdir(conf_dir) if f.endswith(".conf")])
              if os.path.isdir(conf_dir) else 0)
    if n_modules == 33:
        ok("33 modules installed")
    else:
        fail("expected 33 modules, found %d" % n_modules)
    if n_helpers >= 2:
        ok("%d module helpers installed" % n_helpers)
    else:
        fail("expected >=2 module helpers, found %d" % n_helpers)
    if n_conf == 31:
        ok("31 conf.d configuration files installed")
    else:
        fail("expected 31 conf.d files, found %d" % n_conf)
    conf_main = os.path.join(pkg_root, "etc/laptop-mode/laptop-mode.conf")
    if os.path.isfile(conf_main):
        ok("main laptop-mode.conf installed")
    else:
        fail("main laptop-mode.conf missing")

    # Assertion 8: OHOS-inapplicable integration components absent.
    present = [rel for rel in ("etc/init.d", "lib/udev", "lib/systemd",
                               "usr/lib/pm-utils", "usr/share/polkit-1",
                               "usr/share/applications")
               if os.path.exists(os.path.join(pkg_root, rel))]
    if present:
        fail("OHOS-inapplicable components present: %s" % ", ".join(present))
    else:
        ok("no systemd/udev/init.d/pm-utils/polkit/GUI components staged")

    if failures:
        print("%d assertion(s) failed" % failures)
        return 1
    print("all laptop-mode-tools consumer assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
