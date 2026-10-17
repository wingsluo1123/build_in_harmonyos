#!/usr/bin/env python3
"""Conan test_package for libquotient 0.8.0 (Qt6).

Consumer-side verification (R34: real API usage) of the exported
QuotientQt6 CMake package:

  * find_package(QuotientQt6 CONFIG) resolves through the project-installed
    QuotientQt6Config.cmake -- the recipe sets cmake_find_mode=none so
    CMakeDeps does not shadow it. The imported target is the bare
    ``QuotientQt6`` (upstream installs its export with no NAMESPACE), and
    the config's find_dependency(Qt6Gui/Qt6Network/Qt6Keychain) chain must
    resolve against the qtbase-sql-dbus and qtkeychain packages.
  * test_libquotient drives the public API headless (rule12 protocol: one
    TEST PASS/FAIL line per case, TEST SUMMARY, exit 1 on any failure):
    Connection homeserver property round trip, RoomMessageEvent JSON
    parsing/construction/fullJson(), and the loadEvent() dispatch path.
  * on OHOS, test_libquotient_elf.py checks the installed shared objects:
    libQuotientQt6.so.0.8.0 (plus the resolvable .so.0.8 / .so loader
    names) is an AArch64 ELF64 shared object carrying a .codesign section
    (package() re-signs after CMake rewrites RUNPATH on install) with
    basename-only DT_NEEDED entries; OHOS /storage forbids symlinks, so the
    recipe materializes the SOVERSION chain as real copies.

The build/test environment mirrors qtkeychain 0.14.2 (same dependency
stack: qtbase-sql-dbus + qtkeychain, merged in main).
"""
import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibQuotientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtkeychain/0.14.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))

        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase and qtbase.package_folder:
            add_unique(
                modules,
                os.path.join(qtbase.package_folder, "lib", "cmake", "Qt6", "platforms"),
            )

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132 (kitemviews 6.26.0 / kscreenlocker 6.7.2 precedent): the OHOS
        # SDK lld links against libxml2.so.16 shipped in the SDK's llvm/lib
        # directory, which CI workers may not export via LD_LIBRARY_PATH;
        # prepend it so CMake TryCompile can link.
        env = Environment()
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _prepare_runtime_links(self):
        runtime_dirs = {
            self.cpp.build.bindirs[0],
            self.build_folder,
        }
        lib_sources = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            for runtime_dir in runtime_dirs:
                os.makedirs(runtime_dir, exist_ok=True)
                dst = os.path.join(runtime_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)

    def test(self):
        self._prepare_runtime_links()
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
        env.define("QT_QPA_PLATFORM", "offscreen")
        # CI debuggability: a failed ctest case would otherwise only print a
        # bare "***Failed" line, with no cause at all.
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")

        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_libquotient")
        with env.vars(self).apply():
            # OHOS-specific artefact checks (rule12: platform-specific tests).
            if str(self.settings.os) in ("OHOS", "HarmonyOS"):
                package_folder = self.dependencies[self.tested_reference_str].package_folder
                script = os.path.join(self.recipe_folder, "test_libquotient_elf.py")
                interpreter = sys.executable or "python3"
                self.run(
                    " ".join(shlex.quote(x) for x in (interpreter, script, package_folder))
                )
            # Run the consumer test directly first: its per-case TEST
            # PASS/FAIL lines and any loader diagnostics must reach the CI
            # log even when a ctest failure would abort test() beforehand.
            self.run(shlex.quote(test_exe), cwd=self.cpp.build.bindirs[0])
            cmake = CMake(self)
            cmake.test()
