#!/usr/bin/env python3
"""Conan recipe for kimageformats 6.28.0 on HarmonyOS PC.

kimageformats is the KDE Frameworks 6 image format plugins collection for Qt:
it provides QImageIOHandler plugins for formats the stock Qt build does not
ship (ANI, DDS, EXR, FF, HDR, IFF, PCX, PFM, PIC, PSD, PXR, QOI, RAS, RGB,
SCT, TGA, TIM, XCF, JP2, AVIF, RAW).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list).
  - ECM_MODULE_PATH is set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's top-level
    CMakeLists.txt concatenates into CMAKE_MODULE_PATH.
  - conan_cmakedeps_paths.cmake is created manually because qtbase uses
    cmake_find_mode=none, so CMakeDeps does not add its lib/cmake folder to
    CMAKE_PREFIX_PATH. CMAKE_FIND_PACKAGE_PREFER_CONFIG is deliberately NOT
    set: the LibRaw find must run through the repository's own
    cmake/find-modules/FindLibRaw.cmake module (the conan libraw-config.cmake
    defines libraw::libraw but not the LibRaw::LibRaw target the RAW plugin
    links against).
  - OpenJPEG: upstream reads the uppercase OPENJPEG_INCLUDE_DIRS /
    OPENJPEG_LIBRARIES variables (and the OPENJPEG_{MAJOR,MINOR,BUILD}_
    VERSION triple used by the JPEG 2000 write-test gate), which the
    CMakeDeps-generated config does not set; the openjpeg package folder is
    prepended to CMAKE_PREFIX_PATH so the package's own OpenJPEGConfig.cmake
    wins the CONFIG lookup, with toolchain value fallbacks.
  - Imath: the CMakeDeps-generated Imath::Imath only carries the include
    root, while exr.cpp includes <ImathBox.h> flat; the imath package's own
    config (prepended to CMAKE_PREFIX_PATH) exports include/ and
    include/Imath on Imath::Imath.
  - libavif: upstream links the AVIF plugin against a target literally named
    "avif"; a small config shim around the CMakeDeps libavif package creates
    that alias target.
  - SONAME-only shared library rules so install() stays a byte-identical copy
    (see _configure_ohos_shared_library_rules).
  - Upstream CTest runs on the target device (BUILD_TESTING=ON); tests scoped
    to environment limitations are excluded (see _CTEST_EXCLUDE).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class KImageFormatsConan(ConanFile):
    name = "kimageformats"
    version = "6.28.0"
    description = ("KDE Frameworks 6 image format plugins for Qt "
                   "(QImageIOHandler plugins)")
    license = "BSD-2-Clause AND LGPL-2.1-or-later AND MIT"
    homepage = "https://invent.kde.org/frameworks/kimageformats"
    url = "https://download.kde.org/stable/frameworks/6.28/kimageformats-6.28.0.tar.xz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_dds": [True, False],
        "with_openexr": [True, False],
        "with_libraw": [True, False],
        "with_openjpeg": [True, False],
        "with_libavif": [True, False],
    }
    default_options = {
        "shared": True,
        "with_dds": True,
        "with_openexr": True,
        "with_libraw": True,
        "with_openjpeg": True,
        "with_libavif": True,
    }

    # CTest items excluded from the device run. Each entry is an environment
    # limitation rather than a plugin defect; the manual re-runs of the
    # excluded tests and their exact failure lines are recorded in notes.md.
    # read-psd / read-exr are deliberately NOT excluded: upstream 6.28
    # downgrades the missing-TIF comparison cases and the sequential-device
    # passes of a seek-based handler to SKIP entries, so both tests pass
    # (90/40/0 and 7/3/0 passed/skipped/failed on device).
    _CTEST_EXCLUDE = (
        "kimageformats-write-avif"    # libavif is a decoder-only build (no AV1 encoder)
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        if self.options.with_openexr:
            self.requires("openexr/3.3.4")
        if self.options.with_libraw:
            self.requires("libraw/0.22.1")
        if self.options.with_openjpeg:
            self.requires("openjpeg/2.5.4")
        if self.options.with_libavif:
            self.requires("libavif/1.4.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.28.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kimageformats supports Linux and OHOS, got "
                f"{self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        # Plugin gates: enable only the format set whose backing libraries
        # resolve on OHOS (per-format decision table in notes.md). The EPS
        # plugin is naturally off: CMAKE_SYSTEM_NAME=HarmonyOS makes UNIX
        # false and the published qtbase ships no Qt6::PrintSupport.
        tc.variables["KIMAGEFORMATS_DDS"] = "ON" if self.options.with_dds else "OFF"
        tc.variables["KIMAGEFORMATS_HEIF"] = "OFF"
        tc.variables["KIMAGEFORMATS_JXL"] = "OFF"
        tc.variables["KIMAGEFORMATS_WITH_KNOWN_CRASHES_JXR"] = "OFF"
        tc.variables["KIMAGEFORMATS_JP2"] = (
            "ON" if self.options.with_openjpeg else "OFF"
        )
        if not self.options.with_openexr:
            tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenEXR"] = "ON"
        if not self.options.with_libraw:
            tc.variables["CMAKE_DISABLE_FIND_PACKAGE_LibRaw"] = "ON"
        if not self.options.with_libavif:
            # Upstream gates the AVIF plugin purely on find_package(libavif)
            # succeeding, with no option of its own; disable the package
            # search itself.
            tc.variables["CMAKE_DISABLE_FIND_PACKAGE_libavif"] = "ON"
        # KF6Archive (KRA/ORA plugins) is requested at exactly 6.28.0
        # (KF_DEP_VERSION); the registry only publishes karchive/6.26.0, so
        # the archive plugins stay off.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6Archive"] = "ON"

        # Plugin install location: <package>/plugins/imageformats.
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["KDE_INSTALL_QTPLUGINDIR"] = "plugins"
        tc.variables["KDE_INSTALL_PLUGINDIR"] = "lib/plugins"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # FindLibRaw is a plain find_path/find_library module in the
        # repository's cmake/find-modules; it reads the plural
        # LibRaw_LIBRARIES / LibRaw_r_LIBRARIES variables (and creates the
        # LibRaw::LibRaw imported target from them). Pre-set the cache values
        # so the module resolves deterministically.
        if self.options.with_libraw:
            libraw = self.dependencies.get("libraw")
            if libraw:
                libraw_pkg = self._cmake_path(libraw.package_folder)
                tc.variables["LibRaw_INCLUDE_DIR"] = f"{libraw_pkg}/include"
                tc.variables["LibRaw_LIBRARIES"] = f"{libraw_pkg}/lib/libraw.so"
                tc.variables["LibRaw_r_LIBRARIES"] = f"{libraw_pkg}/lib/libraw_r.so"

        # The JPEG 2000 write-test gate compares
        # OPENJPEG_MAJOR_VERSION.OPENJPEG_MINOR_VERSION.OPENJPEG_BUILD_VERSION
        # against 2.5.3, and src/imageformats/CMakeLists.txt consumes
        # OPENJPEG_INCLUDE_DIRS / OPENJPEG_LIBRARIES; the CMakeDeps-generated
        # config sets only the mixed-case OpenJPEG_* variables. The
        # openjpeg package folder is prepended below so the package's own
        # OpenJPEGConfig.cmake wins the lookup; these toolchain values are
        # the fallback if that lookup ever flips (values from
        # openjpeg/2.5.4).
        if self.options.with_openjpeg:
            tc.variables["OPENJPEG_MAJOR_VERSION"] = "2"
            tc.variables["OPENJPEG_MINOR_VERSION"] = "5"
            tc.variables["OPENJPEG_BUILD_VERSION"] = "4"
            openjpeg = self.dependencies.get("openjpeg")
            if openjpeg:
                openjpeg_pkg = self._cmake_path(openjpeg.package_folder)
                tc.variables["OPENJPEG_INCLUDE_DIRS"] = (
                    f"{openjpeg_pkg}/include/openjpeg-2.5"
                )
                tc.variables["OPENJPEG_LIBRARIES"] = (
                    f"{openjpeg_pkg}/lib/libopenjp2.so"
                )

        lines = []
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = self._cmake_path(qtbase.package_folder)
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        if ecm:
            ecm_pkg = self._cmake_path(ecm.package_folder)
            ecm_cmake = f"{ecm_pkg}/share/ECM/cmake"
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        # OpenEXR's config performs find_dependency(Imath); keep OpenEXR and
        # its transitive package folders on the prefix path so the chain
        # resolves even outside the generators directory.
        openexr = self.dependencies.get("openexr")
        if openexr:
            openexr_pkg = self._cmake_path(openexr.package_folder)
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{openexr_pkg}")')
            for req in openexr.dependencies.items():
                req_info = req[1] if isinstance(req, tuple) else req
                req_folder = getattr(req_info, "package_folder", None)
                if req_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{self._cmake_path(req_folder)}")'
                    )
        # libavif: upstream links the plugin against a target literally named
        # "avif". CMakeDeps only defines libavif::libavif, so a two-file shim
        # (config + version) provides the "avif" alias; the shim directory is
        # prepended last so it is searched first and both upstream
        # find_package(libavif ...) calls resolve through it.
        if self.options.with_libavif:
            shim_dir = os.path.join(self.generators_folder, "kif-shims")
            os.makedirs(shim_dir, exist_ok=True)
            save(self, os.path.join(shim_dir, "libavif-config.cmake"), "\n".join([
                "# Compatibility shim in front of the generated libavif config:",
                "# upstream links the AVIF plugin against a target literally",
                '# named "avif", which the generated config does not provide',
                "# (it defines libavif::libavif only).",
                'set(_kif_libavif_real "")',
                'foreach(_kif_cand "libavif-config.cmake" "libavifConfig.cmake")',
                '    if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/../${_kif_cand}")',
                '        set(_kif_libavif_real "${CMAKE_CURRENT_LIST_DIR}/../${_kif_cand}")',
                '    endif()',
                'endforeach()',
                'if(NOT _kif_libavif_real)',
                '    message(FATAL_ERROR "kif-shims: generated libavif config not found next to the shim")',
                'endif()',
                'include("${_kif_libavif_real}")',
                "if(NOT TARGET avif AND TARGET libavif::libavif)",
                "    add_library(avif INTERFACE IMPORTED GLOBAL)",
                "    set_target_properties(avif PROPERTIES",
                "        INTERFACE_LINK_LIBRARIES libavif::libavif)",
                "endif()",
            ]) + "\n")
            save(self, os.path.join(shim_dir, "libavif-config-version.cmake"),
                 "\n".join([
                     'set(PACKAGE_VERSION "1.4.2.2")',
                     "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)",
                     "    set(PACKAGE_VERSION_COMPATIBLE FALSE)",
                     "else()",
                     "    set(PACKAGE_VERSION_COMPATIBLE TRUE)",
                     "    if(PACKAGE_VERSION STREQUAL PACKAGE_FIND_VERSION)",
                     "        set(PACKAGE_VERSION_EXACT TRUE)",
                     "    endif()",
                     "endif()",
                 ]) + "\n")
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        if self.options.with_libavif:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{self._cmake_path(shim_dir)}")'
            )
        # The openjpeg and imath package folders go in front of the
        # generators folder so their own CMake configs win:
        # - OpenJPEGConfig.cmake (package) defines the openjp2 target and
        #   the uppercase OPENJPEG_INCLUDE_DIRS / OPENJPEG_LIBRARIES /
        #   OPENJPEG_*_VERSION variables that upstream consumes; the
        #   CMakeDeps-generated config only sets the mixed-case names.
        # - ImathConfig.cmake (package) exports include/ and include/Imath
        #   on Imath::Imath; the generated config only carries the root,
        #   and exr.cpp includes <ImathBox.h> flat.
        for package_name in ("openjpeg", "imath"):
            dep = self.dependencies.get(package_name)
            if dep:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{self._cmake_path(dep.package_folder)}")'
                )
        # CMAKE_FIND_PACKAGE_PREFER_CONFIG is intentionally left unset so the
        # LibRaw find runs in module mode (see the module note above).
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

        # CMakeDeps generates the dependency CMake config files
        # (OpenEXRConfig, OpenJPEGConfig, libavif-config, plus the
        # Imath/libdeflate/dav1d dependency chains) into the generators
        # directory; the toolchain includes the conan_cmakedeps_paths.cmake
        # file written above, and the kif-shims/ libavif config forwards to
        # the generated libavif-config.cmake.
        deps = CMakeDeps(self)
        deps.generate()

    @staticmethod
    def _cmake_path(path):
        return os.fspath(path).replace("\\", "/")

    def _configure_ohos_shared_library_rules(self, toolchain):
        """SONAME-only shared library rules (kitemviews 6.28.0 precedent,
        kirigami 6.18.0 origin): OHOS CMake ships no Platform/HarmonyOS
        module, so CMAKE_SHARED_LIBRARY_SONAME_* stays unset and lld emits no
        DT_SONAME, which would leak build-machine paths into consumer
        DT_NEEDED entries. HMDFS also rejects symlink(2), so
        CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE keeps the unversioned DT_SONAME
        and drops the versioned-symlink chain. The CMAKE_SHARED_LIBRARY_RUNTIME_
        (rpath) flags are deliberately NOT defined: with them defined cmake
        install() rewrites the ELF to strip the RUNPATH and the device loader
        then rejects the rewritten library on dlopen (EACCES)."""
        rules = os.path.join(
            self.generators_folder, "ohos-shared-library-rules.cmake"
        )
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
            )) + "\n",
        )
        toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if can_run(self):
            self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # ECM's KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt); prepend the SDK llvm lib dir (lld's
            # libxml2 dependency) and /system/lib64 so the compatible
            # libc++_shared.so resolves before the incompatible sandbox copy
            # under /data/storage/el1/bundle (kconfig 6.26.0 / kitemviews
            # 6.28.0 precedent).
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
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
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        # The upstream readtest/writetest binaries load the plugins from the
        # build tree's bin directory (PLUGIN_DIR baked in autotests/); this is
        # the belt-and-braces copy for Qt's own plugin search.
        test_env.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.build_folder, "bin")
        )
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
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '-E "{}"'.format(self.build_folder, self._CTEST_EXCLUDE)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("pkg_config_name", "kimageformats")
        # Pure plugin package (R38): no linker libraries and no executables;
        # Qt loads the QImageIOHandler plugins from
        # <package_folder>/plugins/imageformats at runtime.
        self.cpp_info.libdirs = ["lib", "plugins/imageformats"]
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property(
            "user_info:plugin_dir", "plugins/imageformats"
        )
