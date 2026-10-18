#!/usr/bin/env python3
"""Conan recipe for kdesu 6.26.0 on HarmonyOS PC.

kdesu is the KDE Frameworks 6 privilege-escalation library (libKF6Su.so):
SuProcess / SshProcess / StubProcess / Client, the kdesud daemon and the
kdesu_stub helper. On this platform KDE_INSTALL_LIBEXECDIR_KF resolves to
<prefix>/bin/kf6, so both helpers land there (measured, see notes.md); they
are internal helpers of the library, not user commands, and the recipe
exposes no cpp_info.bindirs, so the package stays a pure library package
(R38 not applicable).

OHOS-specific adaptations (KF6 6.26 chain pattern, kpty 6.26.0 precedent):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list)
  - BUILD_TESTING=ON with the upstream kdesutest/kdesudtest suites run through
    ctest
  - Dependencies: qtbase/6.11.1, kconfig/6.26.0.1, kcoreaddons/6.26.0.1,
    ki18n/6.26.0, kpty/6.26.0 (KF6::Pty is a PUBLIC dependency of KF6Su);
    tool_requires ecm/6.26.0
  - X11 is optional upstream (find_package(X11)); the OHOS sysroot does not
    provide it, so HAVE_X11=0 and the Xauthority code paths compile out
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH
  - /system/lib64 prepended to LD_LIBRARY_PATH for configure and test runs
    (sandbox libc++_shared.so shadowing, kconfig 6.26.0 / kpty 6.26.0
    precedent)
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KDesuConan(ConanFile):
    name = "kdesu"
    version = "6.26.0"
    description = "KDE Frameworks 6 - su/ssh privilege escalation helpers (KF6Su, kdesud, kdesu_stub)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kdesu"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0.1")
        self.requires("kcoreaddons/6.26.0.1")
        self.requires("ki18n/6.26.0")
        self.requires("kpty/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Honour the declared `shared` option: it enters the package_id, so
        # hardcoding ON would produce a "static package id + shared artifact"
        # mismatch for -o kdesu/*:shared=False.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"

        # Native builds on the HarmonyOS device leave CMake in the Generic
        # platform module (no CMAKE_SYSTEM_NAME set because os_build == os_host
        # == OHOS), which has no shared-library SONAME rule. Without this flag
        # CMake drops -Wl,-soname and the resulting libKF6Su.so has no
        # DT_SONAME (CI L5a gate) and the exported CMake targets get
        # IMPORTED_NO_SONAME TRUE (L5c). Inject the Linux-style soname flag so
        # VERSION/SOVERSION target properties take effect (kcodecs 6.26.0 fix
        # 76da86d28c precedent, E330 knowledge entry).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so KDE
        # cmake modules (KDEInstallDirs, KDECMakeSettings, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(KF6*) and
            # transitive find_dependency() chains all resolve.
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
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 (and the qtbase lib dir, already added
            # by _library_runtime_env) so the loader resolves the compatible
            # libc++ first (kconfig 6.26.0 / kpty 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # which shadows the compatible one; prepend /system/lib64 so test
            # executables resolve the compatible libc++ first (kconfig 6.26.0
            # precedent, same fix as _cmake_build_env).
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
        test_env.define("XDG_DATA_HOME",
                        os.path.join(test_home, ".local", "share"))
        with test_env.vars(self).apply():
            # Upstream registers two CTest targets: kdesutest (six QTest slots
            # driving SuProcess against the python fixtures in autotests/) and
            # kdesudtest (lexer round-trip).
            #
            # Hard gate: every upstream target except the environment-blocked
            # kdesutest must pass, and --no-tests=error also catches a build
            # where test registration was lost (a zero-test run must not be
            # green). Same shape as the karchive/kapptemplate recipes.
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 300 -E "^kdesutest$"'.format(self.build_folder)
            )
            # Known exemption: kdesutest needs pty allocation plus su/sudo. The
            # device sandbox denies pty (kf.pty: Can't open a pseudo teletype)
            # before the test body runs and ships no su/sudo/doas, so the
            # measured failure is reported as a warning and declared verbatim
            # in notes.md / test_package/MANIFEST.yml (R51), not folded into
            # the hard gate. The per-target coverage of the packaged API is
            # provided by test_package/.
            rc = self.run(
                'ctest --test-dir "{}" --output-on-failure -R "^kdesutest$" '
                '--timeout 300'.format(self.build_folder),
                ignore_errors=True,
            )
            if rc:
                self.output.warning(
                    "upstream kdesutest is blocked on this platform "
                    "(ctest rc={}); see notes.md for the measured result and "
                    "the sandbox pty/su limitation, not a passing test".format(rc)
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6SuConfig.cmake with a
        # find_dependency(KF6Pty) chain. Use cmake_find_mode=none so CMakeDeps
        # doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Su"]
