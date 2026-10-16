#!/usr/bin/env python3
"""Conan recipe for KTextWidgets 6.26.0 on HarmonyOS PC."""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KTextWidgetsConan(ConanFile):
    name = "ktextwidgets"
    version = "6.26.0"
    description = "KDE Frameworks advanced text widgets (KFindDialog, KReplaceDialog, KRichTextWidget...)"
    license = "GPL-2.0-or-later AND LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/ktextwidgets"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kcompletion/6.26.0.1")
        self.requires("kconfig/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("kwidgetsaddons/6.26.0")
        self.requires("sonnet/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as official_error:
            # The official endpoint is authoritative; fall back to the USTC KDE
            # mirror only when the fixed worker cannot reach download.kde.org
            # (same tarball sha256, verified identical).
            self.output.warning(f"Official source download failed: {official_error}")
            get(
                self,
                url="https://mirrors.ustc.edu.cn/kde/stable/frameworks/6.26/ktextwidgets-6.26.0.tar.xz",
                sha256="6511f9909f90fac951e2873a44dd451b8ac71d38085a62c65a6fb5028e62d84d",
                strip_root=True,
            )

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        # CMake has no Platform/HarmonyOS module; provide the SONAME flag so
        # libKF6TextWidgets.so gets a DT_SONAME + versioned symlink chain
        # (kfilemetadata/baloo/kio/ksanecore precedent, L5 gate).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # Qt Designer plugin requires Qt6UiPlugin which qtbase does not
        # provide on ohpcd; the plugin is a design-time integration, the
        # KF6TextWidgets library itself is unaffected (kio 6.26.0 precedent).
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6UiPlugin"] = "ON"
        # qtexttospeech is not published on ohpcd; the feature only adds the
        # "read selection aloud" action inside KTextEdit, core editing is
        # unaffected (kio 6.26.0 precedent: optional features disabled).
        tc.variables["WITH_TEXT_TO_SPEECH"] = "OFF"
        # Qt6Test is a build-only requirement of the upstream autotests.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6Test"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6Quick"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6PrintSupport"] = "ON"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        # E537 relocatable linkage: kcompletion/kconfig/ki18n/kwidgetsaddons/
        # sonnet are published without a DT_SONAME, so linking by their
        # absolute Conan cache paths makes the linker record machine-private
        # paths in DT_NEEDED. Expose their lib dirs to the patched
        # src/CMakeLists.txt (target_link_directories) so KF6TextWidgets is
        # linked by basename (-lKF6SonnetUi etc.) and the produced artifact
        # stays relocatable (kcompletion 6.26.0.1 precedent).
        kf6_dep_lib_dirs = []
        for dep_name in ("kcompletion", "kconfig", "ki18n", "kwidgetsaddons", "sonnet"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                kf6_dep_lib_dirs.append(os.path.join(dep.package_folder, "lib"))
        if kf6_dep_lib_dirs:
            tc.variables["KTEXTWIDGETS_DEP_LIB_DIRS"] = ";".join(kf6_dep_lib_dirs)

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
        if self.settings.os == "OHOS":
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
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so which shadows the compatible one; prepend
            # /system/lib64 so the loader resolves the compatible libc++
            # first (kconfig 6.26.0 / kcrash 6.26.0 / kio 6.26.0 /
            # ksanecore 26.04.0 precedent).
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env(include_build=True)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_home = os.path.join(self.build_folder, "test-home")
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("TMPDIR", test_tmp)
        test_env.define("TEMP", test_tmp)
        test_env.define("TMP", test_tmp)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 240'.format(
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

        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        lib_sources.extend(glob.glob(os.path.join(self.build_folder, "lib", "lib*.so*")))
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

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6TextWidgets"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )