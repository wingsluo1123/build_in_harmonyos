#!/usr/bin/env python3
"""evemu test_package — consumer level (L1) test.

Two independent checks, both strictly device independent:

  1. a C + C++ consumer links against the packaged libevemu and calls the
     real API (mirrors upstream test/test-c-compile.c and test-cxx-compile.c);
  2. the packaged CLI is exercised on its *information face* only: an invalid
     option must print the upstream usage banner.

No check below opens /dev/input/* or /dev/uinput, and none of them asserts
that input events can be captured or replayed.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EvemuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # musl resolves shared objects through DT_RPATH / LD_LIBRARY_PATH, and
        # neither `evemu-record` nor the packaged libevemu.so.3 carries an
        # RPATH that reaches the Conan cache, so the whole host dependency
        # closure (libevdev included) has to be on LD_LIBRARY_PATH.
        # NOTE: inside a test_package `self.package_folder` points at the
        # test_package folder itself, not at the package under test — resolve
        # everything through the dependency graph.
        _libdirs = []
        for _dep in self.dependencies.values():
            for _libdir in _dep.cpp_info.libdirs:
                if os.path.isdir(_libdir) and _libdir not in _libdirs:
                    _libdirs.append(_libdir)
        _pkg = self.dependencies["evemu"].package_folder
        if os.path.isdir(os.path.join(_pkg, "lib")):
            _libdirs.insert(0, os.path.join(_pkg, "lib"))
        _old = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(_libdirs) + (
            os.pathsep + _old if _old else "")

        cmake = CMake(self)
        cmake.test()

        # Information-face assertion: `--bogus-option` reaches upstream
        # usage() through the getopt_long default branch of
        # tools/evemu-record.c before any device node is touched, and that
        # path returns rc = 1 (evemu-record.c: `int rc = 1;`, the success
        # assignment `rc = 0;` sits only after a successful recording).
        # The return code is asserted explicitly instead of being masked,
        # and the assertion itself is the upstream usage banner.
        _exe = os.path.join(_pkg, "bin", "evemu-record")
        _out = os.path.join(self.build_folder, "evemu-record.usage.txt")
        _p = subprocess.run([_exe, "--bogus-option"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with open(_out, "wb") as _fh:
            _fh.write(_p.stdout)
        if _p.returncode != 1:
            raise Exception("evemu-record --bogus-option expected rc=1, got %d"
                            % _p.returncode)
        self.run(f'grep -q "Usage:" "{_out}"')
        self.run(f'grep -q "autorestart" "{_out}"')
