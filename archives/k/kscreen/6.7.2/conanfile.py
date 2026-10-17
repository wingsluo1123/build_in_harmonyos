#!/usr/bin/env python3
"""Conan recipe for kscreen 6.7.2 on HarmonyOS PC.

kscreen is the KDE Plasma screen-management service: the kded module
(lib/plugins/kf6/kded/kscreen.so — KDEDModule + the KScreen::Config
generator/serializer) plus the kscreen-console diagnostic tool, both on top
of the published libkscreen 6.7.2 runtime (KF6Screen + the shared, QPA
independent backend plugin set).

OHOS-specific adaptations (recipe layer + two minimal source patches):
  - KSCREEN_PLASMA_INTEGRATION=OFF / KSCREEN_BUILD_HDRCALIBRATOR=OFF
    (patch 0001): the Plasma KCM/OSD/plasmoid need Plasma/PlasmaQuick,
    LayerShellQt, the plasma5support/kitemmodels QML modules and
    KF6::KCMUtils/Svg; the HDR calibrator needs Qt6GuiPrivate, the
    Qt6WaylandClient private headers, WaylandProtocols and KF6::Crash —
    none of them published on OHOS. Both groups sit behind configuration
    options that keep the upstream ON default, so the stock desktop build
    is unchanged; the OHOS build keeps the actual screen-management actor
    (kded daemon + console) and drops only the desktop widgets around it.
  - WITH_X11=OFF: upstream's X11-gated XInput touchscreen mapping and
    platform query path; the OHOS Qt builds have FEATURE_xcb/xlib=OFF
    (kwin/kglobalacceld 6.7.2 precedent).
  - KF6::XmlGui dropped from the kded plugin link list (patch 0002): no
    source in the built subset (kded/, common/, console/) references a
    KXmlGui class (vestigial upstream link).
  - kscreen_link_kf6_relocatable() (patch 0002): the published KF6 packages
    ship SONAME-less shared objects, so CMake links the imported targets by
    absolute package path and lld records that path in DT_NEEDED
    (non-relocatable, E537). The helper re-links the KF6 deps by
    -l:<basename> flags with the dependency lib directories attached to
    the target and re-adds the usage requirements; the kscreen_common
    object library propagates the flags through its link interface
    (INTERFACE_FLAGS: kpackage 6.26.0.1 / kscreenlocker 6.7.2 precedent).
  - KF6 is consumed through ECM's FindKF6.cmake umbrella (module mode): no
    ohpcd package ships lib/cmake/KF6/KF6Config.cmake, but ECM ships
    share/ECM/find-modules/FindKF6.cmake, which resolves each requested
    component as find_package(KF6<Component> <version> CONFIG) against
    CMAKE_PREFIX_PATH. Upstream sets CMAKE_MODULE_PATH=${ECM_MODULE_PATH};
    the recipe provides ECM_MODULE_PATH explicitly (CMakeDeps does not
    propagate it), and patch 0001 makes the component list explicit
    (CoreAddons, DBusAddons, I18n, WindowSystem).
  - qtbase/6.11.1.2 pinned with override=True: qtdeclarative/6.11.1, the
    KF6 6.26 stack and libkscreen/6.7.2 all resolve against it (it is the
    provider of Qt6::DBus and of the offscreen QPA plugin used by the
    tests). qtdeclarative (+qtshadertools, build context) and
    ki18n/kwindowsystem are not published as binaries against this Qt
    build, so the platform builds them from source (kwin 6.7.2 has the
    same override shape and its CI accepted the same consequence).
    kcoreaddons is consumed from the 6.26.0.1 dependency revision: the
    6.26.0 binary is not published against this Qt build either, and its
    from-source build dies in the upstream plugin autotest on OHOS
    (KPluginMetaDataTest::testFindingPluginInAppDirFirst — QFile::copy
    fails there), which 6.26.0.1 fixes (patch 0006-qfilecopy-harmonyos-
    plugin-test plus the DT_SONAME flags).
    kdbusaddons is consumed from the 6.18 series: the 6.29.0 revision
    reconciles only with the qtbase/6.11.1 line, and upstream 6.29 forces
    the X11-only Qt6GuiPrivate once the base Qt build ships Gui >= 6.10
    (no XKB_LIBRARY/XKB_INCLUDE_DIR in this toolchain); kdbusaddons/6.18.0
    resolves against qtbase-sql-dbus/6.11.1 with a published binary
    (kglobalacceld 6.7.2 precedent), patch 0003 lowers kscreen's KF6 floor
    accordingly, and KDEDModule's public API is unchanged across the two
    series.
  - Shared libdbus-1.so.3 vendored (built from the official dbus 1.14.10
    sources inside this recipe): libQt6DBus dlopen()s libdbus-1.so.3 at
    runtime, but the ohpcd registry only ships the static libdbus-1.a, so
    without a shared library every Qt6DBus consumer on the device gets an
    invalid session bus (kglobalacceld 6.7.2 precedent; drop this once a
    shared dbus package is published). Because the sandbox denies
    symlink() with EACCES in every writable location, the two alias names
    of the versioned shared object (libdbus-1.so.3, libdbus-1.so) are
    materialized as regular-file copies instead of CMake's symlinks; the
    loader resolves a copy identically.
  - Upstream autotests (tests/osdactions — QScreenActions against
    libkscreen's Fake backend) are built with BUILD_TESTING=ON and really
    executed on device during build(). The test needs no session bus: the
    Fake backend is loaded in-process (KSCREEN_BACKEND=Fake is set by the
    test itself) and only requires QT_PLUGIN_PATH to reach libkscreen's
    KSC_Fake.so. libkscreen's packaged backends however keep a
    build-tree-relative DT_NEEDED ("../../bin/libKF6Screen.so") that the
    loader resolves against the test process CWD, so the recipe stages
    that relative layout as a plain-file copy and puts the relative
    directory first on LD_LIBRARY_PATH (see
    _stage_relative_backend_layout): test binary and plugin then bind the
    same libKF6Screen.so instance, otherwise qobject_cast of the backend
    fails on duplicate QMetaObject chains. With this the full osdactions
    suite (12/12 functions) passes, a non-zero ctest exit code is treated
    as a build failure, and --no-tests=error keeps an empty test discovery
    a hard failure instead of a silent green.
  - package() re-signs the installed ELF tree: cmake.install rewrites the
    RUNPATH, which invalidates the toolchain-stamped .codesign section and
    the OHOS kernel then rejects execution of the shipped binaries
    (kscreenlocker 6.7.2 precedent: llvm-objcopy --remove-section
    .codesign + binary-sign-tool sign -selfSign 1).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KscreenConan(ConanFile):
    name = "kscreen"
    version = "6.7.2"
    description = "KDE Plasma screen management daemon (kded module) and kscreen-console"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/plasma/kscreen"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/Gui/Widgets/DBus/Quick (and the offscreen QPA plugin)
        # come from the 6.11.1.2 build; the override pins qtdeclarative and
        # the KF6 stack to it as well.
        self.requires("qtbase/6.11.1.2", override=True)
        # Qt6::Quick/QuickControls2 (kded plugin) — built from source by the
        # platform for this Qt build.
        self.requires("qtdeclarative/6.11.1")
        # KF6::Screen is the PUBLIC link dependency; libkscreen also ships
        # the backend plugins consumed at runtime through QT_PLUGIN_PATH.
        self.requires("libkscreen/6.7.2")
        # Component link deps of the built subset (see docstring):
        # KAboutData/KPluginFactory/KDirWatch (kcoreaddons_add_plugin in
        # kded/), KDEDModule (kdbusaddons), KLocalizedString (ki18n),
        # KWindowSystem (console). ki18n/kwindowsystem are not published
        # against this Qt build -> built from source by the platform;
        # kcoreaddons rides the 6.26.0.1 dependency revision, whose
        # upstream autotests pass on OHOS whether fetched or built from
        # source (see docstring). kdbusaddons rides the 6.18 series, whose
        # published binary reconciles with qtbase-sql-dbus/6.11.1 (see
        # docstring).
        self.requires("kcoreaddons/6.26.0.1")
        self.requires("kdbusaddons/6.18.0")
        self.requires("ki18n/6.26.0")
        self.requires("kwindowsystem/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # Qt6LinguistTools (lrelease) for the ECMPoQmTools po -> qm step
        # (ki18n_install(po)); published on ohpcd.
        self.tool_requires("qt6linguisttools/6.11.1")

    def layout(self):
        # Ninja generator: the OHOS port of GNU make 4.4.1 uses an
        # mkfifo-based jobserver, and the OHOS sandbox denies mkfifo
        # everywhere (EPERM on HMDFS, EROFS on /tmp) — any make -jN build
        # dies with "make: jobserver mkfifo ... Operation not permitted"
        # (kglobalacceld 6.7.2 precedent).
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendored shared libdbus-1.so.3 runtime for Qt6DBus (dlopen-based
        # loading on OHOS, see docstring). Fixed URL + SHA256.
        get(self,
            url="https://dbus.freedesktop.org/releases/dbus/dbus-1.14.10.tar.xz",
            sha256="ba1f21d2bd9d339da2d4aa8780c09df32fea87998b73da24f49ab9df1e36a50f",
            strip_root=True, destination="dbus-src")

    def _build_vendored_libdbus(self):
        """Build the shared dbus-1 client library (no expat needed)."""
        src = os.path.join(self.source_folder, "dbus-src")
        bld = os.path.join(self.build_folder, "dbus-build")
        gen = self.generators_folder
        # The bundled CMake helper of this conan version cannot configure a
        # custom source/build folder pair, so drive cmake directly, pointing
        # at the same conan_toolchain (Ninja generator, OHOS clang).
        variables = {
            "BUILD_SHARED_LIBS": "ON",
            "DBUS_BUILD_TESTS": "OFF",
            "DBUS_BUILD_TOOLS": "OFF",
            "DBUS_ENABLE_DOXYGEN_DOCS": "OFF",
            "DBUS_ENABLE_XML_DOCS": "OFF",
            "DBUS_ENABLE_X11": "OFF",
            "DBUS_ENABLE_SYSTEMD": "OFF",
            "DBUS_ENABLE_SELINUX": "OFF",
            "DBUS_ENABLE_APPARMOR": "OFF",
            "DBUS_ENABLE_EMBEDDED_TESTS": "OFF",
            "DBUS_ENABLE_MODULAR_TESTS": "OFF",
            "DBUS_ENABLE_INSTALLED_TESTS": "OFF",
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            # OHOS has no CMake platform file ("System is unknown to
            # cmake"); force the UNIX branch so dbus does not pick its
            # Windows transport (dbus/1.14.10 recipe precedent).
            "CMAKE_SYSTEM_NAME": "OHOS",
            "DBUS_SESSION_SOCKET_DIR": "/tmp",
        }
        args = [
            "cmake", "-G", "Ninja",
            "-S", src, "-B", bld,
            f"-DCMAKE_TOOLCHAIN_FILE={os.path.join(gen, 'conan_toolchain.cmake')}",
        ]
        args += [f"-D{k}={v}" for k, v in variables.items()]
        with self._cmake_build_env().vars(self).apply():
            self.run(" ".join(f'"{a}"' for a in args))
            # CMAKE_SYSTEM_NAME=OHOS selects CMake's Linux-like OHOS
            # platform rules, so the linked shared object carries the
            # versioned name libdbus-1.so.3.32.4 (DT_SONAME libdbus-1.so.3)
            # and CMake would normally add the alias names libdbus-1.so.3
            # (dlopen()/DT_NEEDED) and libdbus-1.so (linker) as symbolic
            # links in a follow-up step. The sandbox denies symlink() with
            # EACCES in every writable location (build tree and $HOME
            # alike), so that step aborts the target build right after the
            # object is linked. Build the shared object as an explicit
            # Ninja output and materialize both alias names as
            # regular-file copies instead: the dynamic loader resolves a
            # copy identically, and package() ships all three names.
            so = "libdbus-1.so.3.32.4"  # dbus 1.14.10, sha256 pinned above
            self.run(f'cmake --build "{bld}" --target lib/{so}')
            lib_dir = os.path.join(bld, "lib")
            for alias in ("libdbus-1.so.3", "libdbus-1.so"):
                dest = os.path.join(lib_dir, alias)
                if not os.path.lexists(dest):
                    shutil.copy2(os.path.join(lib_dir, so), dest)

    def _vendored_libdbus_dir(self):
        return os.path.join(self.build_folder, "dbus-build", "lib")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        # Upstream sets CMAKE_CXX_STANDARD 20 itself; drop the profile's
        # cppstd block so the two definitions cannot fight.
        tc.blocks.remove("cppstd")
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        if self.settings.os == "OHOS":
            # See docstring: the Plasma integration and the HDR calibrator
            # dependencies are not published on OHOS; WITH_X11 likewise.
            tc.variables["KSCREEN_PLASMA_INTEGRATION"] = "OFF"
            tc.variables["KSCREEN_BUILD_HDRCALIBRATOR"] = "OFF"
            tc.variables["WITH_X11"] = "OFF"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            # ECM_MODULE_PATH is what upstream's
            # "set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})" installs;
            # find-modules/ carries the FindKF6.cmake umbrella.
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # Qt6LinguistTools_DIR (ki18n_install(po) -> ECMPoQmTools): tool
        # requires are not on the host CMAKE_PREFIX_PATH.
        ltt = self.dependencies.build.get("qt6linguisttools")
        if ltt and ltt.package_folder:
            tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
                ltt.package_folder, "lib", "cmake", "Qt6LinguistTools")

        # qtdeclarative ships the Quick/QuickControls2 configs that
        # Qt6Config's component resolution must see (kscreenlocker 6.7.2
        # precedent).
        declarative = self.dependencies.get("qtdeclarative")
        if declarative and declarative.package_folder:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = declarative.package_folder

        qt_pkgs = [d for d in self.dependencies.values()
                   if d.package_folder and os.path.isdir(os.path.join(d.package_folder, "lib", "cmake"))]
        if qt_pkgs:
            lines = []
            # qtbase/qtdeclarative use cmake_find_mode=none, so CMakeDeps
            # does not emit conan_cmakedeps_paths.cmake; create it manually.
            for dep in qt_pkgs:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
            # qtbase must win the find_package(Qt6) lookup in any case
            # (re-assert last, kscreenlocker 6.7.2 precedent).
            qtbase = self.dependencies.get("qtbase")
            if qtbase and qtbase.package_folder:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qtbase.package_folder}/lib/cmake")')
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            if ltt and ltt.package_folder:
                ltt_cmake = os.path.join(ltt.package_folder, "lib", "cmake", "Qt6LinguistTools")
                lines.append(f'set(Qt6LinguistTools_DIR "{ltt_cmake}")')
            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def _library_runtime_env(self):
        runtime_env = Environment()
        if self.settings.os == "OHOS":
            # Vendored shared libdbus-1.so.3 must be resolvable when
            # Qt6DBus dlopen()s it (see docstring).
            vendored = self._vendored_libdbus_dir()
            if os.path.isdir(vendored):
                runtime_env.prepend_path("LD_LIBRARY_PATH", vendored)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                # qtbase installs its QPA plugins under plugins/, the KF6
                # stack (libkscreen backends) under lib/plugins/: the
                # offscreen platform plugin and KSC_Fake.so are both
                # reached through QT_PLUGIN_PATH.
                runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        for rel in ("bin", "lib", os.path.join("src", "lib"), "tests"):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # KDEInstallDirs runs the qtbase qtpaths host tool during
            # configure; the sandbox LD_LIBRARY_PATH may contain an
            # incompatible libc++_shared.so which shadows the compatible
            # one; prepend /system/lib64 so the loader resolves the
            # compatible libc++ first (kconfig/kcrash/kglobalacceld
            # precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so other
        # platforms are unaffected (kcrash/kglobalacceld precedent).
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
            self._build_vendored_libdbus()
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _stage_relative_backend_layout(self):
        # libkscreen's packaged backend plugins keep a build-tree-relative
        # DT_NEEDED ("../../bin/libKF6Screen.so"); the loader resolves it
        # against the *test process* CWD (= <build_folder>/tests), so
        # materialize "<build_folder>/../bin/libKF6Screen.so" as a plain
        # file copy (symlink() and link() are both refused on the OHOS
        # user volume). Together with the "../../bin" LD_LIBRARY_PATH
        # entry added below, the test binary and the plugin resolve the
        # identical path string to the identical file, i.e. a single
        # libKF6Screen.so instance: an unrelated copy is a second
        # instance, breaks qobject_cast<KScreen::AbstractBackend*> on the
        # QMetaObject chain and makes every osdactions function fail
        # (and a missing file makes the plugin dlopen() fail).
        libks = self.dependencies.get("libkscreen")
        if not (libks and libks.package_folder):
            return
        src = os.path.join(libks.package_folder, "lib", "libKF6Screen.so")
        if not os.path.isfile(src):
            return
        dest_dir = os.path.join(os.path.dirname(self.build_folder), "bin")
        dest = os.path.join(dest_dir, "libKF6Screen.so")
        if os.path.exists(dest):
            return
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(src, dest)

    def _run_upstream_tests(self):
        # tests/osdactions drives the screen actions of kscreen_common
        # against libkscreen's Fake backend (KSCREEN_BACKEND=Fake is set by
        # the test's initTestCase); BackendManager defaults to InProcess
        # for non-XRandR backends, so no session bus and no backend
        # launcher are needed — only QT_PLUGIN_PATH from
        # _library_runtime_env() (KSC_Fake.so) and the offscreen QPA
        # platform plugin from qtbase's plugins/ directory. The relative
        # DT_NEEDED layout of the packaged backend plugins is staged by
        # _stage_relative_backend_layout().
        self._stage_relative_backend_layout()
        test_env = self._library_runtime_env()
        test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # Must stay leftmost of the LD_LIBRARY_PATH prepends (conan applies
        # the last prepend first): the first hit for the test binary's
        # "libKF6Screen.so" NEEDED decides which instance the plugin's
        # relative DT_NEEDED is deduplicated against.
        test_env.prepend_path("LD_LIBRARY_PATH", "../../bin")
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
        # Real run of the upstream autotests; the exit code is captured and a
        # non-zero return fails the build. --no-tests=error additionally keeps
        # an empty discovery (e.g. a future patch/option dropping the test
        # target) a hard failure instead of a silent green (kdbusaddons
        # 6.29.0 precedent). Unlike packages whose tests cannot
        # run in the OHOS sandbox at all (kio 6.26.0 / karchive 6.19.0: those
        # document environment limitations and tolerate failures), the
        # environment staged above makes the osdactions suite genuinely green
        # on OHOS, so a failure here is a real regression — e.g. the
        # relative-DT_NEEDED double-instance failure this package's
        # knowledge draft records — and must not ship as a passing package.
        # Per-test timeout bounds a hung event loop.
        with test_env.vars(self).apply():
            ret = self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 120'.format(self.build_folder),
                ignore_errors=True,
            )
        if ret != 0:
            raise ConanException(
                "upstream osdactions ctest run failed (exit code {}); the "
                "ctest output above is the evidence — fix the regression or "
                "exclude the test explicitly before shipping".format(ret)
            )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()
        if self.settings.os == "OHOS":
            # Ship the vendored shared libdbus-1.so.3 (Qt6DBus dlopens it
            # at runtime; the registry only has a static libdbus-1.a).
            lib_dir = os.path.join(self.package_folder, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            for path in sorted(glob.glob(os.path.join(self._vendored_libdbus_dir(), "libdbus-1.so*"))):
                target = os.path.join(lib_dir, os.path.basename(path))
                if os.path.islink(path):
                    if not os.path.lexists(target):
                        os.symlink(os.readlink(path), target)
                elif not os.path.exists(target):
                    shutil.copy2(path, target)
            # cmake.install rewrote the RUNPATH of the shipped ELFs, which
            # invalidates the toolchain-stamped .codesign section; re-sign
            # (kscreenlocker 6.7.2 precedent).
            self._sign_ohos_elf_tree(self.package_folder)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package_info(self):
        # kscreen installs no linkable library and no CMake package (the
        # kded module and the console are runtime artifacts); keep CMakeDeps
        # from generating find modules for it.
        self.cpp_info.set_property("cmake_find_mode", "none")
