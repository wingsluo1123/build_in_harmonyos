#!/usr/bin/env python3
"""Conan recipe for wireguard-tools 1.0.20260223

WireGuard userspace tools — provides the `wg` command-line binary
and `wg-quick` wrapper script for managing WireGuard VPN interfaces.

Build system: plain Makefile (no configure script).
License: GPL-2.0
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class WireguardToolsConan(ConanFile):
    name = "wireguard-tools"
    version = "1.0.20260223"
    description = "WireGuard userspace tools — wg and wg-quick"
    license = "GPL-2.0"
    homepage = "https://www.wireguard.com/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: Platform check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: All flags from Conan toolchain, no shell env vars
        tc = AutotoolsToolchain(self)
        # OHOS compat: prevent sockaddr_storage redefinition conflict
        # between sys/socket.h and linux/socket.h
        tc.extra_cflags.append("-include")
        tc.extra_cflags.append("ohos_compat.h")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        src_dir = os.path.join(self.build_folder, "src")

        # Create OHOS compatibility header
        # Fixes sockaddr_storage redefinition between sys/socket.h (bionic)
        # and linux/socket.h (kernel UAPI) on HarmonyOS
        compat_h = (
            "#ifndef _OHOS_COMPAT_H\n"
            "#define _OHOS_COMPAT_H\n"
            "/* Prevent linux/socket.h from redefining sockaddr_storage */\n"
            "#define _UAPI_LINUX_SOCKET_H\n"
            "/* Provide __kernel_sa_family_t that linux/netlink.h needs */\n"
            "typedef unsigned short __kernel_sa_family_t;\n"
            "#endif\n"
        )
        save(self, os.path.join(src_dir, "ohos_compat.h"), compat_h)

        # Create uapi/harmonyos symlink to uapi/linux
        # So Makefile's uapi/$(PLATFORM)/ check finds wireguard.h
        uapi_harmonyos = os.path.join(src_dir, "uapi", "harmonyos")
        if not os.path.exists(uapi_harmonyos):
            os.symlink("linux", uapi_harmonyos)

        # Build: plain Makefile, no configure step
        # R33: CC, CFLAGS from AutotoolsToolchain (conan_toolchain.sh)
        # PLATFORM=linux: use uapi/linux headers and wg-quick/linux.bash
        # WITH_WGQUICK=yes: install wg-quick script
        # WITH_BASHCOMPLETION=no: skip bash completion (not standard on OHOS)
        # WITH_SYSTEMDUNITS=no: skip systemd units (not available on OHOS)
        self.run(
            "make -C src V=1 -j1 "
            "PLATFORM=linux "
            "WITH_WGQUICK=yes "
            "WITH_BASHCOMPLETION=no "
            "WITH_SYSTEMDUNITS=no"
        )

    def package(self):
        src_dir = os.path.join(self.build_folder, "src")
        # Install wg binary
        copy(self, "wg", src=src_dir, dst=os.path.join(self.package_folder, "bin"))
        # Install wg-quick script (from wg-quick/linux.bash)
        copy(self, "linux.bash", src=os.path.join(src_dir, "wg-quick"),
             dst=os.path.join(self.package_folder, "bin"))
        os.rename(
            os.path.join(self.package_folder, "bin", "linux.bash"),
            os.path.join(self.package_folder, "bin", "wg-quick")
        )
        # Install man pages
        copy(self, "wg.8", src=os.path.join(src_dir, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "wg-quick.8", src=os.path.join(src_dir, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))

        # ELF signing (HarmonyOS requires ELF signature for execution)
        bin_path = os.path.join(self.package_folder, "bin", "wg")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool) and os.path.exists(objcopy):
            # Remove old signature if present
            subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                           capture_output=True, timeout=10)
            # Sign with self-signed certificate
            tmp = bin_path + ".signed.tmp"
            for _attempt in range(3):
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", bin_path,
                     "-outFile", tmp, "-selfSign", "1"],
                    capture_output=True, timeout=30)
                if r.returncode == 0 and os.path.exists(tmp):
                    shutil.move(tmp, bin_path)
                    break
                import time; time.sleep(1)
            else:
                if os.path.exists(tmp):
                    os.remove(tmp)
                raise ConanException(
                    f"ELF signing failed after 3 attempts for {bin_path}. "
                    f"Binary will not be executable on HarmonyOS."
                )
            os.chmod(bin_path, 0o755)

            # Also sign wg-quick (it's a script, just ensure executable)
            os.chmod(os.path.join(self.package_folder, "bin", "wg-quick"), 0o755)

    def package_info(self):
        # wireguard-tools is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
