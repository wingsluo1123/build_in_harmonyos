#!/usr/bin/env python3
"""Conan test_package for libkdegames 24.12.3.

Verifies that the KDEGames6/KDEGames6Private libraries can be found via
CMake (upstream KDEGames6Config.cmake) and that core APIs (KGameClock,
KGameTheme, KGamePopupItem) are callable (R34: real API usage).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibkdegamesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Cover the full find_dependency() chain of KDEGames6Config.cmake:
        # Qt6Widgets/Xml/Network/Qml/Svg + KF6Config/ConfigWidgets/Completion.
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        # karchive must be overridden exactly like the package under test: the
        # newest kiconthemes/6.18.0 revision asks for karchive/6.19.0 while
        # knewstuff/6.18.0 wants 6.18.0, so a plain requires() would make this
        # standalone test graph unresolvable.
        self.requires("karchive/6.18.0", override=True)
        self.requires("kcolorscheme/6.18.0")
        self.requires("kcompletion/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        # Runtime NEEDED of libKDEGames6.so (OpenAL audio backend).
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Collect every dependency lib dir (plus the package under test) so
        # the ctest ENVIRONMENT property can carry a complete LD_LIBRARY_PATH
        # (ctest replaces the test process env when ENVIRONMENT is set).
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    lib_dirs.append(lib_dir)
        # Mirror the build-tree-relative NEEDED entries of the KF6 packages
        # (e.g. "../../bin/libKF6*.so") into a flat bin dir so the loader can
        # resolve them. Use copies instead of symlinks: the CI sandbox
        # forbids mkfifo and can also deny symlink creation on HMDFS, which
        # would silently drop entries (observed as
        # "Error loading shared library ../../bin/libKF6*.so" in CI while the
        # local run passed).
        # The mirror is 300+ MB, so it lives in conan's build folder and not
        # in the recipe tree (a copy under test_package/ would sit untracked
        # next to the sources). run_test.sh cds into <root>/sub/sub so that
        # "../../bin/<lib>" resolves inside <root>.
        loader_root = os.path.join(self.build_folder, "loader-root")
        tp_bin = os.path.join(loader_root, "bin")
        run_cwd = os.path.join(loader_root, "sub", "sub")
        os.makedirs(tp_bin, exist_ok=True)
        os.makedirs(run_cwd, exist_ok=True)
        for dep in self.dependencies.values():
            if not (dep and dep.package_folder):
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                for name in os.listdir(libdir):
                    if not (
                        name.startswith("libKF6")
                        or name.startswith("libKDEGames")
                        or name.startswith("libQt6")
                    ):
                        continue
                    if not (name.endswith(".so") or ".so." in name):
                        continue
                    link = os.path.join(tp_bin, name)
                    if os.path.exists(link):
                        continue
                    source = os.path.join(libdir, name)
                    try:
                        shutil.copy2(source, link)
                    except OSError as exc:
                        self.output.warning(
                            f"copy2({source}, {link}) failed: {exc}"
                        )
        lib_dirs.append(tp_bin)

        tc = CMakeToolchain(self)
        tc.cache_variables["LKG_TEST_LIB_DIRS"] = ":".join(lib_dirs)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        # Expose all KF6/Qt6 deps so find_dependency() chains resolve.
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
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d: test() must self.run() the compiled test executable. The
        # run_test.sh wrapper re-exports the complete LD_LIBRARY_PATH (all
        # dependency lib dirs collected here) plus the offscreen Qt platform
        # and execs the binary, so any loader error is printed directly into
        # the conan create log (diagnosable in CI) and the exit code
        # propagates. ctest is not used for the final assertion because its
        # ENVIRONMENT property replaces the process environment, which has
        # proven fragile across CI workers.
        lib_dirs = [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ]
        loader_root = os.path.join(self.build_folder, "loader-root")
        lib_dirs.append(os.path.join(loader_root, "bin"))
        env = Environment()
        env.append("LD_LIBRARY_PATH", lib_dirs)
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("LKG_TEST_LIB_DIRS", ":".join(lib_dirs))
        env.define(
            "LKG_TEST_RUN_CWD", os.path.join(loader_root, "sub", "sub")
        )
        with env.vars(self).apply():
            exe = os.path.join(self.cpp.build.bindirs[0], "test_libkdegames")
            wrapper = os.path.join(self.source_folder, "run_test.sh")
            # 用 sh 显式解释 wrapper：git 检出的脚本在部分文件系统（含 HMDFS、
            # core.filemode=false 的构建机）上没有可执行位，直接执行会 exit 126。
            self.run(f'/bin/sh "{wrapper}" "{exe}"')
