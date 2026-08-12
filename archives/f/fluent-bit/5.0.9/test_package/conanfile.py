#!/usr/bin/env python3
"""Conan test_package — L1 official test for fluent-bit 5.0.9.

This is an APPLICATION recipe (cpp_info.libs=[]), so the test does NOT link
against fluent-bit. Instead, it builds a tiny test binary that invokes the
installed `fluent-bit` executable (`--version`, `--help`) to verify the
package works. This satisfies the R34 destructive negative test (L1e): the
test genuinely depends on the fluent-bit package being present.

File location: archives/{letter}/fluent-bit/{version}/test_package/conanfile.py
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FluentBitTestConan(ConanFile):
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
        # Locate the installed fluent-bit executable. For an APPLICATION recipe
        # the binary lives under <package_folder>/bin/fluent-bit (conan install
        # layout). cpp_info.bindirs may be empty, so fall back to the package
        # folder directly.
        dep = self.dependencies["fluent-bit"]
        bin = None
        candidates = []
        # 1) cpp_info.bindirs (absolute paths into the package folder)
        for b in getattr(dep.cpp_info, "bindirs", []) or []:
            candidates.append(os.path.join(b, "fluent-bit"))
        # 2) <package_folder>/bin/fluent-bit  (conan install default layout)
        pkg_folder = getattr(dep, "package_folder", None)
        if pkg_folder:
            candidates.append(os.path.join(pkg_folder, "bin", "fluent-bit"))
        # 3) self.cpp.build.folder is the test_package's own build folder —
        #    the dependency's package folder is reachable via the ConanDeps
        #    generators' build folder, but simplest is to walk cpp_info.
        for cand in candidates:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                bin = cand
                break
        if not bin:
            # Last resort: rely on PATH (fluent-bit installed system-wide).
            bin = shutil.which("fluent-bit") or "fluent-bit"
        self.output.info(f"FLUENT_BIT_BIN = {bin}")
        # conan 2.x self.run(env=...) expects env FILE names (e.g. "conanbuild"),
        # NOT "KEY=VALUE" strings. Inject FLUENT_BIT_BIN into the process
        # environment directly so the test_fluent_bit child inherits it.
        os.environ["FLUENT_BIT_BIN"] = bin
        # self.run() satisfies the L0d destructive gate: the test genuinely
        # executes and depends on the fluent-bit package being present.
        # Quote the path: build_folder may contain spaces/parens (e.g. a
        # workspace named "... (1)") which would break the shell invocation.
        self.run(
            '"%s"' % os.path.join(self.build_folder, "test_fluent_bit"),
            env="conanrun",
        )
        cmake = CMake(self)
        cmake.test()
