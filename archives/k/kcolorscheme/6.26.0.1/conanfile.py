#!/usr/bin/env python3
"""Conan recipe for kcolorscheme 6.26.0.1 on HarmonyOS PC.

kcolorscheme is the KDE Frameworks 6 color-scheme library: the
KF6ColorScheme shared library (KColorScheme color-role lookups,
KColorSchemeManager scheme discovery, KColorSchemeModel exposing the
installed schemes as a model, KStatefulBrush state-aware brushes) with
the built-in BreezeLight/BreezeDark schemes compiled in as Qt
resources.

Revision 6.26.0.1 repairs two defects of the published 6.26.0 package:

  1. The recipe did not declare libxkbcommon, so a source rebuild under a
     consumer qtbase override (kwin 6.7.2 overrides qtbase to 6.11.1.2)
     failed in Qt6GuiPrivate's find_dependency(XKB) with
     "Could NOT find XKB" and Qt6GuiPrivate_FOUND=FALSE. The revision
     declares libxkbcommon/1.6.0 and exposes XKB_INCLUDE_DIR /
     XKB_LIBRARY for Qt's fallback finder.
  2. The installed libKF6ColorScheme.so carried no DT_SONAME and recorded
     build-machine absolute paths in DT_NEEDED for the KF6 dependencies
     (L5a/L5b/L5c). The published KF6 libraries themselves carry no
     DT_SONAME either (kguiaddons and ki18n have no .1 release in the
     registry), so patches/0002 links the four consumed KF6 components by
     exact file name (-l:libKF6*.so) and passes an explicit
     -Wl,-soname,libKF6ColorScheme.so.

Upstream sources, build logic and test cases are unchanged (the only
patch is the relocatable-linkage portability patch in patches/0002).
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KcolorschemeConan(ConanFile):
    name = "kcolorscheme"
    version = "6.26.0.1"
    description = "KDE Frameworks 6 color scheme utilities"
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
        # shared link, package() re-signs the installed ELF and the consumer
        # test loads the shared object at run time. The option stays declared
        # (package_id shape) but a static request is rejected instead of
        # silently producing a package that claims shared=False while
        # containing a shared library (kcolorscheme 6.28.0 precedent).
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "kcolorscheme 6.26.0.1 OHOS adaptation only packages shared "
                "libraries (libKF6ColorScheme.so); use -o '&:shared=True' "
                "(the default)."
            )

    def requirements(self):
        # Qt6::Core/Gui come from the plain qtbase build (Qt6::Test is used
        # by the upstream autotests); Qt6GuiPrivate is part of the qtbase
        # package for Qt >= 6.10 and is linked by src/CMakeLists.
        self.requires("qtbase/6.11.1")
        # kconfig 6.26.0.1 is the published fix release and injects a bare
        # DT_SONAME. kguiaddons and ki18n have no published .1 release in
        # the ohpcd registry (their 6.26.0.1 recipes exist in the main tree
        # but were never uploaded), so the pre-0002 binaries carry no
        # DT_SONAME -- patch 0002 links every consumed KF6 component by
        # exact file name, which is relocatable in both shapes.
        self.requires("kconfig/6.26.0.1")   # KF6::ConfigCore / KF6::ConfigGui
        self.requires("kguiaddons/6.26.0")  # KF6::GuiAddons (KColorUtils)
        self.requires("ki18n/6.26.0")       # KF6::I18n
        # qtbase/6.11.1.x's Qt6GuiPrivate bridge runs find_dependency(XKB);
        # without a declared package the CONFIG lookup falls back to the
        # system paths and fails when a consumer overrides qtbase.
        self.requires("libxkbcommon/1.6.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # the KDE cmake modules are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        # conan_cmakedeps_paths.cmake created manually because qtbase uses
        # cmake_find_mode=none. Every host dependency's lib/cmake goes on
        # the search path so find_package(KF6Config/KF6GuiAddons/KF6I18n/
        # libxkbcommon) and the installed-config find_dependency chains
        # resolve inside the conan cache.
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            for dep_name in ("kconfig", "kguiaddons", "ki18n", "libxkbcommon"):
                dependency = self.dependencies.get(dep_name)
                if dependency and dependency.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dependency.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dependency.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dependency.package_folder}/include")'
                    )

            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w", encoding="utf-8") as paths:
                paths.write("\n".join(lines) + "\n")

        # Qt6GuiPrivate's FindXKB starts with find_package(libxkbcommon
        # CONFIG) and falls back to these cache variables. Expose both so a
        # source rebuild under a consumer qtbase override does not depend on
        # system-wide xkbcommon headers/libraries.
        xkb = self.dependencies.get("libxkbcommon")
        if xkb:
            tc.cache_variables["XKB_INCLUDE_DIR"] = os.path.join(
                xkb.package_folder, "include"
            )
            for candidate in ("libxkbcommon.so", "libxkbcommon.a"):
                candidate_path = os.path.join(xkb.package_folder, "lib", candidate)
                if os.path.exists(candidate_path):
                    tc.cache_variables["XKB_LIBRARY"] = candidate_path
                    break

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _sdk_llvm_lib_dirs(self):
        # The OHOS SDK root is environment specific, so prefer the llvm/lib
        # directory implied by the profile's compiler and fall back to
        # globbing the installed SDK. The SDK version stays unpinned on
        # purpose (kconfig 6.26.0.1 precedent).
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        if cxx:
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(cxx))), "lib")
            )
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            )
        )
        return [c for c in dict.fromkeys(candidates) if os.path.isdir(c)]

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dependency.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dependency.package_folder, "plugins"),
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dependency.package_folder, "plugins", "platforms"),
                )
        for relative_path in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, relative_path)
            )
        return runtime_env

    def _build_environment(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in self._sdk_llvm_lib_dirs():
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM's KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure; the sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so which shadows the compatible one, so prepend
            # /system/lib64 (kconfig 6.26.0.1 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in self._sdk_llvm_lib_dirs():
                test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
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
        self._prepare_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 300'.format(self.build_folder)
            )

    def _prepare_runtime_links(self):
        # ctest runs the tests with WORKING_DIRECTORY set to the test
        # binary's directory (<build>/autotests), and a library recorded in
        # DT_NEEDED as the build-tree-relative "../../bin/..." would then
        # resolve to <build>/../bin -- next to, not inside, the build
        # folder. Stage libKF6ColorScheme.so and every dependency library
        # there (kcolorscheme 6.26.0 precedent; symlink when the filesystem
        # allows it, copy otherwise -- HMDFS denies symlinks).
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        library_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                library_sources.extend(
                    glob.glob(os.path.join(dependency.package_folder, "lib", "lib*.so*"))
                )
        for source in library_sources:
            destination = os.path.join(compatibility_bin, os.path.basename(source))
            if os.path.exists(source) and not os.path.lexists(destination):
                try:
                    os.symlink(source, destination)
                except OSError:
                    shutil.copy2(source, destination)

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
        candidates.extend(
            [
                os.path.join("/data/service/hnp/bin", name),
                os.path.join("/storage/Users/currentUser/usr/local/bin", name),
            ]
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_ohos_elf(self, path, required=True):
        signer = self._find_ohos_tool("binary-sign-tool")
        if not signer:
            if required:
                raise ConanException(
                    "Cannot locate OHOS binary-sign-tool for ELF signing"
                )
            self.output.warning(f"binary-sign-tool not found; cannot sign {path}")
            return False
        objcopy = self._find_ohos_tool("llvm-objcopy")
        if objcopy:
            self.run(
                f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                ignore_errors=True,
            )
        self.run(
            f"{self._quote(signer)} sign -inFile {self._quote(path)} "
            f"-outFile {self._quote(path)} -selfSign 1",
            ignore_errors=not required,
        )
        try:
            os.chmod(path, 0o755)
        except OSError as exc:
            self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
        return True

    def _sign_ohos_package_elfs(self):
        # CMake install rewrites the RUNPATH, which invalidates the .codesign
        # section produced during the build; the OHOS loader rejects such
        # ELFs (kcolorscheme 6.18.0.3 precedent).
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        signed = 0
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                if self._sign_ohos_elf(path):
                    signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_ohos_package_elfs()

    def package_info(self):
        # The project installs its own KF6ColorSchemeConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Gui/KF6Config). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6ColorScheme"]
