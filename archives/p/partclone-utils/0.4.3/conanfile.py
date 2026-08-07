#!/usr/bin/env python3
"""Conan recipe — partclone-utils 0.4.3 (Autotools: configure + make).

Utilities for partclone image files: imagemount, partclone_imageinfo,
ntfsclone_imageinfo, cfchanges, cfdump.

Source is a GitHub archive (no pre-generated configure), so autoreconf is
required. config.guess/config.sub are patched inline after autoreconf for
HarmonyOS (E007). config.status umask 077 is fixed inline after configure
(HMDFS permission issue).

R32: settings.os must check in ("Linux", "OHOS").
R34: test_package executes the package's binaries.
R38: Command-line tool — commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PartcloneUtilsConan(ConanFile):
    name = "partclone-utils"
    version = "0.4.3"
    description = "Utilities for partclone image files (imagemount, imageinfo, cfchanges)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/vasi/partclone-utils"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Include pre-generated autotools files (configure, Makefile.in, etc.)
        # since CI may not have automake/aclocal installed
        copy(self, "pre_generated/autotools-files.tar.gz", self.recipe_folder,
             self.export_sources_folder)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "partclone-utils is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _patch_config_guess_sub(self):
        """Patch config.guess and config.sub for HarmonyOS (E007).

        Must be called AFTER autoreconf, since autoreconf installs fresh
        copies of these files from automake.
        """
        # Patch config.guess: add __OHOS__ LIBC detection + HarmonyOS case
        cg_path = os.path.join(self.source_folder, "config.guess")
        if os.path.exists(cg_path):
            with open(cg_path, 'r') as f:
                content = f.read()
            changed = False
            if "__OHOS__" not in content:
                content = content.replace(
                    "\t#elif defined(__GLIBC__)\n\tLIBC=gnu\n\t#else",
                    "\t#elif defined(__GLIBC__)\n\tLIBC=gnu\n\t#elif defined(__OHOS__)\n\tLIBC=ohos\n\t#else",
                )
                changed = True
            if "HarmonyOS" not in content:
                harmonyos_block = (
                    '    *:HarmonyOS:*:*)\n'
                    '       case "$UNAME_MACHINE" in\n'
                    '           aarch64|arm64) GUESS=aarch64-unknown-linux-ohos ;;\n'
                    '           armv7*|armv8*) GUESS=arm-unknown-linux-ohos ;;\n'
                    '           x86_64|amd64)  GUESS=x86_64-unknown-linux-ohos ;;\n'
                    '           i?86)         GUESS=i686-unknown-linux-ohos ;;\n'
                    '           *)            GUESS=${UNAME_MACHINE}-unknown-linux-ohos ;;\n'
                    '       esac\n'
                    '       ;;\n'
                )
                content = content.replace(
                    "    *:NetBSD:*:*)",
                    harmonyos_block + "    *:NetBSD:*:*)",
                )
                changed = True
            if changed:
                with open(cg_path, 'w') as f:
                    f.write(content)
                os.chmod(cg_path, 0o755)

        # Patch config.sub: add ohos-linux triplet + OS list + kernel-os combo
        cs_path = os.path.join(self.source_folder, "config.sub")
        if os.path.exists(cs_path):
            with open(cs_path, 'r') as f:
                content = f.read()
            changed = False
            if "ohos-linux" not in content:
                content = content.replace(
                    "android-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-android\n\t\t\t\t;;",
                    "android-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-android\n\t\t\t\t;;\n\t\t\tohos-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-ohos\n\t\t\t\t;;",
                )
                changed = True
            if "ohos*" not in content:
                content = content.replace(
                    "gnu* | android* | bsd*",
                    "gnu* | android* | ohos* | bsd*",
                )
                changed = True
            if "linux-ohos*" not in content and "linux-ohos*-" not in content:
                for old_pat, new_pat in [
                    ("| linux-musl*- | linux-relibc*- | linux-uclibc*- | linux-mlibc*- )",
                     "| linux-musl*- | linux-relibc*- | linux-uclibc*- | linux-mlibc*- | linux-ohos*- )"),
                    ("| linux-musl* | linux-relibc* | linux-uclibc* )",
                     "| linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )"),
                ]:
                    if old_pat in content:
                        content = content.replace(old_pat, new_pat)
                        break
                changed = True
            if changed:
                with open(cs_path, 'w') as f:
                    f.write(content)
                os.chmod(cs_path, 0o755)

    def _fix_config_status(self):
        """Fix config.status: remove umask 077 for temp dir (HMDFS permission).

        config.status is a generated file (not in source tarball), so it
        cannot be patched via conandata.yml. Applied inline after configure.
        """
        self._fix_config_status_at(self.build_folder)

    def _fix_config_status_at(self, folder):
        """Fix config.status in the given folder."""
        path = os.path.join(folder, "config.status")
        if not os.path.exists(path):
            self.output.info(f"config.status not found at {path}")
            return
        with open(path, 'r') as f:
            content = f.read()
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        with open(path, 'w') as f:
            f.write(content)
        self.output.info(f"Fixed config.status umask at {path}")

    def build(self):
        # Step 1: Apply source patches (imagemount.c fix)
        apply_conandata_patches(self)

        autotools = Autotools(self)

        # Step 2: Use pre-generated autotools files (CI may not have automake)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("Source has no configure, extracting pre-generated autotools files")
            import tarfile
            tarball = os.path.join(self.source_folder, "pre_generated", "autotools-files.tar.gz")
            if not os.path.exists(tarball):
                # Look in export_sources_folder
                tarball = os.path.join(self.export_sources_folder, "pre_generated", "autotools-files.tar.gz")
            if os.path.exists(tarball):
                with tarfile.open(tarball) as tf:
                    tf.extractall(self.source_folder)
                self.output.info("Pre-generated autotools files extracted")
            else:
                self.output.warning("No pre-generated files found, trying autoreconf")
                self.run(
                    f'cd "{self.source_folder}" && autoreconf --force --install',
                    env="conanbuild"
                )

        # Step 3: Patch config.guess/config.sub for HarmonyOS (E007)
        # Must be after autoreconf since it installs fresh copies
        self._patch_config_guess_sub()

        # Step 4: Configure (may fail due to HMDFS umask 077 in config.status)
        src = self.source_folder
        try:
            autotools.configure(build_script_folder=src)
        except Exception as e:
            self.output.warning(f"configure failed (likely umask 077), attempting fix: {e}")

        # Step 5: Fix config.status (HMDFS umask 077 permission issue)
        # config.status is generated by configure in the build folder
        bld = self.build_folder
        self._fix_config_status_at(bld)
        mk_path = os.path.join(bld, "Makefile")
        cs_path = os.path.join(bld, "config.status")
        if os.path.exists(cs_path) and not os.path.exists(mk_path):
            self.output.info("Re-running config.status after umask fix")
            self.run(f'cd "{bld}" && bash config.status')

        # Step 6: Build (run in build folder where Makefile is generated)
        bld = self.build_folder
        self.run(f'cd "{bld}" && make -j1', env="conanbuild")

    def package(self):
        bld = self.build_folder
        pkg = self.package_folder
        self.run(f'cd "{bld}" && make install DESTDIR="{pkg}"', env="conanbuild")

    def package_info(self):
        # partclone-utils is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure binaries are on PATH for VirtualRunEnv (test_package)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
