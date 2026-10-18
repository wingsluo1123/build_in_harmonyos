#!/usr/bin/env python3
"""Conan recipe for kcolorscheme 6.28.0 on HarmonyOS PC.

kcolorscheme is the KDE Frameworks 6 color-scheme library: the
KF6ColorScheme shared library (KColorScheme color-role lookups,
KColorSchemeManager scheme discovery, KColorSchemeModel exposing the
installed schemes as a model, KStatefulBrush state-aware brushes) with
the built-in BreezeLight/BreezeDark schemes compiled in as Qt
resources.

Upstream hard requirements: Qt6 >= 6.9.0 (Core/Gui, GuiPrivate for
Qt >= 6.10, Test for the autotests), ECM >= 6.28.0, KF6 >= 6.28.0
(Config/GuiAddons/I18n all REQUIRED).

OHOS-specific adaptations:
  - patches/0001: KF_DEP_VERSION 6.28.0 -> 6.26.0. The ohpcd-published
    KF6 stack stops at 6.26.0 (kconfig has a .1 fix release there;
    kguiaddons and ki18n stop at 6.26.0). Only the KF_DEP_VERSION line
    is lowered: the find_package(ECM 6.28.0) line stays untouched
    because the extra-cmake-modules/6.29.0 tool package satisfies it.
  - patches/0002: relocatable basename SONAME linkage (krunner 6.28.0 /
    kscreenlocker 6.7.2 0008 precedent, device-proven). The published
    KF6 libraries carry no DT_SONAME (their exported targets set
    IMPORTED_NO_SONAME), so linking them by their absolute Conan cache
    paths would bake machine-private paths into libKF6ColorScheme.so's
    DT_NEEDED (non-relocatable, E537). lld records the name as given on
    the command line, so the four KF6 components the sources consume
    (ConfigCore/ConfigGui/GuiAddons/I18n) are linked by exact-file-name
    -l: flags (bare basenames) with the dependency directories attached
    PRIVATE to KF6ColorScheme, and the library gets an explicit
    -Wl,-soname,libKF6ColorScheme.so where the platform module defines
    no soname flag. KF6::ConfigCore stays on the link INTERFACE only
    (the public headers include <KSharedConfig>; the installed
    KF6ColorSchemeConfig.cmake already find_dependency(KF6Config)
    upstream, so it is exported by name, never by absolute path).
    Usage requirements of the deps that leave the link line are copied
    by walking the INTERFACE_LINK_LIBRARIES transitive closure of the
    direct KF6 deps with -NOTFOUND sentinel guards on every
    get_target_property lookup (the KDE-installed targets files set the
    per-config IMPORTED_LOCATION_RELEASE only; kscreenlocker 6.7.2 0008
    round 23 precedent).
  - BUILD_TESTING=ON: the upstream autotest suite is one QTest binary
    (kcolorschemetest: construction benchmark, per-color-set
    background/foreground/decoration reads across the 7 ColorSets,
    contrast-config reads) and runs headless with
    QT_QPA_PLATFORM=offscreen in hermetic XDG roots.
  - Dependencies: qtbase/6.11.1 (Core/Gui/Test), the KF6 stack at
    6.26.0 (kconfig at its .1 fix release, which injects a bare
    DT_SONAME; kguiaddons and ki18n have no .1 release -- the -l:
    linkage of patch 0002 handles both shapes)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none
  - package() re-signs every installed ELF (CMake install rewrites the
    RUNPATH, which invalidates the build-time .codesign section and
    makes the OHOS loader refuse the library with "Permission denied";
    krunner 6.28.0 / kscreenlocker 6.7.2 precedent)
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class KcolorschemeConan(ConanFile):
    name = "kcolorscheme"
    version = "6.28.0"
    description = "KDE Frameworks 6 - Color scheme utilities"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcolorscheme"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # Shared-only by construction: patch 0002 gates -Wl,-soname on the
        # shared link, package() runs the OHOS ELF refresh on
        # lib/libKF6ColorScheme.so and the consumer test loads the shared
        # object at run time. The shared option stays declared (package_id
        # shape), but a static request would silently produce a package
        # that claims shared=False while containing a shared library --
        # reject it like the other OHOS adaptations that only package .so
        # (krunner 6.28.0 precedent).
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "kcolorscheme 6.28.0 OHOS adaptation only packages shared "
                "libraries (libKF6ColorScheme.so); use -o '&:shared=True' "
                "(the default)."
            )

    def requirements(self):
        # Qt6::Core/Gui come from the plain qtbase build (Qt6::Test is
        # used by the upstream autotests); Qt6GuiPrivate is part of the
        # qtbase package for Qt >= 6.10 and is linked by src/CMakeLists.
        self.requires("qtbase/6.11.1")
        # KF6 stack at 6.26.0. Direct component use in the sources:
        # kcolorscheme.cpp / kcolorschememanager.cpp use
        # KSharedConfig/KConfigGroup (KF6::ConfigCore; also exposed by the
        # public headers), KConfig loads KF6::ConfigGui for QColor I/O,
        # KColorUtils comes from KF6::GuiAddons and the user-visible
        # scheme names use KLocalizedString (KF6::I18n).
        # kconfig .1 injects a bare DT_SONAME; kguiaddons and ki18n have
        # no .1 release (no DT_SONAME -- patch 0002 links all four by
        # exact-file-name -l: flags, which is relocatable in both shapes).
        self.requires("kconfig/6.26.0.1")   # KF6::ConfigCore / KF6::ConfigGui
        self.requires("kguiaddons/6.26.0")  # KF6::GuiAddons (KColorUtils)
        self.requires("ki18n/6.26.0")       # KF6::I18n

    def build_requirements(self):
        # ECM >= 6.28.0 REQUIRED upstream (the find_package(ECM 6.28.0)
        # line stays untouched); extra-cmake-modules/6.29.0 is the
        # published ECM base for this KF6 generation (krunner 6.28.0
        # precedent).
        self.tool_requires("extra-cmake-modules/6.29.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The profile pins cppstd=17; the KF6 6.28 headers need C++20
        # (KDEFrameworkCompilerSettings raises it upstream; make it
        # explicit here -- krunner 6.28.0 precedent).
        tc.blocks.remove("cppstd")
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but
        # the CMakeDeps-generated ECMConfig.cmake does not. Set it
        # manually so the KDE cmake modules are found (krunner 6.28.0
        # precedent).
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # conan_cmakedeps_paths.cmake created manually because qtbase
        # uses cmake_find_mode=none (kscreenlocker precedent). Every host
        # dependency's lib/cmake goes on the search path so
        # find_package(KF6Config/KF6GuiAddons/KF6I18n) and the
        # installed-config find_dependency chains resolve inside the
        # conan cache.
        qtbase = self.dependencies.get("qtbase")
        lines = []
        if qtbase and qtbase.package_folder:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        if qtbase and qtbase.package_folder:
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _sdk_llvm_lib_dirs(self):
        # The OHOS SDK root is environment specific, so prefer the
        # llvm/lib directory implied by the profile's compiler and fall
        # back to globbing the installed SDK. The SDK version stays
        # unpinned on purpose: a pinned version breaks as soon as a CI
        # image ships a different SDK release (kconfig 6.26.0.1
        # precedent).
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        if cxx:
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            )
        )
        return [c for c in dict.fromkeys(candidates) if os.path.isdir(c)]

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in self._sdk_llvm_lib_dirs():
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM's KDEInstallDirs6 runs the qtbase qtpaths host tool
            # during configure (ecm_query_qt -> QT_INSTALL_PREFIX). The
            # sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64
            # which shadows the compatible one; prepend /system/lib64
            # (and the qtbase lib dir, already added by
            # _library_runtime_env) so the loader resolves the compatible
            # libc++ first (kconfig 6.26.0.1 / krunner 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in self._sdk_llvm_lib_dirs():
                test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # Same /system/lib64 reasoning as _cmake_build_env.
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 300'.format(self.build_folder)
            )

    def _prepare_ctest_runtime_links(self):
        # ctest runs the tests with WORKING_DIRECTORY set to the test
        # binary's directory (<build>/autotests), and a library recorded
        # in DT_NEEDED as the build-tree-relative "../../bin/..." would
        # then resolve to <build>/../bin -- next to, not inside, the
        # build folder. Stage libKF6ColorScheme.so and every dependency
        # library there (kcolorscheme 6.26.0 precedent; symlink when the
        # filesystem allows it, copy otherwise -- HMDFS denies symlinks).
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        library_sources = glob.glob(
            os.path.join(self.build_folder, "bin", "lib*.so*")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                library_sources.extend(
                    glob.glob(
                        os.path.join(dep.package_folder, "lib", "lib*.so*")
                    )
                )
        for source in library_sources:
            destination = os.path.join(
                compatibility_bin, os.path.basename(source)
            )
            if os.path.exists(source) and not os.path.lexists(destination):
                try:
                    os.symlink(source, destination)
                except OSError:
                    shutil.copy2(source, destination)

    # ------------------------------------------------------------------
    # Packaging.
    # ------------------------------------------------------------------

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
        return next(
            (path for path in candidates if path and os.path.isfile(path)), ""
        )

    @staticmethod
    def _quote(value):
        # The value lands in a shell command line: quote for the shell
        # (shlex) so $, backticks and backslashes stay inert.
        return shlex.quote(str(value))

    def _sign_ohos_elf_tree(self, root_folder):
        # CMake install rewrites the RUNPATH of every installed ELF,
        # which invalidates the build-time .codesign section; re-sign
        # everything with the device binary-sign-tool (krunner 6.28.0 /
        # kscreenlocker 6.7.2 precedent).
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
                    f"{self._quote(objcopy)} --remove-section .codesign "
                    f"{self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package_info(self):
        # The project installs its own KF6ColorSchemeConfig.cmake with
        # proper dependency tracking (find_dependency on KF6Config). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it (KF6
        # precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6ColorScheme"]
