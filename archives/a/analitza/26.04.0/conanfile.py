#!/usr/bin/env python3
"""Conan recipe for analitza 26.04.0 on HarmonyOS PC.

analitza is the KDE education math library behind kalgebra 26.04.0
(``find_package(Analitza6 REQUIRED)``). It ships four shared libraries:

  - libAnalitza.so         — expression parser/analyzer, builtin methods,
                             MathML/HTML writers (Analitza6 core).
  - libAnalitzaPlot.so     — plot engine: 2D/3D plot items, PlotsModel,
                             PlotsFactory, marching squares/cubes backends,
                             Plotter2D and the Plotter3DES GL scene.
  - libAnalitzaGui.so      — Gui-side models (operators/variables/highlighter).
  - libAnalitzaWidgets.so  — QWidget views (PlotsView2D + the
                             QOpenGLWidget-based PlotsView3DES).
  plus the QML module ``org.kde.analitza`` (declarative/). Every library is
  emitted under its unversioned name with a bare DT_SONAME (E330: HMDFS
  rejects the versioned symlink chain).

Upstream test suite: 18 CTest entries = 45 QTest functions over 14 QTest
programs (8 in analitza/tests, 5 in analitzaplot/tests, 1 in
analitzagui/tests) + 4 script-type export cases
(export-test-{sin,fancy}-{stl,x3d}, driving analitzaplot/examples/
export3dplotdemo) = 49 upstream test cases.

OHOS adaptations (patches/0001-0006, capability probes, no platform macros):
  - Qt6PrintSupport / Qt6OpenGL / Qt6OpenGLWidgets are probed through their
    imported targets: the published qtbase/6.11.1 line is built with
    PrintSupport and OpenGL disabled, so the top-level find_package moves
    those three modules to OPTIONAL_COMPONENTS and every link is
    conditional on TARGET existence.
  - The GL-backed scene (plotter3d_es), the QOpenGLWidget view
    (plotsview3d_es) and the QML Graph3D item are compiled out when the
    corresponding Qt modules are absent. ANALITZA_HAVE_OPENGL is exported
    as a PUBLIC compile definition of the AnalitzaPlot target (with a
    __has_include fallback for non-CMake consumers) so the installed
    plotter3d_es.h has the same class layout as the library; <QPrinter> is
    probed the same way. The exported 3D API and the X3D/STL export path
    stay available on every platform.
  - Everything else (expression engine, 2D plots, X3D/STL export, the
    org.kde.analitza QML module minus Graph3D) builds unchanged.

Dependency line: qtbase/6.11.1 (Core/Gui/Widgets/Xml/Test) +
qtsvg/6.11.1 (PlotsView2D PRIVATE Qt6::Svg) + qtdeclarative/6.11.1
(Qml/Quick for the QML module) + ecm/6.26.0 + qt6linguisttools/6.11.1
(ECMPoQmTools lrelease/lconvert for the upstream poqm catalogs).
No KF6 framework libraries are linked — do not add kcoreaddons/ki18n.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class AnalitzaConan(ConanFile):
    name = "analitza"
    version = "26.04.0"
    description = (
        "KDE education math library: expression parser/analyzer, 2D/3D plot "
        "engine, widgets views and the org.kde.analitza QML module (26.04.0)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/education/analitza"
    url = (
        "https://download.kde.org/stable/release-service/26.04.0/src/"
        "analitza-26.04.0.tar.xz"
    )
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/Gui/Widgets/Xml (Test for the upstream QTests).
        self.requires("qtbase/6.11.1")
        # Qt6::Svg — AnalitzaWidgets links it PRIVATE (plot item icons).
        self.requires("qtsvg/6.11.1")
        # Qt6 Qml/Quick — required to configure and install the
        # org.kde.analitza QML module in declarative/.
        self.requires("qtdeclarative/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # Qt6LinguistTools (lrelease/lconvert + the Qt6::LinguistTools CMake
        # module) is required by ECMPoQmTools for the upstream poqm catalog
        # step (kdbusaddons 6.29.0 precedent).
        self.tool_requires("qt6linguisttools/6.11.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"analitza is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; kdiagram/abcmidi precedent).
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Run the full upstream CTest suite (18 entries / 49 cases).
        tc.variables["BUILD_TESTING"] = "ON"
        # OHOS is not in the KDE platform list (kfourinline precedent).
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # KDEInstallDirs single-prefix layout on conan.
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # OHOS loader workaround: default lld 0x10000 max-page-size can
            # split .dynsym/.dynstr into separate high-address RW LOAD
            # segments the OHOS loader refuses to mmap; pin the 4K layout.
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            self._configure_ohos_shared_library_rules(tc)
        # ECM's own ECMConfig.cmake sets ECM_MODULE_PATH but the
        # CMakeDeps-generated layout does not propagate the variable the
        # project relies on — set it manually (ki18n/kdiagram precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )
        # Qt6Config.cmake resolves COMPONENTS relative to Qt6_DIR (qtbase),
        # so find_package(Qt6 COMPONENTS LinguistTools) would look inside
        # qtbase's lib/cmake and fail. Pin Qt6LinguistTools_DIR explicitly
        # to the qt6linguisttools package (kdbusaddons 6.29.0 precedent).
        ltt = self.dependencies.build.get("qt6linguisttools")
        if ltt:
            tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
                ltt.package_folder, "lib", "cmake", "Qt6LinguistTools"
            )
        # Qt6 split-package component discovery: Qt6Svg lives in qtsvg,
        # Qt6Qml/Qt6Quick in qtdeclarative (kfourinline/kdiagram pattern).
        qt_extra = []
        for dep_name in ("qtbase", "qtsvg", "qtdeclarative", "qtshadertools"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )
        self._write_cmake_paths()
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        """OHOS CMake does not emit a SONAME for shared libraries by default.
        Without a SONAME a QML plugin or test binary records the build-tree
        relative path in DT_NEEDED, which the OHOS loader treats as a
        cwd-relative path and fails to resolve. Restore the soname/rpath
        flags and suppress the versioned symlink chain: upstream sets
        VERSION/SOVERSION, so CMake would create
        libAnalitza.so.9.0.0 -> .so.9 -> .so, which the OHOS/HMDFS user
        volume rejects (cmake_symlink_library: Permission denied).
        CMAKE_PLATFORM_NO_VERSIONED_SONAME emits a single unversioned .so
        with the relocatable bare SONAME (E330 / ki18n, attica precedent)."""
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
        # Unversioned real .so + bare SONAME; no cmake_symlink_library calls.
        toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"

    def _write_cmake_paths(self):
        # qtbase/qtsvg/qtdeclarative use cmake_find_mode=none, so CMakeDeps
        # does not put their lib/cmake dirs on CMAKE_PREFIX_PATH. Write
        # conan_cmakedeps_paths.cmake manually (ki18n/kdiagram precedent).
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

    def _dependency_runtime_env(self, include_build=False):
        """Runtime env for the split Qt packages. The Qt host tools
        (moc/rcc/qmltyperegistrar/lrelease) and the freshly built QML plugin
        need every dependency lib dir on LD_LIBRARY_PATH, and the tools need
        their bin/libexec dirs on PATH (ki18n precedent)."""
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                prefix = dep.package_folder
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "bin"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "libexec"))
                env.prepend_path("PATH", os.path.join(prefix, "bin"))
                env.prepend_path("PATH", os.path.join(prefix, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(prefix, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(prefix, "lib", "plugins"))
                for rel in ("qml", "lib/qml", "share/qml"):
                    env.prepend_path("QML2_IMPORT_PATH", os.path.join(prefix, rel))
                    env.prepend_path("QML_IMPORT_PATH", os.path.join(prefix, rel))
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def build(self):
        # Capability-based patches: they keep the stock Qt6 build intact
        # (optional components resolve to targets where the modules exist)
        # and drop the disabled modules on the OHOS qtbase line, so they are
        # applied unconditionally (kdiagram precedent).
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._dependency_runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        # Upstream QTests execute target binaries, so honour the standard
        # cross-build opt-outs (celero/dawg/iverilog precedent). The OHPC
        # profile builds natively on the OHOS device, so the suite runs.
        if can_run(self) and not self.conf.get("tools.build:skip_test", default=False):
            self._run_upstream_tests()

    def _build_tree_lib_dirs(self):
        return [
            os.path.join(self.build_folder, rel)
            for rel in (
                "bin",
                "lib",
                "analitza",
                "analitzaplot",
                "analitzagui",
                "analitzawidgets",
                "declarative",
            )
        ]

    def _run_upstream_tests(self):
        self._prepare_ctest_runtime_links()
        test_env = self._dependency_runtime_env(include_build=False)
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
        for lib_dir in self._build_tree_lib_dirs():
            test_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        """Mirror the build-tree shared libraries into every test working
        directory so each ctest-invoked binary resolves its DT_NEEDED
        entries (ctest runs from the test's own binary dir; HMDFS rejects
        symlink() with EPERM -> plain-copy fallback)."""
        so_files = []
        for rel in ("analitza", "analitzaplot", "analitzagui", "analitzawidgets", "lib", "bin"):
            so_files.extend(glob.glob(os.path.join(self.build_folder, rel, "lib*.so*")))
        compatibility_dirs = {
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "lib"),
        }
        for rel in (
            os.path.join("analitza", "tests"),
            os.path.join("analitzaplot", "tests"),
            os.path.join("analitzagui", "tests"),
            os.path.join("analitzaplot", "examples"),
        ):
            path = os.path.join(self.build_folder, rel)
            if os.path.isdir(path):
                compatibility_dirs.add(path)
        for cdir in compatibility_dirs:
            os.makedirs(cdir, exist_ok=True)
        for src in so_files:
            for cdir in compatibility_dirs:
                dst = os.path.join(cdir, os.path.basename(src))
                if not os.path.exists(src) or os.path.abspath(dst) == os.path.abspath(src):
                    continue
                # Refresh stale mirror entries on a rebuilt tree: a previous
                # build may have left a regular-file copy (HMDFS EPERM path)
                # that would otherwise shadow the fresh library in ctest.
                if os.path.lexists(dst):
                    try:
                        os.remove(dst)
                    except OSError:
                        continue
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

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
        """CMake rewrites the RUNPATH of installed shared libraries, which
        invalidates the OHOS build-time .codesign section. The OHOS loader
        then refuses to load the library ("Permission denied"). Re-sign every
        packaged ELF (ki18n/kdiagram precedent)."""
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

    def package(self):
        cmake = CMake(self)
        with self._dependency_runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING.DOC", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        # The project installs its own Analitza6Config.cmake (find_dependency
        # Qt6Core/Qt6Xml) with the KF6::Analitza* exported targets; use
        # cmake_find_mode=none so CMakeDeps does not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = [
            "Analitza",
            "AnalitzaPlot",
            "AnalitzaGui",
            "AnalitzaWidgets",
        ]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        # QML module org.kde.analitza: consumers need the import root on
        # their QML import path.
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
        self.runenv_info.prepend_path(
            "QML_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
