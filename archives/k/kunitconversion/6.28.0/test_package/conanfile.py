#!/usr/bin/env python3
"""Conan test_package for kunitconversion 6.28.0.

Verifies that KF6UnitConversion resolves through CMake on a fresh consumer
and that the public API (Converter / Value / UnitCategory over the
compiled unit tables) computes real conversions against the packaged
binary (R34: real API usage), plus the SONAME/DT_NEEDED regression check
on the produced shared library (test_kunitconversion_ohos).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KUnitConversionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Mirror the recipe pins so the graph resolves to the same
        # binaries and the Qt6/KF6 configs are resolvable.
        self.requires("qtbase/6.11.1")
        self.requires("ki18n/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # KF6UnitConversion ships its own config (cmake_find_mode=none) and
        # its find_dependency(Qt6Core) chain plus the KF6 component configs
        # must be resolvable, so put every dependency's cmake dirs on the
        # search path (kcontacts 6.28.0 test_package precedent).
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
        # SDK's llvm/lib directory; CI workers may not export it via
        # LD_LIBRARY_PATH, which makes CMake's TryCompile fail. Prepend
        # every SDK revision present (same glob as the main recipe) so the
        # probe links on any worker (kcalendarcore 6.26.0 precedent).
        env = Environment()
        for sdk_llvm_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        self._prepare_runtime_links()
        env = Environment()
        for runtime_dir in self._runtime_dirs():
            env.prepend_path("LD_LIBRARY_PATH", runtime_dir)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("XDG_DATA_DIRS", os.path.join(dep.package_folder, "share"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_kunitconversion")
        ohos_test_exe = os.path.join(self.cpp.build.bindirs[0], "test_kunitconversion_ohos")
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )
            self.run(test_exe, cwd=self.cpp.build.bindirs[0])
            self.run(ohos_test_exe, cwd=self.cpp.build.bindirs[0])

    def _runtime_dirs(self):
        bindir = self.cpp.build.bindirs[0]
        return [
            bindir,
            os.path.normpath(os.path.join(bindir, os.pardir, os.pardir, "bin")),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, os.pardir, "bin")),
        ]

    def _prepare_runtime_links(self):
        # libKF6UnitConversion.so links the soname-less ki18n 6.26.0
        # library by bare name (patches/0002), but the published ki18n
        # artifact itself still carries a build-tree-relative NEEDED entry
        # ('../../bin/libKF6I18n.so'). Names containing '/' bypass
        # LD_LIBRARY_PATH and are opened against the process working
        # directory, so materialize every non-Qt dependency library in the
        # two compatibility layouts the run steps above use:
        # cwd = bindir      -> bindir/../../bin
        # cwd = build_folder -> build_folder/../../bin (ctest-spawned test,
        #                       add_test default working directory)
        # (kcontacts 6.18.0 / 6.28.0 precedent; HMDFS rejects symlink()
        # with EPERM -> plain-copy fallback, qzxing precedent.)
        compatibility_dirs = self._runtime_dirs()
        for compatibility_dir in compatibility_dirs:
            os.makedirs(compatibility_dir, exist_ok=True)
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            if dep.ref.name == "qtbase":
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for src in glob.glob(os.path.join(libdir, "lib*.so*")):
                target = os.path.realpath(src)
                for compatibility_dir in compatibility_dirs:
                    dst = os.path.join(compatibility_dir, os.path.basename(src))
                    if os.path.realpath(dst) == target:
                        continue
                    if os.path.lexists(dst):
                        os.unlink(dst)
                    try:
                        os.symlink(target, dst)
                    except OSError:
                        shutil.copy2(target, dst)
