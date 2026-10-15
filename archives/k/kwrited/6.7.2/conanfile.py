#!/usr/bin/env python3
"""Conan recipe for kwrited 6.7.2 on HarmonyOS PC.

kwrited (KDE Plasma) shows the messages that write(1)/wall(1) send to a
terminal as a desktop notification. Upstream builds it in one of two mutually
exclusive ways, selected by CMake itself:

  * BUILD_AS_EXECUTABLE=OFF -- a KDED plugin (installed under plugins/kf6/kded)
    that links KF6::DBusAddons and is loaded by the running KDED.
  * BUILD_AS_EXECUTABLE=ON -- a standalone QGuiApplication installed to bin/.

Upstream's switch is cmake_dependent_option(BUILD_AS_EXECUTABLE ... OFF
"KPty_HAVE_UTEMPTER" ON): when the KPty package reports KPty_HAVE_UTEMPTER
=false, the option is forced ON. The packaged kpty/6.26.0 is built without
UTEMPTER (KPty_HAVE_UTEMPTER=FALSE in its CMake package), so on OHOS the
product is bin/kwrited through the executable branch -- no KF6::DBusAddons
requirement and no source patch are needed (OHOS has no KDE desktop session:
no session D-Bus, no KDED).

OHOS-specific adaptations (KF6 6.26 chain pattern, kpty 6.26.0 precedent):
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS is not in the KDE platform allowlist)
  - KF_SKIP_PO_PROCESSING=ON (no gettext/msgfmt on OHOS; the daemon does not
    need translations to run)
  - CMAKE_CXX_STANDARD=20 asserted on top of the cppstd=17 profile (upstream
    sets C++20 itself)
  - CMAKE_INSTALL_RPATH/CMAKE_BUILD_RPATH carry the dependency lib dirs so the
    packaged bin/kwrited resolves the Qt6/KF6 closure without a session
    environment
  - ECM_MODULE_PATH set manually: the CMakeDeps-generated ECMConfig.cmake does
    not propagate the variable KF6 projects rely on to find
    KDEInstallDirs/KDECMakeSettings
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which keeps CMakeDeps from adding its lib/cmake dir
    to CMAKE_PREFIX_PATH
  - /system/lib64 and the SDK llvm/lib dir prepended to LD_LIBRARY_PATH for
    configure/build (sandbox libc++_shared.so shadowing, kpty 6.26.0 E132
    precedent)
  - upstream ships no test suite at all (inventory evidence recorded in
    notes.md and test_package/MANIFEST.yml); the delivered executable is
    covered by the consumer test in test_package/ (R34/R51)
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KWritedConan(ConanFile):
    name = "kwrited"
    version = "6.7.2"
    description = ("KDE Plasma kwrited - shows write(1)/wall(1) messages as a "
                   "desktop notification; on OHOS it is built as the standalone "
                   "executable (no KDED, no session D-Bus)")
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/plasma/kwrited"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Same KF6 6.26 pins as the kpty/6.26.0 chain (kpty/6.26.0 is published:
        # PR #15405 — see README.md and manifest.yaml l0).
        self.requires("qtbase/6.11.1")
        self.requires("kcoreaddons/6.26.0.1")
        self.requires("ki18n/6.26.0")
        self.requires("knotifications/6.26.0")
        # KF6 Pty decides the build flavour: kpty/6.26.0 exports
        # KPty_HAVE_UTEMPTER=FALSE, which forces upstream's executable branch.
        self.requires("kpty/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"

        # The packaged executable is bin/kwrited while Qt6/KF6 live in the
        # dependencies' lib dirs; OHOS has no desktop session to set them up,
        # so record them in the RPATH (accessibility 26.04.3 precedent).
        rpath_dirs = ["$ORIGIN/../lib"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    rpath_dirs.append(lib_dir)
        tc.variables["CMAKE_INSTALL_RPATH"] = ";".join(rpath_dirs)
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(rpath_dirs)

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so the
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ...) are found.
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
            # ECM 6.26 KDEInstallDirs6 runs the qtbase query tool during
            # configure (ECMQueryQt -> QUERY_EXECUTABLE); Qt6CoreTools does not
            # expose Qt6::qtpaths in this layout (accessibility 26.04.3
            # precedent).
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            if os.path.exists(qtpaths6):
                tc.variables["QUERY_EXECUTABLE"] = qtpaths6
                tc.variables["_cli_option"] = "--query"

        tc.generate()

        # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
        # conan_cmakedeps_paths.cmake. Create it manually: every dependency's
        # cmake/lib/include dirs plus ECM's module dirs (FindKF6/kde-modules
        # umbrella resolution), kpty 6.26.0 precedent.
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")'
                )
        if ecm:
            ecm_pkg = ecm.package_folder
            for sub in ("cmake", "find-modules", "modules", "kde-modules"):
                lines.append(
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_pkg}/share/ECM/{sub}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_pkg}/share/ECM/{sub}")'
                )
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        if qtbase:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as fh:
            fh.write("\n".join(lines) + "\n")

    def build(self):
        # Platform guard (kpty 6.26.0 precedent): no patch is declared for
        # 6.7.2 today, the call keeps the OHOS-only patch path in place if the
        # port ever needs one, without touching other platforms.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)

        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

        self._record_upstream_test_inventory()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # E132: the SDK lld links against libxml2 shipped in the SDK's
            # llvm/lib, which CI workers do not always export; ECM's
            # ECMQueryQt helper also needs the compatible libc++ first.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
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
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _record_upstream_test_inventory(self):
        """R51: kwrited 6.7.2 ships no upstream test suite. Record the evidence
        (test directories, ctest registration) instead of skipping silently."""
        test_dirs = [name for name in ("autotests", "tests", "test")
                     if os.path.isdir(os.path.join(self.source_folder, name))]
        registered = False
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        if os.path.exists(cmake_lists):
            with open(cmake_lists, "r", encoding="utf-8", errors="replace") as fh:
                body = fh.read()
            registered = ("add_test(" in body or "ecm_add_test(" in body
                          or "ECMAddTests" in body)
        self.output.info(
            "upstream test inventory (R51): test_dirs={} ctest_registration={}"
            .format(test_dirs, registered))
        if test_dirs or registered:
            self.output.warning(
                "an upstream test suite is actually present; it must be run and "
                "reported (R51)")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application package: the deliverable is bin/kwrited built through
        # upstream's executable branch (no KDED plugin, no D-Bus session
        # dependency). Upstream's install(CODE ...) would mark the binary
        # setuid root / setgid utmp; that step cannot take effect in a
        # non-privileged package build and is not needed by the OHOS delivery
        # (noted in notes.md).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
