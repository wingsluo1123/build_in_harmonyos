#!/usr/bin/env python3
"""Conan recipe for kcontacts 6.28.0 on HarmonyOS PC.

KContacts is the KDE Frameworks 6 address book library (libKF6Contacts.so):
vCard 2.1/3.0/4.0 and LDIF parsers/serializers plus the Addressee,
ContactGroup and Address data models, the AddressFormatter (postal address
rendering, KI18nLocaleData-backed country metadata) and the vCard MIME
drag/drop helper.

OHOS-specific adaptations (techniques proven by kcontacts 6.18.0,
kfilemetadata 6.28.0 and kcalendarcore 6.26.0):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list)
  - KF_DEP_VERSION 6.28.0 -> 6.26.0 (patches/0001, "# ohpcd KF6 dep
    ceiling"): find_package(KF6 6.28.0 ...) would otherwise reject the KF6
    packages published to ohpcd (Config/CoreAddons/Codecs 6.26.0.1, I18n
    6.26.0 - the highest versions actually registered). KF6 frameworks
    keep API/ABI compatibility inside the 6.x major (kfilemetadata 6.28.0
    precedent).
  - include(ECMQmlModule) wrapped in if(USE_QML) (patches/0001) together
    with USE_QML=OFF: ECMQmlModule unconditionally pulls
    find_package(Qt6 Qml), and Qt6Qml is not part of the published qtbase
    package (kcalendarcore 6.26.0 precedent). This also skips the QML
    plugin subdirectory (src/qml).
  - ki18n_install(po) commented out (patches/0001): it routes through
    ecm_install_po_files_as_qm -> find_package(Qt6 LinguistTools REQUIRED),
    and qtbase ships no LinguistTools component (kfilemetadata 6.28.0
    precedent; kept as a commented line so the diff stays readable).
  - extra-cmake-modules/6.28.0 tool_requires satisfies the project's
    find_package(ECM 6.28.0 NO_MODULE).
  - BUILD_TESTING=ON: the upstream autotests are compiled in build() and
    the 32-entry CTest suite runs with a staged runtime env:
      * LD_LIBRARY_PATH / QT_PLUGIN_PATH, QT_QPA_PLATFORM=offscreen
      * HOME/XDG_* redirected into the build folder (kcalendarcore 6.26.0
        precedent)
      * a minimal vCard MIME database staged with update-mime-database
        (shared-mime-info tool_requires): OHOS ships no /usr/share/mime
        (kcontacts 6.18.0 precedent)
      * iso-codes/4.16.0 as a runtime requirement: its share/ tree is
        injected per-dependency through XDG_DATA_DIRS, which is how
        KI18nLocaleData (KCountry) locates iso-codes/json/*.json off
        /usr/share; this makes kcontacts-addresstest and
        kcontacts-addressformattest runnable (the 6.18.0 port excluded
        both as "requires unavailable OHOS iso-codes data").
  - ECM_MODULE_PATH set manually: the project's CMakeLists.txt does
    set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH}) and the CMakeDeps-shaped
    ECMConfig does not propagate the variable (kfilemetadata 6.28.0
    precedent).
  - conan_cmakedeps_paths.cmake created manually because qtbase and the
    KF6 packages use cmake_find_mode=none, which prevents CMakeDeps from
    adding their lib/cmake builddir to CMAKE_PREFIX_PATH.
  - CMAKE_CXX_STANDARD=20 + CMAKE_CXX_FLAGS=-std=c++20: the CMakeDeps
    toolchain defaults to C++17 which is too old for current KF6 code
    (kfilemetadata 6.28.0 precedent).
  - CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname, plus
    CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON: CMake has no
    Platform/HarmonyOS module, so the SONAME flags stay unset and
    libKF6Contacts.so would be linked without DT_SONAME (siblings then
    record a build-tree-relative NEEDED path). The versioned
    .so.6/.so.6.28.0 symlink chain is disabled at the same time: the
    HMDFS user volume rejects symlink() with EPERM, so CMake's
    cmake_symlink_library post-link step fails the build. One unversioned
    real libKF6Contacts.so keeps a bare, relocatable SONAME for
    downstream DT_NEEDED (DRAFT-cmake-harmonyos-system-name-soname;
    kpeople 6.28.0 / kcolorpicker 0.3.1 precedents).
  - ki18n 6.26.0's libKF6I18n.so and libKF6I18nLocaleData.so are published
    without DT_SONAME, so linking the imported KF6::I18n /
    KF6::I18nLocaleData targets would record their absolute conan-cache
    paths in DT_NEEDED (E537). patches/0002 drops the two targets from the
    KF6Contacts link list and links both libraries by bare name
    (-L<package lib dir> -lKF6I18n -lKF6I18nLocaleData) while keeping their
    include directories; the linker records relocatable DT_NEEDED
    basenames.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KContactsConan(ConanFile):
    name = "kcontacts"
    version = "6.28.0"
    description = "KDE Frameworks 6 - Contacts and address book library (vCard/LDIF)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcontacts"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # KF6 frameworks published to ohpcd, pinned to the highest
        # versions registered per package (device probe results:
        # Config/CoreAddons/Codecs have a 6.26.0.1 revision, I18n tops
        # out at 6.26.0). patches/0001 lowers the upstream
        # KF_DEP_VERSION ceiling to 6.26.0 to match.
        self.requires("kconfig/6.26.0.1")
        self.requires("kcoreaddons/6.26.0.1")
        self.requires("kcodecs/6.26.0.1")
        self.requires("ki18n/6.26.0")
        # iso-codes: the utf-8 JSON data set consumed at runtime by
        # KI18nLocaleData (KCountry). OHOS ships no /usr/share/iso-codes,
        # so without this package the KCountry-backed address formatting
        # (autotests addresstest/addressformattest) cannot resolve
        # country metadata. _run_upstream_tests injects its share/ tree
        # through XDG_DATA_DIRS.
        self.requires("iso-codes/4.16.0")

    def build_requirements(self):
        # find_package(ECM 6.28.0 NO_MODULE): the extra-cmake-modules
        # package ships the 6.28.0 config (kfilemetadata 6.28.0 precedent;
        # the legacy "ecm" package stops at 6.26.0).
        self.tool_requires("extra-cmake-modules/6.28.0")
        # The vcarddragtest autotest uses QMimeDatabase and OHOS ships no
        # freedesktop shared-mime-info database; this package provides
        # update-mime-database for staging a minimal test-time database
        # (kcontacts 6.18.0 precedent).
        self.tool_requires("shared-mime-info/2.5.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Enable the full upstream autotests (also gates the tests/ sample
        # programs and the non-registered vcardtool_benchmark).
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt6Qml is not part of the published qtbase package: keep the QML
        # plugin off and let patches/0001 skip the ECMQmlModule include.
        tc.variables["USE_QML"] = "OFF"
        # Current KF6 sources require C++20; force it explicitly because
        # the CMakeDeps toolchain defaults to C++17 (kfilemetadata
        # 6.28.0 precedent).
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        # CMake has no Platform/HarmonyOS module (the OHOS profile maps to
        # CMAKE_SYSTEM_NAME=HarmonyOS), so the SONAME flags stay unset and
        # libKF6Contacts.so would be linked without DT_SONAME. Restore the
        # flags so the library carries a real soname.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # Disable the versioned .so.6/.so.6.28.0 names: the HMDFS user
        # volume rejects symlink() with EPERM, so CMake's
        # cmake_symlink_library post-link step would fail the build. The
        # unversioned real libKF6Contacts.so keeps a bare soname, so
        # downstream DT_NEEDED stays relocatable
        # (DRAFT-cmake-harmonyos-system-name-soname; kpeople 6.28.0 /
        # kcolorpicker 0.3.1 precedents). Set through both channels: the
        # plain variable reaches conan_toolchain.cmake, the cache entry
        # covers configurations driven through CMakePresets.json.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not. The project's CMakeLists.txt
        # replaces CMAKE_MODULE_PATH with ECM_MODULE_PATH, so set the
        # variable directly (kfilemetadata 6.28.0 precedent).
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase and the KF6 packages use cmake_find_mode=none -> CMakeDeps
            # does not generate conan_cmakedeps_paths.cmake. Create it
            # manually so the toolchain adds their cmake dirs to
            # CMAKE_PREFIX_PATH (find_package(Qt6 ...) and the ECM FindKF6
            # module both resolve in CONFIG mode through these entries).
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Every dependency's lib/cmake dir: the KF6 component configs
            # (KF6CoreAddonsConfig.cmake etc.) live there and are located
            # by the ECM FindKF6 module, and KF6ContactsConfig.cmake does
            # find_dependency(Qt6Gui).
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
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
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        build_env = Environment()
        if self.settings.os == "OHOS":
            # ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool
            # during configure (ecm_query_qt -> QT_INSTALL_PREFIX). The
            # sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so which shadows the compatible one; prepend
            # /system/lib64 (kconfig 6.26.0 / kfilemetadata precedent) and
            # the SDK llvm/lib directory (lld needs libxml2.so.16 from
            # there on hosts that do not export it; kcalendarcore E132
            # observation).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with build_env.vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _library_runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                # iso-codes (share/iso-codes/json/*.json) is located through
                # QStandardPaths/XDG_DATA_DIRS by KI18nLocaleData.
                env.prepend_path(
                    "XDG_DATA_DIRS", os.path.join(dep.package_folder, "share")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        if self.settings.os == "OHOS":
            # Same sandbox libc++ shadowing fix as the build env.
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        for llvm_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
            test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        # Isolated HOME/XDG dirs (kcalendarcore 6.26.0 precedent): the
        # KConfig/i18n code paths write under GenericCacheLocation.
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
        # A minimal vCard MIME database (kcontacts 6.18.0 precedent): OHOS
        # ships no /usr/share/mime, so QMimeDatabase would not know
        # text/x-vcard (used by vcarddragtest and the vCard file-type
        # paths).
        test_env.prepend_path("XDG_DATA_DIRS", self._prepare_test_mime_database())
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -j1'.format(
                    self.build_folder
                )
            )

    def _prepare_test_mime_database(self):
        mime_root = os.path.join(self.build_folder, "test-mime", "share")
        mime_packages = os.path.join(mime_root, "mime", "packages")
        os.makedirs(mime_packages, exist_ok=True)
        mime_xml = os.path.join(mime_packages, "kcontacts-test-vcard.xml")
        with open(mime_xml, "w", encoding="utf-8") as f:
            f.write(
                """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="text/plain">
    <comment>plain text document</comment>
    <glob pattern="*.txt"/>
  </mime-type>
  <mime-type type="text/directory">
    <alias type="text/x-vcard"/>
    <sub-class-of type="text/plain"/>
    <comment>vCard contact information</comment>
  </mime-type>
</mime-info>
"""
            )
        update_mime = self._build_tool_path("shared-mime-info", "update-mime-database")
        if not update_mime:
            raise ConanException("update-mime-database is required for KContacts MIME tests")
        self.run('"{}" "{}"'.format(update_mime, os.path.join(mime_root, "mime")))
        return mime_root

    def _build_tool_path(self, dep_name, executable):
        dep = self.dependencies.build.get(dep_name) or self.dependencies.get(dep_name)
        if dep and dep.package_folder:
            candidate = os.path.join(dep.package_folder, "bin", executable)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(executable) or ""

    def _prepare_ctest_runtime_links(self):
        # CTest entries registered by autotests/CMakeLists.txt run with CWD
        # <build>/autotests, so a DT_NEEDED recorded as the build-tree
        # relative path '../../bin/libKF6I18n.so' resolves to
        # <conan-build-folder>/bin. Names containing '/' bypass
        # LD_LIBRARY_PATH, so the loader opens them against the working
        # directory directly. Published KF6 packages built before the
        # SONAME fix still carry such entries (ki18n 6.26.0's
        # libKF6I18nLocaleData.so wants '../../bin/libKF6I18n.so'), which is
        # why every non-Qt dependency library plus the build outputs are
        # materialized in both compatibility layouts (kcontacts 6.18.0 /
        # kpeople 6.28.0 precedent). Qt is left alone: its libraries carry
        # proper sonames and would only be found through the absolute
        # LD_LIBRARY_PATH entries anyway. HMDFS rejects symlink() with
        # EPERM, so fall back to a plain copy (qzxing precedent).
        compatibility_bins = [
            os.path.join(self.build_folder, "bin"),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin")),
        ]
        lib_sources = glob.glob(
            os.path.join(self.build_folder, "bin", "lib*.so*")
        )
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            if dep.ref.name == "qtbase":
                continue
            lib_sources.extend(
                glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
            )
        for src in lib_sources:
            for compatibility_bin in compatibility_bins:
                os.makedirs(compatibility_bin, exist_ok=True)
                dst = os.path.join(compatibility_bin, os.path.basename(src))
                if not os.path.exists(src):
                    continue
                target = os.path.realpath(src)
                if os.path.realpath(dst) == target:
                    continue
                if os.path.lexists(dst):
                    os.unlink(dst)
                try:
                    os.symlink(target, dst)
                except OSError:
                    shutil.copy2(target, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6ContactsConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Gui / KF6 components).
        # Use cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Contacts"]
