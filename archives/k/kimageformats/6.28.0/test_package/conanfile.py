#!/usr/bin/env python3
"""Conan test_package for kimageformats 6.28.0.

Verifies the packaged QImageIOHandler plugin set and drives the plugin chain
end-to-end through Qt: the executor in test_kimageformats.cpp runs 8 cases
(plugin advertisement, HDR/TGA/QOI/DDS decodes, EXR/JP2 write-read
roundtrips and the package layout) with per-case TEST PASS/FAIL lines, a
final TEST SUMMARY and a non-zero exit code on any failure.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KImageFormatsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if pkg:
            tc.variables["KIMAGEFORMATS_ROOT"] = os.fspath(pkg.package_folder)
            # Reflect the tested package's option set so the consumer checks
            # exactly the plugins that were built.
            for fmt, opt in (
                ("DDS", "with_dds"),
                ("OPENEXR", "with_openexr"),
                ("LIBRAW", "with_libraw"),
                ("OPENJPEG", "with_openjpeg"),
                ("LIBAVIF", "with_libavif"),
            ):
                tc.variables[f"KIMAGEFORMATS_EXPECT_{fmt}"] = (
                    "ON" if pkg.options.get_safe(opt) else "OFF"
                )
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        lines = []
        if qtbase:
            qt_pkg = os.fspath(qtbase.package_folder).replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
        # SDK's llvm/lib directory; CI workers may not export it via
        # LD_LIBRARY_PATH. Prepend every found SDK llvm lib dir so CMake's
        # TryCompile can link. Must not clobber conanbuild env on other hosts.
        env = Environment()
        for sdk_llvm_lib in sorted(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
            )
        ):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if cross_building(self):
            # The OHOS consumer cannot execute on a cross-building host: the
            # platform CI only proves that it links; the native device run is
            # what exercises the packaged plugins.
            self.output.info(
                "Cross build: consumer linked only; native device run still required"
            )
            return
        # E298: do not delegate to CTest — the child process would miss the
        # runtime search path. Run the consumer directly with the dependency
        # lib/plugin directories injected (Environment.prepend_path, not
        # append: the default separator is a blank space).
        env = Environment()
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
            )
            env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
            )
            env.prepend_path(
                "QT_PLUGIN_PATH",
                os.path.join(dep.package_folder, "lib", "plugins"),
            )
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kimageformats")
            )
