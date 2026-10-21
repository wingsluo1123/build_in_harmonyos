#!/usr/bin/env python3
"""Conan recipe for kcmutils 6.28.0 on HarmonyOS PC.

kcmutils is a KDE Frameworks 6 library providing utilities for
configuration modules (libKF6KCMUtils.so, libKF6KCMUtilsCore.so,
libKF6KCMUtilsQuick.so + the kcmshell6 runner).

OHOS-specific adaptations (6.28.0), carried over from the merged 6.26.0
recipe (PR #12534) and re-based on the 6.28.0 release:
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS not in the KDE platform list)
  - KF_DEP_VERSION lowered 6.28.0 -> 6.26.0 (patch 0001): the published KF6
    line on ohpcd tops out at 6.26.0 for kio/kxmlgui/kitemviews/ki18n; the
    kcmutils version itself stays 6.28.0.
  - KCMUTILS_BUILD_QML_PLUGIN declared with an explicit OFF default (patch
    0001): the declarative kcmutilsqmlplugin is not built because it links
    KF6::KIOGui and kio/6.26.0 on ohpcd ships a KIOCORE_ONLY baseline (no
    KIOGui target). The QML KCM test fixture, the QML-plugin loader autotest
    binary and the QML smoke test row are guarded behind the same switch.
  - KF6ConfigWidgets dependency floor lowered 6.26.0 -> 6.18.0 (patch 0001):
    kconfigwidgets is only published at 6.18.0 on ohpcd; the rest of the KF6
    chain uses the 6.26.0 line with conan override entries (kxmlgui 6.26.0
    precedent, task #13725).
  - KI18N_BUILD_WITH_QML fallback (patch 0001): ki18n on ohpcd is built with
    BUILD_WITH_QML=OFF, so the shared QML engine degrades the translation
    domain to a no-op.
  - std::ranges -> std::sort in kcmshell6 (clang 15 / libc++ has no C++20
    ranges support).
  - USE_DBUS=OFF (Qt6 DBus only used by optional kcmshell6 integration)
  - BUILD_TESTING=ON: upstream autotests (including the 6.28 kcmshell6
    smoke-test rows) run on the local arm64 OHOS runner
  - DT_SONAME restored explicitly: CMake has no Platform/HarmonyOS module, so
    CMAKE_SHARED_LIBRARY_SONAME_*_FLAG stay unset and the CMake-generated
    DT_NEEDED fields carry build-tree-relative paths (../bin/... for the
    autotests, ../../bin/... for the fakekcm plugin). The musl loader keys
    loaded DSOs by that name string, so kcmultidialogtest loaded two copies
    of libKF6KCMUtilsCore (qobject_cast<KCModule*> then failed and the test
    dialog fell back to KCMError). Passing the SONAME flags plus
    CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON (HMDFS rejects symlinks, so the
    versioned .so.6 -> .so chain cannot be created) makes every consumer
    request the plain soname instead (syndication 6.26.0 precedent, extended
    with the Android-style no-versioned-soname switch).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KCMUtilsConan(ConanFile):
    name = "kcmutils"
    version = "6.28.0"
    description = "KDE Frameworks 6 - utilities for configuration modules"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcmutils"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase-sql-dbus provides Core/Gui/Widgets/Test/Sql/DBus; the
        # declarative stack (Qml/Quick/QuickWidgets) comes from
        # qtdeclarative (alkimia #9350 / alligator #9578 precedent).
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # KF6 6.26 line. override=True entries are single declarations: they
        # pin the whole graph to this version and add it as a direct
        # requirement (a duplicated plain requires is rejected by conan).
        # The overrides redirect kconfigwidgets/6.18.0's transitive 6.18
        # pins to the 6.26 line (kxmlgui 6.26.0 precedent).
        self.requires("kio/6.26.0")
        self.requires("kxmlgui/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        # kio -> karchive/kservice chain: KF6ArchiveConfig activates
        # find_dependency(OpenSSL)/PkgConfig::LibZstd; libxml2 is needed by
        # the OHOS SDK lld at link time (kio 6.26.0 precedent).
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.28.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        # CMake has no Platform/HarmonyOS module, so the SONAME flag
        # variables stay unset and the toolchain links our three libraries
        # without a DT_SONAME: DT_NEEDED then embeds the build-tree-relative
        # path of each link command (../bin/... for the autotests,
        # ../../bin/... for the fakekcm plugin). musl keys already-loaded
        # DSOs by that string, so the plugin and the test executable each
        # loaded their own copy of libKF6KCMUtilsCore and qobject_cast to
        # KCModule failed across the two copies (kcmultidialogtest saw
        # KCMError pages). Providing the SONAME flags restores DT_SONAME;
        # CMAKE_PLATFORM_NO_VERSIONED_SONAME keeps the plain file names
        # because HMDFS rejects symlinks, so the usual .so.6 -> .so chain
        # cannot be created (syndication 6.26.0 precedent, kfilemetadata).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        # Both variable flavors: cache_variables reaches the configure through
        # CMakePresets while plain variables reach -DCMAKE_TOOLCHAIN_FILE
        # configures (kbookmarks 6.28.0 precedent).
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        # Qt6Qml/Qt6Quick/Qt6QuickWidgets live in the qtdeclarative package;
        # Qt discovers additional components through the official
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH hook (kdeclarative 6.26.0
        # precedent). Without it find_package(Qt6 ... Qml) resolves the
        # qtbase Qt6Config.cmake first and fails on the missing component.
        qt_extra = []
        qtdecl = self.dependencies.get("qtdeclarative")
        if qtdecl and qtdecl.package_folder:
            qt_extra.append(qtdecl.package_folder)
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
        # Platform guard: apply OHOS-specific patches only on OHOS.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
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

    @staticmethod
    def _under_root(path, root):
        """Separator-aware containment test (root itself or below it)."""
        return path == root or path.startswith(root + os.sep)

    @staticmethod
    def _elf_needed_entries(path):
        """Parse DT_NEEDED strings out of an ELF64 file (readelf-free).

        The dynamic section's string table is resolved through
        SHT_DYNAMIC.sh_link instead of assuming the first SHT_STRTAB is
        .dynstr; every read is bound-checked and malformed/truncated
        inputs return [] instead of aborting the build.
        """
        import struct

        try:
            with open(path, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    return []
                f.seek(0)
                data = f.read()
        except OSError:
            return []
        if len(data) < 0x40 or data[4] != 2:
            return []
        try:
            e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
            e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
            if not e_shoff or e_shentsize < 0x40 or not e_shnum:
                return []
            sections = []
            for i in range(e_shnum):
                sh = e_shoff + i * e_shentsize
                sections.append(
                    (
                        struct.unpack_from("<I", data, sh + 4)[0],  # sh_type
                        struct.unpack_from("<Q", data, sh + 0x18)[0],  # sh_offset
                        struct.unpack_from("<Q", data, sh + 0x20)[0],  # sh_size
                        struct.unpack_from("<I", data, sh + 0x28)[0],  # sh_link
                    )
                )
            dynamic = next((sec for sec in sections if sec[0] == 6), None)  # SHT_DYNAMIC
            if dynamic is None or dynamic[3] >= len(sections):
                return []
            dynstr = sections[dynamic[3]]
            if dynstr[0] != 3:  # SHT_STRTAB
                return []
            dyn_off, dyn_sz = dynamic[1], dynamic[2]
            dynstr_off = dynstr[1]
            if dyn_off + dyn_sz > len(data) or dynstr_off >= len(data):
                return []
            needed = []
            for i in range(dyn_sz // 16):
                d_tag, d_val = struct.unpack_from("<QQ", data, dyn_off + i * 16)
                if d_tag != 1:  # DT_NEEDED
                    continue
                start = dynstr_off + d_val
                if start >= len(data):
                    continue
                end = data.find(b"\x00", start)
                if end < 0:
                    continue
                needed.append(data[start:end].decode("utf-8", "replace"))
            return needed
        except (struct.error, ValueError, IndexError, OverflowError):
            return []

    def _bake_needed_path_stubs(self):
        """Fix CI-fatal DT_NEEDED absolute paths baked into published
        binary packages (kio/kxmlgui 6.26.0 line).

        The published libKF6XmlGui.so (and siblings) record absolute
        DT_NEEDED entries pointing at the *build-time* conan cache
        package dirs (e.g. /root/.cache/conan2/p/b/kconfXXXX/p/lib/
        libKF6ConfigWidgets.so). On any other machine (CI worker or
        local runner) those paths do not exist and the loader aborts
        with "Error loading shared library" before LD_LIBRARY_PATH is
        even consulted (absolute DT_NEEDED bypasses the search path).

        Fix: scan every dependency .so for absolute DT_NEEDED entries;
        for each one whose file does not exist, create the exact parent
        directory and symlink the actually-available same-named library
        from the real dependency package into it. Paths outside the
        user-writable roots (home and /data) are skipped; the containment
        test is applied to the realpath-normalized parent, so `..`
        segments and sibling prefixes (e.g. /database) cannot escape.
        """
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
            for needed in self._elf_needed_entries(so):
                if not needed.startswith("/"):
                    continue  # relative NEEDED goes through the search path
                if os.path.exists(needed):
                    continue  # already resolvable
                base = os.path.basename(needed)
                target = available.get(base)
                if not target:
                    continue
                parent = os.path.realpath(os.path.dirname(needed))
                home = os.path.realpath(os.path.expanduser("~"))
                if not (
                    self._under_root(parent, home)
                    or self._under_root(parent, "/data")
                ):
                    continue  # outside writable roots; skip
                try:
                    os.makedirs(parent, exist_ok=True)
                    dst = os.path.join(parent, base)
                    if not os.path.lexists(dst):
                        # HMDFS rejects symlink() (EPERM), so fall back to a
                        # plain copy: the absolute DT_NEEDED string from the
                        # published KF6 binaries otherwise bypasses every
                        # search path (kio/kxmlgui 6.26.0 precedent).
                        import shutil as _shutil
                        try:
                            os.symlink(target, dst)
                        except OSError:
                            _shutil.copy2(target, dst)
                        stubs += 1
                except OSError:
                    continue
        if stubs:
            self.output.info(
                "baked DT_NEEDED path stubs created: %d" % stubs
            )

    def _prepare_ctest_runtime_links(self):
        """Mirror the libraries referenced by build-tree-relative DT_NEEDED
        entries into the compatibility locations expected by the ctest
        working directories (kxmlgui 6.26.0 precedent).

        Some published KF6 libraries record DT_NEEDED as a path relative
        to their own build tree (../../bin/libKF6*.so); the musl loader
        resolves slash-containing names against the process working
        directory, so the ctest directories need the same layout. Only
        libraries that appear as the basename of such a relative DT_NEEDED
        entry are mirrored: everything else resolves through the normal
        search path (LD_LIBRARY_PATH / $ORIGIN), so the full dependency
        closure does not need to be copied.
        """
        import shutil as _shutil
        relative_needed = set()
        elf_files = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                elf_files.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for root, _dirs, files in os.walk(self.build_folder):
            elf_files.extend(os.path.join(root, name) for name in files)
        for path in elf_files:
            if not os.path.isfile(path):
                continue
            for needed in self._elf_needed_entries(path):
                if "/" in needed and not needed.startswith("/"):
                    relative_needed.add(os.path.basename(needed))
        # Test executables live at different depths (autotests/,
        # autotests/module_data_codegen/); their consumers resolve the
        # relative NEEDED strings against the ctest working directory, so
        # mirror the libraries into every plausible resolution point. The
        # os.pardir entry covers ../../bin/... strings evaluated with the
        # ctest working directory at <build>/autotests.
        compatibility_dirs = {
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "lib"),
            os.path.normpath(os.path.join(self.build_folder, "autotests", "bin")),
            os.path.normpath(os.path.join(self.build_folder, "autotests", "module_data_codegen", "bin")),
            os.path.normpath(os.path.join(self.build_folder, "autotests", "module_data_codegen", "..", "..", "bin")),
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
        mirrored = 0
        for src in lib_sources:
            if os.path.basename(src) not in relative_needed:
                continue
            for cdir in compatibility_dirs:
                dst = os.path.join(cdir, os.path.basename(src))
                if os.path.exists(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        _shutil.copy2(src, dst)
                    mirrored += 1
        if mirrored:
            self.output.info(
                "ctest runtime links mirrored: %d (%d relative DT_NEEDED names)"
                % (mirrored, len(relative_needed))
            )

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
            # Our own libraries are linked by their DT_SONAME, so the
            # build tree must be on the loader search path for the ctest
            # run (the plugin lives in a subdirectory whose $ORIGIN does
            # not contain the libraries).
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "bin"))
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # The kcmutilsqmlplugin is not part of the OHOS baseline (KIOGui not
        # published); only the three libraries are shipped.
        self.cpp_info.libs = ["KF6KCMUtils", "KF6KCMUtilsCore", "KF6KCMUtilsQuick"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
