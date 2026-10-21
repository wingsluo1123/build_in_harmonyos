#!/usr/bin/env python3
"""Conan test_package for libkleo 25.12.3."""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibKleoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1.3", override=True)
        self.requires("gpgme/1.24.0.1")
        self.requires("libgpg-error/1.55")
        self.requires("boost/1.84.0")
        self.requires("kcompletion/6.18.0.2")
        self.requires("kcolorscheme/6.18.0.3")
        self.requires("kcodecs/6.18.0.1")
        self.requires("kconfig/6.18.0.1")
        self.requires("kcoreaddons/6.18.0.1", override=True)
        self.requires("ki18n/6.18.0.2")
        self.requires("kitemmodels/6.18.0.1")
        self.requires("kwidgetsaddons/6.18.0.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
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

        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                folder = dep.package_folder.replace("\\", "/")
                add_unique(prefixes, os.path.join(folder, "lib", "cmake"))
                add_unique(prefixes, folder)
                add_unique(libraries, os.path.join(folder, "lib"))
                add_unique(includes, os.path.join(folder, "include"))

        qtbase = self.dependencies.get("qtbase")
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
        cmake = CMake(self)
        cmake.configure()
        cmake.build()


    def _resign_runtime_links_guard(self):
        self._resign_runtime_libs()

    def _sign_ohos_elf(self, path):
        # OHOS 只加载带有效 .codesign 的 ELF；依赖件在缓存/复制过程中签名会失效，
        # 运行期会报 `Error loading shared library <lib>: (needed by <consumer>)`。
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(f"binary-sign-tool not found; skip signing {path}")
            return False
        objcopy = shutil.which("llvm-objcopy")
        if objcopy:
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}"',
                ignore_errors=True,
            )
        self.run(
            f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1',
            ignore_errors=True,
        )
        try:
            os.chmod(path, 0o755)
        except OSError as exc:
            self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
        return True

    def _resign_runtime_libs(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        seen = set()
        signed = 0
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for root, _dirs, files in os.walk(lib_dir):
                for name in files:
                    candidate = os.path.join(root, name)
                    if os.path.islink(candidate) or not os.path.isfile(candidate):
                        continue
                    real = os.path.realpath(candidate)
                    if real in seen:
                        continue
                    seen.add(real)
                    try:
                        with open(real, "rb") as handle:
                            if handle.read(4) != b"\x7fELF":
                                continue
                    except OSError:
                        continue
                    if self._sign_ohos_elf(real):
                        signed += 1
        self.output.info(f"Re-signed {signed} dependency runtime ELF file(s) for test_package")

    def test(self):
        self._resign_runtime_links_guard()
        self._prepare_runtime_links()
        env = Environment()
        test_home = os.path.join(self.build_folder, "test-home")
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("TMPDIR", test_tmp)
        env.define("TEMP", test_tmp)
        env.define("TMP", test_tmp)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
                env.prepend_path("XDG_DATA_DIRS", os.path.join(dep.package_folder, "share"))
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(qtbase.package_folder, "plugins", "platforms"),
            )
        env.define("QT_QPA_PLATFORM", "offscreen")
        for runtime_dir in self._runtime_dirs():
            env.prepend_path("LD_LIBRARY_PATH", runtime_dir)
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_libkleo"),
                cwd=self.cpp.build.bindirs[0],
                env=None,
            )

    def _runtime_dirs(self):
        return [
            self.build_folder,
            os.path.join(self.build_folder, "bin"),
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "bin")),
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]

    def _prepare_runtime_links(self):
        compatibility_dirs = self._runtime_dirs()
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            for src in glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")):
                for dst_dir in compatibility_dirs:
                    os.makedirs(dst_dir, exist_ok=True)
                    dst = os.path.join(dst_dir, os.path.basename(src))
                    target = os.path.realpath(src)
                    if os.path.realpath(dst) == target:
                        continue
                    if os.path.lexists(dst):
                        os.unlink(dst)
                    os.symlink(target, dst)
