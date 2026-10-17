#!/usr/bin/env python3
"""Conan recipe — zyre 2.0.1 (cmake)

Zyre is an open-source framework for proximity-based peer-to-peer
applications over ZeroMQ: local-area discovery via UDP beacons (zbeacon),
gossip discovery, group messaging (JOIN/SHOUT) and the zyre_event API.
Pure C, depends on czmq (which pulls in zeromq).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZyreConan(ConanFile):
    name = "zyre"
    version = "2.0.1"
    description = "Zyre — proximity-based P2P messaging over ZeroMQ"
    license = "MPL-2.0"
    homepage = "https://github.com/zeromq/zyre"
    url = "https://github.com/zeromq/zyre"

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
        # Only mandatory upstream dependency (project.xml <use project="czmq"/>).
        self.requires("czmq/4.2.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ZYRE_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["ZYRE_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        # Release default is OFF; the 5 private classes (zre_msg/zyre_peer/
        # zyre_group/zyre_election/zyre_node) only build with drafts enabled.
        tc.variables["ENABLE_DRAFTS"] = "ON" if self.options.enable_drafts else "OFF"
        # zproject-generated Findlibzmq.cmake / Findczmq.cmake run in MODULE
        # mode (pkg_check_modules + bare find_path/find_library). Conan only
        # puts the generators folder on CMAKE_PREFIX_PATH, so feed the czmq
        # and zeromq package include/lib dirs explicitly. zeromq is a 2nd
        # level dep here, but zyre.h transitively includes czmq.h which
        # includes zmq.h, so the compiler must see it too.
        czmq_info = self.dependencies["czmq"].cpp_info
        zeromq_info = self.dependencies["zeromq"].cpp_info
        include_dirs = list(czmq_info.includedirs) + list(zeromq_info.includedirs)
        lib_dirs = list(czmq_info.libdirs) + list(zeromq_info.libdirs)
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
        # (libczmq.so does carry a SONAME, so czmq links fine via find_library.)
        tc.variables["LIBZMQ_LIBRARIES"] = "-L{0};-lzmq".format(zeromq_info.libdirs[0])
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
        # Upstream zproject contract: pkg-config name "libzyre"; CMake config
        # package "zyre"; exported targets "zyre" (static alias "zyre-static").
        self.cpp_info.set_property("cmake_file_name", "zyre")
        self.cpp_info.set_property("cmake_target_name", "zyre")
        self.cpp_info.set_property("cmake_target_aliases", ["zyre-static"])
        self.cpp_info.set_property("pkg_config_name", "libzyre")
        self.cpp_info.libs = ["zyre"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "rt"]
