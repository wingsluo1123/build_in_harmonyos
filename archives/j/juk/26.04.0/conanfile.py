#!/usr/bin/env python3
"""Conan recipe for juk 26.04.0 on HarmonyOS PC (KDE Gear 26.04 music player).

juk is a Qt Widgets + KF6 desktop application: it exports no library, only the
`juk` binary plus desktop/appdata/icons resources and the handbook. The OHOS
baseline is built from the official KDE release-service tarball.

Dependency matrix - this is the actual adaptation obstacle (see notes.md and
the knowledge-base entry for this failure class). The published ohpcd KF6 line
is fragmented, so no single 6.x version covers juk's 18 required components:

  * kio exists only as 6.14.0 and 6.26.0, and the 6.26.0 recipe is built with
    -DKIOCORE_ONLY=ON: it ships neither KF6::KIOWidgets nor KF6::KIOFileWidgets,
    both of which juk links (src/filehandle.cpp, tageditor, file renamer) ->
    6.14.0 is the only usable KIO;
  * kbookmarks / kconfigwidgets / kjobwidgets / ktextwidgets stop at 6.18.0,
    kwallet exists only as 6.18.0, kdoctools only as 6.19.0 and
    kstatusnotifieritem only as 6.26.0;
  * 6.18.0 is therefore the line with the fewest holes: it is the base, and
    every transitive pin is unified through override=True. KF6 keeps binary
    compatibility inside a major series, so a 6.18 base combined with kio 6.14,
    kdoctools 6.19 and kstatusnotifieritem 6.26 is ABI-safe.

Note: the CMakeLists platform gate (KF6_MIN_VERSION "5.240.0") is satisfied by
every published 6.x recipe, so no source patch is needed for the version gate.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class JukConan(ConanFile):
    name = "juk"
    version = "26.04.0"
    description = "KDE music player (JuK) - KDE Gear 26.04"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/multimedia/juk"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/juk-26.04.0.tar.xz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {}
    default_options = {}

    # KF6 modules juk's CMakeLists.txt asks for (find_package(KF6 COMPONENTS
    # ...)) that kio/6.14.0 does not already pull into the graph, mapped to the
    # version actually published in the ohpcd registry (measured matrix in
    # notes.md). These are real, materialised requirements.
    _KF6_REQUIRES = {
        "kconfigwidgets": "6.18.0",
        "kdbusaddons": "6.18.0",
        "kdoctools": "6.19.0",
        "kglobalaccel": "6.18.0",
        # Only full KIO is usable (see module docstring): 6.14.0 builds
        # KF6KIOCore + KF6KIOWidgets, which is what juk links.
        "kio": "6.14.0",
        "knotifications": "6.18.0",
        "kstatusnotifieritem": "6.26.0",
        "ktextwidgets": "6.18.0",
        "kwallet": "6.18.0",
        "kxmlgui": "6.18.0",
    }

    # Shared KF6 base. Every module here is already required by kio/6.14.0, but
    # at the 6.14 line; a complete 6.14 line does not exist (kglobalaccel has no
    # 6.14 recipe at all) while the modules above need the 6.18 line, so the
    # whole graph is unified with override=True. KF6 keeps binary compatibility
    # inside a major series, so the resulting 6.18 base (plus kio 6.14, kdoctools
    # 6.19, kstatusnotifieritem 6.26) is ABI-safe.
    _KF6_PINS = {
        "karchive": "6.19.0",  # kiconthemes/6.18.0 requires karchive/6.19.0
        "kauth": "6.18.0",
        "kbookmarks": "6.18.0",
        "kcodecs": "6.18.0",
        "kcolorscheme": "6.18.0",
        "kcompletion": "6.18.0",
        "kconfig": "6.18.0",
        "kcoreaddons": "6.18.0",
        "kcrash": "6.18.0",
        "kguiaddons": "6.18.0",
        "ki18n": "6.18.0",
        "kiconthemes": "6.18.0",
        "kitemviews": "6.18.0",
        "kjobwidgets": "6.18.0",
        "kservice": "6.18.0",
        "kwidgetsaddons": "6.18.0",
        # kio/6.14.0 pins 6.14.0, kstatusnotifieritem/6.26.0 pins 6.26.0; the
        # 6.18-line modules only require >= 6.18.0, so 6.26.0 satisfies every
        # CMake version gate (kstatusnotifieritem's CMakeLists asks for
        # KF6WindowSystem 6.26.0 exactly).
        "kwindowsystem": "6.26.0",
        "solid": "6.18.0",
        # Transitive-only conflict, not visible from juk's own requires:
        # karchive/libxml2 ask for zlib/1.3.2 while some Qt-side recipes still
        # reference 1.3.1. The published 1.3.1 static binary was built without
        # -fPIC (zlib's configure only adds it for gcc, CI compiles with clang),
        # so kdoctools fails to link libKF6DocTools.so against libz.a:
        #   ld.lld: relocation R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC
        # The published 1.3.2 binary is PIC, so unify on 1.3.2.
        "zlib": "1.3.2",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 stack. qtbase/6.11.1 is the reference every KF6 recipe in the
        # registry builds against, so keeping it identical avoids a second
        # qtbase generation in the graph.
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        self.requires("taglib/2.3")
        for pkg, ver in self._KF6_REQUIRES.items():
            self.requires("{}/{}".format(pkg, ver))
        for pkg, ver in self._KF6_PINS.items():
            self.requires("{}/{}".format(pkg, ver), override=True)

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
        # tests/CMakeLists.txt registers tagguessertest through ECMAddTests.
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # KDECMakeSettings generates an "uninstall" target via
        # ECMUninstallTarget, which configure_file()s ecm_uninstall.cmake.in.
        # Some CI worker ECM caches lack that template, hard-failing configure
        # (#84826). The uninstall target is meaningless inside a conan package,
        # so skip it entirely via ECM's own official switch.
        tc.variables["KDE_SKIP_UNINSTALL_TARGET"] = "ON"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # KF6 6.x requires C++20.
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # The OHOS loader resolves $ORIGIN only when DT_RPATH (not DT_RUNPATH)
        # is present, hence --disable-new-dtags.
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

        # Qt6 components live in their own packages; Qt's own find_package
        # needs the extra prefixes to locate Qt6Svg / Qt6Multimedia.
        qt_extra = []
        for dep_name in ("qtsvg", "qtmultimedia"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        self._write_taglib_compat_config()
        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        # CMake has no Platform/HarmonyOS module: it honours neither VERSION nor
        # SOVERSION and emits no DT_SONAME, which makes dependents record
        # build-tree relative DT_NEEDED entries. Provide the soname/rpath rules
        # explicitly (kio 6.14.0 / alligator 26.04.0 precedent).
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

    def _write_taglib_compat_config(self):
        # The taglib conan package ships TagLib's own taglib-config.cmake,
        # which defines TagLib::tag / TagLib::TagLib, but juk's CMakeLists
        # links the ECM find-module target name Taglib::Taglib (different
        # capitalisation, see CMakeLists.txt:193). Ship a config-mode
        # wrapper next to the CMakeDeps output (the generators folder is
        # PREPENDED to CMAKE_PREFIX_PATH) that loads the package's real
        # config - so the static archive keeps its full transitive link
        # closure (ZLIB::ZLIB ...) - and aliases its target under the name
        # juk expects. kfilemetadata 6.28.0 precedent.
        dep = self.dependencies.get("taglib")
        if not (dep and dep.package_folder):
            return
        real_config = None
        for dirpath, _dirnames, filenames in os.walk(
            os.path.join(dep.package_folder, "lib", "cmake")
        ):
            for candidate in ("taglib-config.cmake", "TaglibConfig.cmake"):
                if candidate in filenames:
                    real_config = os.path.join(dirpath, candidate)
                    break
            if real_config:
                break
        if not real_config:
            self.output.warning(
                "taglib: no upstream CMake config found; Taglib::Taglib stays undefined"
            )
            return
        version = str(dep.ref.version)
        # The package's own taglib-targets.cmake declares ZLIB::ZLIB in the
        # link interface of TagLib::tag (TagLib's CMake export uses the
        # FindZLIB module target name). Load the conan zlib CMakeDeps config
        # if present, otherwise pre-define the target from the static
        # archive so the interface resolves. kfilemetadata 6.28.0 precedent.
        zlib_lib = ""
        zlib = self.dependencies.get("zlib")
        if zlib and zlib.package_folder:
            for candidate in ("libz.a", "libz.so"):
                candidate_path = os.path.join(zlib.package_folder, "lib", candidate)
                if os.path.exists(candidate_path):
                    zlib_lib = candidate_path.replace("\\", "/")
                    break
        zlib_lines = [
            "if(NOT TARGET ZLIB::ZLIB)",
            "  find_package(ZLIB CONFIG QUIET)",
            "endif()",
        ]
        if zlib_lib:
            zlib_lines += [
                "if(NOT TARGET ZLIB::ZLIB)",
                "  add_library(ZLIB::ZLIB UNKNOWN IMPORTED)",
                "  set_target_properties(ZLIB::ZLIB PROPERTIES",
                '    IMPORTED_LOCATION "{}")'.format(zlib_lib),
                "endif()",
            ]
        save(
            self,
            os.path.join(self.generators_folder, "TaglibConfig.cmake"),
            "\n".join(tuple(zlib_lines) + (
                "# conan-generated Taglib compatibility config (juk 26.04.0).",
                "# Loads the conan package's own config and aliases the real",
                "# target under the ECM find-module name the sources link.",
                'include("{}")'.format(real_config.replace("\\", "/")),
                "if(TARGET TagLib::tag AND NOT TARGET Taglib::Taglib)",
                "  add_library(Taglib::Taglib ALIAS TagLib::tag)",
                "endif()",
                "if(TARGET Taglib::Taglib)",
                "  set(Taglib_FOUND TRUE)",
                '  set(Taglib_VERSION "{}")'.format(version),
                "  set(Taglib_LIBRARIES Taglib::Taglib)",
                "  set_property(GLOBAL APPEND PROPERTY PACKAGES_FOUND Taglib)",
                "endif()",
            )) + "\n",
        )
        save(
            self,
            os.path.join(self.generators_folder, "TaglibConfigVersion.cmake"),
            "\n".join((
                'set(PACKAGE_VERSION "{}")'.format(version),
                "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)",
                "  set(PACKAGE_VERSION_COMPATIBLE FALSE)",
                "else()",
                "  set(PACKAGE_VERSION_COMPATIBLE TRUE)",
                "  if(PACKAGE_VERSION VERSION_EQUAL PACKAGE_FIND_VERSION)",
                "    set(PACKAGE_VERSION_EXACT TRUE)",
                "  endif()",
                "endif()",
            )) + "\n",
        )

    def _write_cmake_paths(self):
        # ECM's installed ECMConfig.cmake sets ECM_MODULE_PATH but the
        # CMakeDeps-generated one does not, and the KF6 *Config.cmake files
        # chain find_dependency() through each other; inject every dependency
        # prefix before project().
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
            'set(CMAKE_PREFIX_PATH "{};${{CMAKE_PREFIX_PATH}}")'.format(";".join(prefixes)),
            'set(CMAKE_LIBRARY_PATH "{};${{CMAKE_LIBRARY_PATH}}")'.format(";".join(libraries)),
            'set(CMAKE_INCLUDE_PATH "{};${{CMAKE_INCLUDE_PATH}}")'.format(";".join(includes)),
            'set(CMAKE_MODULE_PATH "{};${{CMAKE_MODULE_PATH}}")'.format(";".join(modules)),
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._run_upstream_tests()

    def _test_env(self):
        """Environment for the upstream ctest suite (tagguessertest)."""
        test_env = self._runtime_env(include_build=False)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                # KF6 packages install their shared libraries under bin/.
                test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin"))
        for rel in ("bin", "lib"):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        self._make_link_farm()
        # tagguessertest touches QStandardPaths / KConfig, so give it writable
        # and deterministic XDG directories.
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

    def _make_link_farm(self):
        # E537: published KF6 libraries carry build-tree-relative DT_NEEDED
        # entries ("../../bin/libKF6ConfigCore.so") which the OHOS loader
        # resolves against the process CWD (ctest runs from <build>/Release, so
        # ../../bin reaches the build-tree root). Mirror that layout with a farm
        # of every dependency shared library (alligator 26.04.0 precedent).
        farm = os.path.join(os.path.dirname(self.build_folder.rstrip(os.sep)), "bin")
        try:
            os.makedirs(farm, exist_ok=True)
        except OSError as exc:
            self.output.warning("link farm mkdir failed: {}".format(exc))
            return
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for layout_dir in ("lib", "bin"):
                src_dir = os.path.join(dep.package_folder, layout_dir)
                if not os.path.isdir(src_dir):
                    continue
                for name in os.listdir(src_dir):
                    if not name.endswith(".so"):
                        continue
                    link = os.path.join(farm, name)
                    if not os.path.lexists(link):
                        try:
                            os.symlink(os.path.join(src_dir, name), link)
                        except OSError as exc:
                            self.output.warning("link farm entry {} failed: {}".format(name, exc))

    def _run_upstream_tests(self):
        # Upstream registers a single autotest (tests/CMakeLists.txt):
        # tagguessertest, which drives TagGuesser (tagguesser.cpp) over
        # filename -> tag patterns. Reported honestly in notes.md.
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
        # OHOS refuses to exec unsigned ELF files; sign every packaged binary.
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
                    "{} --remove-section .codesign {}".format(
                        self._quote(objcopy), self._quote(path)
                    ),
                    ignore_errors=True,
                )
                self.run(
                    "{} sign -inFile {} -outFile {} -selfSign 1".format(
                        self._quote(signer), self._quote(path), self._quote(path)
                    )
                )
                signed += 1
        self.output.info("Signed {} OHOS package ELF file(s)".format(signed))

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        # The host shell LD_LIBRARY_PATH carries whitespace-padded entries which
        # the OHOS loader cannot resolve, so Qt host tools (moc/qtpaths) fail
        # with "libc++_shared.so not found". List the system dirs explicitly.
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        # Application package: only the executable (and desktop resources) are
        # installed, so no library/header exports are declared.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
