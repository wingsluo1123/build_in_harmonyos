#!/usr/bin/env python3
"""Conan recipe — x-loader 1.5.1-git20110715-fca7cd2 (OMAP first-stage bootloader).

x-loader (the ``MLO`` image) is the first-stage bootloader for Texas Instruments
OMAP2/3/4 boards.  It is bare-metal ARM firmware: the upstream Makefile
cross-compiles the image and also builds ``signGP``, a host utility that
prepends the TI signed-image header (image size + load address) to the raw
image.

HarmonyOS PC adaptation
-----------------------
* The HarmonyOS PC toolchain (clang 15 + LLVM binutils) is a full cross compiler
  with the ARM backend registered, so the upstream Makefile is driven with
  ``CC="clang --target=arm-none-eabi"`` and the LLVM binutils instead of the
  upstream ``arm-none-linux-gnueabi`` GNU toolchain.  Only GNU-only command line
  flags are dropped (see :meth:`build`).
* ``signGP`` is built for the HarmonyOS PC itself (aarch64 + musl), so a signed
  bootloader image can be produced on device.
* R33: every compiler comes from the Conan conf; no bare ``${CC}``/``${CFLAGS}``
  shell variables are used.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rename,
)
from conan.tools.layout import basic_layout

# BeagleBoard / OMAP3530 (Cortex-A8) — the board this upstream tree is named for.
BOARD = "omap3530beagle"


class XLoaderConan(ConanFile):
    name = "x-loader"
    version = "1.5.1-git20110715-fca7cd2"
    description = "TI OMAP first-stage bootloader (MLO) and its signGP host utility"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/joelagnel/x-loader"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: the recipe drives the OHOS/Linux clang toolchain for both platforms.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"x-loader does not support {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, key, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(key, default)

    def build(self):
        apply_conandata_patches(self)

        # R33: toolchain from the Conan conf, never from shell environment variables.
        clang = self._tool("c", "clang")
        ld = self._tool("ld", "ld.lld")
        ar = self._tool("ar", "llvm-ar")
        nm = self._tool("nm", "llvm-nm")
        strip = self._tool("strip", "llvm-strip")
        objcopy = self._tool("objcopy", "llvm-objcopy")
        objdump = self._tool("objdump", "llvm-objdump")

        # mkconfig writes include/config.mk and the include/asm/arch symlink.
        self.run(f"make {BOARD}_config", cwd=self.source_folder)

        # The upstream Makefile derives its tools from CROSS_COMPILE and defaults
        # to an arm-none-linux-gnueabi GNU toolchain plus a `gcc` host compiler.
        # clang is a cross compiler, so the same Makefile is reused with the
        # clang/LLVM tools.  Only GNU-only flags are dropped:
        #   * AFLAGS_DEBUG=-Wa,-gstabs and OBJCFLAGS=--gap-fill=0xff are not
        #     understood by the LLVM assembler/objcopy (the linker script emits
        #     contiguous sections, so no gap fill is required);
        #   * PLATFORM_RELFLAGS contains -ffixed-r8, which clang rejects for ARM;
        #   * PLATFORM_LIBS adds -lgcc, which does not exist for clang's
        #     bare-metal target (the ARM EABI division helpers are provided by
        #     0001/0002 instead).
        # CFLAGS/HOSTCFLAGS are cleared in the environment because the upstream
        # Makefile uses `CFLAGS += ...`: a CFLAGS leaked from the caller would
        # otherwise end up on every compile line.
        make_args = " ".join(
            [
                "-j1",
                "CROSS_COMPILE=",
                f"CC={shlex.quote(clang + ' --target=arm-none-eabi')}",
                f"LD={shlex.quote(ld)}",
                f"AR={shlex.quote(ar)}",
                f"NM={shlex.quote(nm)}",
                f"STRIP={shlex.quote(strip)}",
                f"OBJCOPY={shlex.quote(objcopy)}",
                f"OBJDUMP={shlex.quote(objdump)}",
                f"HOSTCC={shlex.quote(clang)}",
                "AFLAGS_DEBUG=",
                "PLATFORM_RELFLAGS=",
                "PLATFORM_LIBS=",
                "OBJCFLAGS=",
                "all",
            ]
        )
        self.run(f"CFLAGS= HOSTCFLAGS= make {make_args}", cwd=self.source_folder)

    def package(self):
        firmware = os.path.join(self.package_folder, "share", "x-loader")
        for artifact in (
            "MLO",
            "x-load.bin",
            "x-load.bin.ift",
            "System.map",
            "x-load.map",
        ):
            copy(self, artifact, self.source_folder, firmware, keep_path=False)
        copy(self, "x-load", self.source_folder, firmware, keep_path=False)
        rename(
            self,
            os.path.join(firmware, "x-load"),
            os.path.join(firmware, "x-load.elf"),
        )

        copy(
            self,
            "signGP",
            self.source_folder,
            os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        # The upstream tree ships its GPL notice inside README.
        copy(
            self,
            "README",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
