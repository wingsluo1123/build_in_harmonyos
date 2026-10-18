#!/usr/bin/env python3
"""Conan test_package — uget 2.2.3 (GTK+ download manager, executables).

test.sh drives the packaged `uget-gtk` / `uget-gtk-1to2` binaries through
headless behaviour: --version/--help are handled in main() before
gtk_init() (ui-gtk/UgtkApp-main.c:253-289) and the 1to2 migrator prints
its banner and exits EXIT_SUCCESS on argc==1, so no display is needed.
It prints the HMBS_TEST_PACKAGE_RESULT evidence marker.

On a cross-building container the binaries cannot run — the emulation
guest libc is stock musl without the OHOS-only fortified libc symbols
(__fd_chk/__memcpy_chk) referenced by the registry-built glib/gtk
(lcdproc/0.5.9 §8, transfuse/0.7.6 §5.1): the ELF64/AArch64 layout is
asserted statically there and the full runtime assertions execute on
native CI workers.

HMBS_UPSTREAM_TEST_RESULT: the 6 upstream noinst test programs (tests/)
run for real inside recipe build() whenever the build host can execute
them; the summary is persisted as res/upstream_test_result.json in the
package and re-emitted here.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class UgetTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _assert_elf_aarch64(self, path):
        """Static consumer check: packaged binary must be ELF64
        little-endian AArch64 (e_machine == 183 == 0xB7)."""
        with open(path, "rb") as f:
            head = f.read(20)
        if len(head) < 20 or head[:4] != b"\x7fELF":
            raise ConanException("not an ELF binary: %s" % path)
        if head[4] != 2 or head[5] != 1:
            raise ConanException("expected ELF64 little-endian: %s" % path)
        if head[18] != 0xB7 or head[19] != 0x00:
            raise ConanException("expected AArch64 ELF (e_machine=183): %s"
                                 % path)

    def test(self):
        package_folder = self.dependencies["uget"].package_folder
        bin_gtk = os.path.join(package_folder, "bin", "uget-gtk")
        bin_1to2 = os.path.join(package_folder, "bin", "uget-gtk-1to2")
        assert os.path.isfile(bin_gtk), "uget-gtk binary not found: %s" % bin_gtk
        assert os.path.isfile(bin_1to2), "uget-gtk-1to2 binary not found: %s" % bin_1to2
        self._assert_elf_aarch64(bin_gtk)
        self._assert_elf_aarch64(bin_1to2)

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = (os.environ.get("SHELL")
                     or shutil.which("bash") or "/bin/sh")
            cwd = os.environ.get("TMPDIR") or self.recipe_folder
            # uget-gtk dynamically links gtk/glib/curl/openssl: run the script
            # in the conanrun environment so the loader finds the dependency
            # .so files (VirtualRunEnv generates them).
            self.run('"%s" "%s" "%s" "%s"' % (
                shell, test_script, bin_gtk, bin_1to2), cwd=cwd, env="conanrun")
        else:
            summary = {
                "assertions": ("static: bin/uget-gtk + bin/uget-gtk-1to2 "
                               "present, ELF64 little-endian AArch64"),
                "runtime": "skipped",
                "reason": ("cross-building container cannot execute the OHOS "
                           "binaries: its emulation guest libc is stock musl "
                           "without the OHOS-only fortified libc symbols "
                           "(__fd_chk, __memcpy_chk, ...) referenced by the "
                           "registry-built glib/gtk (lcdproc/0.5.9 §8, "
                           "transfuse/0.7.6 §5.1); native CI workers run the "
                           "full test.sh"),
            }
            print("HMBS_TEST_PACKAGE_RESULT=%s"
                  % json.dumps(summary, ensure_ascii=False), flush=True)

        result_file = os.path.join(package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_file):
            raise ConanException(
                "upstream_test_result.json missing in package: %s — "
                "build() must have failed to persist the upstream test result"
                % result_file)
        with open(result_file, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(upstream, ensure_ascii=False), flush=True)
