#!/usr/bin/env python3
"""Conan recipe for kturtle 26.04.0 on HarmonyOS PC.

kturtle (KDE Education) is the Logo programming learning environment: a
Qt Widgets desktop application producing the single executable bin/kturtle.

OHOS-specific adaptations (KF6 6.26 chain pattern, kwrited 6.7.2 precedent):
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS is not in the KDE platform allowlist)
  - KF_SKIP_PO_PROCESSING=ON (no gettext/msgfmt on OHOS; ki18n_install(po)
    catalog generation is skipped, kturtle runs with its built-in defaults)
  - KF6DocTools disabled (optional upstream dep; kdoctools 6.19.0 line is
    incompatible with the 6.26 graph and the manual does not affect runtime)
  - Version overrides redirect the older pins carried by knewstuff/6.29.0.1
    and ktextwidgets/6.18.0 onto the single published 6.26 line, exactly as
    kxmlgui/6.26.0 already does for kconfigwidgets' 6.18 pins (KF6 libraries
    keep ABI compatibility within the 6.x series; one copy of each library
    exists at runtime)
  - CMAKE_INSTALL_RPATH/CMAKE_BUILD_RPATH carry the dependency lib dirs so
    the packaged bin/kturtle resolves the Qt6/KF6 closure without a session
    environment
  - ECM_MODULE_PATH set manually: the CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable KF6 projects rely on
  - conan_cmakedeps_paths.cmake created manually because qtbase/qtsvg use
    cmake_find_mode=none, which keeps CMakeDeps from adding their lib/cmake
    dirs to CMAKE_PREFIX_PATH (qtsvg additionally needs
    QT_ADDITIONAL_PACKAGES_PREFIX_PATH for Qt6SvgWidgets config resolution)
  - upstream ships no test suite (inventory evidence recorded in notes.md
    and test_package/MANIFEST.yml); the delivered executable is covered by
    the consumer test in test_package/ (R34/R51)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KturtleConan(ConanFile):
    name = "kturtle"
    version = "26.04.0"
    description = ("KDE Education kturtle - the Logo programming learning "
                   "environment (educational IDE for the TurtleScript "
                   "language)")
    license = "GPL-2.0-or-later OR GFDL-1.2-only"
    homepage = "https://invent.kde.org/education/kturtle"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Real edges: only what kturtle's CMakeLists.txt links directly.
        # qtbase/6.11.1: the version every published KF6 binary was built
        # against (their package_ids pin the actual 6.11.1 graph -- any other
        # variant forces full KF rebuilds that die on the XKB wall). Qt6::DBus
        # and Qt6::PrintSupport are optional upstream features gated at build
        # time (patches 0001-0003): no published qtbase variant pairs the
        # 6.11.1 graph with those modules, and OHOS has neither a session
        # D-Bus nor a printing service, so the delivered kturtle runs with
        # both features compiled out (kwrited no-session-D-Bus precedent).
        # Conan 2 rejects a plain requires plus an override on the same ref,
        # so kturtle carries only the override and the real qtbase edge comes
        # from kio/knewstuff.
        self.requires("qtsvg/6.11.1")         # Svg, SvgWidgets (canvas sprite/icons)
        self.requires("kio/6.26.0")           # KF6::KIOCore
        self.requires("knewstuff/6.29.0.1")   # KF6::NewStuffWidgets
        self.requires("ktextwidgets/6.18.0")  # KF6::TextWidgets
        self.requires("kxmlgui/6.26.0")       # KF6::XmlGui
        self.requires("kcrash/6.26.0")        # KF6::Crash
        # KF6::CoreAddons / KF6::I18n are linked directly by kturtle, but the
        # real graph edges already exist via kio/6.26.0 (6.26.0); the override
        # entries below redirect knewstuff/ktextwidgets' 6.18.0 pins onto the
        # same single version (plain requires + override on the same ref is
        # rejected by Conan 2).

        # Overrides only (no direct edge here; the real edges come from the
        # dependencies above). Only the unavoidable kio(6.26-line) vs
        # knewstuff/ktextwidgets(6.18-line) conflicts are redirected, so the
        # published binaries of every other package still resolve (verified
        # against their package_id "requires" on the registry):
        self.requires("qtbase/6.11.1", override=True)
        self.requires("karchive/6.26.0", override=True)
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        # kpackage/6.26.0.1: knewstuff pins kpackage/6.18.0.2, whose recipe
        # assumes the static karchive/6.19.0 pairing (zstd reached it
        # transitively); with karchive/6.26.0 its generate() KeyError's on
        # the zstd lookup. The 6.26.0.1 recipe requires zstd directly and its
        # published binary resolves (karchive/6.26.Z + zstd/1.5.Z, minor).
        self.requires("kpackage/6.26.0.1", override=True)
        # zstd: kpackage/6.26.0.1 pins zstd/1.5.7.1 while kxmlgui pins
        # zstd/1.5.7 -- same minor range (1.5.Z), redirect to kpackage's pin
        # so its published binary resolves unchanged.
        self.requires("zstd/1.5.7.1", override=True)
        # zlib: knewstuff pins 1.3.1.1, ktextwidgets pins 1.3.2 -- same
        # minor range (1.3.Z), so redirecting to one version only costs a
        # rebuild for the redirected side (knewstuff, already rebuilding).
        self.requires("zlib/1.3.2", override=True)

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
        # Optional upstream dep: manual/doc toolchain (kdoctools 6.19.0 line)
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"

        # The packaged executable is bin/kturtle while Qt6/KF6 live in the
        # dependencies' lib dirs; OHOS has no desktop session to set them up,
        # so record them in the RPATH (kwrited 6.7.2 precedent).
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
            # ECM's KDEInstallDirs6 runs the qtbase query tool during
            # configure (ECMQueryQt -> QUERY_EXECUTABLE); Qt6CoreTools does
            # not expose Qt6::qtpaths in this layout (kwrited precedent).
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            if os.path.exists(qtpaths6):
                tc.variables["QUERY_EXECUTABLE"] = qtpaths6
                tc.variables["_cli_option"] = "--query"

        tc.generate()

        # qtbase/qtsvg use cmake_find_mode=none -> CMakeDeps does not generate
        # conan_cmakedeps_paths.cmake. Create it manually (kwrited precedent);
        # qtsvg additionally registers via QT_ADDITIONAL_PACKAGES_PREFIX_PATH
        # because Qt only searches that variable for extra module configs
        # (Qt6SvgWidgets lives in the qtsvg package, qtpositioning precedent).
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
        # Extra Qt module prefixes: Svg/SvgWidgets live in the qtsvg package.
        # Qt only searches QT_ADDITIONAL_PACKAGES_PREFIX_PATH for extra module
        # configs (qtpositioning precedent).
        extra_qt_prefixes = []
        qtsvg = self.dependencies.get("qtsvg")
        if qtsvg and qtsvg.package_folder:
            extra_qt_prefixes.append(qtsvg.package_folder)
        if extra_qt_prefixes:
            lines.append(
                f'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH '
                f'"{";".join(extra_qt_prefixes)}")'
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
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)

        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

        self._record_upstream_test_inventory()

    def _cmake_build_env(self):
        build_env = self._runtime_env()
        if self.settings.os == "OHOS":
            # E132: the SDK lld links against libxml2 shipped in the SDK's
            # llvm/lib, which CI workers do not always export (kwrited
            # precedent).
            import glob
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        return runtime_env

    def _record_upstream_test_inventory(self):
        """R51: kturtle 26.04.0 ships no upstream test suite. Record the
        evidence (test directories, ctest registration) instead of skipping
        silently."""
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
        # Application package: the deliverable is bin/kturtle (no libraries,
        # no plugins). No desktop session needed to start the binary; it runs
        # with the Qt offscreen platform for headless smoke testing.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
