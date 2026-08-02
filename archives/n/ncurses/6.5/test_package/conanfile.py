import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidate = executables.get("c")
        if self._is_usable_executable(candidate):
            return candidate
        candidate = self._ohos_toolchain_compiler()
        if self._is_usable_executable(candidate):
            return candidate
        return os.environ.get("CC") or shutil.which("clang") or "clang"

    def _ohos_toolchain_compiler(self):
        home = os.environ.get("HOME")
        if self.settings.os != "OHOS" or not home:
            return None
        return os.path.join(home, "validation", "toolchain-bin", "ohos-clang")

    def _is_usable_executable(self, path):
        if not path:
            return False
        return not os.path.isabs(path) or os.access(path, os.X_OK)

    def build(self):
        dep = self.dependencies["ncurses"].cpp_info
        includes = " ".join(f"-I{shlex.quote(path)}" for path in dep.includedirs)
        libdirs = " ".join(f"-L{shlex.quote(path)}" for path in dep.libdirs)
        libs = " ".join(f"-l{lib}" for lib in dep.libs)
        self.run(
            f"{shlex.quote(self._compiler())} test_ncurses.c -o test_ncurses "
            f"{includes} {libdirs} {libs}"
        )

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self.run("TERM=xterm-256color ./test_ncurses", env="conanrun")
        self.run("TERM=xterm-256color tput colors >/dev/null", env="conanrun")
