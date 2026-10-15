#!/usr/bin/env python3
"""Conan recipe for kcontacts5 5.116.0 (KDE Frameworks 5 / Qt5) on HarmonyOS PC.

kcontacts (KF5/Qt5) is the KDE Frameworks 5 address-book contact library:
vCard 2.1/3.0/4.0 + LDIF parsing/serialization, the Addressee/Address/
PhoneNumber/Email/Geo/Picture/... value types, contact groups and the
libaddressinput-derived address formatting tables (KF5Contacts, the single
build target of this tarball).

OHOS-specific adaptations (validated on the kcoreaddons5 / kconfig5 /
ki18n5 / kcodecs5 / kjobwidgets5 KF5 skeleton):

  - QT_MAJOR_VERSION=5 so the project selects Qt5 (qt5-qtbase/5.15.2.2, the
    DBus-capable superset binary).
  - CMAKE_SYSTEM_NAME=Linux (variables + cache_variables double cover): the
    OHOS Conan toolchain maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, for
    which CMake defines neither UNIX nor a platform module.  ECM registers
    the upstream ctest cases only when the build is not cross-compiling
    (if(NOT CMAKE_CROSSCOMPILING)); OHOS is POSIX so forcing the Linux
    platform keeps the whole upstream test suite intact (chain-wide
    convention).
  - patches/0001: Qt Quick is demoted from required to optional component
    (the library itself never links Qt5::Quick - only the manual tests/
    QML demo did; the OHOS graph has no Quick supply on the 5.15.2.2 line)
    and the broken tests/ subdirectory (upstream marks testread/testwrite
    as "FIXME: Build fails"; none of its targets registers a ctest case)
    is skipped.  The real test suite lives in autotests/ and is untouched.
  - KF_IGNORE_PLATFORM_CHECK=TRUE: HarmonyOS is not in the KDE platform
    list.
  - KF_SKIP_PO_PROCESSING=ON: Qt5LinguistTools is not published to ohpcd
    (chain-wide convention); GETTEXT_{MSGFMT,MSGMERGE}_EXECUTABLE still
    point at the gettext package tools because KF5I18n's ki18n_install(po)
    registers a pofiles build target that runs msgfmt on every catalog
    (gettext reaches this graph transitively through ki18n5).
  - cmake_find_mode=none for qt5-qtbase: the package's own native Qt5
    CMake configs are consumed (Qt5::Core/Gui/Test plus the Qt5 macros and
    the mkspec include path); the CMakeDeps-generated Qt5 configs would
    shadow them.
  - The four KF5 dependencies (kcoreaddons5 / ki18n5 / kconfig5 /
    kcodecs5) are consumed through their own KF5*Config.cmake files
    (cmake_find_mode=none, E429), so every dependency's lib/cmake is
    injected into CMAKE_PREFIX_PATH through a hand-written
    conan_cmakedeps_paths.cmake (find_package(KF5 COMPONENTS CoreAddons
    I18n Config Codecs) resolves through ECM's FindKF5 forwarding module).
  - qt5-qtbase/5.15.2.2 is forced (force=True): the published
    kcoreaddons5/5.116.0 recipe still pins qt5-qtbase/5.15.2 and Conan
    refuses the mixed graph (E429); .2 is the DBus-capable superset binary
    and is ABI-compatible, so the whole graph is normalised onto 5.15.2.2.
  - ECM_MODULE_PATH / ECM_DIR set manually because ecm is a tool_requires
    (build context) and CMakeDeps does not wire its share/ECM tree into
    the host prefix paths.
  - CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE point at the qt5-qtbase bin
    tools; Qt5CoreConfigExtrasMkspecDir.cmake hard-codes a build-tree path
    <prefix>/../b/mkspecs/... which the packaged cache entry never has;
    generate() recreates the whole mkspecs tree there.
  - CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE +
    CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname," -> relocatable,
    unversioned DT_SONAME (W3 CI L5 soname gate).
  - CMAKE_BUILD_WITH_INSTALL_RPATH=ON (E537): OHOS refuses to mmap
    PROT_EXEC a shared library whose ELF was rewritten after linking.
  - CMAKE_BUILD_PARALLEL_LEVEL=1: the HMDFS cache filesystem refuses the
    make jobserver fifo (EPERM).
  - Every packaged ELF is re-signed with llvm-objcopy + binary-sign-tool
    after cmake.install() (CMake rewrites the RUNPATH of installed shared
    libraries, which invalidates the OHOS build-time .codesign section;
    kitemmodels / kirigami / ki18n 6.26.0.1 precedent).
  - /system/lib64 is prepended to LD_LIBRARY_PATH while running the Qt
    host tools and the upstream tests so the loader resolves the
    compatible libc++ first (kcoreaddons5 / kitemviews5 precedent).
  - BUILD_TESTING=ON registers the 32 upstream ctest cases from
    autotests/ (kcontacts-testroundtrip, 29 ecm_add_tests targets with the
    kcontacts- prefix, addressformattest and picturetest); they are really
    executed from build() through ctest.  The KCountry-based functions of
    addresstest (countryToISO/ISOtoCountry) and the addressformat
    repository validation need the iso-codes runtime data (JSON country
    tables + translated iso_3166-1 catalogs), which reaches this graph
    transitively through ki18n5 and is deployed into the per-test
    XDG_DATA_HOME (ki18n5 precedent).
"""

import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Kcontacts5Conan(ConanFile):
    name = "kcontacts5"
    version = "5.116.0"
    description = (
        "KDE Frameworks 5 - address book contact library "
        "(vCard/LDIF parsing and formatting)"
    )
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcontacts"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KF5 dependencies of the project's find_package(KF5 COMPONENTS ...)
        # list, declared BEFORE qt5-qtbase so their lib/cmake config
        # directories stay ahead of the CMakeDeps Qt5 entries in
        # CMAKE_PREFIX_PATH (kjobwidgets5 / kpeople5 precedent).
        self.requires("kcoreaddons5/5.116.0")
        self.requires("ki18n5/5.116.0")
        self.requires("kconfig5/5.116.0")
        self.requires("kcodecs5/5.116.0")
        # Runtime data dependency for the upstream autotests: the KCountry
        # functions (Address::countryToISO / Address::ISOtoCountry, the
        # addressformat repository validation) read the iso-codes JSON
        # tables and the translated iso_3166-1 catalogs.  Declared as a
        # direct requirement so package_folder is available to the test
        # data deployment (the same version ki18n5/5.116.0 pins; as a mere
        # transitive node its package_folder resolves to None here).
        self.requires("iso-codes/4.20.1")
        # .2 is the DBus-capable superset; force=True normalises the graph
        # (kcoreaddons5/5.116.0 still pins qt5-qtbase/5.15.2, E429).
        self.requires("qt5-qtbase/5.15.2.2", force=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kcontacts5 only supports Linux and OHOS, got {}".format(
                    self.settings.os
                )
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Consume the native Qt5 configs shipped inside qt5-qtbase: they
        # provide the Qt5::Core/Qt5::Gui/Qt5::Test imported targets, the Qt5
        # CMake macros and the mkspec include path the project relies on.
        # The CMakeDeps-generated Qt5 configs would shadow them.
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Treat OHOS as a Linux-like target so CMake defines UNIX, ECM's
        # POSIX compiler/rpath settings apply and the upstream ctest cases
        # are registered (see module docstring).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # HMDFS cannot create the make jobserver fifo (EPERM).
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        # E537: link with the final install RPATH so the install step does
        # not rewrite the ELF in place.
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        # Relocatable, unversioned DT_SONAME (W3 CI L5 soname gate).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Double cover: the OHOS-adapted conan toolchain maps os=OHOS
            # onto CMAKE_SYSTEM_NAME=HarmonyOS through its own cache entry,
            # which would win over tc.variables; pin the Linux platform
            # through the cache as well so KDECMakeSettings / ECMAddTests
            # behave as on a native POSIX build.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if str(self.settings.arch) == "armv8":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        qtbase = self.dependencies["qt5-qtbase"]
        # Qt5CoreConfigExtrasMkspecDir.cmake hard-codes a build-tree path
        # (<prefix>/../b/mkspecs/linux-clang) that does not exist in the
        # packaged cache entry; recreate it (kcoreaddons5 precedent).
        self._prepare_qt_mkspec_compat(qtbase.package_folder)
        qbin = os.path.join(qtbase.package_folder, "bin")
        for tool, cmake_var in (
            ("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
            ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
            ("uic", "CMAKE_AUTOUIC_EXECUTABLE"),
        ):
            tool_path = os.path.join(qbin, tool)
            if not os.path.isfile(tool_path):
                raise ConanInvalidConfiguration(
                    "qt5-qtbase/5.15.2.2 does not provide the required "
                    "bin/{} tool".format(tool)
                )
            tc.variables[cmake_var] = tool_path

        # KF5I18n's ki18n_install(po) registers a pofiles build target that
        # runs msgfmt on every po/ catalog; the sandbox PATH has no msgfmt,
        # so without this the generated build rule carries an empty
        # -DGETTEXT_MSGFMT_EXECUTABLE= and fails (gettext reaches this
        # graph transitively through ki18n5).
        gettext = self.dependencies.get("gettext")
        if gettext:
            for tool, cmake_var in (
                ("msgfmt", "GETTEXT_MSGFMT_EXECUTABLE"),
                ("msgmerge", "GETTEXT_MSGMERGE_EXECUTABLE"),
            ):
                tool_path = os.path.join(gettext.package_folder, "bin", tool)
                if os.path.isfile(tool_path):
                    tc.variables[cmake_var] = tool_path

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        tc.generate()

        # Wire the search paths CMakeDeps cannot provide (E429):
        #  * qt5-qtbase is consumed in "none" find-mode, so its install
        #    prefix must be added manually for find_package(Qt5 ... CONFIG)
        #    to resolve the native Qt5 configs.
        #  * ECM is a build-context requirement, so its config-mode
        #    directory must be added for find_package(ECM 5.116.0 NO_MODULE).
        #  * the KF5 dependencies declare cmake_find_mode=none (they ship
        #    their own KF5*Config.cmake with dependency tracking), so every
        #    dependency's lib/cmake must be on CMAKE_PREFIX_PATH, otherwise
        #    find_package(KF5 COMPONENTS CoreAddons I18n Config Codecs)
        #    fails with "Could not find a package configuration file
        #    provided by KF5CoreAddons".  Iterating every dependency also
        #    covers the transitive find_dependency() chains of the KF5
        #    configs (ktextwidgets / kjobwidgets5 precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        qt_pkg = qtbase.package_folder
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(qt_pkg))
        lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(qt_pkg))
        lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(qt_pkg))
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "{}")'.format(ecm_cmake))
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(ecm_cmake))
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(
                    dep.package_folder
                )
            )
            lines.append(
                'list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(dep.package_folder)
            )
            lines.append(
                'list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(
                    dep.package_folder
                )
            )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if not os.path.isdir(source):
            return
        os.makedirs(expected, exist_ok=True)
        for name in os.listdir(source):
            src_entry = os.path.join(source, name)
            dst_entry = os.path.join(expected, name)
            if os.path.exists(dst_entry):
                continue
            if os.path.isdir(src_entry):
                shutil.copytree(src_entry, dst_entry)
            else:
                shutil.copy2(src_entry, dst_entry)

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _cmake_build_env(self):
        # Host tools executed during configure/build (moc/rcc/uic, and the
        # msgfmt run by the pofiles target) must load a compatible
        # libc++_shared.so: the sandbox LD_LIBRARY_PATH can contain an
        # incompatible one under /data/storage/el1/bundle/libs/arm64 which
        # shadows the compatible system copy (kwidgetsaddons5 precedent).
        # ECMAddTests also freezes QT_PLUGIN_PATH into the ctest
        # ENVIRONMENT property at configure time, so the plugin paths must
        # be exported here as well, not only at test time.
        build_env = self._library_runtime_env()
        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase and qtbase.package_folder:
            build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        gettext = self.dependencies.get("gettext")
        if gettext and gettext.package_folder:
            build_env.prepend_path(
                "PATH", os.path.join(gettext.package_folder, "bin")
            )
        if str(self.settings.os) == "OHOS":
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib*"
                )
            ):
                if os.path.isdir(llvm_lib):
                    build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return build_env

    def _run_upstream_tests(self):
        # The 32 upstream ctest cases are registered by ECM's ecm_add_tests
        # / add_test from autotests/ (BUILD_TESTING=ON).  They are
        # QTEST_GUILESS_MAIN / QTEST_MAIN binaries driving the real KContacts
        # public API: the QTEST_MAIN ones run headless through the offscreen
        # QPA platform plugin shipped in qt5-qtbase, the vCard roundtrip
        # test reads its reference data from an embedded qrc, and the
        # addressformat / country-name functions read the iso-codes runtime
        # data deployed into the per-test XDG_DATA_HOME below.
        if not can_run(self):
            return
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        try:
            os.chmod(xdg_runtime, 0o700)
        except OSError:
            pass
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        if str(self.settings.os) == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        self._deploy_iso_codes_test_data(
            os.path.join(test_home, ".local", "share")
        )
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _deploy_iso_codes_test_data(self, xdg_data):
        # The KCountry-based functions (Address::countryToISO /
        # Address::ISOtoCountry and the addressformat repository
        # validation) resolve the iso-codes country tables and the
        # translated iso_3166-1 catalogs through
        # QStandardPaths::GenericDataLocation (kcontacts tests do not enable
        # QStandardPaths test mode, so XDG_DATA_HOME is the effective data
        # root; ki18n5 precedent).  iso-codes reaches this graph
        # transitively through ki18n5.
        isocodes = self.dependencies.get("iso-codes")
        if not isocodes:
            return
        pkg = isocodes.package_folder
        data_root = os.path.join(pkg, "share")
        pairs = [
            ("iso-codes/json", "iso-codes/json"),
            ("locale", "locale"),
        ]
        for src_rel, dst_rel in pairs:
            src = os.path.join(data_root, src_rel)
            if not os.path.exists(src):
                self.output.warn(
                    "iso-codes data missing in package: {}".format(src)
                )
                continue
            dst = os.path.join(xdg_data, dst_rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        self.output.info(
            "Deployed iso-codes test data to {}".format(xdg_data)
        )

    def _prepare_ctest_runtime_links(self):
        # ctest launches the test executables from <build>/bin.  The linked
        # libKF5Contacts.so records versioned NEEDED entries
        # (libKF5CoreAddons.so.5 / libKF5Codecs.so.5 ...), but the conan
        # packages only ship unversioned .so files, and the former
        # build_folder/../bin shim directory was never on the test
        # LD_LIBRARY_PATH.  Put both the unversioned and the versioned (.so.5)
        # aliases of every runtime lib into <build>/lib, which
        # _library_runtime_env() keeps on LD_LIBRARY_PATH for ctest
        # (kcoreaddons5 / kitemviews5 precedent).
        # kcontacts5 links with an unversioned soname but its KF5 deps
        # (kcoreaddons5/kcodecs5) were built with VERSIONED sonames, so
        # libKF5Contacts.so records versioned NEEDED entries.  Glob every
        # lib*.so* variant (versioned AND unversioned) and link each under
        # its own name, plus a .so.5 alias for bare .so files.
        compat_lib = os.path.join(self.build_folder, "lib")
        os.makedirs(compat_lib, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        seen = set()
        linked_names = []
        for src in lib_sources:
            base = os.path.basename(src)
            if base in seen:
                continue
            seen.add(base)
            names = {base}
            if base.endswith(".so"):
                # bare .so: also expose the major-versioned NEEDED name
                names.add(base[:-3] + ".so.5")
            else:
                # fully versioned file (libX.so.5.116.0): expose the
                # major-level soname the loader actually looks up (libX.so.5)
                m = re.match(r"^(lib\S+)\.so\.(\d+)(?:\..*)?$", base)
                if m:
                    names.add(m.group(1) + ".so." + m.group(2))
                    names.add(m.group(1) + ".so")
            for name in sorted(names):
                dst = os.path.join(compat_lib, name)
                if not os.path.exists(dst):
                    # copy first (HMDFS symlink pitfalls precedent), symlink
                    # only as a fallback for very large files
                    try:
                        shutil.copy2(src, dst)
                    except OSError:
                        try:
                            os.symlink(src, dst)
                        except OSError:
                            pass
                if os.path.exists(dst):
                    linked_names.append(name)
        # v4 diagnostics: make the shim state visible in the CI log so the
        # local-green / CI-red divergence becomes decidable from the build
        # log alone (three failed CI rounds shared the identical
        # "Error loading libKF5CoreAddons.so.5" tail with zero shim
        # visibility).
        self.output.info(
            "KMBS_SHIM: {} names exposed in {} (from {} sources)".format(
                len(linked_names), compat_lib, len(lib_sources)
            )
        )
        self.output.info(
            "KMBS_SHIM: names: {}".format(sorted(linked_names)[:40])
        )
        # Assert the exact sonames the ctest binaries need; when one is
        # missing, dump every dependency package lib/ listing so the next CI
        # run pinpoints the divergent package file set.
        needed_sonames = [
            "libKF5CoreAddons.so.5",
            "libKF5Codecs.so.5",
        ]
        for soname in needed_sonames:
            if os.path.exists(os.path.join(compat_lib, soname)):
                self.output.info("KMBS_SHIM: OK {} present".format(soname))
            else:
                self.output.warn(
                    "KMBS_SHIM: MISSING {} — dumping dependency lib/ dirs".format(
                        soname
                    )
                )
                for dep in self.dependencies.values():
                    if not (dep and dep.package_folder):
                        continue
                    deplib = os.path.join(dep.package_folder, "lib")
                    if not os.path.isdir(deplib):
                        continue
                    listing = sorted(
                        f for f in os.listdir(deplib) if f.startswith("lib")
                    )
                    self.output.warn(
                        "KMBS_SHIM: {} lib/: {}".format(
                            dep.ref.name, listing[:20]
                        )
                    )
        # v5 root-cause fix: the upstream kcoreaddons5/kcodecs5 binary
        # revisions published 2026-09-28 carry a broken .codesign state —
        # the musl loader refuses them ("Error loading shared library
        # libKF5CoreAddons.so.5") even though the file is present and
        # byte-identical to the previously loadable revision. CI always
        # resolves the latest binary revision, which is why every CI round
        # stayed red while a local run against the older cached revision
        # passed (the local-green/CI-red divergence). Re-sign the shim
        # copies with the local self-sign tool: experimentally verified the
        # re-signed copy loads while the identical un-re-signed copy does
        # not (sha256-equal files, only the signature state differs).
        self._sign_ohos_elf_tree(compat_lib)
        self.output.info(
            "KMBS_SHIM: re-signed shim copies for loader acceptance"
        )

    # ------------------------------------------------------------------
    # OHOS ELF re-signing (ki18n 6.26.0.1 / kitemmodels 6.18.0.1
    # precedent): CMake rewrites the RUNPATH of installed shared libraries,
    # which invalidates the OHOS build-time .codesign section; the OHOS
    # loader then refuses to load the library ("Permission denied").
    # ------------------------------------------------------------------
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
        return next(
            (path for path in candidates if path and os.path.isfile(path)), ""
        )

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        if (
            str(self.settings.os) not in ("OHOS", "HarmonyOS")
            or not os.path.isdir(root_folder)
        ):
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

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        # The project installs its own KF5ContactsConfig.cmake
        # (find_dependency on KF5CoreAddons/KF5Config/KF5I18n/KF5Codecs)
        # with the KF5::Contacts exported target; use cmake_find_mode=none
        # so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Contacts"]
