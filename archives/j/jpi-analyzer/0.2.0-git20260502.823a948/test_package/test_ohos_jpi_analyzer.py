#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OHOS-specific tests for jpi-analyzer 0.2.0-git20260502.823a948 (HarmonyOS PC).

Upstream ships no test suite (commit 823a948 has no tests/, no pytest config,
no CI workflows -> NO_UPSTREAM_TESTS). These port-added tests cover this run's
actual OHOS adaptation points instead:

  OHOS-T1: the Conan-injected PYTHONPATH resolves the packaged jpi_analyzer
           AND its Conan dependency click inside the ohos-aarch64 target env
           (dependency closure travels through runenv, not site-packages).
  OHOS-T2: everything runs under the target interpreter of the ohos-aarch64
           profile (HarmonyOS device python: sys.platform == 'ohos', aarch64,
           >= 3.10).
  OHOS-T3: the packaged console scripts (jpi-analyzer, jpia) execute for real
           on the target platform and produce actual results end-to-end:
           a synthesized minimal .JPI sample is parsed by `info`, and `csv`
           decodes flight records and writes a real CSV with metric values
           (consumer-style e2e, not pure assertions).
"""

import os
import platform
import shutil
import struct
import subprocess
import sys

FAILED = []


def check(test_id, name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    line = f"{test_id} {status}: {name}"
    if detail:
        line += f" [{detail}]"
    print(line)
    if not cond:
        FAILED.append(name)
    return cond


# ---------------------------------------------------------------- JPI synthesis

def _rec(text):
    """One $-record of a JPI file: '$TEXT*XX\\r\\n' (XX = 2 checksum chars)."""
    return text.encode("ascii") + b"*00\r\n"


def _be(word):
    return struct.pack(">H", word)


def build_sample_jpi():
    """Build a minimal valid JPI EDM file (deterministic bytes).

    Layout follows upstream filespec.md: $-records header ($U/$T/$C/$F/$D/$L),
    then per-flight binary blocks. Model EDM830 without $P keeps Edm_Typ off
    (8-bit delta records); cfg bits enable E1 (bit 2), C1 (bit 11); BAT is
    always-on. Each 13-byte record: sync words 0x07/0x07, rep=0, control bytes
    {0x01,0x01,0x10}, sign bytes {0,0,0}, data deltas, filler.
    """
    out = bytearray()
    out += _rec("$U,N123XY")
    out += _rec("$T,6,15,26,12,34,56000")
    out += _rec("$C,830,1024,0,0,0,0,252,64,0")
    out += _rec("$F,0")
    out += _rec("$D,1,200")  # flight 1, size 200 words -> 400 bytes
    out += _rec("$L,0")

    flight = bytearray()
    flight += _be(1)                              # flight id
    flight += _be((1 << 2) | (1 << 11))           # cfg_word[0]: E1 + C1
    flight += _be(0)                              # cfg_word[1]
    flight += bytes([0])                          # fuel unit: gallons
    flight += bytes([65])                         # horsepower setting
    flight += _be(6)                              # record interval: 6 s
    flight += _be(15 | (6 << 5) | (26 << 9))      # date: 2026-06-15
    flight += _be(56 | (34 << 5) | (12 << 11))    # time: 12:34:56
    flight += bytes([0])                          # reserved
    egt = [2, 3, 1, 2, 0, 1, 3, 2, 1, 0, 2, 1]
    cht = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1]
    for i in range(12):
        flight += bytes([0x07, 0x07, 0x00, 0x01, 0x01, 0x10, 0x00, 0x00, 0x00,
                         egt[i % 12], cht[i % 12], (i * 3) % 250, 0x00])
    while len(flight) < 400:
        flight += bytes([0x07, 0x07, 0x00, 0x01, 0x01, 0x10, 0x00, 0x00, 0x00,
                         0, 0, 0, 0])
    out += flight[:400]
    out += _rec("$V Created by EDM830 VER 252 BLD 64 BETA 0")
    return bytes(out)


# ------------------------------------------------------------------ test steps

def t1_pythonpath_resolution():
    """OHOS-T1: imports resolve from the Conan-injected PYTHONPATH."""
    print("-- OHOS-T1: PYTHONPATH resolution of package + click in target env")
    try:
        import jpi_analyzer  # noqa: F401
        from jpi_analyzer import cli as jpi_cli
    except ImportError as exc:
        check("OHOS-T1", "jpi_analyzer importable in target env", False, str(exc))
        return None
    import click

    pyenv = os.environ.get("PYTHONPATH", "")
    ja_file = os.path.abspath(jpi_analyzer.__file__)
    ja_root = os.path.dirname(os.path.dirname(ja_file))
    click_root = os.path.dirname(os.path.dirname(os.path.abspath(click.__file__)))
    check("OHOS-T1", "jpi_analyzer resolved under a PYTHONPATH entry",
          any(ja_root == os.path.normpath(p)
              for p in pyenv.split(os.pathsep) if p),
          f"jpi_analyzer at {ja_root}; PYTHONPATH={pyenv}")
    check("OHOS-T1", "click dependency resolved under a PYTHONPATH entry",
          any(click_root == os.path.normpath(p)
              for p in pyenv.split(os.pathsep) if p),
          f"click at {click_root}")
    try:
        from importlib import metadata
        click_version = metadata.version("click")
    except Exception:
        click_version = getattr(click, "__version__", "0")
    parts = click_version.split(".")
    major_minor = (int(parts[0]), int(parts[1])) if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit() else (0, 0)
    check("OHOS-T1", "click satisfies upstream floor click>=8.1",
          major_minor >= (8, 1), click_version)
    check("OHOS-T1", "jpi_analyzer exposes CLI entry (cli.main)",
          hasattr(jpi_cli, "main"))
    return ja_root


def t2_target_platform():
    """OHOS-T2: running on the ohos-aarch64 target (HarmonyOS device python)."""
    print("-- OHOS-T2: target platform identity")
    check("OHOS-T2", "target interpreter is AArch64 (ohos-aarch64 profile)",
          platform.machine() == "aarch64", platform.machine())
    # HarmonyOS PC device python reports sys.platform == "ohos"
    # (observed: host 'HarmonyOS-HongMeng_Kernel', python 3.12.9)
    check("OHOS-T2", "target userspace is OHOS (sys.platform=='ohos')",
          sys.platform == "ohos", sys.platform)
    check("OHOS-T2", "device python >= 3.10 (upstream requires-python)",
          sys.version_info >= (3, 10), sys.version.split()[0])


def t3_cli_end_to_end(pkg_root):
    """OHOS-T3: packaged console scripts really execute on the target."""
    print("-- OHOS-T3: packaged CLI executes end-to-end on target")
    bin_dir = os.path.join(pkg_root, "bin")
    cli = os.path.join(bin_dir, "jpi-analyzer")
    alias = os.path.join(bin_dir, "jpia")
    if not check("OHOS-T3", "console scripts installed into <pkg>/bin",
                 os.path.isfile(cli) and os.path.isfile(alias),
                 f"{bin_dir}: {sorted(os.listdir(bin_dir)) if os.path.isdir(bin_dir) else 'missing'}"):
        return

    # OHOS /tmp can be read-only -> work under the (writable) build dir
    work = os.path.join(os.getcwd(), "jpi_ohos_e2e_work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    try:
        jpi_path = os.path.join(work, "sample.JPI")
        with open(jpi_path, "wb") as fh:
            fh.write(build_sample_jpi())

        env = dict(os.environ)  # carries conanrun PYTHONPATH/PATH

        r = subprocess.run([cli, "--file", jpi_path, "info"],
                           capture_output=True, text=True, env=env, timeout=120)
        check("OHOS-T3", "jpi-analyzer info exits 0 on target",
              r.returncode == 0, r.stderr.strip().splitlines()[-1] if r.returncode else "")
        check("OHOS-T3", "info reports synthesized tail number",
              "N123XY" in r.stdout)
        check("OHOS-T3", "info reports EDM830 model metadata",
              "EDM830" in r.stdout and "sw=252" in r.stdout)
        check("OHOS-T3", "info lists 1 decoded flight with valid data",
              "Flights:        1" in r.stdout and "valid=True" in r.stdout,
              r.stdout.strip().splitlines()[-1] if r.stdout else "")

        out_dir = os.path.join(work, "csvout")
        r2 = subprocess.run([cli, "--file", jpi_path, "csv",
                             "--flights", "all", "--out-dir", out_dir],
                            capture_output=True, text=True, env=env, timeout=120)
        check("OHOS-T3", "jpi-analyzer csv exits 0 on target",
              r2.returncode == 0, r2.stderr.strip().splitlines()[-1] if r2.returncode else "")
        csv_path = os.path.join(out_dir, "flight_1.csv")
        produced_csv = False
        lines = []
        if os.path.isfile(csv_path):
            with open(csv_path, "r") as fh:
                lines = [ln.rstrip("\r\n") for ln in fh if ln.strip()]
            produced_csv = (
                len(lines) >= 10
                and lines[0] == "datetime,E1,C1,DIF,CLD,BAT,MARK"
                and any(ln.startswith("2026-") for ln in lines[1:])
                and any(",242," in ln for ln in lines[1:])  # first decoded E1 value
            )
        check("OHOS-T3", "csv decodes flight records into flight_1.csv "
              "(header + >=10 rows + real EGT value 242)",
              produced_csv,
              f"lines={len(lines) if os.path.isfile(csv_path) else 0}")

        r3 = subprocess.run([alias, "--file", jpi_path, "info"],
                            capture_output=True, text=True, env=env, timeout=120)
        check("OHOS-T3", "jpia alias console script works on target",
              r3.returncode == 0 and "N123XY" in r3.stdout)
    finally:
        # always clean: the test_package build dir IS the worktree source dir,
        # so leftovers would pollute the candidate worktree
        shutil.rmtree(work, ignore_errors=True)


def main():
    print(f"host: {platform.platform()} | python {sys.version.split()[0]} "
          f"at {sys.executable}")
    pkg_root = t1_pythonpath_resolution()
    t2_target_platform()
    if pkg_root:
        t3_cli_end_to_end(pkg_root)
    else:
        check("OHOS-T3", "skipped: package root unknown (T1 failed)", False)

    print("")
    if FAILED:
        print(f"OHOS jpi-analyzer tests: {len(FAILED)} FAILED -> {FAILED}")
        sys.exit(1)
    print("OHOS jpi-analyzer tests: all PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
