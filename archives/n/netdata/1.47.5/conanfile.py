#!/usr/bin/env python3
"""Conan recipe for netdata 1.47.5 — real-time system monitoring tool.

netdata is a system monitoring daemon that provides real-time metrics
for CPU, memory, disk, network, and more via a built-in web dashboard.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
import os


def _create_pc_alias(gen_dir, source_pc, target_pc, source_name, target_name):
    """Create a pkg-config alias file (e.g., yaml-0.1.pc from libyaml.pc)."""
    import os
    src = os.path.join(gen_dir, source_pc)
    dst = os.path.join(gen_dir, target_pc)
    if os.path.exists(src) and not os.path.exists(dst):
        with open(src) as f:
            content = f.read()
        content = content.replace(f"Name: {source_name}", f"Name: {target_name}")
        with open(dst, 'w') as f:
            f.write(content)


class NetdataConan(ConanFile):
    name = "netdata"
    version = "1.47.5"
    description = "Real-time system monitoring tool with built-in web dashboard"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/netdata/netdata"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")
        self.requires("lz4/1.10.0")
        self.requires("libuv/1.52.1")
        self.requires("json-c/0.18")
        self.requires("libyaml/0.2.5")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # netdata tarball has a './' entry at root which breaks strip_root=True
        get(self, **self.conan_data["sources"], strip_root=False)
        src_dir = "netdata-v1.47.5"
        if os.path.isdir(src_dir):
            for item in os.listdir(src_dir):
                src = os.path.join(src_dir, item)
                dst = os.path.join(".", item)
                if os.path.exists(dst):
                    continue
                os.rename(src, dst)
            os.rmdir(src_dir)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["OS_OHOS"] = "True"
        tc.variables["ENABLE_ACLK"] = "False"
        tc.variables["ENABLE_CLOUD"] = "False"
        tc.variables["ENABLE_ML"] = "False"
        tc.variables["ENABLE_PLUGIN_EBPF"] = "False"
        tc.variables["ENABLE_PLUGIN_GO"] = "False"
        tc.variables["ENABLE_PLUGIN_FREEIPMI"] = "False"
        tc.variables["ENABLE_PLUGIN_CUPS"] = "False"
        tc.variables["ENABLE_PLUGIN_SYSTEMD_JOURNAL"] = "False"
        tc.variables["ENABLE_PLUGIN_XENSTAT"] = "False"
        tc.variables["ENABLE_PLUGIN_NFACCT"] = "False"
        tc.variables["ENABLE_PLUGIN_APPS"] = "False"
        tc.variables["ENABLE_PLUGIN_DEBUGFS"] = "False"
        tc.variables["ENABLE_PLUGIN_LOCAL_LISTENERS"] = "False"
        tc.variables["ENABLE_PLUGIN_NETWORK_VIEWER"] = "False"
        tc.variables["ENABLE_EXPORTER_MONGODB"] = "False"
        tc.variables["ENABLE_EXPORTER_PROMETHEUS_REMOTE_WRITE"] = "False"
        tc.variables["ENABLE_WEBRTC"] = "False"
        tc.variables["ENABLE_SENTRY"] = "False"
        tc.variables["ENABLE_H2O"] = "False"
        tc.variables["USE_MOLD"] = "False"
        tc.generate()
        # Generate pkg-config files for dependencies (netdata uses pkg_check_modules)
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # Create yaml-0.1.pc (netdata looks for yaml-0.1, but conan generates libyaml.pc)
        import os
        gen_dir = self.generators_folder
        _create_pc_alias(gen_dir, "libyaml.pc", "yaml-0.1.pc", "libyaml", "yaml-0.1")
        # Create libcrypto.pc (netdata looks for libcrypto, but conan generates openssl.pc)
        _create_pc_alias(gen_dir, "openssl.pc", "libcrypto.pc", "openssl", "libcrypto")
        # Create libuv.pc (static build generates libuv-static.pc)
        _create_pc_alias(gen_dir, "libuv-static.pc", "libuv.pc", "libuv-static", "libuv")
        # Create liblz4.pc (conan lz4 package may generate lz4.pc instead of liblz4.pc)
        _create_pc_alias(gen_dir, "lz4.pc", "liblz4.pc", "lz4", "liblz4")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin", "libexec/netdata/plugins.d"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
