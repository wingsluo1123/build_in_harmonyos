#!/usr/bin/env python3
"""Conan recipe for kcompletion 6.28.0 on HarmonyOS PC.

kcompletion is a KDE Frameworks 6 library providing text-completion helpers
and the KLineEdit / KComboBox widgets (libKF6Completion.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_DESIGNERPLUGIN=OFF: the Designer plugin would need Qt6UiPlugin,
    which is not published to ohpcd
  - KF_SKIP_PO_PROCESSING=ON: ECMPoQmTools' ecm_process_po_files_as_qm()
    returns early when this option is set, so translation catalog generation
    is skipped without a source patch and without requiring Qt6LinguistTools
    (not published to ohpcd)
  - KF_DEP_VERSION lowered 6.28.0 -> 6.26.0 (patches/0001): ohpcd publishes
    KF6Codecs/KF6Config only up to 6.26.0.1 while KF6WidgetsAddons is at
    6.28.0; 6.26.0 is the common floor that satisfies all three
    find_package() calls (kbookmarks 6.28.0 precedent)
  - BUILD_TESTING=ON: the upstream QTest suite (autotests/, five executables)
    is built and executed with ctest; the three interactive GUI programs in
    tests/ (kcomboboxtest, kcompletionuitest, klineedittest) never terminate
    on their own, so they are excluded from ctest and instead run as
    launch-alive smoke checks under a timeout (kglobalaccel 6.28.0 precedent).
    A missing smoke binary fails the build instead of silently reducing the
    gate to 0/3
  - Shared-only recipe: validate() rejects shared=False, because the
    unversioned-soname workaround and package_info() describe
    libKF6Completion.so and a static package would contradict its package id
  - Dependencies: qtbase/6.11.1, kcodecs/6.26.0.1, kconfig/6.26.0.1,
    kwidgetsaddons/6.28.0, ecm/6.28.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase and the three
    KF6 packages use cmake_find_mode=none, which prevents CMakeDeps from
    adding their lib/cmake builddirs to CMAKE_PREFIX_PATH
  - Shared libraries are emitted unversioned (CMAKE_PLATFORM_NO_VERSIONED_SONAME
    plus explicit -soname flags, both in plain and cache variables): HMDFS
    rejects symlink() with EPERM, so CMake's versioned .so chain cannot be
    created on device (kwidgetsaddons 6.28.0 / kitemviews 6.28.0 precedent)
  - OHOS SDK llvm/lib and /system/lib64 prepended to LD_LIBRARY_PATH during
    build and tests (E132 lld libxml2 dependency and the sandbox
    libc++_shared.so shadowing, kconfig 6.26.0 precedent)
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KcompletionConan(ConanFile):
    name = "kcompletion"
    version = "6.28.0"
    description = "KDE Frameworks 6 - Text completion widgets"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcompletion"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # Highest versions published to ohpcd (device registry probe,
        # 2026-10-18): kconfig/kcodecs top out at 6.26.0.1,
        # kwidgetsaddons is at 6.28.0. patches/0001 lowers the upstream
        # KF_DEP_VERSION to the 6.26.0 common floor.
        self.requires("kcodecs/6.26.0.1")
        self.requires("kconfig/6.26.0.1")
        self.requires("kwidgetsaddons/6.28.0")

    def build_requirements(self):
        # kcompletion 6.28.0 requires ECM >= 6.28.0 (find_package(ECM 6.28.0
        # NO_MODULE) in the top-level CMakeLists.txt); ohpcd publishes
        # ecm/6.28.0 since 2026-10-14.
        self.tool_requires("ecm/6.28.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # The unversioned-soname workaround (E330) and package_info() both
        # describe libKF6Completion.so. Refuse static builds instead of
        # silently emitting a shared library under a static package id.
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "kcompletion is packaged as a shared library only: the "
                "unversioned-soname workaround and package_info() target "
                "libKF6Completion.so. Configure with "
                "-o kcompletion/*:shared=True."
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Shared-only: validate() rejects shared=False (see above).
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # ECMPoQmTools' ecm_process_po_files_as_qm() returns early when this
        # option is set, so po/qm catalog generation is skipped without
        # needing Qt6LinguistTools (not published to ohpcd).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # HMDFS (the device user volume) rejects symlink() with EPERM, so the
        # versioned lib<name>.so.<major> symlink chain CMake creates after
        # linking fails the build on device. Emit every shared library under
        # its plain name instead (kwidgetsaddons 6.28.0 / kitemviews 6.28.0
        # precedent).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        # CMake ships no Platform/HarmonyOS module, so
        # CMAKE_SHARED_LIBRARY_SONAME_* stays empty and lld emits no
        # DT_SONAME. Consumers then record the absolute build-machine path of
        # this library in DT_NEEDED and fail to load it on CI workers or any
        # clean cache. Provide the flags so the library gets a DT_SONAME and
        # consumers record the bare soname instead. Set both variable
        # flavors: cache_variables reaches the configure only through
        # CMakePresets while plain variables reach -DCMAKE_TOOLCHAIN_FILE
        # configures.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
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
            # qtbase and the KF6 packages use cmake_find_mode=none -> CMakeDeps
            # does not generate conan_cmakedeps_paths.cmake. Create it manually
            # so the toolchain adds their cmake dirs to CMAKE_PREFIX_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            for dep_name in ("kcodecs", "kconfig", "kwidgetsaddons"):
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
        # Apply patches unconditionally: patches/0001 aligns the upstream
        # KF_DEP_VERSION with the dependency versions pinned in
        # requirements(), and those pins apply on every platform. Gating the
        # patch on OHOS would leave non-OHOS builds resolving KF6Codecs/
        # KF6Config 6.28.0 against the pinned 6.26.0.1 packages.
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
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
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # E132: the OHOS SDK lld links against libxml2.so.16 shipped in
            # the SDK's llvm/lib directory; prepend it so all link steps can
            # load it (kconfig 6.26.0 precedent).
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64 which
            # shadows the compatible one; prepend /system/lib64 (and the
            # qtbase lib dir, already added by _library_runtime_env) so the
            # loader resolves the compatible libc++ first (kconfig 6.26.0 /
            # kwidgetsaddons 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
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
        with test_env.vars(self).apply():
            # The three programs in tests/ are interactive demos whose event
            # loop only ends on a button click; exclude them from ctest (a
            # timeout there is a test failure) and smoke-run them below.
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 120 -E '
                '"^(kcomboboxtest|kcompletionuitest|klineedittest)$"'.format(
                    self.build_folder
                )
            )
            self._smoke_manual_gui_tests()

    def _manual_test_binary(self, name):
        for rel in (
            os.path.join("bin", name),
            os.path.join("tests", name),
            os.path.join("tests", "Release", name),
            os.path.join("tests", "Debug", name),
        ):
            candidate = os.path.join(self.build_folder, rel)
            if os.path.isfile(candidate):
                return candidate
        # Last resort: a different generator/layout may place the executable
        # elsewhere in the build tree. Search recursively so the smoke gate
        # cannot silently degrade to 0/3 on a layout change. Filter to regular
        # files: **/name can also match a directory called like the binary,
        # and executing that would raise IsADirectoryError instead of the
        # diagnostic ConanException below.
        hits = [
            h for h in glob.glob(os.path.join(self.build_folder, "**", name), recursive=True)
            if os.path.isfile(h)
        ]
        return hits[0] if hits else ""

    def _smoke_manual_gui_tests(self):
        # Launch-alive check (kglobalaccel 6.28.0 precedent): with the
        # offscreen platform a working GUI program reaches its event loop and
        # keeps running until the timeout kills it (rc=124 equivalent =
        # TimeoutExpired here). A loader/plugin failure aborts immediately
        # with a non-zero code, which fails the package build.
        for name in ("kcomboboxtest", "kcompletionuitest", "klineedittest"):
            exe = self._manual_test_binary(name)
            if not exe:
                raise ConanException(
                    "manual GUI test {} was not built; the launch-alive smoke "
                    "gate is the only check covering the three interactive "
                    "tests/ programs that ctest excludes, so it must not be "
                    "skipped".format(name)
                )
            try:
                proc = subprocess.run(
                    [exe],
                    timeout=15,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
            except subprocess.TimeoutExpired:
                self.output.info(
                    "{}: event loop reached (still running after 15 s), "
                    "smoke PASS".format(name)
                )
                continue
            output = (proc.stdout or b"").decode(errors="replace")[-400:]
            # A program that exits on its own before the 15 s window never
            # proves that it reached QApplication::exec(); both a clean (rc=0)
            # and a failed early exit must fail the launch-alive gate
            # (kglobalaccel 6.28.0 precedent: killed by the timeout means
            # alive).
            raise ConanException(
                "{}: exited before the 15 s launch-alive window (rc={}); the "
                "interactive tests/ programs must still be running when the "
                "timeout fires: {}".format(name, proc.returncode, output)
            )

    def package(self):
        cmake = CMake(self)
        # The host cmake (/data/service/hnp/bin/cmake) runs during install;
        # apply the same /system/lib64 libc++ shadowing fix as build().
        with self._cmake_build_env().vars(self).apply():
            cmake.install()

    def package_info(self):
        # The project installs its own KF6CompletionConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Widgets for shared
        # builds). Use cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Completion"]
