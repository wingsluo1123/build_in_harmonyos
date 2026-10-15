#!/usr/bin/env python3
"""Conan recipe for kscreenlocker 6.7.2 on HarmonyOS PC.

kscreenlocker is the KDE Plasma screen locker: the KScreenLocker library
(KSldApp lock-state machine, Wayland lock server, global-shortcut
handling, logind session tracking, power-management inhibition) plus the
kscreenlocker daemon binary. The greeter (PAM + PlasmaQuick UI) and the
KCM settings module are not built: their dependency chain is not
published on ohpcd.

Upstream hard requirements: Qt6 >= 6.10.0 (DBus/Widgets/Quick/Test),
ECM >= 6.26.0, KF6 >= 6.26.0 (GlobalAccel/I18n/IdleTime/Notifications/
Solid/WindowSystem/XmlGui), Wayland 1.3+ (Client/Server).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list)
  - patches/0001: HAVE_X11 gate — the X11/XCB finds become OPTIONAL and
    the X11 locker (x11locker.cpp) plus the X11 grab paths in ksldapp.cpp
    / globalaccel.cpp compile out when X11 is unavailable; the Wayland
    lock path remains
  - patches/0002: KSCREENLOCKER_BUILD_GREETER / KSCREENLOCKER_BUILD_KCM
    options (both OFF here). The greeter needs PAM, PlasmaQuick,
    LayerShellQt and KF6Screen; the KCM needs KCMUtils — none published
    on ohpcd. The core library, the settings static lib and the
    kscreenlocker daemon build without them.
  - patches/0003: the Qt6GuiPrivate find_package becomes optional — only
    the X11 locker autotest uses it (private qtx11extras_p.h)
  - patches/0004: C++20 compatibility. std::expected is C++23-only and
    the OHOS toolchain (clang 15 / libc++ 15) ships no <expected>;
    PowerInhibitor's expected<uint, QDBusError> is replaced by
    QDBusReply<uint> (identical value-or-error semantics) and the
    upstream CMAKE_CXX_STANDARD is lowered from 23 to 20
    (knighttime 6.7.2 precedent)
  - patches/0005: upstream 6.7.2 never defines KScreenLocker_HEADERS,
    so install() ships no public headers at all; the patch defines it
    (ksldapp.h plus the KsldApp forwarding header)
  - BUILD_TESTING=OFF in the conan build: logindTest needs a session
    D-Bus and kscreenlocker_test is an interactive demo that locks
    immediately and runs until unlock (see notes.md); consumer-side
    verification is carried by the test_package E2E
  - Dependencies: qtbase/6.11.1 + qtbase-sql-dbus/6.11.1 (the plain
    qtbase is built FEATURE_dbus=OFF and the sql-dbus variant provides
    Qt6::DBus; the two packages coexist by design — knighttime
    precedent), qtdeclarative/6.11.1 (Qt6::Quick), wayland/1.22.0, the
    KF6 stack at 6.26.0
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable
  - WaylandScanner_EXECUTABLE pinned to the wayland package's
    bin/wayland-scanner (arm64 native binary; libkscreen precedent);
    on OHOS the binary is staged into the build folder and re-signed
    (pool-cache ELF signatures are rejected by the device kernel)
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none; Qt6_DIR is re-asserted to qtbase-sql-dbus
    LAST so find_package(Qt6 COMPONENTS DBus) resolves there
  - No CMAKE_SHARED_LIBRARY_SONAME flags: on OHOS the missing platform
    soname flag keeps the build free of the versioned .so symlink chain
    (the device kernel denies symlinks on /storage, round 21 evidence);
    DT_SONAME comes from patch 0008's explicit -Wl,-soname link option
    and the KF6 deps are linked by exact-file-name -l:libKF6*.so flags
    (the KF6:: targets are dropped from the link interface) so the
    linker records bare basenames instead of cache paths
    (kpackage/6.26.0.1 0005 precedent for the basename goal)
  - package() re-signs every installed ELF (knotifyconfig 6.26.0
    precedent: CMake install rewrites the RUNPATH, which invalidates
    the build-time .codesign section and makes the OHOS loader refuse
    the library with "Permission denied")
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KscreenlockerConan(ConanFile):
    name = "kscreenlocker"
    version = "6.7.2"
    description = "KDE Plasma screen locker (KScreenLocker library + daemon)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/plasma/kscreenlocker"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # Shared-only by construction: patch 0008 gates -Wl,-soname on the
        # shared link, package() runs the OHOS ELF refresh on
        # lib/libKScreenLocker.so and the consumer test loads the shared
        # object at run time.  The shared option stays declared (it is part
        # of this recipe family's package_id shape), but a static request
        # would silently produce a package that claims shared=False while
        # containing a shared library -- reject it like the other OHOS
        # adaptations that only package .so (ace 8.0.5, aeolus 0.10.4,
        # adwaita-qt 1.4.2 precedent).
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "kscreenlocker 6.7.2 OHOS adaptation only packages shared "
                "libraries (libKScreenLocker.so); use -o '&:shared=True' "
                "(the default)."
            )

    def requirements(self):
        # Qt6::Core/Gui/Widgets/Test from the plain qtbase build.
        self.requires("qtbase/6.11.1")
        # Qt6::DBus lives only in the qtbase-sql-dbus variant (the plain
        # qtbase/6.11.1 is built with FEATURE_dbus=OFF; the two packages
        # coexist by design, see qtbase-sql-dbus notes).
        self.requires("qtbase-sql-dbus/6.11.1")
        # Qt6::Quick for the settings module (Qt6QuickConfig.cmake).
        self.requires("qtdeclarative/6.11.1")
        # Wayland::Client + Wayland::Server (upstream min 1.3).
        self.requires("wayland/1.22.0")
        # KF6 stack: the 6.26.0 version gate in find_package(KF6 ...)
        # requires every component at >= 6.26.0 (patch 0002 moves
        # Crash/KIO/Svg into the greeter and KCMUtils into the KCM, both
        # OFF here). kconfig/kcoreaddons/kpackage are direct requires
        # because CMakeDeps only generates per-package KF6 config files
        # for direct requires, and kscreenlocker links their targets
        # outside the gated find (CMakeLists:217-219 KF6::CoreAddons/
        # ConfigGui/Package; patch 0006 adds CoreAddons/Config/Package to
        # the KF6 COMPONENTS find and drops the vestigial ConfigQml link
        # from settings/ — real-machine G2 configure failures, rounds
        # 14/16: "target was not found" / no KF6ConfigGuiConfig.cmake).
        # kpackage/6.26.0.1 is the fix release that pairs karchive/6.26.0
        # (kpackage/6.26.0 pinned karchive/6.19.0 exactly, which
        # conflicts with kiconthemes/6.26.0's exact karchive/6.26.0 pin
        # in any graph containing both; 6.26.0.1 also requires zstd
        # directly so its generate() link-flag lookups stay satisfied).
        self.requires("kconfig/6.26.0")         # KF6Config package -> KF6::ConfigGui (core target); ConfigQml dropped (patch 0006)
        # kconfigwidgets/6.18.0 (via kxmlgui) pins kcoreaddons/6.18.0
        # exact while kpackage/6.26.0.1 pins 6.26.0 exact — override to
        # 6.26.0 (kpackage's 6.19.0 KF_DEP_VERSION floor rules out going
        # down to 6.18.0). The published 6.26-gen recipes override
        # kconfig/ki18n/kcolorscheme/kguiaddons/kwidgetsaddons the same
        # way; kcoreaddons is the one gap this consumer closes.
        self.requires("kcoreaddons/6.26.0", override=True)  # KF6::CoreAddons
        self.requires("kglobalaccel/6.26.0")    # KF6::GlobalAccel
        self.requires("ki18n/6.26.0")           # KF6::I18n + translations
        self.requires("kidletime/6.26.0")       # KF6::IdleTime
        self.requires("knotifications/6.26.0")  # KF6::Notifications
        self.requires("kpackage/6.26.0.1")      # KF6::Package (fix release, karchive 6.26.0 pairing)
        self.requires("solid/6.26.0")           # KF6::Solid
        self.requires("kwindowsystem/6.26.0")   # KF6::WindowSystem
        self.requires("kxmlgui/6.26.0")         # KF6::XmlGui

    def build_requirements(self):
        # ECM >= 6.26.0 REQUIRED upstream.
        self.tool_requires("ecm/6.26.0")
        # Qt6LinguistTools for the ECMPoQmTools po -> qm step
        # (ki18n_install(po)); published on ohpcd as qt6linguisttools.
        self.tool_requires("qt6linguisttools/6.11.1")
        # wayland-scanner runs at build time (ecm_add_wayland_server_protocol
        # for protocols/ksld.xml); the wayland package ships an arm64
        # scanner binary that runs natively on this host.
        self.tool_requires("wayland/1.22.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The OHOS profile pins cppstd=17; patch 0004 lowers the upstream
        # C++23 to C++20, which clang 15 compiles cleanly (knighttime
        # precedent).
        tc.blocks.remove("cppstd")
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KSCREENLOCKER_BUILD_GREETER"] = "OFF"
        tc.variables["KSCREENLOCKER_BUILD_KCM"] = "OFF"
        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules are found (libkscreen precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # WaylandScanner_EXECUTABLE: the wayland package's arm64 scanner
        # (libkscreen precedent), qtbase libexec copy as fallback. On
        # OHOS the binary is staged into the build folder and re-signed
        # before build (see _stage_ohos_wayland_scanner): pool-cache
        # ELFs carry CI certificates the device kernel rejects on exec
        # ("Operation not permitted", round 19 evidence).
        scanner_source = self._wayland_scanner_source()
        if scanner_source:
            if str(self.settings.os) in ("OHOS", "HarmonyOS"):
                scanner_source = os.path.join(
                    self.build_folder, "wayland-scanner-tool", "wayland-scanner"
                )
            tc.variables["WaylandScanner_EXECUTABLE"] = scanner_source

        # Qt6LinguistTools_DIR (libkscreen precedent).
        ltt = self.dependencies.build.get("qt6linguisttools")
        if ltt:
            tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
                ltt.package_folder, "lib", "cmake", "Qt6LinguistTools"
            )

        # Qt6::Quick lives in the qtdeclarative package: advertise its
        # root to Qt6Config (knighttime precedent).
        qtdecl = self.dependencies.get("qtdeclarative")
        if qtdecl and qtdecl.package_folder:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = qtdecl.package_folder

        # conan_cmakedeps_paths.cmake created manually because qtbase uses
        # cmake_find_mode=none (libkscreen/kwayland precedent).
        qtbase = self.dependencies.get("qtbase")
        lines = []
        if qtbase and qtbase.package_folder:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        if ecm:
            ecm_pkg = ecm.package_folder
            ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        # Every host dependency's lib/cmake so find_package(KF6...) and
        # the Wayland config resolve inside the conan cache. The plain
        # qtbase/6.11.1 lacks Qt6DBus and must not win the Qt6_DIR
        # lookup — the re-assert below puts qtbase-sql-dbus back first.
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
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
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        if qtbase and qtbase.package_folder:
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
        if ltt:
            ltt_cmake = os.path.join(
                ltt.package_folder, "lib", "cmake", "Qt6LinguistTools")
            lines.append(f'set(Qt6LinguistTools_DIR "{ltt_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ltt_cmake}")')
        sqlqt = self.dependencies.get("qtbase-sql-dbus")
        if sqlqt and sqlqt.package_folder:
            # Re-assert the DBus-enabled qtbase LAST so it wins the
            # Qt6_DIR lookup (list(PREPEND) puts the last entry first).
            lines.append(f'set(Qt6_DIR "{sqlqt.package_folder}/lib/cmake/Qt6")')
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{sqlqt.package_folder}/lib/cmake")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def _wayland_scanner_source(self):
        qtbase = self.dependencies.get("qtbase")
        wayland = self.dependencies.build.get("wayland") or self.dependencies.get("wayland")
        candidates = []
        if wayland and wayland.package_folder:
            candidates.append(
                os.path.join(wayland.package_folder, "bin", "wayland-scanner"))
        if qtbase and qtbase.package_folder:
            candidates.append(
                os.path.join(qtbase.package_folder, "libexec", "wayland-scanner"))
        return next((cand for cand in candidates if os.path.isfile(cand)), "")

    def _stage_ohos_wayland_scanner(self):
        # Pool-cache ELF binaries are signed with CI certificates the
        # OHOS device kernel rejects on exec ("Operation not permitted";
        # round 19: wayland-scanner failed in make at 40%). Copy the
        # scanner into the build folder and re-sign it with the device
        # binary-sign-tool (selfSign) before CMake runs it — the same
        # strip+resign the recipe applies to its own installed ELFs in
        # package(). Linux/CI keeps the pool binary untouched.
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        source = self._wayland_scanner_source()
        if not source:
            return
        dest_dir = os.path.join(self.build_folder, "wayland-scanner-tool")
        dest = os.path.join(dest_dir, "wayland-scanner")
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(source, dest)
        os.chmod(dest, 0o755)
        self._sign_ohos_elf_tree(dest_dir)

    def build(self):
        apply_conandata_patches(self)
        self._stage_ohos_wayland_scanner()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
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
        # The value lands in a shell command line, so quote for the
        # shell (shlex): the previous double-quote-only escaping left
        # $, backticks and backslashes live inside the quotes.
        return shlex.quote(str(value))

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
        # The project installs its own KScreenLockerConfig.cmake with
        # find_dependency(Qt6Core). cmake_find_mode=none keeps CMakeDeps
        # from shadowing it (KF6 precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KScreenLocker"]
