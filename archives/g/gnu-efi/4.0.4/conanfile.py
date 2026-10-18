#!/usr/bin/env python3
"""Conan recipe for gnu-efi 4.0.4 (upstream raw Makefile build).

gnu-efi is the EFI development toolkit: it packages the UEFI Boot/Runtime
Services wrappers (libefi.a), the GNU-EFI runtime helper library
(libgnuefi.a), the aarch64 EFI entry stub (crt0-efi-aarch64.o) and the
linker script (elf_aarch64_efi.lds) that `objcopy`-based consumers such as
efibootmgr need in order to turn an ELF image into a PE32+ EFI binary.

The upstream build system is a hand-written Makefile, not Autotools/CMake,
so the compiler and the binutils are not taken from a Conan toolchain file:
they must be passed to `make` on the command line (see build()/package()).
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GnuEfiConan(ConanFile):
    name = "gnu-efi"
    version = "4.0.4"
    description = ("EFI development toolkit: UEFI Boot/Runtime Services wrappers, "
                   "GNU-EFI runtime library and the ELF-to-PE32+ (efi-app) helpers")
    license = "GPL-2.0-or-later OR BSD-3-Clause"
    homepage = "https://github.com/ncroxon/gnu-efi"
    url = "https://github.com/ncroxon/gnu-efi"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    # gnu-efi builds freestanding aarch64 EFI images only; the target arch is
    # fixed by the vendor branch it is compiled on.
    efi_arch = "aarch64"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Upstream Makefile builds in-tree, so build() must run in the source tree.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    # ── toolchain discovery ────────────────────────────────────────────────
    @staticmethod
    def _tool(name, *fallbacks):
        """Resolve a build tool from PATH, never from an undefined shell var (R33)."""
        for candidate in (name,) + fallbacks:
            found = shutil.which(candidate)
            if found:
                return found
        return name

    def _make_vars(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return {
            "ARCH": self.efi_arch,
            # The in-tree `VERSION` variable lags the release tag (Makefile says
            # 4.0.3 while this package is 4.0.4) and is only consumed by the
            # gnuefi/gnu-efi.pc generator, so pin it to the real release version
            # from the command line instead of shipping a mismatched .pc.
            "VERSION": self.version,
            "CC": compilers.get("c") or self._tool("clang", "gcc"),
            "HOSTCC": self._tool("clang", "gcc"),
            "AS": compilers.get("c") or self._tool("clang", "as"),
            "LD": self._tool("ld.lld", "ld"),
            "AR": self._tool("llvm-ar", "ar"),
            "RANLIB": self._tool("llvm-ranlib", "ranlib"),
            # GNU objcopy is required: it understands `-O efi-app-aarch64`.
            "OBJCOPY": self._tool("objcopy", "llvm-objcopy"),
            # OpenHarmony ships no `install(1)`; GNU coreutils provides `ginstall`.
            "INSTALL": self._install_tool(),
        }

    INSTALL_SHIM = """#!/bin/sh
# Minimal install(1) shim: gnu-efi only uses `install -d DIR` and
# `install -m MODE SRC [SRC...] DST`.
mode=644
directory=0
while [ $# -gt 0 ]; do
    case "$1" in
        -d|--directory) directory=1; shift ;;
        -m) mode="$2"; shift 2 ;;
        -o|-g|-t) shift 2 ;;
        -*) shift ;;
        *) break ;;
    esac
done
[ $# -eq 0 ] && exit 0
last=""
for arg in "$@"; do last="$arg"; done
if [ "$directory" = 1 ]; then
    mkdir -p "$last"
    exit $?
fi
for arg in "$@"; do
    [ "$arg" = "$last" ] && continue
    cp -f "$arg" "$last" 2>/dev/null || cp -f "$arg" "$last"/
    chmod "$mode" "$last/$(basename "$arg")" 2>/dev/null || chmod "$mode" "$last"
done
exit 0
"""

    def _install_tool(self):
        """Resolve a usable `install`, falling back to a local POSIX shim."""
        for candidate in ("ginstall", "install"):
            found = shutil.which(candidate)
            if found:
                return found
        shim = os.path.join(self.generators_folder, "gnuefi-install-shim.sh")
        with open(shim, "w", encoding="utf-8") as handle:
            handle.write(self.INSTALL_SHIM)
        os.chmod(shim, 0o755)
        return shim

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("gnu-efi is built with a POSIX Makefile (got os=%s)" % self.settings.os)
        jobs = self.conf.get("tools.build:jobs", default=4)
        make_vars = self._make_vars()
        # `make` also generates gnuefi/gnu-efi.pc from the in-tree VERSION variable.
        args = " ".join('%s="%s"' % (k, v) for k, v in make_vars.items())
        self.run("make -j%s %s" % (jobs, args))

    def package(self):
        make_vars = self._make_vars()
        # Upstream ignores DESTDIR semantics for its two-level layout: it installs
        # under $(INSTALLROOT)$(LIBDIR) / $(INSTALLROOT)$(INCLUDEDIR) while LIBDIR and
        # INCLUDEDIR are rooted at the hard-coded PREFIX (/usr/local).  Passing
        # INSTALLROOT alone would land everything in <package>/usr/local/..., so the
        # root prefix is emptied at the same time.
        args = " ".join('%s="%s"' % (k, v) for k, v in make_vars.items())
        self.run('make install INSTALLROOT="%s" PREFIX=/ %s' % (self.package_folder, args))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._relocate_pc()

    def _relocate_pc(self):
        """Make the installed gnu-efi.pc relocatable.

        gnuefi/gnu-efi.pc is generated during `make` (the install target does not
        depend on it), so it carries the build-time PREFIX.  Rewrite the four path
        variables to the Conan package root so consumers can use pkg-config.
        """
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "gnu-efi.pc")
        if not os.path.isfile(pc):
            return
        with open(pc, encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace("includedir=/usr/local/include", "includedir=${prefix}/include")
        text = text.replace("libdir=/usr/local/lib", "libdir=${prefix}/lib")
        text = text.replace("exec_prefix=/usr/local", "exec_prefix=${prefix}")
        text = text.replace("prefix=/usr/local", "prefix=${pcfiledir}/../..")
        with open(pc, "w", encoding="utf-8") as handle:
            handle.write(text)

    def package_info(self):
        efi = self.efi_arch
        self.cpp_info.set_property("pkg_config_name", "gnu-efi")
        self.cpp_info.libs = ["gnuefi", "efi"]
        self.cpp_info.includedirs = [os.path.join("include", "efi"), "include"]
        # The EFI entry stub, the linker script and the archives all live in lib/:
        # consumers link `crt0-efi-<arch>.o` + `-T elf_<arch>_efi.lds -lefi -lgnuefi`.
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []
        self.cpp_info.cflags = ["-ffreestanding", "-fno-stack-protector"]
        self.cpp_info.defines = ["CONFIG_%s" % efi]
        self.cpp_info.components["gnuefi"].libs = ["gnuefi"]
        self.cpp_info.components["gnuefi"].requires = ["efi"]
        self.cpp_info.components["efi"].libs = ["efi"]
