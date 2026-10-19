#!/usr/bin/env python3
"""Conan recipe for threadweaver 6.28.0 on HarmonyOS PC.

threadweaver is a KDE Frameworks 6 library providing a job queue / job
scheduling framework on top of QThread (libKF6ThreadWeaver.so). It is a
QtCore-level dependency.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_TESTING=ON and ctest execution for the 7 upstream autotests
  - Dependencies: qtbase/6.11.1 (Qt6Core; the unconditionally-built examples
    also use Qt6Widgets/Network/Xml/Test and the uic/moc tools, all shipped
    inside the qtbase package), ecm/6.28.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    save,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class ThreadweaverConan(ConanFile):
    name = "threadweaver"
    version = "6.28.0"
    description = "KDE Frameworks 6 - ThreadWeaver job scheduling and threading framework"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/threadweaver"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.28.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)
        # Upstream adds examples/ to the build unconditionally (HelloWorld,
        # HelloWorldRaw, HelloInternet, ThumbNailer). They need Qt6 Widgets/
        # Network/Xml/Test plus the uic tool, and all of these ship inside the
        # qtbase package, so no gating patch is required at 6.28.0.

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

    def _configure_ohos_shared_library_rules(self, toolchain):
        """OHOS CMake ships no Platform/HarmonyOS module, so
        CMAKE_SHARED_LIBRARY_SONAME_* stays unset and lld emits no DT_SONAME.
        Consumers then record the absolute build-machine path of this library
        in DT_NEEDED and fail to load it on CI workers or any clean cache.
        Restore the soname flags through the user make-rules override
        (kirigami 6.18.0 precedent). HMDFS additionally rejects symlink(2)
        with EPERM, so the versioned-symlink chain CMake creates for a
        versioned library (libKF6ThreadWeaver.so.6 -> .so.6.28.0) can never be
        materialized; NO_VERSIONED_SONAME keeps the (unversioned) DT_SONAME
        and drops the chain (KF5/expat-validated pattern).

        The CMAKE_SHARED_LIBRARY_RUNTIME_* (rpath) flags are deliberately not
        defined here. With them defined, CMake bakes the build-tree library
        directories into a RUNPATH, and cmake install() then rewrites the ELF
        in place to strip it; this device's loader rejects the rewritten
        library on dlopen (EACCES while the untouched linker output loads).
        Without the flags CMake emits no RUNPATH at all and install() is a
        pure copy, which is what the 6.26.0 line (SONAME-only recipe) shipped
        and what packaged consumers load."""
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
            )) + "\n",
        )
        toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def build(self):
        # conandata.yml declares no patches at 6.28.0; the call stays so a
        # future patch entry is applied without touching this method.
        apply_conandata_patches(self)
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
            # ECM 6.28 KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 (and the qtbase lib dir, already added
            # by _library_runtime_env) so the loader resolves the compatible
            # libc++ first (kconfig 6.26.0 / bluez-qt 6.28.0 precedent).
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
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # which shadows the compatible one; prepend /system/lib64 so test
            # executables resolve the compatible libc++ first (kconfig 6.26.0
            # / bluez-qt 6.28.0 precedent, same fix as _cmake_build_env).
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
            # ThreadWeaverJobTests::RequestAbortCollectionTest is timing
            # sensitive: the abort propagation races the dispatching of the
            # next collection element, so under the concurrent-build load of
            # the shared OHOS device this single case fails in roughly half of
            # the runs (12 reruns: 5 pass / 7 fail, always the same assertion;
            # the other 6 test binaries and the remaining 48 cases are
            # stable). Retry only what fails, matching the kf5wayland 5.116.0
            # precedent; deterministic failures still fail (8 attempts of
            # ~0.5s each).
            ctest_command = (
                'ctest --test-dir "{}" --output-on-failure '
                "--repeat until-pass:8 --timeout 60 --no-tests=error"
            ).format(self.build_folder)
            self.run(ctest_command)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6ThreadWeaverConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6ThreadWeaver"]
