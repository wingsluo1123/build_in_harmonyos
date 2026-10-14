#!/usr/bin/env python3
"""Conan recipe — czmq 4.2.1 (cmake)

CZMQ is the high-level C binding for ZeroMQ: convenience classes
(zsock/zframe/zmsg/zstr), zactor services (zauth/zbeacon/zgossip/zmonitor/
zproxy), data structures (zhashx/zlistx/ztrie) and the zmakecert CLI tool.
Pure C, depends on zeromq (libzmq).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CzmqConan(ConanFile):
    name = "czmq"
    version = "4.2.1"
    description = "CZMQ — the high-level C binding for ZeroMQ"
    license = "MPL-2.0"
    homepage = "https://github.com/zeromq/czmq"
    url = "https://github.com/zeromq/czmq"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_drafts": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "enable_drafts": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # Only mandatory upstream dependency (project.xml <use project="libzmq"/>).
        self.requires("zeromq/4.3.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CZMQ_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["CZMQ_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        # Release default is OFF; keep it explicit (zyre 2.0.1 only consumes
        # stable classes, no CZMQ_BUILD_DRAFT_API needed).
        tc.variables["ENABLE_DRAFTS"] = "ON" if self.options.enable_drafts else "OFF"
        # Optional deps: upstream options default to ${X_FOUND} which drifts
        # with the host environment; disable all six explicitly for a
        # deterministic feature set (none is mandatory in project.xml).
        tc.variables["CZMQ_WITH_UUID"] = False
        tc.variables["CZMQ_WITH_SYSTEMD"] = False
        tc.variables["CZMQ_WITH_LZ4"] = False
        tc.variables["CZMQ_WITH_LIBCURL"] = False
        tc.variables["CZMQ_WITH_NSS"] = False
        tc.variables["CZMQ_WITH_LIBMICROHTTPD"] = False
        # zproject-generated Findlibzmq.cmake runs in MODULE mode
        # (pkg_check_modules + bare find_path/find_library). Conan only puts
        # the generators folder on CMAKE_PREFIX_PATH, so feed the zeromq
        # package include/lib dirs explicitly.
        include_dirs = []
        lib_dirs = []
        zeromq_info = self.dependencies["zeromq"].cpp_info
        include_dirs += zeromq_info.includedirs
        lib_dirs += zeromq_info.libdirs
        tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(include_dirs)
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_dirs)
        # OHOS is a CMake-unknown platform (no Platform/HarmonyOS module), so
        # CMake drops DT_SONAME and versioned names entirely. Per house
        # knowledge E330: keep an ELF SONAME without versioned symlinks
        # (HMDFS-backed paths reject symlink creation).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # Link libzmq by -L/-l so the linker records a relative DT_NEEDED
        # ("libzmq.so") instead of the Conan cache absolute path: the
        # published zeromq binary carries no SONAME for the linker to use.
        tc.variables["LIBZMQ_LIBRARIES"] = "-L{0};-lzmq".format(lib_dirs[0])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os in ("Linux", "OHOS"):
            self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = shutil.which("llvm-objcopy") or "llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # Upstream zproject contract, consumed by zyre 2.0.1 Findczmq.cmake:
        #   pkg-config name must be "libczmq"; CMake config package "czmq";
        #   exported targets "czmq" (static alias "czmq-static").
        self.cpp_info.set_property("cmake_file_name", "czmq")
        self.cpp_info.set_property("cmake_target_name", "czmq")
        self.cpp_info.set_property("cmake_target_aliases", ["czmq-static"])
        self.cpp_info.set_property("pkg_config_name", "libczmq")
        self.cpp_info.libs = ["czmq"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "rt"]
