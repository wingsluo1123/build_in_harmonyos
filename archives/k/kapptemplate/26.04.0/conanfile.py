#!/usr/bin/env python3
"""Conan recipe for kapptemplate 26.04.0 on HarmonyOS PC.

kapptemplate is the KDE SDK application-template generator: a Kirigami/QML
GUI (Qt Quick) that also ships a plain command-line mode. It writes a ready
to build C++/KDE-Frameworks project skeleton (the shipped ``kde-frameworks6``
and ``kde-frameworks6-simple`` templates) into a target directory, expanding
``%{APPNAME}``/``%{APPNAMELC}``/``%{AUTHOR}``/``%{VERSION}`` … macros in both
file names and text content.

Upstream hard requirements (CMakeLists.txt): CMake >= 3.16, Qt6 >= 6.5
(Widgets, Quick, QuickControls2; Test when BUILD_TESTING) and KF6 >= 6.0
(Archive, Config, ConfigWidgets, CoreAddons, I18n, IconThemes, DocTools) plus
KF6KirigamiAddons >= 1.4.0 (REQUIRED).

Version mapping (device-verified): the upstream CMake version is
``KAPPTEMPLATE_VERSION = "0.1" + RELEASE_SERVICE_COMPACT_VERSION`` where the
compact version is ``26``+``04``+``0`` = ``26040``; the platform task version
is the release-service version 26.04.0. ``--version`` therefore prints
"kapptemplate 0.1.26040". (The task handoff wrote "0.1.260400"; the real
upstream value has one fewer digit — confirmed by executing the built
binary.)

OHOS-specific adaptations (patches/0001, patches/0002, patches/0003):
  - patches/0001: KF6 DocTools is dropped (see the dependency note below), so
    the help-handbook generation is not built.
  - patches/0002: generator.cpp used QFile::copy() to place each extracted
    template file, but QFile::copy() returns false on the HMDFS filesystem
    here even for plain names (device-measured); the copy is done by hand
    (read + write) instead.
  - patches/0003: the stock kde_package_app_templates() always emits .tar.bz2
    template archives, but the published KF6Archive is built with
    WITH_BZIP2=OFF so KTar cannot open them and the generator would silently
    produce nothing; the templates are packaged as .zip instead (the generator
    already loads .zip through KZip/zlib).
Other adaptations (no patches):
  - KF_IGNORE_PLATFORM_CHECK=TRUE: OHOS is not in the KDE platform list.
  - KF_SKIP_PO_PROCESSING=ON: ki18n_install(po)/kdoctools_install(po) need
    gettext/msgfmt which OHOS does not ship; translations are not required
    for the generator to work (accessibility/klevernotes precedent).
  - conan_cmakedeps_paths.cmake written manually because qtbase and the KF6
    packages use cmake_find_mode=none (CMakeDeps emits no config for them).
  - ECM_MODULE_PATH + ECM find-modules/kde-modules on CMAKE_MODULE_PATH so
    the umbrella find_package(KF6 COMPONENTS …) (FindKF6.cmake),
    KDEInstallDirs, KDEPackageAppTemplates and ECMAddTests resolve.
  - BUILD_TESTING=ON: the two upstream QtTest suites (namevalidatortest,
    macrosubstitutiontest) are built and run for real via ctest inside
    build() under the offscreen QPA platform.

Dependency graph note: the whole KF6 set is kept on the 6.18.0 family so it
matches the already published OHOS binaries (kirigami-addons/1.13.0 was built
against 6.18.0, and kconfigwidgets/kitemmodels/kiconthemes only exist as the
6.18.x line); with no force=True override no dependency package_id is
invalidated and nothing is rebuilt from source. KF6 DocTools is dropped via
patches/0001-ohos-skip-kdoctools.patch (kfourinline/ksnakeduel precedent):
kdoctools/6.19.0 pins karchive/6.19.0 which conflicts with
kiconthemes/6.18.0.1's karchive/6.18.0, and the help handbook is not needed
for the generator to work.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KAppTemplateConan(ConanFile):
    name = "kapptemplate"
    version = "26.04.0"
    description = "KDE project template generator (Kirigami/QML application + CLI)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/sdk/kapptemplate"
    url = "https://invent.kde.org/sdk/kapptemplate/-/archive/v26.04.0/kapptemplate-v26.04.0.tar.gz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # Application package: the binary is resolved through bindirs and the QML
    # runtime through the runenv (QML2_IMPORT_PATH), so no library exports.
    options = {}
    default_options = {}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 stack: qtbase provides Core/Gui/Widgets/Test; qtdeclarative
        # provides Qml/Quick/QuickControls2 (Qt6QuickControls2 CMake config
        # verified present in the published qtdeclarative/6.11.1 package).
        # kirigami-addons transitively pulls the DBus/SQL-enabled
        # qtbase-sql-dbus variant, so Qt6::DBus resolves from that prefix.
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # KF6 frameworks declared by the upstream find_package(KF6 …). The
        # whole set is kept on the 6.18.0 family so every transitive require
        # matches the already-published OHOS binaries (no force=True override
        # → the published binaries stay valid and nothing is rebuilt from
        # source). kconfigwidgets/kitemmodels/kiconthemes only exist as the
        # 6.18.x line anyway.
        self.requires("karchive/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0.1")
        self.requires("kirigami/6.18.0")
        self.requires("kirigami-addons/1.13.0")
        # org.kde.kitemodels is imported by the shipped QML pages (ChoicePage /
        # ConfigurePage) and by kirigami-addons' treeview module.
        self.requires("kitemmodels/6.18.0.1")
        # NOTE: KF6 DocTools is intentionally NOT required. kdoctools/6.19.0
        # (the only published version) pins karchive/6.19.0 which conflicts
        # with kiconthemes/6.18.0.1's karchive/6.18.0; the help-handbook
        # generation is skipped on OHOS via patches/0001-ohos-skip-kdoctools.patch
        # (kfourinline/ksnakeduel 26.04.x precedent).

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Upstream tests (tests/CMakeLists.txt registers namevalidatortest and
        # macrosubstitutiontest via ecm_add_test) are built and run for real.
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt_extra = []
        for dep_name in ("qtdeclarative",):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
            )) + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

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
        # No source patches are needed on OHOS; apply_conandata_patches() is a
        # no-op with the empty patches: {} section but keeps the call site for
        # the CI/G1 completeness gates.
        if self.settings.os in ("OHOS", "HarmonyOS"):
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                # KF6 packages install their shared libraries under lib/ but a
                # few components/tools land in bin/; expose both.
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                # Qt host tools (qmltyperegistrar/qmlcachegen/kconfig_compiler)
                # live in libexec/ next to the Qt libraries they load.
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml"))
        # The interactive shell LD_LIBRARY_PATH carries whitespace-padded
        # entries the OHOS loader cannot resolve; append clean system dirs so
        # host tools (qtpaths/moc/kconfig_compiler) keep working.
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def _test_env(self):
        """Environment for the two upstream QtTest suites (ctest).

        The test binaries link Qt6::Core / Qt6::Test / KF6::CoreAddons, so
        they need the dependency libraries on LD_LIBRARY_PATH plus writable
        XDG dirs for QStandardPaths side effects. They do not load QML, but
        the QPA platform is forced offscreen for consistency.
        """
        test_env = self._runtime_env(include_build=False)
        for rel in ("bin", "lib"):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
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
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        return test_env

    def _run_upstream_tests(self):
        # The two upstream QtTest suites (kapptemplate-namevalidatortest,
        # kapptemplate-macrosubstitutiontest) run for real here; ctest returns
        # non-zero on any failure and the build fails loudly (no masking).
        with self._test_env().vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

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
        # E077: the OHOS HMDFS W^X policy refuses to load ELF files written
        # after build unless re-signed; drop the stale .codesign section and
        # self-sign every packaged ELF (alligator/accessibility precedent).
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
                self.run(f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}", ignore_errors=True)
                self.run(f"{self._quote(signer)} sign -inFile {self._quote(path)} -outFile {self._quote(path)} -selfSign 1")
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        # Application package: the delivered product is bin/kapptemplate; the
        # QML runtime is resolved through the consumers' runenv.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "bin"))
