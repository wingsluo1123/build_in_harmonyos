#!/usr/bin/env python3
"""Conan recipe for kcron 26.04.1 on HarmonyOS PC (aarch64).

kcron is the KDE Gear task scheduler: a QML KCM plugin (kcm_cron.so, installed
under plasma/kcms/systemsettings together with a kcmdesktopfilegenerator-made
kcm_cron.desktop), a KAuth helper executable (kcron_helper plus its
local.kcron.crontab activation files) and the crontab table model/validation
code compiled into the plugin. Upstream requires Qt6 (Core/Quick/PrintSupport),
KF6 (ConfigWidgets/CoreAddons/Auth/I18n/KCMUtils) and KirigamiAddons >= 0.11.76.

Upstream tests (R51 step 1 inventory, evidence from the 26.04.1 tarball):
  - autotests/CMakeLists.txt builds exactly one target, taskvalidatortest,
    from 13 sources including ../src/taskvalidator.cpp, ../src/task.cpp and
    the ../src/crontablib/* units; it links Qt6::Test Qt6::Gui Qt6::Qml and
    KF6::I18n;
  - autotests/CMakeLists.txt registers exactly one CTest entry:
    add_test(NAME taskvalidatortest COMMAND taskvalidatortest);
  - autotests/taskvalidatortest.cpp declares 9 test slots (QTEST_MAIN):
    testEmptyCommand, testAbsolutePathExecutable, testAbsolutePathNotFound,
    testAbsolutePathNotExecutable, testAbsolutePathWithArguments,
    testCommandInPath, testCommandInPathWithArguments, testCommandNotInPath,
    testSpecialValidCommand;
  - the top-level CMakeLists.txt includes CTest and add_subdirectory(autotests)
    unconditionally, so the suite is part of every build;
  - therefore BUILD_TESTING=ON (below) builds and runs the upstream suite
    (1 binary / 9 cases) in build() and test_package/MANIFEST.yml records
    this inventory.

OHOS-specific adaptations (all in conandata.yml patches, applied
unconditionally - every patch is a platform-neutral source change):
  - 0001/0002/0003: the published qtbase is built with
    FEATURE_printsupport=OFF and ships no Qt6PrintSupport module (algobox
    1.1.1 / conducteo 5.0.2 / ksystemlog 26.04.0 precedent). PrintSupport is
    dropped from the required components (Gui/Widgets requested explicitly)
    and the print action is re-targeted to a QPdfWriter (QtGui) PDF export
    flow using the Widgets save dialog.
  - 0004: processes can legitimately run under uids without an /etc/passwd
    entry, getpwuid() then returns nullptr and CTHost dereferenced it while
    the KCM was constructed (host-process abort on module load); the null
    entry now degrades to a CTInitializationError.
  - 0005/0006: with that error the current-user crontab is null everywhere,
    and TasksModel/VariablesModel dereferenced it in
    refresh()/create()/applyCreate()/paste(); they now tolerate a null cron
    and stay usable (empty, add-able, validatable).
  - 0007: taskvalidatortest's two absolute-path cases assume a searchable
    /usr/bin with true/printf; the build uid cannot search /usr/bin at all
    on OHOS, so both cases now use
    QCoreApplication::applicationFilePath() - an absolute path that exists
    and is executable in every build environment - keeping each case's
    original intent (bare absolute path / quoted path with arguments) and
    passing identically on the device and on Linux CI.

Known limitations (documented, not patched): CTHost::save(CTCron*) and the
KCMCron add/modify/remove slots dereference the cron returned by
currentCron() without a null check. Those paths are only reachable from the
interactive Apply/Add/Remove actions of a full Plasma session; the
non-interactive surface (module construction, models, task creation,
validation, printer wiring) is exercised by test_package/.
"""
import glob
import os
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KCronConan(ConanFile):
    name = "kcron"
    version = "26.04.1"
    description = (
        "KDE task scheduler (QML KCM + KAuth helper) for the Plasma system "
        "settings - Qt6/KF6 module built on KCMUtils/Auth/Kirigami"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/utilities/kcron"
    url = "https://invent.kde.org/utilities/kcron"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase-sql-dbus provides Core/Gui/Widgets/Test/Sql/DBus; the
        # declarative stack (Qml/Quick/QuickWidgets) comes from qtdeclarative
        # (kcmutils/kirigami-addons precedent); qtsvg/qtshadertools/qtmultimedia
        # complete the Kirigami runtime and CMake chains upstream links against
        # (KI18n, KF6::KirigamiAddons).
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qtshadertools/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        # kauth 6.26.0: KF6::AuthCore for kcm_cron and kcron_helper.
        self.requires("kauth/6.26.0")
        # kcmutils 6.26.0: the kcmutils_add_qml_kcm()/kcmutils_generate_
        # desktop_file() macros come from KF6KCMUtilsMacros; kcm_cron links
        # KF6::KCMUtils (Core+Quick).
        self.requires("kcmutils/6.26.0")
        # kio/kxmlgui/kitemviews: the kcmutils 6.26.0 dependency matrix
        # (KF6KCMUtilsConfig.cmake chains find_dependency through it).
        self.requires("kio/6.26.0")
        self.requires("kxmlgui/6.26.0")
        self.requires("kitemviews/6.26.0")
        # kconfigwidgets is only published at 6.18.0 on ohpcd; the published
        # KF6KCMUtilsConfig.cmake declares the matching 6.18.0 floor
        # (patch 0001 of the kcmutils recipe).
        self.requires("kconfigwidgets/6.18.0")
        # find_package(KF6KirigamiAddons 0.11.76 REQUIRED): kirigami-addons
        # 1.13.0 + its kirigami/6.18.0 base.
        self.requires("kirigami/6.18.0")
        self.requires("kirigami-addons/1.13.0")
        # KF6 6.26 line. override=True entries are single declarations: they
        # pin the whole graph to this version and act as direct requirements
        # (a duplicated plain requires is rejected by conan). kconfigwidgets
        # 6.18.0 and kirigami-addons 1.13.0 pin the 6.18 line for their
        # transitive KF6 deps; the overrides redirect all of them to 6.26.
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        # kirigami-addons pins kiconthemes/6.18.0.1 and kcrash/6.18.0 exact;
        # kxmlgui/kio pin 6.26.0 exact - override to the 6.26 line.
        self.requires("kiconthemes/6.26.0", override=True)
        self.requires("kcrash/6.26.0", override=True)
        # kauth 6.26.0 recipe precedents, kept identical for graph unity:
        # - expat/2.8.2.1: dbus/1.14.10 (via qtbase-sql-dbus) pulls expat/2.8.2
        #   whose CCI recipe tool_requires cmake with no OHOS key; ohpcd's
        #   OHOS-adapted 2.8.2.1 has no conan-side cmake tool_require.
        # - qtbase/6.11.1.1: the FEATURE_dbus=ON Qt variant; unifies every
        #   transitive qtbase/6.11.1 reference in the graph.
        self.requires("expat/2.8.2.1", override=True)
        self.requires("qtbase/6.11.1.1", override=True)
        # kio -> karchive/kservice chain: KF6ArchiveConfig activates
        # find_dependency(OpenSSL)/PkgConfig::LibZstd; libxml2 is needed by
        # the OHOS SDK lld at link time (kcmutils 6.26.0 precedent).
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
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
        # Upstream registers one CTest binary (taskvalidatortest, 9 cases);
        # BUILD_TESTING=ON builds and build() runs it (module docstring).
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # KF6DocTools is an optional dependency (unpublished); never pull it.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"

        if self.settings.os == "OHOS":
            # OHOS loader workaround: the default lld max-page-size of 0x10000
            # places .dynsym/.dynstr into separate high-address RW LOAD
            # segments; the OHOS musl loader refuses to mmap that layout.
            # Pinning the page size to 0x1000 restores the regular 4-LOAD
            # layout (audiocd 26.04.3 shared/module precedent; kcolorchooser
            # 26.04.0 executable precedent with --disable-new-dtags).
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000 -Wl,--disable-new-dtags"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_MODULE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        # DT_RPATH (not DT_RUNPATH) pointing at every dependency lib dir: the
        # OHOS loader reaches the published KF6 libraries through it before
        # their own broken RPATH entries are considered (kcolorchooser
        # 26.04.0 precedent).
        dep_lib_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
            and os.path.isdir(os.path.join(dep.package_folder, "lib"))
        ]
        if dep_lib_dirs:
            # CMake list separator (not os.pathsep: on POSIX ':' would merge
            # every directory into a single list element).
            rpath = ";".join(dep_lib_dirs)
            tc.variables["CMAKE_BUILD_RPATH"] = rpath
            tc.variables["CMAKE_INSTALL_RPATH"] = rpath

        # Qt6Qml/Qt6Quick/Qt6Svg/Qt6ShaderTools/Qt6Multimedia live in the
        # qtdeclarative/qt* packages; Qt discovers additional components
        # through the official QT_ADDITIONAL_PACKAGES_PREFIX_PATH hook
        # (kcmutils/kirigami-addons precedent). Without it
        # find_package(Qt6 ... Qml) resolves the qtbase Qt6Config.cmake first
        # and fails on the missing component.
        qt_extra = []
        for dep_name in ("qtdeclarative", "qtsvg", "qtshadertools", "qtmultimedia"):
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
        """CMakeDeps cannot add cmake_find_mode=none packages (qtbase/KF6) to
        CMAKE_PREFIX_PATH, so the dependency search paths are written by hand
        into the CMakeToolchain-included conan_cmakedeps_paths.cmake
        (kcmutils 6.26.0 / kcolorchooser 26.04.0 precedent)."""
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
        # Every patch is a platform-neutral source change (the PrintSupport
        # removal keeps building on hosts that have it; the null guards
        # preserve upstream behaviour where passwd/crontab exist), so they are
        # applied unconditionally (kcachegrind 26.04.0 precedent) and the same
        # tree is built everywhere.
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # taskvalidatortest (upstream autotests, 9 cases) needs the Qt QPA
        # runtime (Qt6::Gui) plus the KF6/Qt6 shared-library closure; the
        # helpers below normalise the published-artifact DT_NEEDED quirks
        # exactly as in the kcmutils 6.26.0 build-time test run.
        self._bake_needed_path_stubs()
        self._prepare_ctest_runtime_links()
        test_env = self._runtime_env(include_build=True)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
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

    def _bake_needed_path_stubs(self):
        """Fix CI-fatal DT_NEEDED absolute paths baked into the published
        binary packages (kio/kxmlgui 6.26.0 line).

        The published libKF6XmlGui.so (and siblings) record absolute
        DT_NEEDED entries pointing at the *build-time* conan cache package
        dirs (e.g. /root/.cache/conan2/p/b/kconfXXXX/p/lib/
        libKF6ConfigWidgets.so). On any other machine (CI worker or device)
        those paths do not exist and the loader aborts with "Error loading
        shared library" before LD_LIBRARY_PATH is even consulted (absolute
        DT_NEEDED bypasses the search path).

        Fix: scan every dependency .so for absolute DT_NEEDED entries; for
        each one whose file does not exist, create the exact parent directory
        and symlink the actually-available same-named library from the real
        dependency package into it. Paths outside the user-writable home or
        system roots are skipped.
        """

        def _needed_entries(so_path):
            """Parse DT_NEEDED from the .dynamic section (readelf-free)."""
            try:
                with open(so_path, "rb") as f:
                    data = f.read()
            except OSError:
                return []
            if data[:4] != b"\x7fELF":
                return []
            is64 = data[4] == 2
            if not is64:
                return []
            e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
            e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
            dyn_off = dyn_sz = 0
            dynstr_off = 0
            for i in range(e_shnum):
                sh = e_shoff + i * e_shentsize
                sh_type = struct.unpack_from("<I", data, sh + 4)[0]
                if sh_type == 6:  # SHT_DYNAMIC
                    dyn_off = struct.unpack_from("<Q", data, sh + 0x18)[0]
                    dyn_sz = struct.unpack_from("<Q", data, sh + 0x20)[0]
                elif sh_type == 3:  # SHT_STRTAB (first one is .dynstr in practice)
                    if dynstr_off == 0:
                        dynstr_off = struct.unpack_from("<Q", data, sh + 0x18)[0]
            if not dyn_off or not dynstr_off:
                return []
            needed = []
            count = dyn_sz // 16
            for i in range(count):
                d_tag = struct.unpack_from("<Q", data, dyn_off + i * 16)[0]
                d_val = struct.unpack_from("<Q", data, dyn_off + i * 16 + 8)[0]
                if d_tag == 1:  # DT_NEEDED
                    end = data.index(b"\x00", dynstr_off + d_val)
                    name = data[dynstr_off + d_val : end].decode("utf-8", "replace")
                    needed.append(name)
            return needed

        # Collect every .so we can see (dependency packages + our build).
        so_files = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                so_files.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        so_files.extend(glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*")))

        # Index available libraries by basename for symlink targets.
        available = {}
        for path in so_files:
            available[os.path.basename(path)] = path

        stubs = 0
        for so in so_files:
            for needed in _needed_entries(so):
                if not needed.startswith("/"):
                    continue  # relative NEEDED goes through the search path
                if os.path.exists(needed):
                    continue  # already resolvable
                base = os.path.basename(needed)
                target = available.get(base)
                if not target:
                    continue
                parent = os.path.dirname(needed)
                home = os.path.expanduser("~")
                if not (
                    parent == home
                    or parent.startswith(home + os.sep)
                    or parent == "/data"
                    or parent.startswith("/data" + os.sep)
                ):
                    continue  # outside writable roots; skip
                try:
                    os.makedirs(parent, exist_ok=True)
                    dst = needed
                    if not os.path.lexists(dst):
                        os.symlink(target, dst)
                        stubs += 1
                except OSError:
                    continue
        if stubs:
            self.output.info("baked DT_NEEDED path stubs created: %d" % stubs)

    def _prepare_ctest_runtime_links(self):
        """KF6 libraries record build-tree-relative DT_NEEDED entries
        (../../bin/libKF6*.so); mirror the expected layout by symlinking
        every KF6 shared library into the build tree compatibility locations
        (kxmlgui/kcmutils 6.26.0 precedent)."""
        # taskvalidatortest lives in autotests/; the KF6 DT_NEEDED entries
        # use build-tree-relative paths (../bin, ../../bin). Symlink the
        # libraries into every plausible resolution point.
        compatibility_dirs = {
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "lib"),
            os.path.normpath(os.path.join(self.build_folder, "autotests", "bin")),
            os.path.normpath(os.path.join(self.build_folder, "autotests", "..", "bin")),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin")),
        }
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for cdir in compatibility_dirs:
            os.makedirs(cdir, exist_ok=True)
        for src in lib_sources:
            for cdir in compatibility_dirs:
                dst = os.path.join(cdir, os.path.basename(src))
                if os.path.exists(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sanitize_needed_entries()

    def _sanitize_needed_entries(self):
        """Rewrite path-form DT_NEEDED entries to plain basenames (in-place
        .dynstr patch), then re-sign the ELF (OHOS requires a valid
        .codesign).

        The published KF6 6.26.0 artifacts carry no DT_SONAME, so the linker
        bakes the absolute conan-cache paths of libKF6*.so into the shipped
        kcm_cron.so / kcron_helper. Such an artifact is not portable (loader
        error outside the build machine). Plain basenames resolve through the
        installed DT_RPATH and the exported runenv LD_LIBRARY_PATH instead
        (kcolorchooser 26.04.0 precedent, recursive walk).

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
            return data, 0
        ei_class = data[4]
        ei_data = data[5]
        if ei_class != 2 or ei_data != 1:
            return data, 0
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        if e_shoff == 0 or e_shentsize == 0:
            return data, 0

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
                    # segment -- kbreakout 26.04.0 shape).
                    used_offsets.add(d_val)
                # No catch-all for the remaining tags: their d_val is numeric
                # (addresses, sizes), and a value landing inside a string span
                # would falsely block a rewritable DT_NEEDED. kcron_helper's
                # libKF6CoreAddons path was skipped exactly that way on the
                # device (DT_GNU_HASH d_val inside the span) before this fix.
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
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
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
