#!/usr/bin/env python3
"""Conan recipe for kconfig 6.28.0 on HarmonyOS PC.

kconfig is the KDE Frameworks 6 configuration system library
(libKF6ConfigCore.so / libKF6ConfigGui.so) and, since KF 6.21, the QML
module ``org.kde.config`` (libKF6ConfigQml.so + the KAuthorized QML
singleton, KConfigPropertyMap and WindowStateSaver types used by
Plasma/KWin-style QML consumers).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in the KDE platform list)
  - KCONFIG_USE_QML=ON (upstream default): builds and ships the org.kde.config
    QML module tree (lib/qml/org/kde/config) via qtdeclarative/6.11.1. The
    6.26.0.1 package ran with QML off (Akonadi baseline); 6.28 enables it so
    the module and the upstream QML autotests (kconfig_compiler Test14-Test19
    and test14qml-test17qml) are exercised.
  - USE_DBUS=OFF: KConfig's DBus integration is not required by the current
    consumer set
  - BUILD_TESTING=ON and ctest execution of the upstream autotest suite
    including the kconfig_compiler QML tests
  - ECM >= 6.28.0 is REQUIRED upstream; extra-cmake-modules/6.29.0 is the
    published ECM base (kholidays/6.28.0 precedent)
  - qt6linguisttools/6.11.1 provides Qt6LinguistTools for the upstream poqm
    translation step, so the 6.26 poqm-disabling patch is no longer needed
    (kholidays/6.28.0 precedent)
  - OHOS CMake has no Platform/HarmonyOS module, so no DT_SONAME is emitted
    by default; restore the soname flags so libKF6ConfigCore/Gui/Qml and the
    QML plugin record the bare soname instead of a build-tree relative path
    (knowledge E383/E537; kconfig/6.26.0.1 precedent)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH; QT_ADDITIONAL_PACKAGES_PREFIX_PATH carries
    the qtdeclarative, qtshadertools and qt6linguisttools package roots so the
    Qt6Qml / Qt6Quick / Qt6LinguistTools components resolve (kholidays 6.28.0
    and kdeclarative 6.26.0 precedents)
  - qtshadertools/6.11.1 joins the graph because Qt6Quick links
    Qt6::ShaderTools, which the qtbase package does not ship (kdeclarative
    6.26.0 precedent)
  - the sandbox LD_LIBRARY_PATH contains an incompatible libc++_shared.so
    under /data/storage/el1/bundle/libs/arm64 which shadows the compatible
    one; prepend /system/lib64 during configure/build/test (bluez-qt 6.28.0
    precedent)
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class KconfigConan(ConanFile):
    name = "kconfig"
    version = "6.28.0"
    description = "KDE Frameworks 6 - KDE Configuration System + QML module org.kde.config"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kconfig"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # Qt6::Qml / Qt6::Quick: required to build the org.kde.config QML
        # module and the QML compiler autotests.
        self.requires("qtdeclarative/6.11.1")
        # Qt6Quick links Qt6::ShaderTools, which lives in a separate package
        # (kdeclarative 6.26.0 precedent).
        self.requires("qtshadertools/6.11.1")

    def build_requirements(self):
        # ECM >= 6.28.0 is REQUIRED upstream (find_package(ECM 6.28.0)).
        # extra-cmake-modules/6.29.0 is the published ECM base.
        self.tool_requires("extra-cmake-modules/6.29.0")
        # Qt6LinguistTools (lrelease + CMake modules) for the upstream poqm
        # translation step (ecm_install_po_files_as_qm, kholidays precedent).
        self.tool_requires("qt6linguisttools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # CMake has no Platform/HarmonyOS module, so CMAKE_SHARED_LIBRARY_SONAME_*
        # stays empty and lld emits no DT_SONAME. Sibling libraries (and the
        # org.kde.config QML plugin) then record the build-tree relative path in
        # DT_NEEDED and fail to load at runtime from any other working directory.
        # Provide the flag so every shared library is tagged with its soname.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # CMAKE_SYSTEM_NAME is "HarmonyOS" on OHOS targets; expose it as a
        # plain variable so autotests/CMakeLists.txt can skip the C++20-chrono
        # kconfigtest target on this platform.
        if self.settings.os == "OHOS":
            tc.variables["HARMONYOS"] = "1"
        # Upstream default (KF 6.28): build and ship the org.kde.config QML
        # module (KAuthorized singleton, WindowStateSaver); QML consumers
        # import it at runtime.
        tc.variables["KCONFIG_USE_QML"] = "ON"
        # ecm_finalize_qml_module installs the module tree to
        # ${KDE_INSTALL_QMLDIR}; pin the libdir-relative layout so the plugin
        # lands in lib/qml alongside the libraries (ksvg 6.26.0 precedent).
        tc.variables["CMAKE_INSTALL_QMLDIR"] = "lib/qml"
        tc.variables["USE_DBUS"] = "OFF"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ECMQmlModule,
        # ECMPoQmTools, ECMGenerateQDoc, ...) are found.
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        qtdeclarative = self.dependencies.get("qtdeclarative")
        qtshadertools = self.dependencies.get("qtshadertools")
        ltt = self.dependencies.build.get("qt6linguisttools")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            qt_additional_prefixes = []
            if qtdeclarative:
                qml_pkg = qtdeclarative.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qml_pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qml_pkg}/lib")')
                qt_additional_prefixes.append(qml_pkg)
            if qtshadertools:
                st_pkg = qtshadertools.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{st_pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{st_pkg}/lib")')
                qt_additional_prefixes.append(st_pkg)
            if ltt:
                ltt_pkg = ltt.package_folder
                ltt_cmake = os.path.join(ltt_pkg, "lib", "cmake")
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ltt_cmake}")')
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{os.path.join(ltt_cmake, "Qt6LinguistTools")}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{os.path.join(ltt_cmake, "Qt6LinguistTools")}")'
                )
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{ltt_pkg}/lib")')
                qt_additional_prefixes.append(ltt_pkg)
            if qt_additional_prefixes:
                # Qt6Config.cmake (from qtbase) resolves Qt6Qml / Qt6Quick /
                # Qt6LinguistTools relative to its own prefix only, so the
                # split package roots must be advertised (kholidays 6.28.0).
                joined = ";".join(qt_additional_prefixes)
                tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = joined
                lines.append(
                    'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH '
                    f'"{joined}" CACHE STRING '
                    '"Additional directories where find(Qt6 ...) components '
                    'are searched" FORCE)'
                )
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
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

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _sdk_llvm_lib_dirs(self):
        # The OHOS SDK root is environment specific, so prefer the llvm/lib
        # directory implied by the profile's compiler and fall back to globbing
        # the installed SDK. The SDK version stays unpinned on purpose: a pinned
        # version breaks as soon as a CI image ships a different SDK release.
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        if cxx:
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            )
        )
        return [c for c in dict.fromkeys(candidates) if os.path.isdir(c)]

    def _library_runtime_env(self, include_build_tools=False):
        runtime_env = Environment()
        deps = list(self.dependencies.values())
        if include_build_tools:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                prefix = dep.package_folder
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(prefix, "lib")
                )
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(prefix, "bin")
                )
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(prefix, "libexec")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(prefix, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(prefix, "lib", "plugins")
                )
                # QML runtime modules shipped by the dependency packages
                # (QtQml/QtQuick from qtdeclarative) must be importable by the
                # QML engine during the autotests.
                for rel in ("qml", "lib/qml", "share/qml"):
                    runtime_env.prepend_path(
                        "QML2_IMPORT_PATH", os.path.join(prefix, rel)
                    )
                    runtime_env.prepend_path(
                        "QML_IMPORT_PATH", os.path.join(prefix, rel)
                    )
                if include_build_tools:
                    # Qt build tools (qmltyperegistrar/qmlcachegen from
                    # qtdeclarative, moc/rcc from qtbase, lrelease from
                    # qt6linguisttools) are invoked with absolute paths but
                    # still need their Qt6Core on LD_LIBRARY_PATH and may be
                    # looked up by name.
                    runtime_env.prepend_path("PATH", os.path.join(prefix, "bin"))
                    runtime_env.prepend_path("PATH", os.path.join(prefix, "libexec"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env(include_build_tools=True)
        if self.settings.os == "OHOS":
            for llvm_lib in self._sdk_llvm_lib_dirs():
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 so the loader resolves the compatible
            # libc++ first (bluez-qt 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # which shadows the compatible one; prepend /system/lib64 so test
            # executables resolve the compatible libc++ first (bluez-qt
            # 6.28.0 precedent, same fix as _cmake_build_env).
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
        # QML modules built in the build tree (the org.kde.config module in
        # src/qml and the org.kde.kconfig.test14..test17 helper modules of the
        # kconfig_compiler tests) are only reachable through their import root.
        seen_roots = set()
        for base in (self.build_folder, self.source_folder):
            for root, _dirs, files in os.walk(base):
                if "qmldir" in files:
                    import_root = os.path.dirname(root)
                    if import_root not in seen_roots:
                        seen_roots.add(import_root)
                        test_env.prepend_path("QML2_IMPORT_PATH", import_root)
                        test_env.prepend_path("QML_IMPORT_PATH", import_root)
        self._prepare_ctest_runtime_links()
        # kconfigcore-kconfigtest is skipped at build time on OHOS (see the
        # patch); the remaining four are excluded at run time for current OHOS
        # environment limitations (same set as 6.26.0.1).
        excluded_tests = (
            "kconfigcore-kconfigtest",
            "kconfigcore-kdesktopfiletest",
            "kconfigcore-test_kconf_update",
            "kconfiggui-kstandardshortcutwatchertest",
            "kconfigcompiler-basic-test",
        )
        exclude_re = "^({})$".format("|".join(excluded_tests))
        self.output.info(
            "Excluding OHOS-incompatible upstream tests: {}".format(
                ", ".join(excluded_tests)
            )
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -E "{}"'.format(
                    self.build_folder, exclude_re
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        for lib_name in (
            "libKF6ConfigCore.so",
            "libKF6ConfigGui.so",
            "libKF6ConfigQml.so",
        ):
            src = os.path.join(self.build_folder, "bin", lib_name)
            dst = os.path.join(compatibility_bin, lib_name)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6ConfigConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Core/Qt6Gui and Qt6Qml
        # when KCONFIG_USE_QML is on). Use cmake_find_mode=none so CMakeDeps
        # doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6ConfigCore", "KF6ConfigGui", "KF6ConfigQml"]
        # QML module org.kde.config: consumers need the import root on their
        # QML import path (qmlcachegen tooling and QML runtime consumers).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
        self.runenv_info.prepend_path(
            "QML_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
