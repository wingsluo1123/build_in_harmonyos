#!/usr/bin/env python3
"""test_package — spatialite-gui 2.1.0-beta1 (autotools GUI executable).

An application package, not a library: there is no header to compile against,
so the consumer test is a shell suite that inspects the packaged executable
rather than a CMake project that links it.

spatialite-gui has no --version/--help short circuit — MyApp::OnInit() builds
MyFrame and enters the event loop right away (Main.cpp:99-115) — and it cannot
be launched headlessly on this target (gtk/3.24.43 is broadway-only with no
broadwayd runtime; see wxwidgets-gtk3's notes.md). The suite therefore asserts
the artifact contract, and conanfile.py only locates and invokes it.
"""
import os
import shutil

from conan import ConanFile


class SpatialiteGuiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass

    def test(self):
        tested = self.dependencies[self.tested_reference_str]
        binary = os.path.join(tested.package_folder, "bin", "spatialite_gui")
        script = os.path.join(self.source_folder, "test_spatialite_gui.sh")

        if not os.path.isfile(script):
            raise Exception(f"missing test script: {script}")
        if not os.path.isfile(binary):
            raise Exception(
                f"packaged binary not found at {binary}; the recipe should fail "
                "rather than produce a package without it"
            )

        # OHOS: /system/bin/sh (mksh) cannot reliably execute ELF binaries, so
        # the suite is launched with bash like the other recipes in this repo.
        shell = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or shutil.which("sh")
            or "/data/service/hnp/bin/bash"
        )

        # conanrun puts every dependency's bin/ and lib/ on the search paths, so
        # the script's DT_NEEDED resolution check sees the real closure.
        # SG_LIB_DIR is injected as a shell-prefix assignment: conan 2's
        # ConanFile.run() has no "vars=" argument (that was Conan 1 thinking),
        # and a prefix assignment is version-independent shell semantics.
        lib_dirs = ":".join(
            dict.fromkeys(
                path
                for _ref, dep in self.dependencies.items()
                for path in dep.cpp_info.libdirs
            )
        )
        self.run(
            f'SG_LIB_DIR="{lib_dirs}" "{shell}" "{script}" "{binary}"',
            env="conanrun",
        )
