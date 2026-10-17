#!/usr/bin/env python3
"""Conan recipe for skladnik 26.04.2 - KDE Sokoban (warehouse keeper) game.

skladnik (KDE Gear 26.04.2) is the KDE port of ksokoban: a Qt6 Widgets /
QGraphicsView puzzle game built on the KDE Games framework (KDEGames6 from
libkdegames). The player pushes stones onto goal fields across the five
built-in collections (Sasquatch, Mas Sasquatch, Sasquatch III, Microban,
Sasquatch IV) that ship embedded in the binary through src/skladnik.qrc.
Upstream installs a single executable, bin/skladnik.

Upstream registers no test suite (no tests/, no autotests/, no add_test(),
no enable_testing(), no ECMAddTests anywhere in the tarball - grep
verified, N=0). Consumer-side verification lives in test_package.

OHOS adaptations (patches/0001..0003):

* KIO trimmed. Upstream uses KIO in exactly two places, both in
  src/MainWindow.cpp: KIO::file_copy() to download a *remote* level
  collection into a QTemporaryFile, and KUrlMimeData::urlsFromMimeData()
  to read the URLs of a drag-and-drop payload. The kio conan package is
  published on the 6.14.0 and 6.26.0 KF6 lines only, while libkdegames
  (a REQUIRED dependency) anchors the 6.18.0 line; mixing the lines
  changes every KF6 package id and no prebuilt binary matches
  (kgoldrunner 26.04.0 precedent). Both uses are replaced by their Qt
  equivalents - QNetworkAccessManager with NoLessSafeRedirectPolicy inside
  a blocking QEventLoop (mirroring the blocking job->exec() upstream) and
  QMimeData::urls() - so http/https/ftp/file collection URLs and URL drops
  keep working. Only KIO-proprietary VFS schemes (smb://, webdav://, ...)
  are lost; their kioslave backends are not published for this platform
  either, so the trimmed build loses no reachable behaviour.
* KF6::CoreAddons is linked explicitly. Upstream src/CMakeLists.txt never
  lists it, yet src/main.cpp includes KAboutData; that header only reached
  the compile line through the transitive KCoreAddons interface of
  KF6::KIOCore. Trimming KIO therefore has to relink CoreAddons, otherwise
  the build dies with a missing KAboutData header (kgoldrunner 26.04.0 patch
  precedent; reproduced by CI build #92200 on this recipe before the fix).
* KF6DocTools is already optional upstream (find_package without REQUIRED,
  doc/ and kdoctools_install(po) guarded by if(KF6DocTools_FOUND)), so no
  patch is needed - the toolchain sets
  CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE and the DocBook handbook is
  skipped (kdoctools is not part of the published KF6 closure; audiocd
  26.04.3 / kgoldrunner 26.04.0 precedent).
* POVRay is disabled through CMAKE_DISABLE_FIND_PACKAGE_POVRay. Upstream
  src/images/CMakeLists.txt regenerates the sprite PNGs with POV-Ray when
  the renderer happens to be on PATH; the tarball already ships the
  rendered PNGs that themes/CMakeLists.txt installs, so pinning the
  renderer absent keeps the build deterministic on any worker.
* KF_IGNORE_PLATFORM_CHECK=TRUE bypasses the KDE platform allowlist (OHOS
  is not in it) and KF_SKIP_PO_PROCESSING=ON skips the ki18n_install(po)
  catalog step (no gettext toolchain on the worker; audiocd precedent).
* OHOS musl loader workaround: -Wl,-z,max-page-size=0x1000 on the
  executable link. The default lld 0x10000 max-page-size splits
  .dynsym/.dynstr into separate high-address RW LOAD segments that the
  OHOS loader refuses to mmap (audiocd 26.04.3 / kfourinline 26.04.0
  precedent).

Dependency line: qtbase/6.11.1 (Qt6 Core/Gui/Widgets/Network) plus the KF6
6.18.0 line pinned to match the libkdegames/26.04.0 binary closure
(kconfig/kconfigwidgets/kcoreaddons/kcrash/kdbusaddons/ki18n/
kwidgetsaddons/kcodecs/kxmlgui/kiconthemes), ecm/6.26.0 as the build tool
(ECM modules are forward-compatible with the 6.18 KF6 line).

Runtime environment: the game is a QApplication, so on the OHOS worker it
runs with QT_QPA_PLATFORM=offscreen and an isolated HOME
(kirigami-addons 1.13.0 / audiocd 26.04.3 / kgoldrunner 26.04.0 test
precedent).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class SkladnikConan(ConanFile):
    name = "skladnik"
    version = "26.04.2"
    description = ("KDE Sokoban game (Skladnik) - push every stone onto its "
                   "goal field (KDE Games, Qt6 Widgets + KDEGames6)")
    license = "GPL-2.0-or-later AND GFDL-1.2-only"
    homepage = "https://invent.kde.org/games/skladnik"
    url = ("https://download.kde.org/stable/release-service/26.04.2/src/"
           "skladnik-26.04.2.tar.xz")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KF6 6.18 line - must match the libkdegames/26.04.0 binary closure
        # exactly (any version bump changes every downstream package id and
        # no prebuilt binaries remain).
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.18.0", options={"shared": True})
        self.requires("kconfigwidgets/6.18.0", options={"shared": True})
        self.requires("kcoreaddons/6.18.0", options={"shared": True})
        self.requires("kcrash/6.18.0", options={"shared": True})
        self.requires("kdbusaddons/6.18.0", options={"shared": True})
        self.requires("ki18n/6.18.0", options={"shared": True})
        self.requires("kwidgetsaddons/6.18.0", options={"shared": True})
        self.requires("kcodecs/6.18.0", options={"shared": True})
        self.requires("kxmlgui/6.18.0", options={"shared": True})
        self.requires("libkdegames/26.04.0")
        # karchive: force the 6.18.0 line for the whole graph. Every 6.18
        # package's prebuilt binary anchors karchive/6.18.Z, so the override
        # keeps the closure consistent (same override libkdegames uses).
        self.requires("karchive/6.18.0", override=True,
                      options={"shared": True})
        # kiconthemes: skladnik never asks for KF6 IconThemes itself (it is
        # transitive through kxmlgui/kconfigwidgets/libkdegames), so this is a
        # pure version override, not a direct require.
        #
        # Pin 6.18.0.1, NOT 6.18.0. The newest kiconthemes/6.18.0 recipe
        # revision requires karchive/6.19.0, so under the karchive/6.18.0
        # override its package id (5937e6fd...) has no published binary and
        # conan rebuilds it from source on every CI run. That dependency-side
        # rebuild is the single largest source of worker flakiness for this
        # package: its own BUILD_TESTING=ON ctest suite fails when the
        # worker's KF6 libraries do not load (build #92382, two conan homes
        # mixed in one log), and its CMake compiler probe dies with
        # "/bin/sh: Resource temporarily unavailable" on fork-starved workers
        # (builds #92399 and #92881, Error 127 before any of our code is
        # compiled). kiconthemes/6.18.0.1 is the R37 adaptation-fix release of
        # the same upstream 6.18.0 sources, pinned to karchive/6.18.0, and its
        # published binary carries exactly package id 5937e6fd... - so the
        # override turns the whole graph prebuilt and removes the rebuild.
        # Verified with conan graph info: 0 nodes needing a build.
        self.requires("kiconthemes/6.18.0.1", override=True,
                      options={"shared": True})

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def validate(self):
        # R32: never compare settings.os with == "Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"skladnik is adapted for Linux and OHOS, not "
                f"{self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # po/ catalog generation needs the gettext msgfmt toolchain, which
        # the worker does not provide (audiocd 26.04.3 precedent).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # Upstream already guards doc/ with if(KF6DocTools_FOUND); disabling
        # the lookup keeps kdoctools (absent from the published KF6 closure)
        # out of the configure step entirely.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"
        # Deterministic sprites: never regenerate the shipped PNGs with
        # POV-Ray even if a povray binary happens to be on the worker PATH.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_POVRay"] = "TRUE"
        # KDEInstallDirs single-prefix layout inside the conan package
        # (libkdegames / kgoldrunner precedent).
        tc.variables["KDE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # ECM's own ECMConfig.cmake sets ECM_MODULE_PATH but the
        # CMakeDeps-generated one does not (audiocd precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )
        if self.settings.os == "OHOS":
            # OHOS musl loader workaround (audiocd precedent): pin the 4K
            # page layout so .dynsym/.dynstr do not end up in a separate
            # high-address RW LOAD segment the loader refuses to mmap.
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
        tc.generate()

        # qtbase and the KF6 packages use cmake_find_mode=none, so CMakeDeps
        # does not generate conan_cmakedeps_paths.cmake. Write it manually
        # (audiocd / libkcddb / kgoldrunner precedent).
        lines = []
        all_pkgs = {}
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep in self.dependencies.host.values():
            if dep and dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep in self.dependencies.build.values():
            if dep and dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep_name in sorted(all_pkgs):
            pkg = all_pkgs[dep_name]
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            for libdir in ("lib", "lib64"):
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/{libdir}")'
                )
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
            bindir = os.path.join(pkg, "bin")
            if os.path.isdir(bindir):
                lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{bindir}")')
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM",
                                     "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                f'list(PREPEND CMAKE_PROGRAM_PATH "{ecm.package_folder}/bin")'
            )
        # KDEGames6 exports its cmake config under lib/cmake/KDEGames6.
        kdegames = self.dependencies.get("libkdegames")
        if kdegames and kdegames.package_folder:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{kdegames.package_folder}/lib/cmake/KDEGames6")'
            )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
        paths_file = os.path.join(self.generators_folder,
                                  "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools (moc / uic / rcc / kconfig_compiler) shipped by the
        # conan packages are OHOS binaries: they need libc++_shared from
        # /system/lib64 plus every dependency lib dir on LD_LIBRARY_PATH
        # (audiocd 26.04.3 / kconfig 6.26.0 precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            import glob as _glob
            for llvm_lib in sorted(
                _glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/"
                    "llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        copy(self, "LICENSES",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Runtime helpers for consumers (test_package): the theme assets are
        # installed under share/skladnik/themes and the KGameRenderer theme
        # lookup goes through XDG_DATA_DIRS.
        self.runenv_info.prepend_path(
            "XDG_DATA_DIRS", os.path.join(self.package_folder, "share")
        )
        # libKDEGames6.so NEEDs libopenal.so.1 and libsndfile (transitive
        # requirements of libkdegames); surface their lib dirs on the run
        # environment so consumer tests can resolve every ELF.
        for dep_name in ("openal-soft", "libsndfile"):
            try:
                dep = self.dependencies.get(dep_name)
            except Exception:
                dep = None
            if dep and dep.package_folder:
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    self.runenv_info.prepend_path("LD_LIBRARY_PATH", lib)
