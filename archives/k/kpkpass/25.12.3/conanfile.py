#!/usr/bin/env python3
"""Conan recipe for kpkpass 25.12.3 on HarmonyOS PC.

kpkpass is the KDE PIM Apple Wallet pass library (KPim6PkPass, SOVERSION 6,
PIM_VERSION 6.6.3) plus the QML module org.kde.pkpass. The package provides
a single unversioned shared library libKPim6PkPass.so (with DT_SONAME
recorded) and the QML plugin libkpkpassqmlplugin.so under
lib/qml/org/kde/pkpass.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform allow-list)
  - KF_SKIP_PO_PROCESSING=ON: Qt6LinguistTools is not part of the qtbase
    package in this repository
  - BUILD_TESTING=ON and ctest execution for the two upstream autotests
    (pkpasstest, fieldtest)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's
    CMakeLists.txt relies on
  - qtbase and qtdeclarative both set cmake_find_mode=none, so their
    lib/cmake dirs are PREPENDed to CMAKE_PREFIX_PATH through a hand-written
    conan_cmakedeps_paths.cmake; the same file exposes the karchive builddir
    so find_package(KF6 COMPONENTS Archive) resolves through ECM's FindKF6
  - The Qt host tools (moc, rcc, qmltyperegistrar, qmlcachegen) live in the
    split qtbase/qtdeclarative packages; their dependency lib dirs are
    prepended to LD_LIBRARY_PATH while running configure/build/install
    (kitemodels 6.26.0 precedent)
  - ECM 6.26+ KDEInstallDirs6 runs qtpaths at configure time; /system/lib64
    is prepended to LD_LIBRARY_PATH so the compatible libc++_shared.so is
    found instead of the sandbox one (kconfig 6.26.0 precedent)
  - SharedMimeInfo is a build tool: update-mime-database is pinned through
    UPDATE_MIME_DATABASE_EXECUTABLE so ECM's FindSharedMimeInfo module can
    read its version (2.5.1 >= 2.5, so no MIME XML install rule runs)
  - OHOS CMake does not emit a SONAME for shared libraries by default; the
    QML plugin would record a build-tree path in DT_NEEDED without it.
    With CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE and explicit
    -Wl,-soname, flags the install tree carries a single unversioned
    libKPim6PkPass.so that still records DT_SONAME (HMDFS refuses the
    versioned symlink chain; attica 6.14.0 precedent)
  - CMake install rewrites the RUNPATH of installed shared libraries, which
    invalidates the OHOS build-time .codesign section; every packaged ELF is
    re-signed (kitemodels 6.26.0 precedent)
"""
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class KPkPassConan(ConanFile):
    name = "kpkpass"
    version = "25.12.3"
    description = "KDE PIM - Apple Wallet pass library (KPim6PkPass) and QML module org.kde.pkpass"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/pim/kpkpass"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6Core/Qt6Gui, Qt6Qml (required by the org.kde.pkpass QML plugin)
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # find_package(KF6 ... COMPONENTS Archive): KZip reads the pass bundle
        self.requires("karchive/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # ECM's FindSharedMimeInfo consumes update-mime-database at configure
        # time; version 2.5.1 keeps both MIME XML install rules disabled.
        self.tool_requires("shared-mime-info/2.5.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # The upstream top-level CMakeLists.txt sets CMAKE_CXX_STANDARD 20
        # after project(); keep the toolchain cache variable in sync so no
        # -std=gnu++17 leaks into the compile command line.
        tc.variables["CMAKE_CXX_STANDARD"] = "20"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        smi = self.dependencies.build.get("shared-mime-info")
        if smi:
            tool = os.path.join(smi.package_folder, "bin", "update-mime-database")
            if os.path.isfile(tool):
                # Pinning the cache entry makes find_program() take this path
                # instead of searching PATH.
                tc.variables["UPDATE_MIME_DATABASE_EXECUTABLE"] = tool

        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        qt_prefixes = []
        for name in ("qtbase", "qtdeclarative"):
            dep = self.dependencies.get(name)
            if dep and dep.package_folder:
                qt_prefixes.append(dep.package_folder)
        if qt_prefixes:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_prefixes)

        prefixes = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefixes.append(dep.package_folder)
        if ecm:
            prefixes.append(ecm.package_folder)

        if prefixes or ecm:
            lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
            for pkg in prefixes:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            runtime_lib_dirs = ";".join(f"{p}/lib" for p in prefixes)
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{runtime_lib_dirs}")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        """OHOS CMake does not emit a SONAME for shared libraries by default,
        and HMDFS refuses the versioned .so.6 / .so symlinks that CMake wants
        to create for an explicitly versioned target. Without a SONAME the
        QML plugin records a build-tree relative path in DT_NEEDED, which the
        OHOS loader treats as a cwd-relative path and fails to resolve.
        Keep SONAME emission, skip the versioned symlinks (attica 6.14.0
        precedent)."""
        toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        toolchain.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        toolchain.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

    def _dependency_runtime_env(self, include_build=False):
        """Runtime env for the split Qt packages and the build tools: the Qt
        host tools and the freshly built QML plugin need every dependency lib
        dir on LD_LIBRARY_PATH (kitemodels 6.26.0 precedent)."""
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
                for rel in ("qml", "lib/qml", "share/qml"):
                    env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, rel))
                    env.prepend_path("QML_IMPORT_PATH", os.path.join(dep.package_folder, rel))
        return env

    def _cmake_build_env(self):
        build_env = self._dependency_runtime_env(include_build=True)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool while
            # configuring; the sandbox LD_LIBRARY_PATH contains an
            # incompatible libc++_shared.so which shadows the compatible one,
            # so /system/lib64 is prepended (kconfig 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def build(self):
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        ctest_path = self._find_ohos_tool("ctest")
        if not ctest_path:
            raise ConanException("Cannot locate CTest beside the configured compiler")
        test_env = self._dependency_runtime_env(include_build=False)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        with test_env.vars(self).apply():
            manifest = subprocess.run(
                [ctest_path, "--test-dir", self.build_folder, "-N"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if manifest.returncode != 0:
                raise ConanException(
                    "Unable to enumerate upstream CTest cases: "
                    + (manifest.stderr.strip() or manifest.stdout.strip())
                )
            match = re.search(r"Total Tests:\s*(\d+)", manifest.stdout)
            # pkpasstest + fieldtest (one testBoardingPass slot each; the
            # initTestCase lifecycle slots are not test cases).
            if not match or int(match.group(1)) != 2:
                raise ConanException(
                    "Expected all 2 upstream CTest cases (pkpasstest, fieldtest); "
                    "actual CTest manifest:\n" + manifest.stdout
                )
            self.output.info("Upstream CTest manifest contains 2/2 expected cases")
            self.run(
                '{} --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self._quote(ctest_path), self.build_folder
                )
            )

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

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
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        """CMake rewrites the RUNPATH of installed shared libraries, which
        invalidates the OHOS build-time .codesign section. The OHOS loader
        then refuses to load the library. Re-sign every packaged ELF
        (kitemodels 6.26.0 precedent)."""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
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
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package_info(self):
        # The project installs its own KPim6PkPassConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6 Core/Gui and KF6Archive).
        # Use cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KPim6PkPass"]
        # QML module org.kde.pkpass: consumers need the import root on their
        # QML import path.
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
        self.runenv_info.prepend_path(
            "QML_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
