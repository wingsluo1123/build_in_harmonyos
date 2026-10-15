#!/usr/bin/env python3
"""Consumer execution test for the kea 3.2.0 package: runs the packaged daemons.

The static probes (test_kea_api / test_ohos_platform / test_ohos_runtime)
cover the delivery surface (headers, libraries, ABI, closure); this driver
covers actual execution of the server binaries the package exists for:

* ``-v`` on all five executables reports the 3.2.0 version (daemon startup
  path + libkea-* linkage under the OHOS loader);
* ``-W`` on kea-dhcp4 and kea-dhcp-ddns prints the build config report - the
  path through the build-time generated config_report.cc (libkea-cfgrpt)
  that the platform script-execve patches feed;
* ``-t`` on kea-dhcp4 / kea-dhcp6 accepts a valid configuration (exit 0) and
  rejects broken ones (nonzero exit), i.e. the real parse/verify code runs.

Usage: test_kea_daemons.py <package-folder>
Exits non-zero on any failed check.
"""
import os
import subprocess
import sys
import tempfile

FAILURES = 0


def check(cond, what, detail=""):
    global FAILURES
    line = ("ok   - " if cond else "FAIL - ") + what
    if detail and not cond:
        line += " :: " + detail.strip().replace("\n", " ")[:300]
    print(line)
    if not cond:
        FAILURES += 1


def run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def write_conf(directory, name, text):
    path = os.path.join(directory, name)
    with open(path, "w") as handle:
        handle.write(text)
    return path


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: test_kea_daemons.py <package-folder>")
    bindir = os.path.join(sys.argv[1], "bin")

    # 1: version output of every packaged executable.
    for name in ("kea-dhcp4", "kea-dhcp6", "kea-dhcp-ddns", "kea-lfc",
                 "perfdhcp"):
        path = os.path.join(bindir, name)
        result = run([path, "-v"])
        output = result.stdout + result.stderr
        check(result.returncode == 0 and "3.2.0" in output,
              "{} -v reports 3.2.0".format(name), output)

    # 2: the config report (generated config_report.cc + libkea-cfgrpt).
    for name in ("kea-dhcp4", "kea-dhcp-ddns"):
        result = run([os.path.join(bindir, name), "-W"])
        output = result.stdout + result.stderr
        check(result.returncode == 0 and "3.2.0" in output
              and "Kea source configure results" in output,
              "{} -W prints the build config report".format(name), output)

    # 3: configuration check on valid and invalid configurations.
    workdir = tempfile.mkdtemp(prefix="kea-daemon-test-")
    dhcp4_good = write_conf(workdir, "dhcp4-good.json", """{
  "Dhcp4": {
    "interfaces-config": {"interfaces": []},
    "subnet4": [{"id": 1, "subnet": "192.0.2.0/24"}]
  }
}
""")
    dhcp4_unknown = write_conf(workdir, "dhcp4-unknown.json", """{
  "Dhcp4": {
    "interfaces-config": {"interfaces": []},
    "no-such-parameter": true,
    "subnet4": [{"id": 1, "subnet": "192.0.2.0/24"}]
  }
}
""")
    dhcp6_good = write_conf(workdir, "dhcp6-good.json", """{
  "Dhcp6": {
    "interfaces-config": {"interfaces": []},
    "subnet6": [{"id": 1, "subnet": "2001:db8:1::/64"}]
  }
}
""")
    dhcp6_unknown = write_conf(workdir, "dhcp6-unknown.json", """{
  "Dhcp6": {
    "interfaces-config": {"interfaces": []},
    "no-such-parameter": true,
    "subnet6": [{"id": 1, "subnet": "2001:db8:1::/64"}]
  }
}
""")
    dhcp4 = os.path.join(bindir, "kea-dhcp4")
    dhcp6 = os.path.join(bindir, "kea-dhcp6")

    result = run([dhcp4, "-t", dhcp4_good])
    check(result.returncode == 0, "kea-dhcp4 -t accepts a valid configuration",
          result.stdout + result.stderr)

    result = run([dhcp4, "-t", dhcp4_unknown])
    check(result.returncode != 0,
          "kea-dhcp4 -t rejects an unknown parameter",
          result.stdout + result.stderr)

    result = run([dhcp4, "-t", os.path.join(workdir, "missing.json")])
    check(result.returncode != 0, "kea-dhcp4 -t rejects a missing file",
          result.stdout + result.stderr)

    result = run([dhcp6, "-t", dhcp6_good])
    check(result.returncode == 0, "kea-dhcp6 -t accepts a valid configuration",
          result.stdout + result.stderr)

    result = run([dhcp6, "-t", dhcp6_unknown])
    check(result.returncode != 0,
          "kea-dhcp6 -t rejects an unknown parameter",
          result.stdout + result.stderr)

    if FAILURES == 0:
        print("kea/3.2.0 daemon execution check OK")
        return 0
    print("kea/3.2.0 daemon execution check FAILED ({:d} check(s))".format(FAILURES))
    return 1


if __name__ == "__main__":
    sys.exit(main())
