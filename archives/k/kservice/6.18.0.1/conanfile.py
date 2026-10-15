#!/usr/bin/env python3
"""Conan recipe for kservice 6.18.0.1 on HarmonyOS PC.

kservice is a KDE Frameworks 6 library for desktop service discovery and the
KSycoca service cache (libKF6Service.so and kbuildsycoca6).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation for the
    initial KF baseline
  - BUILD_PYTHON_BINDINGS=OFF to avoid Shiboken/PySide requirements
  - CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON to keep optional docs out of the
    baseline package
  - BUILD_TESTING=ON and ctest execution for upstream autotests available in
    the current headless feature set
  - Dependencies: qtbase/6.11.1.3, kconfig/6.18.0.1, kcoreaddons/6.18.0.1,
    ki18n/6.18.0.2, ecm/6.26.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KserviceConan(ConanFile):
    name = "kservice"
    version = "6.18.0.1"
    description = "KDE Frameworks 6 - desktop service discovery"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kservice"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1.3")
        self.requires("kconfig/6.18.0.1")
        self.requires("kcoreaddons/6.18.0.1")
        self.requires("ki18n/6.18.0.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS/HarmonyOS 在 CMake 里没有完整平台模块，共享库默认拿不到 SONAME；
        # 不设会让消费者把**绝对路径**写进 DT_NEEDED，运行期加载失败（与 kio 配方同法）。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_PYTHON_BINDINGS"] = "OFF"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            for dep_name in ("kconfig", "kcoreaddons", "ki18n"):
                dep = self.dependencies.get(dep_name)
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

            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
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
        test_env.define("XDG_DATA_DIRS", self._prepare_test_mime_database())
        test_env.define("KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS", "1")
        self._prepare_xdg_menu_fixture(test_home)
        self._repair_absolute_needed_entries(self.build_folder)
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_xdg_menu_fixture(self, test_home):
        """上游 autotests 需要 XDG 菜单夹具 `applications.menu`，两个测试各有各的找法：

        * `ksycocatest::initTestCase()` **先删掉** `$HOME/.qttest/config/menus`，再用
          `QFile::copy(QFINDTESTDATA("test-applications.menu"), menusDir()+"/applications.menu")`
          自己拷贝 ⇒ 只往目标目录预放文件没用，必须让 `QFINDTESTDATA` 找得到**源文件**
          （其首选查找位置是测试二进制所在目录与当前工作目录）。
        * `ksycoca_xdgdirstest` 把 `XDG_CONFIG_DIRS` 设为 `<测试二进制目录>/data`，源码注释写明
          "The buildsystem copied applications.menus into bin/data/menus"。

        上游那步拷贝发生在 install/package 阶段，而本仓的测试跑在 `build()` 里，届时还不存在，
        因此在跑 ctest 前把夹具铺到上述所有查找点（`test_home` 也保留一份，便于诊断）。
        """
        sources = [
            os.path.join(self.source_folder, "autotests", "test-applications.menu"),
            os.path.join(self.build_folder, os.pardir, "autotests", "test-applications.menu"),
            os.path.join(self.build_folder, "autotests", "test-applications.menu"),
        ]
        source = next((path for path in sources if os.path.isfile(path)), None)
        if not source:
            self.output.warning("upstream test-applications.menu not found; cannot stage XDG menu fixture")
            return
        autotests_dir = os.path.dirname(source)
        bindirs = [
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, os.pardir, "bin"),
        ]
        # 夹具集合：菜单 + 各 `org.kde.*.desktop`（kservicetest 需要后者，它靠 QFINDTESTDATA 找源文件）
        fixtures = [source]
        try:
            fixtures += [
                os.path.join(autotests_dir, name)
                for name in sorted(os.listdir(autotests_dir))
                if name.endswith(".desktop")
            ]
        except OSError as exc:
            self.output.warning(f"cannot list autotests dir {autotests_dir}: {exc}")
        targets = []
        for fixture in fixtures:
            for bindir in bindirs:
                # ① QFINDTESTDATA 首选：与测试二进制同目录
                targets.append((fixture, os.path.join(bindir, os.path.basename(fixture))))
            # ③ ctest --test-dir 的工作目录
            targets.append((fixture, os.path.join(self.build_folder, os.path.basename(fixture))))
        for bindir in bindirs:
            # ② 上游注释里的 bin/data/menus（ksycoca_xdgdirstest 的 XDG_CONFIG_DIRS）
            targets.append((source, os.path.join(bindir, "data", "menus", "applications.menu")))
        targets.append((source, os.path.join(self.build_folder, "data", "menus", "applications.menu")))
        staged = 0
        for fixture, target in targets:
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(fixture, target)
                staged += 1
            except OSError as exc:
                self.output.warning(f"cannot stage fixture at {target}: {exc}")
        self.output.info(
            f"Staged {len(fixtures)} test fixture(s) ({', '.join(os.path.basename(f) for f in fixtures)}) "
            f"to {staged} location(s)"
        )

    def _prepare_test_mime_database(self):
        mime_root = os.path.join(self.build_folder, "test-mime", "share")
        mime_packages = os.path.join(mime_root, "mime", "packages")
        os.makedirs(mime_packages, exist_ok=True)
        mime_xml = os.path.join(mime_packages, "freedesktop.org.xml")
        with open(mime_xml, "w") as f:
            f.write(
                """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/octet-stream">
    <comment>unknown binary data</comment>
    <glob pattern="*.bin"/>
  </mime-type>
  <mime-type type="application/x-executable">
    <sub-class-of type="application/octet-stream"/>
    <glob pattern="*.exe"/>
  </mime-type>
  <mime-type type="text/plain">
    <comment>plain text document</comment>
    <glob pattern="*.txt"/>
  </mime-type>
  <mime-type type="text/html">
    <sub-class-of type="text/plain"/>
    <glob pattern="*.html"/>
    <glob pattern="*.htm"/>
  </mime-type>
  <mime-type type="text/x-csrc">
    <sub-class-of type="text/plain"/>
    <alias type="text/c-src"/>
    <glob pattern="*.c"/>
  </mime-type>
  <mime-type type="text/x-java">
    <sub-class-of type="text/plain"/>
    <glob pattern="*.java"/>
  </mime-type>
  <mime-type type="text/x-python">
    <sub-class-of type="text/plain"/>
    <glob pattern="*.py"/>
  </mime-type>
  <mime-type type="text/javascript">
    <sub-class-of type="text/plain"/>
    <sub-class-of type="application/x-executable"/>
    <glob pattern="*.js"/>
  </mime-type>
  <mime-type type="application/ecmascript">
    <sub-class-of type="text/javascript"/>
  </mime-type>
  <mime-type type="image/jpeg">
    <glob pattern="*.jpg"/>
    <glob pattern="*.jpeg"/>
  </mime-type>
  <mime-type type="image/png">
    <glob pattern="*.png"/>
  </mime-type>
  <mime-type type="application/pdf">
    <alias type="application/x-pdf"/>
    <glob pattern="*.pdf"/>
  </mime-type>
  <mime-type type="application/msword">
    <alias type="application/vnd.ms-word"/>
    <glob pattern="*.doc"/>
  </mime-type>
  <mime-type type="application/zip">
    <sub-class-of type="application/octet-stream"/>
    <glob pattern="*.zip"/>
  </mime-type>
  <mime-type type="application/x-7z-compressed">
    <sub-class-of type="application/octet-stream"/>
    <glob pattern="*.7z"/>
  </mime-type>
  <mime-type type="application/vnd.oasis.opendocument.text">
    <sub-class-of type="application/zip"/>
    <glob pattern="*.odt"/>
  </mime-type>
  <mime-type type="application/x-kns">
    <sub-class-of type="application/zip"/>
    <glob pattern="*.kns"/>
  </mime-type>
  <mime-type type="application/x-shellscript">
    <sub-class-of type="text/plain"/>
    <sub-class-of type="application/x-executable"/>
    <glob pattern="*.sh"/>
  </mime-type>
  <mime-type type="application/x-desktop">
    <sub-class-of type="text/plain"/>
    <glob pattern="*.desktop"/>
  </mime-type>
  <mime-type type="application/x-theme">
    <sub-class-of type="application/x-desktop"/>
    <glob pattern="*.theme"/>
  </mime-type>
  <mime-type type="x-scheme-handler/mailto">
    <comment>mailto URL handler</comment>
  </mime-type>
  <mime-type type="x-scheme-handler/someprotocol">
    <comment>test URL handler</comment>
  </mime-type>
</mime-info>
"""
            )
        mime_types = [
            "application/octet-stream",
            "application/x-executable",
            "text/plain",
            "text/html",
            "text/x-csrc",
            "text/x-java",
            "text/x-python",
            "text/javascript",
            "application/ecmascript",
            "image/jpeg",
            "image/png",
            "application/pdf",
            "application/msword",
            "application/zip",
            "application/x-7z-compressed",
            "application/vnd.oasis.opendocument.text",
            "application/x-kns",
            "application/x-shellscript",
            "application/x-desktop",
            "application/x-theme",
            "x-scheme-handler/mailto",
            "x-scheme-handler/someprotocol",
        ]
        for mime_type in mime_types:
            mime_entry = os.path.join(mime_root, "mime", *mime_type.split("/")) + ".xml"
            os.makedirs(os.path.dirname(mime_entry), exist_ok=True)
            with open(mime_entry, "w") as f:
                f.write(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">\n'
                    f'  <mime-type type="{mime_type}"/>\n'
                    '</mime-info>\n'
                )
        return mime_root

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
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
        self.cpp_info.libs = ["KF6Service"]
