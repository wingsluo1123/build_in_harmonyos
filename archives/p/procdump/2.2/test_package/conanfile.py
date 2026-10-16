#!/usr/bin/env python3
"""test_package for procdump 2.2 — consumer-side verification of the packaged CLI.

Three layers, because this recipe is a cross-compiled application:

* static assertions (always run): the installed tree layout, the man page, and --
  most importantly -- that the aarch64 executable really carries the ~10 MB CLR
  profiler blob upstream embeds with `ld -r -b binary`. A build that silently
  skipped the embed step would still link and still pass a plain "binary runs"
  check, so the blob is asserted by content, not by size.
* runtime assertions (run whenever the packaged binary can actually execute here):
  `procdump -?` must print the usage block and must not die from a signal. With
  patch 0004 the usage request always goes through GetOptions() (any euid), so
  the expected exit code is 255 for both root and non-root workers.
* upstream execution layer (rule4/rule12): the non-dotnet integration scenarios
  from the upstream 2.2 tag are executed for real (see
  upstream_tests/run_upstream_ohos.sh) -- each launches a real load process, the
  packaged procdump monitors it, and a dump file must (not) appear. That is a
  genuine end-to-end consumer use case (rule12). The layer first probes the
  platform's capabilities (euid / PTRACE_SEIZE / PTRACE_ATTACH / /proc/<pid>/mem,
  plus gcore presence and target-process identity) and prints the raw evidence, so
  every skip is evidence-backed instead of a bare "no environment". Scenarios are
  then handled in three classes: 7 that need no dump backend are really executed,
  14 that assert "a dump file appears" are skipped while the backend is missing
  (they are NOT counted as passed), and the 19 dotnet_* scenarios are counted as
  blocked (OHOS has no .NET/CoreCLR diagnostics pipe).

HOW EXECUTABILITY IS DECIDED (2026-10-16): by *running* the packaged binary, not
by the host machine name. A cross host that has an aarch64 binfmt/qemu layer can
execute the artifact, and a host whose `platform.machine()` says aarch64 may still
fail to load the OHOS libc. The probe distinguishes the two by the observable
outcome (banner + usage block vs. loader error / 127), and the reason is printed.
When the binary genuinely cannot execute, the runtime layer and the upstream
execution layer are reported as deferred explicitly rather than silently skipped.
"""
import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


def _host_machine_is_target():
    """Fast path only. `can_run()` knows nothing about conan's os=OHOS, so it
    happily reports True on an x86_64 Linux host and the test then dies on
    'Error relocating ...'. The authoritative answer comes from _can_execute()."""
    return platform.machine().lower() in ("aarch64", "arm64")


def _pick_bash():
    """OHOS: /system/bin/sh (mksh) cannot exec ELF binaries, so a real bash is
    required. Fall back to whatever bash exists on the host running conan (a
    local x86_64 host with an aarch64 exec layer has no /data/service/hnp/bin)."""
    for cand in (os.environ.get("CONFIG_SHELL"), "/data/service/hnp/bin/bash",
                 shutil.which("bash"), "/bin/bash", "/bin/sh"):
        if cand and os.path.exists(cand):
            return cand
    return "/bin/sh"


def _can_execute(bash, procdump_bin):
    """Return (ok, reason). Decide by running the packaged binary once: a host
    that cannot execute the OHOS aarch64 artifact fails at load time (127 /
    'Error relocating' / 'cannot execute'), while a host that can prints the
    upstream banner and the usage block (exit 255 by design, see test.sh [11])."""
    try:
        p = subprocess.run([bash, "-c", "'%s' -?" % procdump_bin.replace("'", "'\\''")],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    except Exception as exc:                      # noqa: BLE001 - reported, not raised
        return False, "exec probe could not run (%s: %s)" % (type(exc).__name__, exc)
    out = (p.stdout or b"").decode("utf-8", "replace")
    if "ProcDump v" in out and "Capture Usage" in out:
        return True, ("exec probe OK: '<bin> -?' printed the banner and usage block, "
                      "rc=%d" % p.returncode)
    first = out.strip().splitlines()[0] if out.strip() else "<no output>"
    return False, ("exec probe says the artifact does not execute here "
                   "(rc=%d, first line: %s)" % (p.returncode, first))


class ProcdumpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = _pick_bash()
        pkg = self.dependencies["procdump"].package_folder
        procdump_bin = os.path.join(pkg, "bin", "procdump")
        runner = os.path.join(self.recipe_folder, "upstream_tests",
                              "run_upstream_ohos.sh")

        if can_run(self) and _host_machine_is_target():
            executes, reason = True, "host machine reports %s" % platform.machine()
        else:
            executes, reason = _can_execute(bash, procdump_bin)
        self.output.info("executability: " + reason)

        if executes:
            self.run("%s test.sh --execute" % bash, env="conanrun")
            # rule4/rule12: 上游测试真实执行层。先做平台能力探测并打印原始证据，
            # 再逐类处置（7 个无需转储的场景真跑；缺转储后端的 14 个有据跳过、
            # 不计入 passed；19 个 dotnet_* 如实阻塞）。CC 取自 profile conf。
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict)
            cc = compilers.get("c", "clang")
            self.run("%s '%s' '%s' '%s' %s"
                     % (bash, runner, procdump_bin, cc, bash), env="conanrun")
        else:
            self.output.info("the packaged aarch64 executable cannot execute on this "
                             "host; runtime assertions and the upstream execution layer "
                             "are deferred to an aarch64/OHOS runner, static assertions "
                             "still enforced.")
            self.run("%s test.sh --static-only" % bash, env="conanrun")
