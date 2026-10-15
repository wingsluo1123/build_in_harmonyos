#!/usr/bin/env python3
"""Conan recipe — libkdumpfile 0.5.5 (autotools)

libkdumpfile is a library for reading kernel crash dumps (kdump) in the
diskdump / ELF / lkcd / sadump formats, plus the addrxlat address
translation library.  Both libraries are installed by the upstream build.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibkdumpfileConan(ConanFile):
    name = "libkdumpfile"
    version = "0.5.5"
    description = "Library for reading kernel crash dumps (kdump) and address translation"
    license = "GPL-2.0-or-later"  # COPYING.GPLv2/GPLv3/LGPLv3 dual; header lib is GPLv2+
    homepage = "https://github.com/ptesarik/libkdumpfile"
    url = "https://github.com/ptesarik/libkdumpfile"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib is used for decompressing compressed diskdump page data.
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # kdumpid requires binutils opcodes (dis-asm.h), which is not available
        # in the OHOS toolchain; it is an optional auxiliary tool upstream.
        tc.configure_args.append("--disable-kdumpid")
        # Python bindings are optional; `make install` runs `setup.py install`
        # which writes to the (read-only) /lib in the CI sandbox.  Keep the
        # recipe to the C libraries.
        tc.configure_args.append("--without-python")
        _zlib = self.dependencies["zlib"].package_folder
        tc.extra_cflags.append(f"-I{_zlib}/include")
        tc.extra_ldflags.append(f"-L{_zlib}/lib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Official v0.5.5 release asset ships a generated configure script
        # (configure, aclocal.m4, Makefile.in are part of the tarball), so no
        # autoreconf is needed.  CI workers do not provide automake/aclocal
        # (E058/E248), so we must not regenerate the build system here.
        if self.settings.os == "OHOS":
            self._patch_config_guess_sub()
            self._patch_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        if self.settings.os == "OHOS":
            self._patch_libtool()
        autotools.make(args=["-j1"])

    # ---- OHOS platform fixes (E007 / E011) ----

    def _patch_config_guess_sub(self):
        """E007: GNU config.guess/sub do not recognize HarmonyOS.

        Inline equivalents of the skill's patch-autotools-ohos.pl so the
        recipe is self-contained for CI.  Missing patterns are non-fatal
        warnings; the generated files vary with the installed autotools.
        """
        for f in ("config.guess", "config.sub"):
            path = os.path.join(self.source_folder, f)
            if not os.path.exists(path):
                self.output.warning(f"config.guess/sub not found: {f}")
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            changed = False
            if f == "config.guess":
                # 1) __OHOS__ LIBC detection
                if "__OHOS__" not in text:
                    new_text = re.sub(
                        r"(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                        r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                        text, count=1, flags=re.M)
                    changed |= new_text != text
                    text = new_text
                # 2) HarmonyOS system identification before the NetBSD case
                if "HarmonyOS" not in text:
                    block = (
                        "    *:HarmonyOS:*:*)\n"
                        "\tcase \"$UNAME_MACHINE\" in\n"
                        "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                        "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                        "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                        "\t    i?86)         MACHINE=i686 ;;\n"
                        "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                        "\tesac\n"
                        "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                        "\t;;\n\n")
                    new_text = re.sub(
                        r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)",
                        block + r"\1", text, count=1, flags=re.M)
                    changed |= new_text != text
                    text = new_text
            else:  # config.sub
                # 1) ohos-linux triplet after android-linux
                if "ohos-linux" not in text:
                    new_text = re.sub(
                        r"^(\s*android-linux\)\s*\n)((\s*)basic_machine=\$field1-unknown\s*\n)((\s*)basic_os=linux-android\s*\n)(\s*;;\s*\n)",
                        r"\1\2\4\6\tohos-linux)\n\3basic_machine=$field1-unknown\n\5basic_os=linux-ohos\n\6",
                        text, count=1, flags=re.M)
                    changed |= new_text != text
                    text = new_text
                # 2) ohos* in the OS type list
                if not re.search(r"gnu\*\s*\|\s*android\*\s*\|\s*ohos\*", text):
                    new_text = re.sub(r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*",
                                      text, count=1)
                    changed |= new_text != text
                    text = new_text
                # 3) linux-ohos in the kernel-OS validation list
                #    Guard must match the validation-list entry itself, not the
                #    `basic_os=linux-ohos` text added by the triplet step above.
                if not re.search(r"linux-ohos\*- \)|linux-ohos\*\)", text):
                    new_text = re.sub(
                        r"(linux-uclibc\*- )\)", r"\1| linux-ohos*- )",
                        text, count=1)
                    changed |= new_text != text
                    text = new_text
            if changed:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                self.output.info(f"Patched {f} for OHOS")
            else:
                self.output.warning(f"{f}: OHOS patch patterns not found "
                                    "(file may already be patched)")

    def _patch_configure_umask(self):
        """E011: HMDFS UID mapping makes umask-077 temp dirs unwritable.

        autotools' configure creates its secure tmp dir with `umask 077`;
        on HMDFS the created directory cannot be written by the actual
        process UID, so config.status fails with 'Permission denied'.
        Relaxing to umask 022 is safe in the single-user build sandbox.
        """
        path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(path):
            self.output.warning("configure not found for umask patch")
            return
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        if "umask 077" not in text:
            self.output.warning("umask 077 pattern not found in configure")
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace("umask 077", "umask 022"))
        self.output.info("Patched configure umask 077 -> 022 (E011)")

    def _patch_libtool(self):
        """Fix the generated libtool for this environment:
        - define the lowercase `echo` variable (only ECHO was set);
        - old_archive_cmds/postinstall referenced an unset `tool_oldlib`,
          so `ranlib` was invoked without an argument.
        """
        candidates = [
            os.path.join(self.source_folder, "libtool"),
            os.path.join(self.build_folder, "libtool"),
        ]
        for path in candidates:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            changed = False
            # The generated libtool always uses $echo (lowercase) in its
            # argument parsing but only defines ECHO (uppercase).  Append
            # `echo=$ECHO` right after the ECHO assignment, whatever value
            # configure detected in this environment.
            if "echo=$ECHO" not in text:
                new_text = re.sub(r"(^ECHO=.*$)",
                                  r"\1\necho=$ECHO",
                                  text, count=1, flags=re.M)
                changed |= new_text != text
                text = new_text
            # The generated libtool stores these commands with backslash-escaped
            # variables (config section), e.g. `\$RANLIB \$tool_oldlib`.
            if "$RANLIB $tool_oldlib" in text:
                text = text.replace("$RANLIB $tool_oldlib", "$RANLIB $oldlib")
                changed = True
            if "\\$RANLIB \\$tool_oldlib" in text:
                text = text.replace("\\$RANLIB \\$tool_oldlib",
                                    "\\$RANLIB \\$oldlib")
                changed = True
            if "$RANLIB -t $tool_oldlib" in text:
                text = text.replace("$RANLIB -t $tool_oldlib", "$RANLIB -t $oldlib")
                changed = True
            if "\\$RANLIB -t \\$tool_oldlib" in text:
                text = text.replace("\\$RANLIB -t \\$tool_oldlib",
                                    "\\$RANLIB -t \\$oldlib")
                changed = True
            if changed:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                self.output.info(f"Patched {os.path.basename(path)} (echo/tool_oldlib)")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libkdumpfile (kdump reader) and libaddrxlat (address translation)
        # are both installed by the upstream build.
        self.cpp_info.libs = ["kdumpfile", "addrxlat"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]
