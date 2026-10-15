#!/usr/bin/env python3
"""two-ms 5.2.4 消费者用例 + 交付形态自检 + 鸿蒙特有用例。

用法:
    python3 consumer_check.py <package_folder> [--expect-machine aarch64]
                              [--require-signature] [--expect-version 5.2.4]

消费者用例（C1–C7）**真跑交付出来的 bin/2ms**，断言真实 stdout / stderr / 退出码：
  * C1 版本串来自构建期 `-X github.com/checkmarx/2ms/v5/cmd.Version=5.2.4`；
  * C3/C4 复刻上游 tests/e2e_test.go 的 filesystem 扫描语义（含 secret → 退出码 2，
    `--ignore-on-exit results` → 0），并解析 --report-path 产出的 JSON 报告；
  * C6 是上游错误路径（engine 错误 → 退出码 1）。

鸿蒙特有用例（H1）——OHOS/HarmonyOS 专有，≥1：
  * H1 校验交付 ELF 带 .codesign 段（knowledge E128：鸿蒙 execve 前置条件）、
    为 aarch64 静态 ELF，并且**在本机真实执行成功**。

交付形态自检（M1–M13）检查二进制本体与包内容物，不依赖任何外部资源。
任一 check 失败 → 退出码 1（R34 反空壳：把 bin/ 挪走后本脚本必然失败）。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

_MACHINE_ID = {"aarch64": 0xB7, "x86_64": 0x3E}
_CODESIGN = b".codesign"
_WORKDIR_MARKERS = (b"conan-go-build", b".go-work")

# 与上游 tests/e2e_test.go:generateFileWithSecret 同形的假凭据（GitHub PAT 形态）
_FAKE_SECRET = "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"


class Report(object):
    def __init__(self):
        self.ok = 0
        self.fail = 0
        self.note = 0

    def check(self, condition, label):
        if condition:
            self.ok += 1
            print("        [ok] %s" % label)
        else:
            self.fail += 1
            print("        [FAIL] %s" % label)
        return bool(condition)

    def skip(self, label):
        self.note += 1
        print("        [skip] %s" % label)


def _run(binary, args, timeout=120):
    proc = subprocess.Popen([binary] + args, cwd="/",
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return None, "", "timeout after %ss" % timeout
    return (proc.returncode, out.decode("utf-8", "replace"),
            err.decode("utf-8", "replace"))


def _elf(data):
    ei_class, ei_data = data[4], data[5]
    e_machine = int.from_bytes(data[18:20], "little")
    e_phoff = int.from_bytes(data[32:40], "little")
    e_phentsize = int.from_bytes(data[54:56], "little")
    e_phnum = int.from_bytes(data[56:58], "little")
    ptypes = []
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        if off + 4 > len(data):
            break
        ptypes.append(int.from_bytes(data[off:off + 4], "little"))
    return ei_class, ei_data, e_machine, ptypes


def _iter_entries(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            yield dirpath, name
        for name in dirnames:
            yield dirpath, name


def main(argv):
    if len(argv) < 2:
        print("usage: consumer_check.py <package_folder> [options]")
        return 2
    package_folder = os.path.abspath(argv[1])
    expect_machine = "aarch64"
    require_signature = False
    expect_version = "5.2.4"
    rest = argv[2:]
    while rest:
        opt = rest.pop(0)
        if opt == "--expect-machine":
            expect_machine = rest.pop(0)
        elif opt == "--require-signature":
            require_signature = True
        elif opt == "--expect-version":
            expect_version = rest.pop(0)
        else:
            print("unknown option: %s" % opt)
            return 2

    report = Report()
    bin_dir = os.path.join(package_folder, "bin")
    binary = os.path.join(bin_dir, "2ms")
    print("[step] package folder: %s" % package_folder)
    print("[step] binary: %s" % binary)
    print("[step] expect machine=%s version=%s require_signature=%s"
          % (expect_machine, expect_version, require_signature))

    if not os.path.isfile(binary):
        print("[FAIL] bin/2ms missing — nothing to test")
        return 1

    with open(binary, "rb") as handle:
        data = handle.read()

    workdir = tempfile.mkdtemp(prefix="two-ms-consumer-")
    try:
        secret_dir = os.path.join(workdir, "with-secret")
        clean_dir = os.path.join(workdir, "clean")
        os.makedirs(secret_dir)
        os.makedirs(clean_dir)
        with open(os.path.join(secret_dir, "secret.txt"), "w") as fh:
            fh.write("bla bla bla\nGitHubToken: %s\nbla bla bla\n" % _FAKE_SECRET)
        with open(os.path.join(clean_dir, "ok.txt"), "w") as fh:
            fh.write("nothing sensitive here\n")

        # ── C: 消费者用例（真跑交付出来的二进制）──────────────────
        print("[step] C1: 2ms --version")
        code, out, err = _run(binary, ["--version"])
        report.check(code == 0, "C1 exit code 0 (got %s)" % code)
        report.check(out == "2ms version %s\n" % expect_version,
                     "C1 stdout == '2ms version %s' (got %r)"
                     % (expect_version, out))

        print("[step] C2: 2ms --help")
        code, out, err = _run(binary, ["--help"])
        report.check(code == 0, "C2 exit code 0 (got %s)" % code)
        report.check("2ms Secrets Detection" in out,
                     "C2 stdout carries the upstream app banner")
        report.check("filesystem" in out and "Scan Commands" in out,
                     "C2 stdout documents the scan commands")

        print("[step] C3: filesystem scan finds the planted secret (exit 2)")
        report_c3 = os.path.join(workdir, "report_with_secret.json")
        code, out, err = _run(binary, ["filesystem", "--path", secret_dir,
                                       "--report-path", report_c3])
        report.check(code == 2, "C3 exit code 2 when secrets are found (got %s)"
                     % code)
        found = None
        if os.path.isfile(report_c3):
            with open(report_c3, "r", encoding="utf-8", errors="replace") as fh:
                found = fh.read()
        report.check(found is not None, "C3 --report-path report written")
        if found is not None:
            try:
                parsed = json.loads(found)
            except ValueError:
                parsed = None
            report.check(isinstance(parsed, dict) and parsed.get("totalSecretsFound", 0) >= 1,
                         "C3 report totalSecretsFound >= 1")
            report.check(_FAKE_SECRET in found,
                         "C3 report carries the planted secret value")

        print("[step] C4: same scan with --ignore-on-exit results exits 0")
        code, out, err = _run(binary, ["filesystem", "--path", secret_dir,
                                       "--report-path",
                                       os.path.join(workdir, "r4.json"),
                                       "--ignore-on-exit", "results"])
        report.check(code == 0,
                     "C4 exit code 0 with --ignore-on-exit results (got %s)" % code)

        print("[step] C5: clean directory scan finds nothing (exit 0)")
        report_c5 = os.path.join(workdir, "report_clean.json")
        code, out, err = _run(binary, ["filesystem", "--path", clean_dir,
                                       "--report-path", report_c5])
        report.check(code == 0, "C5 exit code 0 on a clean tree (got %s)" % code)
        if os.path.isfile(report_c5):
            with open(report_c5, "r", encoding="utf-8", errors="replace") as fh:
                clean_text = fh.read()
            try:
                clean_parsed = json.loads(clean_text)
            except ValueError:
                clean_parsed = {}
            report.check(clean_parsed.get("totalSecretsFound", 1) == 0,
                         "C5 clean scan reports 0 secrets")

        print("[step] C6: missing path is an engine error (exit 1)")
        code, out, err = _run(binary, ["filesystem", "--path",
                                       "/no/such/two-ms-dir-xyz",
                                       "--report-path",
                                       os.path.join(workdir, "r6.json")])
        report.check(code == 1, "C6 exit code 1 on a missing path (got %s)" % code)

        print("[step] C7: 2ms rules lists the built-in rule set")
        code, out, err = _run(binary, ["rules"])
        report.check(code == 0, "C7 exit code 0 (got %s)" % code)
        report.check(len(out.strip()) > 0, "C7 stdout is non-empty")

        # ── H: 鸿蒙特有用例（OHOS/HarmonyOS 专有）──────────────────
        print("[step] H1 (HMOS): signed aarch64 static ELF that really executes")
        ei_class, ei_data, e_machine, ptypes = _elf(data)
        if require_signature:
            report.check(_CODESIGN in data,
                         "H1 [HMOS] .codesign section present (E128 execve "
                         "precondition)")
            report.check(3 not in ptypes,
                         "H1 [HMOS] statically linked (no PT_INTERP pointer "
                         "into missing /lib/ld.so)")
            report.check(e_machine == _MACHINE_ID[expect_machine],
                         "H1 [HMOS] e_machine 0x%X == %s"
                         % (e_machine, expect_machine))
            code, out, err = _run(binary, ["--version"])
            report.check(code == 0 and out.strip().endswith(expect_version),
                         "H1 [HMOS] delivered binary execve's on this OHOS host "
                         "and reports its version")
        else:
            report.skip("H1 [HMOS] signature checks not required on %s"
                        % expect_machine)

        # ── M: 交付形态自检 ───────────────────────────────────────
        print("[step] M1: bin/2ms exists")
        report.check(os.path.isfile(binary), "M1 bin/2ms is a regular file")

        print("[step] M2: plausible binary size")
        size = os.path.getsize(binary)
        report.check(5 * 1024 * 1024 <= size <= 300 * 1024 * 1024,
                     "M2 size %d bytes within 5MiB..300MiB" % size)

        print("[step] M3: owner execute bit")
        report.check(os.access(binary, os.X_OK),
                     "M3 binary is executable by the current user")

        print("[step] M4: ELF magic")
        report.check(data[:4] == b"\x7fELF",
                     "M4 starts with the ELF magic (got %r)" % data[:4])

        print("[step] M5: ELF machine is %s" % expect_machine)
        report.check(ei_class == 2 and ei_data == 1,
                     "M5 ELF64 little-endian (class=%d data=%d)" % (ei_class, ei_data))
        report.check(e_machine == _MACHINE_ID[expect_machine],
                     "M5 e_machine 0x%X == %s (0x%X)"
                     % (e_machine, expect_machine, _MACHINE_ID[expect_machine]))

        print("[step] M8: bin/ contains only the delivered binary")
        entries = sorted(os.listdir(bin_dir))
        report.check(entries == ["2ms"],
                     "M8 bin/ listing is exactly ['2ms'] (got %r)" % entries)

        print("[step] M9: license shipped")
        license_path = os.path.join(package_folder, "licenses", "LICENSE")
        license_text = ""
        if os.path.isfile(license_path):
            with open(license_path, "r", encoding="utf-8", errors="replace") as fh:
                license_text = fh.read()
        report.check("Apache License" in license_text and "Version 2.0" in license_text,
                     "M9 licenses/LICENSE is the upstream Apache-2.0 text (%d bytes)"
                     % len(license_text))

        print("[step] M10-M12: package content hygiene")
        go_sources, hidden, objects = [], [], []
        for dirpath, name in _iter_entries(package_folder):
            rel = os.path.relpath(os.path.join(dirpath, name), package_folder)
            if name.endswith(".go") or name in ("go.mod", "go.sum") \
                    or name.endswith(".test"):
                go_sources.append(rel)
            if name.startswith(".") or name in ("__pycache__", "go-build"):
                hidden.append(rel)
            if name.endswith((".o", ".a", ".c", ".s", ".h")):
                objects.append(rel)
        report.check(not go_sources,
                     "M10 no Go sources/module files in the package (got %r)"
                     % go_sources[:5])
        report.check(not hidden,
                     "M11 no hidden files or build caches in the package (got %r)"
                     % hidden[:5])
        report.check(not objects,
                     "M12 no intermediate object/source files in the package (got %r)"
                     % objects[:5])

        print("[step] M13: build work directory path not embedded (-trimpath)")
        embedded = [marker.decode() for marker in _WORKDIR_MARKERS if marker in data]
        report.check(not embedded,
                     "M13 binary embeds no build work-dir marker (got %r)" % embedded)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("[summary] consumer checks: %d passed, %d failed, %d skipped"
          % (report.ok, report.fail, report.note))
    if report.fail:
        print("[summary] two-ms consumer check FAILED")
        return 1
    print("[summary] two-ms consumer check PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
