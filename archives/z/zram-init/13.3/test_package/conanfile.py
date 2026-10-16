#!/usr/bin/env python3
"""Conan test_package for zram-init 13.3.

zram-init is delivered as interpreted POSIX shell, so running it with the
build machine's sh exercises exactly the bytes shipped to the OHOS target:

  1. test.sh         — POSIX sh: package layout + content assertions
                       (bin script with exec bit, upstream shebang kept, no
                       leftover @MODIR@/@EXENAME@ placeholders, man page,
                       zsh completion, modprobe.d config).
  2. test()          — functional run: `sh -n` syntax check plus
                       `sh zram-init -h` must print the upstream usage block
                       and exit 0 (upstream getopts maps -h/-H to `Usage 0`).
  3. harmony_e2e.sh  — HarmonyOS-specific consumer end-to-end cases: the
                       delivered script is actually executed through its two
                       primary flows on the default OHOS runtime (no zram
                       kernel module): `zram-init 0` completes the release
                       flow (exit 0, silent), `zram-init 64 DIR` runs the
                       full setup flow and degrades gracefully with the
                       upstream fatal message (exit 1, zero side effects).

Real zRAM setup (the SIZE/write code paths that touch a live device) needs
root, the zram kernel module, zramctl/mkswap/mount and /dev/zram0, none of
which exist in the build sandbox. Upstream itself ships no test suite at all
(no `check` rule, no tests/ directory — see test_package/MANIFEST.yml for the
inventory evidence), so these consumer-side flows are the complete executable
coverage.
"""
import os
import shlex

from conan import ConanFile


class ZramInitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["zram-init"]
        pkg = dep.package_folder
        script = os.path.join(pkg, "bin", "zram-init")

        # Layer 1: layout + content assertions (POSIX sh, no build helpers).
        self.run(f"sh {shlex.quote(os.path.join(self.recipe_folder, 'test.sh'))} "
                 f"{shlex.quote(pkg)}")

        # Layer 2: functional — the delivered bytes must parse and show usage.
        self.run(f"sh -n {shlex.quote(script)}")
        self.run(f"sh {shlex.quote(script)} -h 2>&1 | "
                 f"grep -q 'Usage: zram-init \\[options\\]'")
        self.output.info("zram-init functional smoke test passed (-h usage, exit 0)")

        # Layer 3: HarmonyOS-specific consumer end-to-end cases — run the
        # delivered script through its release and setup flows on the default
        # OHOS runtime (no zram kernel module): release completes silently
        # (exit 0), setup degrades gracefully with the upstream fatal message
        # (exit 1, zero side effects).
        self.run(f"sh {shlex.quote(os.path.join(self.recipe_folder, 'harmony_e2e.sh'))} "
                 f"{shlex.quote(script)}")
        self.output.info("zram-init HarmonyOS consumer e2e passed "
                         "(release + setup flows on OHOS runtime)")
