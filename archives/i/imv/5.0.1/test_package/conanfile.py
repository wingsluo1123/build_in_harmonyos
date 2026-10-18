#!/usr/bin/env python3
"""Consumer test for imv 5.0.1.

imv is a GUI/CLI application (package_type = application), so the consumer
contract is "the shipped artifacts run and behave like imv". The assertions
are performed by src/test_imv.sh against the installed package (R34: removing
bin/ must make the test fail).

Three groups of assertions, all against the *installed* package:

  1. run bin/imv-msg for real (argument handling + AF_UNIX connect attempt);
  2. check the bin/imv artifact itself (executable, .codesign non-empty,
     DT_NEEDED of the window/GL/imaging stack);
  3. diagnostic group: bin/imv cannot be exec'd on this platform because the
     published wayland package ships libwayland-cursor.so.0 with an invalid
     .codesign (measured: dlopen -> "Permission denied", i.e. EACCES, while
     libwayland-client/libwayland-egl load fine; see notes.md). The script
     builds a re-signed copy of that one library and preloads it, then runs
     `imv -h` and asserts the upstream help text (version + 9 backends). This
     proves the imv artifact itself is sound; if the signing tools are missing
     the group is reported as SKIP instead of failing the build.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class ImvTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["imv"].package_folder
        bindir = os.path.join(pkg, "bin")
        for name in ("imv", "imv-msg"):
            binary = os.path.join(bindir, name)
            if not os.path.isfile(binary):
                raise ConanException(f"imv: installed binary missing: {binary}")
        self.output.info(f"imv: testing installed binaries in {bindir}")

        script = os.path.join(self.source_folder, "src", "test_imv.sh")
        if not os.path.isfile(script):
            raise ConanException(f"imv: consumer test script missing: {script}")

        # the wayland dependency is needed by group 3 (re-signed preload copy)
        wayland_lib = None
        try:
            wayland_lib = os.path.join(
                self.dependencies["wayland"].package_folder, "lib")
        except Exception:
            pass

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cmd = f'{bash} "{script}" "{bindir}"'
        if wayland_lib and os.path.isdir(wayland_lib):
            cmd += f' "{wayland_lib}"'
        # env="conanrun" puts every dependency libdir on LD_LIBRARY_PATH
        self.run(cmd, env="conanrun")
        self.output.info("imv: consumer test finished")
