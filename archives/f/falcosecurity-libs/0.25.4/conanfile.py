#!/usr/bin/env python3
"""Conan recipe for falcosecurity-libs 0.25.4."""

import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class FalcoSecurityLibsConan(ConanFile):
    name = "falcosecurity-libs"
    version = "0.25.4"
    description = "Core libscap and libsinsp userspace libraries for Falco and Sysdig"
    license = "Apache-2.0"
    homepage = "https://github.com/falcosecurity/libs"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="falcosecurity-libs.tar.gz", strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["FALCOSECURITY_LIBS_VERSION"] = str(self.version)
        # Bundled deps (jsoncpp/zlib/re2/tbb) are installed to lib/falcosecurity/
        # Engine libs (nodriver/source_plugin) go to lib/ alongside main libs.
        # DT_NEEDED uses build-relative paths; set RPATH via linker flags since
        # CMAKE_INSTALL_RPATH is overridden by upstream CMakeLists.txt.
        if self.settings.os == "OHOS":
            rpath = "\\$ORIGIN:\\$ORIGIN/falcosecurity"
            tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = f"-Wl,-rpath,{rpath}"
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_C_COMPILER_TARGET"] = "aarch64-linux-ohos"
            tc.cache_variables["CMAKE_CXX_COMPILER_TARGET"] = "aarch64-linux-ohos"
            # OHOS Clang defines __linux__; avoid pulling in Linux platform
            # stubs via a project-level macro rather than __OHOS__ guards.
            # NOTE: Only set cmake cache variable, NOT preprocessor definition.
            #   defined(HAS_LINUX_PLATFORM) in C++ is true when macro is defined
            #   to ANY value (including "0"), which defeats the guard in 0001 patch.
            #   The 0001 patch uses `#if defined(__linux__) && HAS_LINUX_PLATFORM`
            #   (value check), which is false when HAS_LINUX_PLATFORM is undefined.
            tc.cache_variables["HAS_LINUX_PLATFORM"] = False
        else:
            tc.cache_variables["HAS_LINUX_PLATFORM"] = True
            tc.preprocessor_definitions["HAS_LINUX_PLATFORM"] = "1"
        tc.cache_variables["USE_BUNDLED_DEPS"] = True
        tc.cache_variables["USE_BUNDLED_DRIVER"] = False
        tc.cache_variables["MUSL_OPTIMIZED_BUILD"] = self.settings.os == "OHOS"
        tc.cache_variables["BUILD_SHARED_LIBS"] = True
        tc.cache_variables["CREATE_TEST_TARGETS"] = False
        tc.cache_variables["ENABLE_E2E_TESTS"] = False
        tc.cache_variables["ENABLE_DRIVERS_TESTS"] = False
        tc.cache_variables["ENABLE_LIBSCAP_TESTS"] = False
        tc.cache_variables["ENABLE_LIBSCAP_FUZZERS"] = False
        tc.cache_variables["ENABLE_LIBSCAP_FUZZ_TOOLS"] = False
        tc.cache_variables["ENABLE_LIBSINSP_E2E_TESTS"] = False
        tc.cache_variables["ENABLE_BENCHMARKS"] = False
        tc.cache_variables["BUILD_LIBSCAP_EXAMPLES"] = False
        tc.cache_variables["BUILD_LIBSINSP_EXAMPLES"] = False
        tc.cache_variables["BUILD_LIBSCAP_MODERN_BPF"] = False
        tc.cache_variables["ENABLE_ENGINE_KMOD"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # DT_NEEDED in built shared libs uses build-relative paths
        # (e.g. ../jsoncpp-prefix/src/lib/libjsoncpp.so). Fix by converting
        # all path-based DT_NEEDED to SONAME-only references, then setting
        # RUNPATH so the dynamic linker finds them by SONAME.
        lib_dir = os.path.join(self.package_folder, "lib")
        bundled_dir = os.path.join(lib_dir, "falcosecurity")
        known_sos = set()
        for so in glob.glob(os.path.join(lib_dir, "*.so")) + glob.glob(os.path.join(lib_dir, "*.so.*")):
            known_sos.add(os.path.basename(so))
        for so in glob.glob(os.path.join(bundled_dir, "*.so")) + glob.glob(os.path.join(bundled_dir, "*.so.*")):
            known_sos.add(os.path.basename(so))
        for so_file in glob.glob(os.path.join(lib_dir, "*.so")) + glob.glob(os.path.join(lib_dir, "*.so.*")):
            if os.path.islink(so_file):
                continue
            try:
                needed_str = subprocess.check_output("patchelf --print-needed " + so_file, shell=True, text=True)
            except subprocess.CalledProcessError:
                needed_str = ""
            for dep in needed_str.strip().split("\n"):
                dep = dep.strip()
                if not dep:
                    continue
                dep_basename = os.path.basename(dep)
                if dep != dep_basename and dep_basename in known_sos:
                    self.run("patchelf --remove-needed '" + dep + "' " + so_file)
                    self.run("patchelf --add-needed '" + dep_basename + "' " + so_file)
            self.run("patchelf --set-rpath '$ORIGIN:$ORIGIN/falcosecurity' " + so_file)
        for so_file in glob.glob(os.path.join(bundled_dir, "*.so")) + glob.glob(os.path.join(bundled_dir, "*.so.*")):
            if os.path.islink(so_file):
                continue
            self.run("patchelf --set-rpath '$ORIGIN' " + so_file)
        scap_error_a = os.path.join(self.build_folder, "build", "Release", "libscap", "libscap_error.a")
        scap_event = os.path.join(lib_dir, "libscap_event_schema.so")
        if os.path.exists(scap_error_a) and os.path.exists(scap_event):
            fix_so = os.path.join(lib_dir, "libscap_error_fix.so")
            if not os.path.exists(fix_so):
                self.run("ar x " + scap_error_a + " strerror.c.obj", cwd=lib_dir)
                cc = os.environ.get("CC", "clang")
                self.run(cc + " -shared -fPIC -o libscap_error_fix.so strerror.c.obj", cwd=lib_dir)
                os.unlink(os.path.join(lib_dir, "strerror.c.obj"))
            self.run("patchelf --set-rpath '$ORIGIN' " + fix_so)
            self.run("patchelf --add-needed 'libscap_error_fix.so' " + scap_event)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "falcosecurity-libs")
        self.cpp_info.set_property("cmake_target_name", "falcosecurity-libs::falcosecurity-libs")
        self.cpp_info.includedirs = ["include/falcosecurity"]
        self.cpp_info.libdirs = ["lib", "lib/falcosecurity"]
        self.cpp_info.libs = ["sinsp", "scap", "scap_event_schema"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
