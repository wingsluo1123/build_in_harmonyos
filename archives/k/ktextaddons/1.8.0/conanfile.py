#!/usr/bin/env python3
"""Conan recipe for ktextaddons 1.8.0 on HarmonyOS PC."""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KTextAddonsConan(ConanFile):
    name = "ktextaddons"
    version = "1.8.0"
    description = "KDE text addon utilities for KF6 text editing consumers"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/libraries/ktextaddons"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Local staging for the unified Qt provider; remote CI waits for .3.
        self.requires("qtbase/6.11.1.3", override=True)
        self.requires("kcompletion/6.18.0.2", override=True)  # conflict convergence (preflight)
        self.requires("kcodecs/6.18.0.1", override=True)  # conflict convergence (preflight)
        self.requires("zstd/1.5.7.1", override=True)
        self.requires("zlib/1.3.2", override=True)
        self.requires("openssl/3.5.6.1", override=True)
        self.requires("kconfig/6.18.0.1", override=True)
        self.requires("kcolorscheme/6.18.0.3")
        # kguiaddons/6.18.0 的共享库没有 SONAME（消费者 DT_NEEDED 记绝对路径）；收敛到已发布的 6.18.0.1。
        self.requires("kguiaddons/6.18.0.1", override=True)
        self.requires("karchive/6.18.0")
        self.requires("kitemviews/6.18.0")
        self.requires("ktextwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0.1")
        self.requires("ki18n/6.18.0.2", override=True)
        self.requires("ksyntaxhighlighting/6.18.0")
        self.requires("kwidgetsaddons/6.18.0.1", override=True)
        self.requires("sonnet/6.18.0.1", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # OHOS/HarmonyOS 在 CMake 里没有完整平台模块，共享库默认拿不到 SONAME；
        # 不设会让消费者把**绝对路径**写进 DT_NEEDED，运行期加载失败（与 kio 配方同法，真机已验证）。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_QUICK"] = "OFF"
        tc.variables["BUILD_KIO_SUPPORT"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["OPTION_ADD_AUTOGENERATETEXT"] = "OFF"
        tc.variables["BUILD_TEXTAUTOCORRECTION"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6Keychain"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6MultimediaWidgets"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6TextToSpeech"] = "ON"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        self._restore_textautocorrection()
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
            self._run_upstream_tests()

    def _restore_textautocorrection(self):
        cmake_path = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_path, encoding="utf-8") as stream:
            source = stream.read()
        source = source.replace(
            "find_package(KF6WidgetsAddons ${KF_MIN_VERSION} CONFIG REQUIRED)\n",
            "find_package(KF6WidgetsAddons ${KF_MIN_VERSION} CONFIG REQUIRED)\n"
            "find_package(KF6Archive ${KF_MIN_VERSION} CONFIG REQUIRED)\n"
            "find_package(KF6ItemViews ${KF_MIN_VERSION} CONFIG REQUIRED)\n"
            "find_package(KF6TextWidgets ${KF_MIN_VERSION} CONFIG REQUIRED)\n",
            1,
        )
        # 0003 补丁已保留上游的 add_subdirectory(textautocorrection)，此处只在缺失时补，
        # 否则会写出两行同名 add_subdirectory → CMake 报 binary directory 已被占用。
        if "add_subdirectory(textautocorrection)\n" not in source:
            source = source.replace(
                "add_subdirectory(textaddonswidgets)\n",
                "add_subdirectory(textaddonswidgets)\nadd_subdirectory(textautocorrection)\n",
                1,
            )
        with open(cmake_path, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(source)

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            runtime_env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(qtbase.package_folder, "plugins", "platforms"),
            )
        for rel in (
            "bin",
            "lib",
            os.path.join("textaddonswidgets", "lib"),
            os.path.join("textemoticons", "core", "lib"),
            os.path.join("textemoticons", "widgets", "lib"),
            os.path.join("textcustomeditor", "lib"),
            os.path.join("textutils", "lib"),
        ):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        self._prepare_ctest_runtime_links()
        self._repair_absolute_needed_entries(self.build_folder)
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bins = {
            self.build_folder,
            os.path.join(self.build_folder, "bin"),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin")),
        }
        for root, _, files in os.walk(self.build_folder):
            if "CTestTestfile.cmake" in files:
                compatibility_bins.add(root)
                for depth in range(1, 5):
                    compatibility_bins.add(
                        os.path.normpath(
                            os.path.join(root, *([os.pardir] * depth), "bin")
                        )
                    )

        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            for compatibility_bin in sorted(compatibility_bins):
                os.makedirs(compatibility_bin, exist_ok=True)
                dst = os.path.join(compatibility_bin, os.path.basename(src))
                if not os.path.exists(src) or os.path.exists(dst):
                    continue
                if os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.extend(
            [
                os.path.join("/data/service/hnp/bin", name),
                os.path.join("/storage/Users/currentUser/usr/local/bin", name),
            ]
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_ohos_elf(self, path, required=True):
        signer = self._find_ohos_tool("binary-sign-tool")
        if not signer:
            if required:
                raise ConanException(
                    "Cannot locate OHOS binary-sign-tool for ELF signing"
                )
            self.output.warning(f"binary-sign-tool not found; cannot sign {path}")
            return False
        objcopy = self._find_ohos_tool("llvm-objcopy")
        if objcopy:
            self.run(
                f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                ignore_errors=True,
            )
        self.run(
            f"{self._quote(signer)} sign -inFile {self._quote(path)} "
            f"-outFile {self._quote(path)} -selfSign 1",
            ignore_errors=not required,
        )
        try:
            os.chmod(path, 0o755)
        except OSError as exc:
            self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
        return True

    def _sign_ohos_package_elfs(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        signed = 0
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                if self._sign_ohos_elf(path):
                    signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def _needed_entries(self, readelf, elf_path):
        try:
            probe = subprocess.run(
                [readelf, "-d", elf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
        except OSError as exc:
            self.output.warning(f"readelf failed for {elf_path}: {exc}")
            return []
        if probe.returncode != 0:
            return []
        entries = []
        marker = "Shared library: ["
        for line in probe.stdout.splitlines():
            if marker not in line:
                continue
            entries.append(line.split(marker, 1)[1].split("]", 1)[0])
        return entries

    def _runtime_library_map(self, extra_roots=()):
        libraries = {}
        roots = []
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                roots.append(os.path.join(dep.package_folder, "lib"))
                roots.append(os.path.join(dep.package_folder, "bin"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            roots.append(os.path.join(self.build_folder, rel))
        roots.extend(root for root in extra_roots if root)
        for root in dict.fromkeys(os.path.normpath(root) for root in roots):
            if not os.path.isdir(root):
                continue
            for current, dirs, files in os.walk(root):
                dirs[:] = [name for name in dirs if name != "CMakeFiles"]
                for name in files:
                    path = os.path.join(current, name)
                    if os.path.isfile(path) and ".so" in name:
                        libraries.setdefault(name, path)
        return libraries

    def _iter_runtime_elfs(self, extra_roots=()):
        roots = []
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                roots.append(os.path.join(dep.package_folder, "lib"))
        roots.extend(root for root in extra_roots if root)
        for root in dict.fromkeys(os.path.normpath(root) for root in roots):
            if not os.path.isdir(root):
                continue
            for current, dirs, files in os.walk(root):
                dirs[:] = [name for name in dirs if name != "CMakeFiles"]
                for name in files:
                    path = os.path.join(current, name)
                    if self._is_elf(path):
                        yield path

    @staticmethod
    def _is_conan_cache_needed_path(needed):
        return os.path.isabs(needed) and "/.cache/conan2/" in needed.replace("\\", "/")

    def _link_needed_library(self, source, target):
        if os.path.lexists(target):
            try:
                if os.path.exists(target) and os.path.samefile(source, target):
                    return False
            except OSError:
                pass
            if os.path.exists(target) and not os.path.islink(target):
                return False
            os.unlink(target)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            os.symlink(source, target)
        except OSError:
            shutil.copy2(source, target)
        return True

    def _repair_absolute_needed_entries(self, base_folder):
        """KF6 链上部分依赖没有 SONAME，消费者因此把绝对路径写进 DT_NEEDED；
        该路径在测试机上可能不存在（构建机本地缓存路径），或指向被复制后
        签名失效、OHOS 加载器拒绝加载的库。这里按 basename 在依赖包中找同名库：
        路径缺失就软链过去，路径存在就重新自签名。"""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        readelf = self._find_ohos_tool("llvm-readelf") or self._find_ohos_tool("readelf")
        if not readelf:
            self.output.warning("llvm-readelf/readelf not found; skip absolute NEEDED repair")
            return
        libraries = self._runtime_library_map((base_folder,))
        linked = 0
        resigned = 0
        missing = []
        handled = set()
        for elf_path in self._iter_runtime_elfs((base_folder,)):
            for needed in self._needed_entries(readelf, elf_path):
                if not self._is_conan_cache_needed_path(needed):
                    continue
                key = os.path.realpath(needed)
                if key in handled:
                    continue
                handled.add(key)
                source = libraries.get(os.path.basename(needed))
                if not source:
                    missing.append(needed)
                    continue
                if os.path.lexists(needed):
                    if os.path.islink(needed) or not self._is_elf(needed):
                        continue
                    self._sign_ohos_elf(needed, required=False)
                    resigned += 1
                    continue
                if self._link_needed_library(source, needed):
                    linked += 1
        if linked or resigned:
            self.output.info(
                f"Repaired absolute DT_NEEDED entries: {linked} linked, {resigned} re-signed"
            )
        if missing:
            self.output.warning(
                "No source found for DT_NEEDED entries: "
                + ", ".join(sorted(set(missing))[:8])
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_ohos_package_elfs()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = [
            "KF6TextCustomEditor",
            "KF6TextEmoticonsWidgets",
            "KF6TextEmoticonsCore",
            "KF6TextAddonsWidgets",
            "KF6TextUtils",
            "KF6TextAutoCorrectionWidgets",
        ]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
