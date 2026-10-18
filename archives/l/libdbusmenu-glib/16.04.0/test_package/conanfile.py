#!/usr/bin/env python3
"""Consumer-side test for libdbusmenu-glib: build a tiny client against
libdbusmenu-glib and exercise the core object surface (menu item
properties/children, server create/set_root/status) without a DBus
session — object-level assertions only."""
import os
import sys
import shlex
import tempfile
import stat
from pathlib import Path
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualRunEnv

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


def _private_temp_directory(prefix):
    rejected = []
    candidates = [os.environ.get("TMPDIR"), tempfile.gettempdir(),
                  "/data/storage/el2/base/cache", "/data/service/hnp/tmp",
                  str(Path.home())]
    seen = set()
    for value in candidates:
        if not value or value in seen:
            continue
        seen.add(value)
        manager = None
        try:
            supplied = Path(value)
            if not supplied.is_absolute():
                raise RuntimeError("relative parent")
            base = supplied.resolve(strict=True)
            if (not base.is_dir() or base.stat().st_uid != os.getuid()
                    or any(p.is_symlink() for p in (base, *base.parents))
                    or not os.access(base, os.W_OK | os.X_OK)):
                raise RuntimeError("parent ownership or write access")
            manager = tempfile.TemporaryDirectory(prefix=prefix, dir=str(base))
            private = Path(manager.name)
            metadata = private.lstat()
            if (private.is_symlink() or private.resolve(strict=True) != private
                    or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o700
                    or len(os.fsencode(private / "dbus-XXXXXXXXXXXXXXXX")) >= 108):
                raise RuntimeError("private owner, mode, canonical path or socket length")
            return manager
        except (OSError, RuntimeError) as error:
            if manager is not None:
                manager.cleanup()
            rejected.append(str(value) + ": " + type(error).__name__ + ": " + str(error))
    raise RuntimeError("No suitable UID-owned private POSIX temporary directory; "
                       + "; ".join(rejected))

class LibdbusmenuGlibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        command = executables.get("c")
        # A profile can supply an interpreter plus a real compiler wrapper.
        # CMake requires the executable and its mandatory arguments separately.
        if command and not Path(command).is_file():
            argv = shlex.split(command)
            if len(argv) > 1:
                executable = Path(argv[0])
                if not executable.is_absolute() or not executable.is_file():
                    raise ConanInvalidConfiguration("Compiler command requires an actual executable")
                toolchain.blocks["compilers"].values["compilers"]["C"] = str(executable)
                toolchain.variables["CMAKE_C_COMPILER_ARG1"] = shlex.join(argv[1:])
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            raise ConanInvalidConfiguration("Actual native consumer execution is required")
        directory = (Path(self.build_folder) / self.cpp.build.bindir).resolve()
        sign = Path(self.source_folder) / "sign_elf.py"
        if str(self.settings.os) == "OHOS":
            for name in ("dbusmenu_smoke", "dbusmenu_harmony"):
                self.run(shlex.join([sys.executable, str(sign), str(directory / name)]))
        self.run(shlex.join([str(directory / "dbusmenu_smoke")]), env="conanrun")
        if str(self.settings.os) == "OHOS":
            with _private_temp_directory("conan-dbusmenu-") as name:
                private = Path(name)
                if private.is_symlink() or private.stat().st_uid != os.getuid() or stat.S_IMODE(private.stat().st_mode) != 0o700:
                    raise ConanInvalidConfiguration("Invalid private Harmony test root")
                self.run(shlex.join([str(directory / "dbusmenu_harmony"), name]), env="conanrun")
