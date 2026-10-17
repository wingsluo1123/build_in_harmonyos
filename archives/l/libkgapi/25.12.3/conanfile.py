#!/usr/bin/env python3
"""Conan recipe for libkgapi 25.12.3 on HarmonyOS PC."""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibKGAPIConan(ConanFile):
    name = "libkgapi"
    version = "25.12.3"
    description = "KDE PIM Google API library"
    license = "LGPL-2.1-only OR LGPL-3.0-only"
    homepage = "https://invent.kde.org/pim/libkgapi"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _libraries = (
        "KPim6GAPIBlogger",
        "KPim6GAPICalendar",
        "KPim6GAPICore",
        "KPim6GAPIDrive",
        "KPim6GAPILatitude",
        "KPim6GAPIMaps",
        "KPim6GAPIPeople",
        "KPim6GAPITasks",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1.3", override=True)
        self.requires("ki18n/6.18.0.2", override=True)  # conflict convergence (preflight)
        self.requires("kcodecs/6.18.0.1", override=True)  # conflict convergence (preflight)
        self.requires("kconfig/6.18.0.1", override=True)  # conflict convergence (preflight)
        self.requires("kcoreaddons/6.18.0.1", override=True)  # conflict convergence (preflight)
        self.requires("qtdeclarative/6.11.1.2", override=True)
        self.requires("kcalendarcore/6.18.0")
        self.requires("kcontacts/6.18.0")
        self.requires("kwallet/6.18.0")
        self.requires("cyrus-sasl/2.1.28.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_SASL_PLUGIN"] = "ON"
        tc.variables["KGAPI_BUILD_EXAMPLES"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths()
        tc.generate()

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep_name in self._preferred_dependency_order():
            dep = self._dependency(dep_name) or self._dependency(dep_name, build=True)
            if dep and dep.package_folder:
                self._add_package_folder(dep.package_folder, prefixes, libraries, includes)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                self._add_package_folder(dep.package_folder, prefixes, libraries, includes)

        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            add_unique(
                modules,
                os.path.join(qtbase.package_folder, "lib", "cmake", "Qt6", "platforms"),
            )

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

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

    @staticmethod
    def _add_package_folder(folder, prefixes, libraries, includes):
        normalized = folder.replace("\\", "/")
        for collection, value in (
            (prefixes, os.path.join(normalized, "lib", "cmake")),
            (prefixes, normalized),
            (libraries, os.path.join(normalized, "lib")),
            (includes, os.path.join(normalized, "include")),
        ):
            if value not in collection:
                collection.append(value)

    def _preferred_dependency_order(self):
        return (
            "qtbase",
            "qtbase",
            "kwallet",
            "kcalendarcore",
            "kcontacts",
            "cyrus-sasl",
            "kconfig",
            "kcodecs",
            "kcoreaddons",
            "ki18n",
            "ecm",
        )

    def _dependency(self, name, build=False):
        try:
            deps = self.dependencies.build if build else self.dependencies
            return deps.get(name)
        except KeyError:
            return None

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
            self._run_upstream_tests()

    def _library_runtime_env(self, include_build=False):
        runtime_env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                runtime_env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                runtime_env.prepend_path("XDG_DATA_DIRS", os.path.join(dep.package_folder, "share"))
                runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
        cyrus_sasl = self.dependencies["cyrus-sasl"]
        runtime_env.define_path(
            "SASL_PATH", os.path.join(cyrus_sasl.package_folder, "lib", "sasl2")
        )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env(include_build=True)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
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
        excluded_tests = "|".join(
            (
                "calendar-eventcreatejobtest",
                "calendar-eventmodifyjobtest",
                "calendar-freebusyqueryjobtest",
            )
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 240 -E "{}"'.format(self.build_folder, excluded_tests)
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_dirs = {
            self.build_folder,
            os.path.join(self.build_folder, "bin"),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin")),
        }
        for root, _, files in os.walk(self.build_folder):
            if "CTestTestfile.cmake" in files:
                compatibility_dirs.add(root)

        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        lib_sources.extend(glob.glob(os.path.join(self.build_folder, "lib", "lib*.so*")))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")))
        for src in lib_sources:
            for dst_dir in sorted(compatibility_dirs):
                os.makedirs(dst_dir, exist_ok=True)
                dst = os.path.join(dst_dir, os.path.basename(src))
                if not os.path.exists(src):
                    continue
                target = os.path.realpath(src)
                if os.path.realpath(dst) == target:
                    continue
                if os.path.lexists(dst):
                    os.unlink(dst)
                os.symlink(target, dst)

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder, "package")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

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
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder, label):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        if not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "Cannot locate OHOS llvm-objcopy/binary-sign-tool for ELF signing"
            )

        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                try:
                    os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
                signed += 1
        self.output.info(f"Signed {signed} OHOS {label} ELF file(s)")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = list(self._libraries)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.runenv_info.prepend_path("SASL_PATH", os.path.join(self.package_folder, "lib", "sasl2"))
