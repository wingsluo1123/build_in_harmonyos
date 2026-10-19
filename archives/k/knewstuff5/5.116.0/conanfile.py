#!/usr/bin/env python3
"""Conan recipe for knewstuff5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

KNewStuff is the KDE "Get Hot New Stuff" framework (libKF5NewStuffCore /
libKF5NewStuff / libKF5NewStuffWidgets + knewstuff-dialog tool).

OHOS-specific adaptations (pattern proven by karchive5/kconfig5/attica5):
  - KF_IGNORE_PLATFORM_CHECK=TRUE: OHOS is not in the KDE platform list.
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation.
  - BUILD_DESIGNERPLUGIN=OFF (upstream forces OFF when cross-compiling).
  - BUILD_TESTING=ON + ctest for the upstream autotests.
  - ECM_MODULE_PATH / conan_cmakedeps_paths.cmake written manually because
    ecm and qt5-qtbase are cmake_find_mode=none, so CMakeDeps does not wire
    their lib/cmake dirs into the search paths.
  - SONAME flags on OHOS (CMAKE_PLATFORM_NO_VERSIONED_SONAME pattern, E537).
  - Upstream CMakeLists.txt requires KF5 components that are not published on
    ohpcd (KIO5/XmlGui5/KService5/Completion5/IconThemes5/Package5); patches
    scope the build down to the always-available KF5NewStuffCore +
    knewstuff-dialog, see patches/ for the exact set.
  - test_package exercises the real KNSCore API (KNSCore::Entry /
    KNSCore::Author) - R34.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class Knewstuff5Conan(ConanFile):
    name = "knewstuff5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - Get Hot New Stuff framework"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/knewstuff"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    # KF5NewStuffCore is delivered shared-only on OHOS: the runtime mirror /
    # re-sign mechanism and the Qt/KF5 dependency closure all assume shared
    # libs. A static option is intentionally not exposed rather than
    # advertising a shared=False that BUILD_SHARED_LIBS ignores.

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # force=True: attica5 pins qtbase 5.15.2, kconfig5 pins 5.15.2.2
        # (with Qt5Xml). 5.15.2.2 is the superset - force it to resolve the
        # version conflict (same resolution as kconfig5's KF5 deps).
        self.requires("qt5-qtbase/5.15.2.2", force=True)
        # Root-level force: qt5-qtbase exact-pins zlib/1.3.1 whose remote
        # binary is non-PIC and breaks the karchive5 shared link (E541/E533);
        # zlib/1.3.1.1 is the PIC rebuild and its binaries are cached.
        self.requires("zlib/1.3.1.1", force=True)
        # KF5 NewStuff required deps (upstream CMakeLists.txt), published on
        # ohpcd at 5.116.0:
        self.requires("attica5/5.116.0")
        self.requires("kcoreaddons5/5.116.0")
        self.requires("kconfig5/5.116.0")
        self.requires("ki18n5/5.116.0")
        self.requires("kitemviews5/5.116.0")
        self.requires("kwidgetsaddons5/5.116.0")
        self.requires("karchive5/5.116.0")
        self.requires("kpackage5/5.116.0")
        # Runtime-only upstream dep (find_package(KF5Kirigami2) TYPE RUNTIME):
        # the shipped qtquick plugin's QML imports org.kde.kirigami and
        # knewstuff-dialog needs it to load. Not REQUIRED at configure so its
        # absence is invisible to the build - must be in the closure anyway.
        self.requires("kirigami2/5.116.0")
        # qtquick plugin (org.kde.newstuff QML plugin) needs Qt5::Qml/Quick;
        # qt5-qtbase does not ship Qml, the standalone qt5-qtdeclarative does.
        self.requires("qt5-qtdeclarative/5.15.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase ships per-module cmake configs but no aggregated Qt5Config
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # Scope the build to dependency-complete targets: KIO/Service/
        # XmlGui/Completion/IconThemes KF5 components are not published on
        # ohpcd, upstream REQUIRED find_package list must be trimmed (see
        # patches/0001). Scoped = KF5NewStuffCore + qtquick plugin +
        # knewstuff-dialog.
        tc.variables["KNEWSTUFF_OHOS_SCOPED"] = "ON"

        if str(self.settings.os) == "OHOS":
            # SONAME emission on OHOS (karchive5/kconfig5 precedent, E537)
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            targets = {"armv8": "aarch64-linux-ohos"}
            target = targets.get(str(self.settings.arch))
            if target:
                tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = self._cmake_path(
                os.path.join(ecm.package_folder, "share", "ECM")
            )
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    f"{ecm_share}/modules",
                    f"{ecm_share}/find-modules",
                    f"{ecm_share}/kde-modules",
                ]
            )

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            moc_path = os.path.join(qtbase.package_folder, "bin", "moc")
            rcc_path = os.path.join(qtbase.package_folder, "bin", "rcc")
            if not os.path.isfile(moc_path):
                raise RuntimeError(
                    "qt5-qtbase/5.15.2.2 does not provide the required bin/moc tool"
                )
            if not os.path.isfile(rcc_path):
                raise RuntimeError(
                    "qt5-qtbase/5.15.2.2 does not provide the required bin/rcc tool"
                )
            tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
            tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path

        self._prepare_qt_mkspec_compat(qtbase.package_folder)

        # conan_cmakedeps_paths.cmake: qtbase and the KF5 deps are
        # cmake_find_mode=none, CMakeDeps does not add their lib/cmake dirs
        # to CMAKE_PREFIX_PATH - do it manually (karchive5/kconfig5 pattern).
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
        ]
        qt_pkg = self._cmake_path(qtbase.package_folder)
        lines += [
            f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
            f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
            f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
        ]
        if ecm:
            ecm_pkg = self._cmake_path(ecm.package_folder)
            ecm_cmake = f"{ecm_pkg}/share/ECM/cmake"
            lines += [
                f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")',
                f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")',
            ]
        for dep_name in (
            "attica5",
            "kcoreaddons5",
            "kconfig5",
            "ki18n5",
            "kitemviews5",
            "kwidgetsaddons5",
            "karchive5",
            "kpackage5",
            "qt5-qtdeclarative",
        ):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                dep_pkg = self._cmake_path(dep.package_folder)
                lines += [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep_pkg}/lib/cmake")',
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep_pkg}/lib")',
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep_pkg}/include")',
                ]
        lines += [
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")',
            # qt_add_resources (used by src/tools and src widgets) is defined
            # as a Qt6-style alias inside qtbase's Qt5CoreMacros.cmake, which
            # is not pulled in under CMakeDeps. Include it directly.
            'include("' + qt_pkg + '/lib/cmake/Qt5Core/Qt5CoreMacros.cmake")',
            # Upstream links Qt5::Qml/Quick via find_package(Qt5 COMPONENTS
            # Qml Quick); CMakeDeps emits qtdeclarative as a standalone
            # Qt5QmlConfig.cmake that the COMPONENTS form never loads. Pull
            # it in explicitly from this same generators folder; it defines
            # Qt5::Qml carrying all qtdeclarative libs (incl. Qt5Quick).
            'if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/Qt5QmlConfig.cmake")',
            '  include("${CMAKE_CURRENT_LIST_DIR}/Qt5QmlConfig.cmake")',
            'endif()',
            # CMakeDeps declares only Qt5::Qml (one global target); alias
            # Qt5::Quick to it so upstream target_link_libraries(Qt5::Quick)
            # resolves.
            'if(TARGET Qt5::Qml AND NOT TARGET Qt5::Quick)',
            '  add_library(Qt5::Quick INTERFACE IMPORTED)',
            '  set_property(TARGET Qt5::Quick APPEND PROPERTY '
            'INTERFACE_LINK_LIBRARIES Qt5::Qml)',
            'endif()',
        ]
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    @staticmethod
    def _cmake_path(path):
        return os.fspath(path).replace("\\", "/")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # Qt5CoreConfigExtrasMkspecDir.cmake points at a build-tree path
        # (<pkg>/../b/mkspecs/linux-clang); mirror the whole mkspecs tree so
        # '../common/posix/qplatformdefs.h' resolves (karchive5 precedent).
        src_mkspecs = os.path.join(qt_package_folder, "mkspecs")
        dst_mkspecs = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs"
        )
        if os.path.isdir(src_mkspecs) and not os.path.isdir(dst_mkspecs):
            os.makedirs(os.path.dirname(dst_mkspecs), exist_ok=True)
            shutil.copytree(src_mkspecs, dst_mkspecs)

    def _runtime_env(self):
        env = Environment()
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib"):
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, os.pardir)
        )
        return env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.info(
                "Skipping upstream CTest during cross-compilation; target "
                "execution is required on OHOS"
            )
            return
        mirror = self._build_runtime_mirror()
        test_env = Environment()
        # Materialised view only - never point at package lib dirs (E505:
        # versioned soname symlink aliases do not resolve) or at untrusted
        # ELF copies (E212). /system/lib64 first for platform libs.
        test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.prepend_path("LD_LIBRARY_PATH", mirror)
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
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    # Path to the system ELF self-sign tool (hmmac/E212 requirement).
    _SIGN_TOOL = "/data/service/hnp/bin/binary-sign-tool"

    def _build_runtime_mirror(self):
        """Materialise and freshly self-sign the full shared-lib closure.

        Two OHOS loader constraints make the conan package lib dirs
        unusable directly at test time:
          - E505: the musl loader cannot resolve dependencies through the
            versioned soname symlink aliases in package folders
            (libfoo.so.5 -> libfoo.so.5.116.0).
          - E212: package ELF files carry self-sign data the current system
            does not trust, so dlopen fails with "Permission denied" even
            though the Unix mode grants access.

        Materialise every dependency library and the just-built shared
        libs as real files in one directory and re-self-sign each ELF with
        the system binary-sign-tool. Signed output is written via a temp
        file and then cat-over the target so the original executable mode
        is preserved (HMDFS ignores chmod).
        """
        mirror = os.path.join(self.build_folder, "runtime-mirror")
        if os.path.isdir(mirror):
            shutil.rmtree(mirror)
        os.makedirs(mirror)

        candidates = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                candidates.extend(glob.glob(os.path.join(libdir, "*.so")))
                candidates.extend(
                    glob.glob(os.path.join(libdir, "*.so.[0-9]*"))
                )
        # Just-built shared libraries (real files under build/bin).
        candidates.extend(
            glob.glob(os.path.join(self.build_folder, "bin", "lib*.so"))
        )

        def _resolve_elf(src):
            # Follow the whole symlink chain; return a path to a real ELF
            # file (or None if the entry is dangling/non-ELF).
            real = os.path.realpath(src)
            if real and os.path.isfile(real):
                return real
            return None

        copied = set()
        for src in candidates:
            # Materialise every link NAME (libfoo.so, libfoo.so.5) with the
            # content of its real target - the loader looks up these exact
            # soname names, so the aliases cannot be dropped (E505).
            name = os.path.basename(src)
            if name in copied:
                continue
            real = _resolve_elf(src)
            if not real:
                continue
            dst = os.path.join(mirror, name)
            shutil.copyfile(real, dst)
            # Preserve the link entry's intended executable mode: prefer the
            # real target's mode (chmod is a no-op on HMDFS).
            shutil.copymode(real, dst)
            copied.add(name)

        if not copied:
            raise RuntimeError("runtime-mirror collected no libraries")

        for name in copied:
            path = os.path.join(mirror, name)
            tmp = os.path.join(mirror, ".tmp-signed")
            self.run(
                '"{}" sign -selfSign 1 -inFile "{}" -outFile "{}" '
                "-signAlg SHA256withECDSA".format(self._SIGN_TOOL, path, tmp),
                quiet=True,
            )
            # Preserve path's executable mode: overwrite content instead
            # of replacing the inode (chmod is a no-op on HMDFS).
            with open(tmp, "rb") as src_f, open(path, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f)
            os.remove(tmp)

        self.output.info(
            "runtime-mirror prepared: {} signed libraries at {}".format(
                len(copied), mirror
            )
        )
        return mirror

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5NewStuffCore"]
        self.cpp_info.bindirs = ["bin"]
