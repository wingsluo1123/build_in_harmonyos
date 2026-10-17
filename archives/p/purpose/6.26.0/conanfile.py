#!/usr/bin/env python3
"""Conan recipe for purpose 6.26.0 on HarmonyOS PC.

purpose is the KDE Frameworks 6 "share / export" framework: libKF6Purpose.so
(plugin/job framework), the purposequickplugin QML module org.kde.purpose used
by Kirigami applications (koko 26.04.0 shares images through it), the
purposeprocess external-process helper and the share plugins
(saveas/imgur/pastebin/clipboard/reviewboard/phabricator/barcode plus the
D-Bus ones: youtube/nextcloud/kdeconnect).

OHOS-specific adaptations (6.26.0):
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS is not in the KDE platform list)
  - USE_DBUS stays at the platform default (OFF): OHOS leaves the generic UNIX
    variable unset, so upstream's `if(UNIX AND NOT APPLE ...)` already keeps the
    D-Bus feature set out. Purpose's D-Bus share plugins (youtube/nextcloud/
    kdeconnect) additionally need a D-Bus session bus plus the kdeconnect and
    nextcloud daemon/account backends, none of which exist on the OHOS
    baseline; kio/6.26.0 is also a KIOCORE_ONLY build, so the KF6::KIOGui and
    KIOWidgets targets used by the account helpers are absent. The packages
    themselves are published (kwidgetsaddons/6.26.0, kaccounts-integration/
    26.04.0), so the plugins stay out because their runtime services are
    missing, not because a dependency is unavailable.
  - OHOS baseline cuts (patches 0001-0003), each one forced by a published
    ohpcd package that was built with a reduced feature set (see
    manifest.yaml knowledge_gained):
      * fileitemactionplugin -> KF6::KIOWidgets, kio/6.26.0 is KIOCORE_ONLY
      * accounts (accountshelper QML) -> KF6::KIOGui + KAccounts6
      * share plugins email/telegram/kdeconnect_sms -> KF6::KIOGui
      * widgets (KF6PurposeWidgets) -> KF6::I18nQml, ki18n/6.26.0 is
        published with BUILD_WITH_QML=OFF
      * ecm_find_qmlmodule(org.kde.prison)/(org.kde.kcmutils) are relaxed to
        optional: neither prison/6.18.0 nor kcmutils/6.26.0 ships its QML
        module; org.kde.kitemodels is a REAL runtime import of
        src/quick/AlternativesView.qml and stays REQUIRED (kitemmodels/6.26.0
        is published with QML support).
  - tests/ (menudemo, sharetool demo apps) dropped together with the widgets
    cut; autotests/ keeps alternativesmodeltest, which really exercises
    Purpose::AlternativesModel + Purpose::Configuration + Purpose::Job by
    running the saveasplugin export job (patch 0005 replaces its emailplugin
    sample with clipboardplugin, an Export plugin that is in the OHOS build).
  - BUILD_TESTING=ON and ctest executed during the build (see notes.md).
  - CMAKE_CXX_STANDARD=20: purpose uses C++20; the profile pins 17.
  - Patch 0001 also re-points the imported targets of the published kcoreaddons,
    kconfig and ki18n packages at the linker's name form (-lKF6CoreAddons and
    friends) plus the directory holding them. Those packages ship their shared
    libraries without a DT_SONAME, so CMake hands the linker the absolute Conan
    cache path of the imported library and lld records it in DT_NEEDED, pinning
    the binaries to the build machine (the W3 L5b gate). The packages' own
    targets files already set IMPORTED_NO_SONAME, and that alone does not change
    the link line on this toolchain (CMake ships no Platform module for OHOS), so
    the recipe overrides the imported location instead. package() re-reads every
    installed shared object and fails the build if such a path ever comes back.
"""
import glob
import hashlib
import os
import shutil
import struct
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PurposeConan(ConanFile):
    name = "purpose"
    version = "6.26.0"
    description = "KDE Frameworks 6 - Purpose (share and export framework)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/purpose"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase-sql-dbus provides Core/Gui/Widgets/Network/Test/Sql/DBus; the
        # declarative stack (Qml/Quick) comes from qtdeclarative
        # (kcmutils/alligator precedent: Qt discovers it through
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH).
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # KF6 6.26 line. override=True entries are single declarations: they
        # pin the whole graph to this version and add the dependency as a
        # direct requirement (a duplicated plain requires is rejected).
        self.requires("kio/6.26.0")
        self.requires("kservice/6.26.0")
        self.requires("kirigami/6.26.0")
        self.requires("knotifications/6.26.0")
        # org.kde.kitemmodels QML module: src/quick/AlternativesView.qml imports
        # it and the top-level CMakeLists checks for it with ecm_find_qmlmodule.
        self.requires("kitemmodels/6.26.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        # kio -> karchive/kservice chain: KF6ArchiveConfig activates
        # find_dependency(OpenSSL)/PkgConfig::LibZstd; libxml2 is needed by the
        # OHOS SDK lld at link time (kio 6.26.0 precedent).
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
        # ecm_find_qmlmodule() (see the CMakeLists patch) can only look in the
        # consumer's own install prefix and in Qt's own QT_INSTALL_QML, so a QML
        # module shipped by a Conan package is never visible at configure time.
        # That relaxation is compensated here for the one module purpose really
        # imports - src/quick/AlternativesView.qml does `import
        # org.kde.kitemmodels` - by asserting the module exists in the
        # kitemmodels package that ends up on QML2_IMPORT_PATH at runtime.
        kitemmodels = self.dependencies.get("kitemmodels")
        qml_dir = kitemmodels.package_folder if kitemmodels else ""
        qmldir = os.path.join(qml_dir or "", "lib", "qml", "org", "kde", "kitemmodels", "qmldir")
        if not os.path.isfile(qmldir):
            raise ConanException(
                "kitemmodels does not provide the org.kde.kitemmodels QML module "
                f"({qmldir} is missing), purpose's QML import would fail at runtime"
            )
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Honour the option instead of pinning the value, so -o shared=False
        # cannot produce a shared library behind a static package_id.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        # Platform default on OHOS: upstream's UNIX-based detection already
        # leaves the D-Bus plugin set out (see the docstring).
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        # CMake has no Platform/HarmonyOS module, so its shared-library SONAME
        # flag stays empty and CMake then ignores VERSION/SOVERSION entirely:
        # libKF6Purpose.so would get neither a DT_SONAME nor the versioned
        # symlink chain, and the linker would bake the build-relative path of
        # the library into the DT_NEEDED of every plugin (loading
        # saveasplugin.so then fails with "Error loading shared library
        # ../../../bin/libKF6Purpose.so"). kio/6.26.0 precedent.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # Qt6Qml/Qt6Quick live in the qtdeclarative package; Qt only looks
        # there via the official QT_ADDITIONAL_PACKAGES_PREFIX_PATH hook
        # (kcmutils 6.26.0 / kdeclarative 6.26.0 precedent).
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
        self._report_ohos_dbus_default()

    @staticmethod
    def _elf_dt_needed(path):
        """Return the DT_NEEDED entries of a 64-bit little-endian ELF file.

        Plain Python on purpose: readelf is not guaranteed to be on PATH inside
        the build environment.
        """
        with open(path, "rb") as handle:
            data = handle.read()
        if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            return []
        e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
        e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x36)
        segments = []
        dyn_off = dyn_size = None
        for index in range(e_phnum):
            header = e_phoff + index * e_phentsize
            p_type = struct.unpack_from("<I", data, header)[0]
            if p_type == 1:                                   # PT_LOAD
                p_offset, p_vaddr = struct.unpack_from("<QQ", data, header + 0x08)
                p_filesz = struct.unpack_from("<Q", data, header + 0x20)[0]
                segments.append((p_vaddr, p_offset, p_filesz))
            elif p_type == 2 and dyn_off is None:              # PT_DYNAMIC
                dyn_off = struct.unpack_from("<Q", data, header + 0x08)[0]
                dyn_size = struct.unpack_from("<Q", data, header + 0x20)[0]
        if dyn_off is None or not dyn_size:
            return []
        strtab = strsz = None
        offsets = []
        for index in range(dyn_size // 16):
            d_tag, d_val = struct.unpack_from("<qQ", data, dyn_off + index * 16)
            if d_tag == 0:                                     # DT_NULL
                break
            if d_tag == 1:                                     # DT_NEEDED
                offsets.append(d_val)
            elif d_tag == 5:                                   # DT_STRTAB
                strtab = d_val
            elif d_tag == 10:                                  # DT_STRSZ
                strsz = d_val
        if strtab is None or not offsets:
            return []
        strtab_offset = None
        for p_vaddr, p_offset, p_filesz in segments:
            if p_vaddr <= strtab < p_vaddr + p_filesz:
                strtab_offset = p_offset + (strtab - p_vaddr)
                break
        if strtab_offset is None:
            return []
        limit = strtab_offset + (strsz or 0)
        names = []
        for offset in offsets:
            start = strtab_offset + offset
            end = data.find(b"\x00", start, limit) if limit > start else -1
            names.append(data[start:end if end != -1 else limit].decode("utf-8", "replace"))
        return names

    def _check_no_absolute_needed(self):
        """Fail the build when an installed binary points back at this machine.

        The W3 L5b quality gate rejects DT_NEEDED entries that hold a path
        instead of a bare library name. That is what happens whenever a library
        is linked by its absolute file name, which is CMake's behaviour for
        imported libraries without a DT_SONAME (see patch 0001). Checking the
        installed files here means a regression fails the build instead of
        surfacing only in the CI gate.
        """
        offenders = []
        inspected = 0
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                needed = self._elf_dt_needed(path)
                if not needed:
                    continue
                inspected += 1
                relative = os.path.relpath(path, self.package_folder)
                for entry in needed:
                    if "/" in entry:
                        offenders.append(f"{relative} -> {entry}")
        if offenders:
            raise ConanException(
                "installed shared objects carry a path in DT_NEEDED, which pins them "
                "to the build machine (the W3 L5b gate rejects this):\n  "
                + "\n  ".join(sorted(offenders))
            )
        self.output.info(
            "DT_NEEDED check: %d installed shared object(s), no absolute path" % inspected
        )

    def _report_ohos_dbus_default(self):
        """Record the platform-detection trap this recipe documents.

        purpose computes USE_DBUS_DEFAULT from `if(UNIX AND NOT APPLE ...)`.
        Conan's OHOS toolchain sets CMAKE_SYSTEM_NAME=HarmonyOS, which leaves
        the plain UNIX variable undefined, so the D-Bus default silently
        becomes OFF. The recipe pins that value explicitly instead of relying
        on the side effect of a missing variable.
        """
        self.output.info(
            "OHOS: USE_DBUS=OFF (upstream's UNIX-based default evaluates to OFF "
            "because CMAKE_SYSTEM_NAME=HarmonyOS leaves UNIX unset); the "
            "youtube/nextcloud/kdeconnect share plugins are not built"
        )

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
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        self._report_built_plugins()
        test_env = self._runtime_env(include_build=True)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        # KIO creates its worker socket as
        # <QStandardPaths::RuntimeLocation>/<app><random>.N.kioworker.socket and
        # a Unix socket path is capped at 108 bytes, so the runtime directory
        # must stay short: one inside the Conan build folder (~85 bytes) pushes
        # the socket path over the limit and QLocalServer::listen() fails. An
        # explicit OHOS_PURPOSE_RUNTIME_DIR wins, then the system temp directory,
        # then ~/tmp - the workspace keeps /tmp read-only, so the fallbacks are
        # tried in order and the first creatable one is used.
        runtime_suffix = "purpose-rt-" + hashlib.sha1(self.build_folder.encode()).hexdigest()[:10]
        runtime_dir = None
        for candidate in (
            os.environ.get("OHOS_PURPOSE_RUNTIME_DIR"),
            os.path.join(tempfile.gettempdir(), runtime_suffix),
            os.path.join(os.path.expanduser("~"), "tmp", runtime_suffix),
        ):
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
            except OSError:
                continue
            runtime_dir = candidate
            break
        if runtime_dir is None:
            raise ConanException(
                "no creatable runtime directory for the KIO worker socket "
                "(set OHOS_PURPOSE_RUNTIME_DIR to a short, writable path)"
            )
        os.chmod(runtime_dir, 0o700)
        # Qt only accepts a runtime directory that is owned by the current user
        # and closed to everybody else. Filesystems that report another owner
        # (build sandboxes, shared checkouts) make that impossible, and KIO
        # then cannot create its worker socket - the two job cases of
        # alternativesmodeltest skip themselves instead of failing.
        runtime_stat = os.stat(runtime_dir)
        if runtime_stat.st_uid != os.getuid() or runtime_stat.st_mode & 0o077:
            self.output.warning(
                "runtime directory %s is not usable for KIO worker sockets "
                "(owner %d, current uid %d, mode %o); alternativesmodeltest will "
                "skip its job cases" % (runtime_dir, runtime_stat.st_uid, os.getuid(), runtime_stat.st_mode & 0o777)
            )
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", runtime_dir)
        test_env.define("TMPDIR", runtime_dir)
        test_env.define("TMP", runtime_dir)
        test_env.define("TEMP", runtime_dir)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        with test_env.vars(self).apply():
            # KPluginMetaData::findPlugins("kf6/purpose") looks the share
            # plugins up under QCoreApplication::libraryPaths(), i.e. under
            # every QT_PLUGIN_PATH entry; the build tree drops them into
            # <build>/bin/kf6/purpose (src/plugins/CMakeLists.txt), so the
            # tests can only see them with that directory on the path.
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _report_built_plugins(self):
        """Log which share plugins the build produced.

        src/plugins/CMakeLists.txt sets LIBRARY_OUTPUT_DIRECTORY to
        <build>/bin/kf6/purpose, which is the layout
        KPluginMetaData::findPlugins("kf6/purpose") expects one level below a
        library path entry, so nothing is moved or fabricated here. The KDE
        plugin metadata is embedded in the .so through K_PLUGIN_FACTORY_WITH_JSON
        (no .json lands on disk), hence this counts libraries.
        """
        plugin_dir = os.path.join(self.build_folder, "bin", "kf6", "purpose")
        if os.path.isdir(plugin_dir):
            found = sorted(glob.glob(os.path.join(plugin_dir, "*.so")))
            self.output.info(
                "share plugins built for the tests: %d (%s)"
                % (len(found), ", ".join(os.path.basename(p) for p in found)))

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        includes = list(self.dependencies.build.values()) if include_build else []
        for dep in deps + includes:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                # Qt keeps plugins/ and qml/ at the prefix root, while the KF6
                # packages of this baseline install them under lib/: the KIO
                # file worker sits in lib/plugins/kf6/kio/kio_file.so (without
                # it a job on a file:// URL dies with "Unknown protocol
                # 'file'") and org.kde.kitemmodels lives in lib/qml. Both
                # layouts are exported when they exist.
                for sub in ("plugins", os.path.join("lib", "plugins")):
                    candidate = os.path.join(dep.package_folder, sub)
                    if os.path.isdir(candidate):
                        env.prepend_path("QT_PLUGIN_PATH", candidate)
                for sub in ("qml", os.path.join("lib", "qml")):
                    candidate = os.path.join(dep.package_folder, sub)
                    if os.path.isdir(candidate):
                        env.prepend_path("QML2_IMPORT_PATH", candidate)
                # kioworker is launched from bin/kf6 in this baseline.
                for sub in ("bin", os.path.join("bin", "kf6")):
                    candidate = os.path.join(dep.package_folder, sub)
                    if os.path.isdir(candidate):
                        env.prepend_path("PATH", candidate)
        if include_build:
            # The share plugins are loaded by plugin id at test time.
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(self.build_folder, "bin"))
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        # The installed objects must reference their dependencies by name; a
        # path here would pin the package to this machine (W3 L5b gate).
        self._check_no_absolute_needed()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Purpose"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # Consumers (koko) both import the org.kde.purpose QML module and let
        # Purpose::AlternativesModel load the share plugins by plugin id, so
        # the install directories have to be on the consumer runtime paths
        # (KDE_INSTALL_QMLDIR=<libdir>/qml, KDE_INSTALL_PLUGINDIR=<libdir>/plugins).
        for qml_dir in (os.path.join("lib", "qml"), "qml"):
            self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, qml_dir))
        for plugin_dir in (os.path.join("lib", "plugins"), "plugins"):
            self.runenv_info.prepend_path("QT_PLUGIN_PATH", os.path.join(self.package_folder, plugin_dir))
