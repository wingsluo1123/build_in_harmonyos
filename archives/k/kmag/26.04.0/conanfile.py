#!/usr/bin/env python3
"""Conan recipe for kmag 26.04.0 (aarch64-linux-ohos).

KMagnifier is the KDE accessibility screen magnifier: a Qt6 Widgets
application (KXmlGui main window) that magnifies the area around the mouse
cursor, with follow-mouse / follow-focus / selection-window modes, zoom
presets, rotation, colour-blindness simulation and snapshot export. The
snapshot is written to a temporary file and copied through KIO
(KIO::file_copy), so the application is a real KF6 KIOCore consumer in
addition to KXmlGui/Config/I18n/Crash.

OHOS-specific adaptations:
  - Qt6 PrintSupport removed (patches 0001/0002): the published qtbase
    builds Qt with FEATURE_printsupport=OFF and ships no Qt6PrintSupport
    module (ksystemlog 26.04.0 precedent), so the component is dropped
    from find_package(), the link line and the destructor include. The
    print action is removed from the KXmlGui UI file and the QPrinter /
    QPrintDialog code is compiled out with QT_NO_PRINTER, which upstream
    already uses to guard the whole implementation. Snapshot export
    (QImageWriter + KIO::file_copy) is unaffected.
  - BUILD_DOC=OFF: KF6DocTools is not published on ohpcd and the handbook
    is not a runtime requirement (ksystemlog 26.04.0 precedent).
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS is not in the KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: no gettext/msgfmt toolchain on the device
  - QUERY_EXECUTABLE=qtpaths6: ECMQueryQt cannot resolve Qt6::qtpaths in
    this layout
  - CMAKE_SYSTEM_NAME=Linux: CMake has no HarmonyOS platform module, so
    UNIX would stay FALSE and every if(UNIX)-guarded probe would be
    skipped silently
  - conan_cmakedeps_paths.cmake written manually: qtbase/KF6 packages use
    cmake_find_mode=none, so CMakeDeps does not generate it
  - CMAKE_INSTALL_RPATH over the dependency lib directories: the installed
    app resolves Qt6/KF6 libraries without any environment
  - Linker flag -Wl,-z,max-page-size=0x1000: the default lld 0x10000 page
    size can split .dynsym/.dynstr into separate high-address RW LOAD
    segments that the OHOS musl loader refuses to mmap (ksystemlog
    precedent)
  - Dependencies: qtbase/6.11.1, kio/6.26.0, kxmlgui/6.26.0,
    kcrash/6.26.0, ki18n/6.26.0 and the KF6 6.26.0 line, with
    kconfigwidgets kept at 6.18.0 (the only version published on ohpcd;
    its transitive KF6 pins are overridden to the 6.26.0 line, kxmlgui
    6.26.0 precedent). openssl/zstd are declared explicitly for the
    KF6ArchiveConfig find_dependency chain.
  - Upstream ships no tests (no tests/ directory, no add_test/ctest
    registration, no QTEST macro anywhere); R51 self-authored
    test_package provides the verification.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KmagConan(ConanFile):
    name = "kmag"
    version = "26.04.0"
    description = "KDE screen magnifier for accessibility (KMagnifier)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/accessibility/kmag"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("kde", "accessibility", "magnifier", "ohos")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # Direct upstream requirements (find_package(KF6 COMPONENTS ...)).
        self.requires("kio/6.26.0")
        self.requires("kxmlgui/6.26.0")
        self.requires("kcrash/6.26.0")
        self.requires("ki18n/6.26.0")
        # KF6 6.26 line. kconfig/kcoreaddons/kguiaddons/kwidgetsaddons are
        # declared once with override=True: in Conan 2 the override form
        # both pins the whole graph to this version and adds it as a direct
        # requirement.
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        # kconfigwidgets is only published at 6.18.0 on ohpcd; its own
        # recipe pins the 6.18 line for its transitive KF6 deps, which are
        # overridden here so the whole graph resolves to the 6.26 line
        # (kxmlgui 6.26.0 precedent).
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        # Transitive KF6 closure declared explicitly so every package's
        # cmake dir lands on CMAKE_PREFIX_PATH for the installed
        # KF6*Config.cmake find_dependency chains.
        self.requires("kiconthemes/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("karchive/6.26.0")
        self.requires("kservice/6.26.0")
        # kiconthemes -> karchive exports KF6ArchiveConfig.cmake which
        # activates find_dependency(OpenSSL) and PkgConfig::LibZstd.
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")

    def build_requirements(self):
        # Upstream: find_package(ECM ${KF_MIN_VERSION} REQUIRED NO_MODULE).
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake has no HarmonyOS platform module: without this the system
        # name stays "HarmonyOS", UNIX is FALSE and every if(UNIX)-guarded
        # module silently skips all searches (kmousetool 26.04.0 precedent).
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_TESTING"] = "OFF"
        # KF6DocTools is not published on ohpcd; the handbook is not a
        # runtime requirement.
        tc.variables["BUILD_DOC"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # ki18n_install(po) needs gettext/msgfmt, which OHOS does not ship.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"

        # OHOS loader workaround (ksystemlog 26.04.0 precedent): pin the 4K
        # page layout so lld does not split .dynsym/.dynstr into separate
        # high-address RW LOAD segments.
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        # ECM's installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not. Set it manually so KDE cmake
        # modules (KDEInstallDirs, KDECMakeSettings, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # ECMQueryQt.cmake looks for TARGET Qt6::qtpaths via Qt6CoreTools,
        # which Qt6Config.cmake does not load in this layout. Point
        # QUERY_EXECUTABLE at qtpaths6 directly (kmousetool precedent).
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            if os.path.exists(qtpaths6):
                tc.variables["QUERY_EXECUTABLE"] = qtpaths6
                tc.variables["_cli_option"] = "--query"

        # Runtime rpath: resolve bare-name Qt6/KF6 entries of the installed
        # app without any environment.
        rpath_dirs = ["$ORIGIN"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    rpath_dirs.append(lib_dir)
        tc.variables["CMAKE_INSTALL_RPATH"] = ";".join(rpath_dirs)
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(rpath_dirs)

        # Qt6Config.cmake resolves extra components relative to
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH (kmousetool precedent).
        qt_extra = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                qt_cmake_dir = os.path.join(dep.package_folder, "lib", "cmake")
                if os.path.isdir(qt_cmake_dir) and any(
                        n.startswith("Qt6")
                        for n in os.listdir(qt_cmake_dir)
                ):
                    qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables[
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH"
            ] = ";".join(qt_extra)

        tc.generate()

        # qtbase and the KF6 packages use cmake_find_mode=none, so
        # CMakeDeps does not generate conan_cmakedeps_paths.cmake. Create
        # it manually with every dependency's cmake/lib/include dirs, plus
        # ECM's cmake and find-modules dirs (kmousetool precedent).
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")'
                )
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
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        # Build-time helper tools (uic/moc/kconfig_compiler) are OHOS
        # binaries: expose every dependency's lib dir to the build
        # environment or they cannot load libQt6Core.so.6.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    self.buildenv.append_path("LD_LIBRARY_PATH", lib_dir)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in
            # the SDK's llvm/lib directory; CI workers may not export it
            # via LD_LIBRARY_PATH. Prepend it so CMake TryCompile can link.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos"
                    "/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The compatible libc++_shared.so lives in /system/lib64; the
            # dependency trees may ship an incompatible copy that shadows
            # it, so prepend the system path (kio 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application package: the delivered product is bin/kmag.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
