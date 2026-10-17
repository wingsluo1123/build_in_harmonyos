#!/usr/bin/env python3
"""Conan recipe for kdialog 26.04.0 on HarmonyOS PC (aarch64).

kdialog is the KDE dialog-shell utility: a scriptable Qt6/KF6 Widgets front
end that pops every KDE-styled dialog type (yesno/yesnocancel/msgbox/
inputbox/imgbox/textbox/textinputbox/combobox/menu/checklist/radiolist/
passivepopup/getopenfilename/getsavefilename/getexistingdirectory/geticon/
progressbar/getcolor/slider/calendar/...) from shell scripts, plus a second
executable, ``kdialog_progress_helper`` — the D-Bus service
(org.kde.kdialog-<pid>) that carries the --progressbar dialogs. Upstream
(KDE release-service 26.04.0, invent.kde.org/utilities/kdialog) requires
Qt6 DBus (find_package(Qt6 CONFIG REQUIRED COMPONENTS DBus)) and the KF6
components TextWidgets / Notifications / GuiAddons / IconThemes /
WindowSystem / KIO / DBusAddons; X11 integration is optional
(option WITHOUT_X11, off by default). The helper uses
qt_add_dbus_adaptor() to generate its D-Bus adaptor from
org.kde.kdialog.ProgressDialog.xml.

Upstream tests (R51 step 1 inventory, evidence from the 26.04.0 tarball):
  - tests/ ships three interactive demo shell scripts only (tests/test,
    tests/progressdemo, tests/progresscanceldemo — a human clicking
    buttons, or qdbus driving the progress helper); there is no
    CMakeLists.txt under tests/ and the top-level CMakeLists.txt never
    calls add_subdirectory(tests), so they are not part of the build;
  - no CMake file registers a test target: a recursive grep for add_test /
    enable_testing / BUILD_TESTING / ecm_add_test / ctest across all
    CMakeLists.txt / cmake files returns nothing;
  - a recursive search for any file whose name contains "test" finds only
    tests/ itself and tests/test;
  - .kde-ci.yml declares the eight KF6 framework dependencies plus
    require-passing-tests-on: ['Linux', 'FreeBSD'], but registers no test
    target those platforms could run;
  - .gitlab-ci.yml pulls seven shared KDE templates (linux-qt6,
    linux-qt6-next, freebsd-qt6, flatpak, xml-lint, yaml-lint,
    snap-snapcraft-lxd) which invoke ctest only when the project registers
    tests — it does not.
  Therefore the upstream suite is 0 tests: BUILD_TESTING=OFF and the whole
  verification surface is the test_package consumer suite (R34), which
  exercises both shipped executables and is recorded in
  test_package/MANIFEST.yml (``upstream_tests: []``).

Licensing note: the tree is REUSE/SPDX-style (LICENSES/GPL-2.0-or-later.txt,
source headers say GPL-2.0-or-later) and src/kdialog.cpp passes
KAboutLicense::GPL to KAboutData; org.kde.kdialog.metainfo.xml declares
GPL-2.0+. The recipe records GPL-2.0-or-later and the consumer case asserts
the GPL text of ``--license``.

OHOS-specific adaptations (two explicit source patches — conandata.yml
carries them; every other difference is configuration-level):
  - Link swap KF6::KIOWidgets -> KF6::KIOCore (patches/0001): the published
    kio/6.26.0 on ohpcd is the KIOCORE_ONLY baseline and ships no
    KIOWidgets library; kdialog's only KIO symbol, KRecentDocument::add()
    (getsavefilename branch), lives in KIOCore, so the feature is
    preserved. KF6::IconWidgets (kiconthemes' second library, exported by
    the same KF6IconThemes config) is unaffected.
  - Explicit framework declarations (patches/0002): the published ohpcd
    KF6 6.26.0 packages export only each framework's own include
    directory and flatten dependency links (-lKF6Xxx flags, absolute
    INTERFACE_LINK_DIRECTORIES), so the transitive include directories of
    a full KF6 install do not propagate; the directly used
    KF6::WidgetsAddons (KMessageBox/KPasswordDialog/KNewPasswordDialog/
    KDatePicker), KF6::CoreAddons (KAboutData), KF6::ConfigCore (KConfig)
    and KF6::I18n (KLocalizedString) are listed explicitly on the
    kdialog target, with the components added to
    find_package(KF6 COMPONENTS ...) (KConfig is requested as component
    Config; its targets stay KF6::ConfigCore/KF6::ConfigGui;
    'KMessageBox' file not found before the patch).
  - find_package(Qt6 ... COMPONENTS DBus): provided by qtbase/6.11.1.1, the
    FEATURE_dbus=ON variant exporting the Qt6::DBus component;
    qt_add_dbus_adaptor() generates the helper's adaptor at build time
    (kauth 6.26.0 precedent: it works on OHOS).
  - WITHOUT_X11=ON: the X11 integration in utils.cpp sits behind
    HAVE_X11 && !K_WS_QTONLY; skipping find_package(X11) compiles it out
    (the platform has no X11 headers/libraries). KWindowSystem's Qt-only
    backend is what remains.
  - KF_IGNORE_PLATFORM_CHECK=TRUE: OHOS is not in KDE's platform whitelist.
  - KF_SKIP_PO_PROCESSING=ON: ki18n_install(po) would need the gettext
    msgfmt/lconvert toolchain; .qm catalogs are not required for the
    smoke-verified deliverable (kcolorchooser/kcron precedent).
  - CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE: defensive — 26.04.0 has
    no doc/ and never finds DocTools, but the flag keeps ECM's optional
    hooks from probing the unpublished package.
  - OHOS loader workarounds: -Wl,-z,max-page-size=0x1000 (the default lld
    0x10000 layout puts .dynsym/.dynstr into separate high-address RW LOAD
    segments the OHOS musl loader refuses) plus --disable-new-dtags on the
    executables and CMAKE_BUILD/INSTALL_RPATH pointing at every dependency
    lib dir. package() additionally rewrites path-form DT_NEEDED entries
    to plain basenames in place and re-signs every ELF
    (llvm-objcopy --remove-section .codesign + binary-sign-tool; OHOS
    requires a valid .codesign); remaining path-form entries abort
    packaging (fail-closed) rather than shipping a non-portable artifact
    (kcolorchooser 26.04.0 / kcron 26.04.1 precedent).

Known limitations (documented, not patched): the interactive dialog flows
cannot be asserted on the offscreen platform. The test_package consumer
suite covers both products, the CLI metadata surface, the
QCommandLineParser failure path, a real QMessageBox modal event loop
(alive-bounded, killed after a grace period) and the complete DT_NEEDED
closure of both executables. Two upstream branches are deliberately not
driven end to end: --passivepopup (26.04.0 has no KPassivePopup fallback
any more: when no notification daemon answers — as on a device without a
session bus — sendVisualNotification() returns false and qApp->exec()
then runs with no window and nothing to quit it) and --progressbar (needs
kdialog_progress_helper on PATH plus a session bus, and blocks until the
D-Bus client closes the dialog). test.sh executes the helper binary
directly instead — its DT_NEEDED closure is the point — and bounds every
GUI launch with a kill timer.
"""
import os
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KDialogConan(ConanFile):
    name = "kdialog"
    version = "26.04.0"
    description = (
        "KDE dialog shell utility (KDialog) - scriptable Qt6/KF6 Widgets "
        "dialogs plus the kdialog_progress_helper D-Bus service, built on "
        "KIOCore/TextWidgets/Notifications/GuiAddons/IconThemes/"
        "WindowSystem/DBusAddons"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/utilities/kdialog"
    url = "https://invent.kde.org/utilities/kdialog"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # The two portability patches declared in conandata.yml
        # (patches/0001-ohos-link-kiocore.patch,
        # patches/0002-ohos-explicit-framework-links.patch) must travel
        # with the exported sources; build() applies them in order via
        # apply_conandata_patches() (kcron 26.04.1 / kirigami-addons
        # 1.13.0 pattern).
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 foundation. qtbase/6.11.1.1 is the FEATURE_dbus=ON variant:
        # it exports the Qt6::DBus component that upstream's
        # find_package(Qt6 ... COMPONENTS DBus) requires for the
        # Qt::DBus link and the helper's generated D-Bus adaptor.
        # override=True pins every transitive qtbase/6.11.1 reference in the
        # graph to it (kcron 26.04.1 precedent).
        self.requires("qtbase/6.11.1.1", override=True)
        # Qt6Svg completes the kiconthemes -> Qt6Svg chain
        # (KF6IconThemesConfig find_dependency(Qt6Svg)); found through
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH below.
        self.requires("qtsvg/6.11.1")
        # Upstream REQUIRED KF6 component set (find_package(KF6 ...
        # COMPONENTS TextWidgets Notifications GuiAddons IconThemes
        # WindowSystem KIO DBusAddons), matching .kde-ci.yml's dependency
        # list). The remaining 6.26 entries below are the CMake/runtime
        # chains of that set (ktextwidgets -> kcompletion/sonnet/kservice;
        # kiconthemes -> karchive; kio -> kservice/kcrash); they are
        # declared explicitly so the consumer graph and the exported
        # runenv are complete without relying on transitive activation
        # (kbackup 26.04.0 precedent).
        self.requires("ktextwidgets/6.26.0")
        self.requires("knotifications/6.26.0")
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("kiconthemes/6.26.0")
        self.requires("kwindowsystem/6.26.0")
        self.requires("kio/6.26.0")
        self.requires("ki18n/6.26.0", override=True)
        # kdbusaddons is published on ohpcd only at 6.14.0/6.18.0/6.29.0
        # (no 6.26.0); 6.18.0 is what the merged 6.26-line consumers pin
        # (kaccounts-integration 26.04.0 precedent, same cross-line graph).
        # Its own recipe requires qtbase-sql-dbus/6.11.1 (a separate full Qt
        # build), which therefore joins the graph transitively; Qt6::DBus
        # for kdialog itself still comes from qtbase/6.11.1.1.
        self.requires("kdbusaddons/6.18.0")
        # The KF6 6.26 line. override=True entries both pin the whole graph
        # to this version and act as direct requirements (a duplicated
        # plain requires of the same ref is rejected by conan); the 6.18
        # pins of the kdbusaddons subtree collapse onto 6.26 wherever a
        # package exists at both. The binaries link the cross-line shared
        # libraries by SONAME and KF6 keeps ABI compatibility within the
        # 6.x series (kaccounts-integration 26.04.0 precedent).
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kcrash/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcompletion/6.26.0.1")
        self.requires("sonnet/6.26.0")
        self.requires("kservice/6.26.0")
        # kiconthemes -> karchive chain: KF6ArchiveConfig.cmake activates
        # find_dependency(OpenSSL) and PkgConfig::LibZstd.
        self.requires("karchive/6.26.0", override=True)
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        # expat/2.8.2.1: dbus/1.14.10 (via kdbusaddons -> qtbase-sql-dbus)
        # pulls expat/2.8.2 whose CCI recipe tool_requires cmake with no
        # OHOS key; ohpcd's OHOS-adapted 2.8.2.1 has no conan-side cmake
        # tool_require (kcron 26.04.1 precedent).
        self.requires("expat/2.8.2.1", override=True)
        # Declared so its lib dir is on LD_LIBRARY_PATH: kio 6.26.0
        # requires libxml2, and the OHOS SDK lld depends on libxml2.so.16
        # at link time (kio 6.26.0 precedent).
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Upstream registers no tests at all (0 tests, evidence in the
        # module docstring / test_package/MANIFEST.yml).
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # No X11 on the platform: upstream's WITHOUT_X11 option skips
        # find_package(X11), HAVE_X11 stays unset and utils.cpp compiles
        # its X11 integration out (KWindowSystem's Qt-only backend).
        tc.variables["WITHOUT_X11"] = "ON"
        # Defensive: 26.04.0 has no doc/ and never finds DocTools, but the
        # flag keeps ECM's optional hooks from probing the unpublished
        # package.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"

        # Keep the platform predicate in sync with the recipe idiom
        # (str(self.settings.os) + ("OHOS", "HarmonyOS"); R1 整改
        # 2026-10-17 离线检视 #3): a bare ``== "OHOS"`` would skip the
        # loader workaround under a HarmonyOS setting (kcharselect
        # 26.04.0 precedent).
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # OHOS loader workaround: the default lld max-page-size of
            # 0x10000 places .dynsym/.dynstr into separate high-address RW
            # LOAD segments; the OHOS musl loader refuses to mmap that
            # layout. Pinning the page size to 0x1000 restores the regular
            # 4-LOAD layout (kcolorchooser 26.04.0 / kcron 26.04.1
            # precedent); --disable-new-dtags keeps the RPATH below as
            # DT_RPATH.
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000 -Wl,--disable-new-dtags"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_MODULE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        # DT_RPATH (not DT_RUNPATH) pointing at every dependency lib dir:
        # the OHOS loader reaches the published KF6 libraries through it
        # before their own broken RPATH entries are considered
        # (kcolorchooser 26.04.0 precedent).
        dep_lib_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
            and os.path.isdir(os.path.join(dep.package_folder, "lib"))
        ]
        if dep_lib_dirs:
            # CMake list separator (not os.pathsep: on POSIX ':' would
            # merge every directory into a single list element).
            rpath = ";".join(dep_lib_dirs)
            tc.variables["CMAKE_BUILD_RPATH"] = rpath
            tc.variables["CMAKE_INSTALL_RPATH"] = rpath

        # Qt6Svg lives in the qtsvg package; Qt discovers additional
        # component prefixes through the official
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH hook (kcron/kirigami
        # precedent). Without it find_package(Qt6 ... Svg) would resolve
        # the qtbase Qt6Config.cmake first and fail on the missing
        # component.
        qt_extra = []
        for dep_name in ("qtsvg",):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder and dep.package_folder not in qt_extra:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths()
        tc.generate()

    def _write_cmake_paths(self):
        """CMakeDeps cannot add cmake_find_mode=none packages (qtbase/KF6)
        to CMAKE_PREFIX_PATH, so the dependency search paths are written by
        hand into the CMakeToolchain-included
        conan_cmakedeps_paths.cmake (kcron 26.04.1 / kcolorchooser 26.04.0
        precedent)."""
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # The two source patches (conandata.yml) are applied here before
        # configure; everything else is configuration-level (generate()).
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        # Upstream 26.04.0 ships no test suite (0 tests, evidence in the
        # module docstring and test_package/MANIFEST.yml), so there is no
        # ctest invocation here; the consumer verification runs in
        # test_package/ during conan create.

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sanitize_needed_entries()

    def _sanitize_needed_entries(self):
        """Rewrite path-form DT_NEEDED entries to plain basenames (in-place
        .dynstr patch), then re-sign the ELF (OHOS requires a valid
        .codesign).

        The published KF6 6.26.0 artifacts carry no DT_SONAME, so the
        linker bakes the absolute conan-cache paths of libKF6*.so into the
        shipped executables. Such an artifact is not portable (loader
        error outside the build machine). Plain basenames resolve through
        the installed DT_RPATH and the exported runenv LD_LIBRARY_PATH
        instead (kcolorchooser 26.04.0 / kcron 26.04.1 precedent,
        recursive walk covering both bin/kdialog and
        bin/kdialog_progress_helper).

        Any path-form entry the exclusivity guard refuses to rewrite aborts
        the packaging (fail-closed): shipping a non-portable artifact
        silently is worse than a loud build failure.
        """
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        replaced = 0
        for root, dirs, files in os.walk(self.package_folder):
            dirs[:] = [d for d in dirs if d not in ("share", "include")]
            for name in sorted(files):
                if not (
                    name.endswith(".so")
                    or ".so." in name
                    or "." not in name
                ):
                    continue
                path = os.path.join(root, name)
                if not self._is_elf(path):
                    continue
                replaced += self._patch_needed_paths_in_place(path)
        if replaced:
            self.output.info(f"DT_NEEDED entries sanitized: {replaced}")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _patch_needed_paths_in_place(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
        patched, count, leftover = self._elf_dynstr_patch(data)
        if leftover:
            raise ConanException(
                f"path-form DT_NEEDED still present in {os.path.basename(path)}: "
                f"{leftover} — refusing to package a non-portable artifact "
                "(check the exclusivity guard / shared string spans)"
            )
        if count:
            with open(path, "wb") as handle:
                handle.write(patched)
            self.output.info(
                f"NEEDED sanitized in {os.path.basename(path)}: {count}"
            )
            self._resign_elf(path)
        return count

    @staticmethod
    def _elf_dynstr_patch(data):
        if data[:4] != b"\x7fELF":
            return data, 0, []
        ei_class = data[4]
        ei_data = data[5]
        if ei_class != 2 or ei_data != 1:
            return data, 0, []
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        if e_shoff == 0 or e_shentsize == 0:
            return data, 0, []

        sections = []
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            sh_type = struct.unpack_from("<I", data, off + 4)[0]
            sh_addr = struct.unpack_from("<Q", data, off + 16)[0]
            sh_offset = struct.unpack_from("<Q", data, off + 24)[0]
            sh_size = struct.unpack_from("<Q", data, off + 32)[0]
            sections.append((sh_type, sh_addr, sh_offset, sh_size))

        buf = bytearray(data)
        replaced = 0
        leftover = []  # path-form entries blocked by the exclusivity guard
        for sh_type, sh_addr, sh_offset, sh_size in sections:
            if sh_type != 6 or sh_size == 0:
                continue
            strtab_addr = None
            strtab_size = None
            needed_offsets = []
            used_offsets = set()
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:
                    break
                if d_tag == 5:
                    strtab_addr = d_val
                elif d_tag == 10:
                    strtab_size = d_val
                elif d_tag == 1:  # DT_NEEDED: the only path-form rewrite target
                    needed_offsets.append(d_val)
                    used_offsets.add(d_val)
                elif d_tag in (14, 15, 29) and d_val:
                    # SONAME/RPATH/RUNPATH: protect the string span, never
                    # rewrite (an RPATH/RUNPATH is a ':'-joined directory
                    # list; rsplit("/") would collapse it to its last
                    # segment — kbreakout 26.04.0 shape).
                    used_offsets.add(d_val)
                # No catch-all for the remaining tags: their d_val is numeric
                # (addresses, sizes), and a value landing inside a string span
                # would falsely block a rewritable DT_NEEDED (kcron 26.04.1
                # device finding).
            if strtab_addr is None or not needed_offsets:
                continue
            strtab_off = None
            for sh_type2, sh_addr2, sh_offset2, sh_size2 in sections:
                if sh_addr2 == strtab_addr and sh_type2 in (3, 6, 7, 1):
                    strtab_off = sh_offset2
                    strtab_size = min(strtab_size or sh_size2, sh_size2)
                    break
            if strtab_off is None:
                continue
            strtab = bytes(buf[strtab_off:strtab_off + (strtab_size or 0)])
            for off in needed_offsets:
                if off >= len(strtab):
                    continue
                end = strtab.find(b"\x00", off)
                if end < 0:
                    continue
                old = strtab[off:end]
                if b"/" not in old:
                    continue
                base = old.rsplit(b"/", 1)[1]
                if any(off < u < end for u in used_offsets):
                    leftover.append(old.decode("utf-8", "replace"))
                    continue
                new = base + b"\x00" * (len(old) - len(base))
                buf[strtab_off + off:strtab_off + end] = new
                replaced += 1
        return bytes(buf), replaced, leftover

    def _resign_elf(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy") or self._find_ohos_tool(
            "objcopy"
        )
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "OHOS ELF signing tools not found (llvm-objcopy / "
                "binary-sign-tool); the sanitized ELF must be re-signed to "
                f"load on the device: {path}"
            )
        mode = os.stat(path).st_mode & 0o777
        signed = path + ".signed"
        probe = subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            raise ConanException(
                f"llvm-objcopy --remove-section .codesign failed for {path}: "
                f"{probe.stderr.strip()[:200]}"
            )
        probe = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            raise ConanException(
                f"binary-sign-tool sign failed for {path}: "
                f"{probe.stderr.strip()[:200]}"
            )
        shutil.move(signed, path)
        os.chmod(path, mode)
        return True

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _runtime_env(self, include_build=False):
        """Environment for the CMake configure/build/install steps: prepend
        every dependency's bin/lib dir (the build context included) plus
        the Qt plugin/qml locations, and keep the offscreen QPA pin
        (kcron 26.04.1 precedent)."""
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("XDG_DATA_DIRS", os.path.join(dep.package_folder, "share"))
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    directory = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(directory):
                        env.prepend_path("QT_PLUGIN_PATH", directory)
                for rel in ("qml", os.path.join("lib", "qml")):
                    directory = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(directory):
                        env.prepend_path("QML2_IMPORT_PATH", directory)
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                self.runenv_info.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
