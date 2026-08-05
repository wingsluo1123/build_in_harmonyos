#!/usr/bin/env python3
"""Conan recipe — abiword-plugin-epub 3.0.8

AbiWord EPUB e-book export plugin.
Part of the AbiWord 3.0.8 source tree. Depends on libgsf-1 (gsf_req).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AbiwordPluginEpubConan(ConanFile):
    name = "abiword-plugin-epub"
    version = "3.0.8"
    description = "AbiWord EPUB e-book export plugin"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/World/AbiWord"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # epub plugin needs libgsf-1 (gsf_req) per upstream plugin.m4
        self.requires("libgsf/1.14.53")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Enable only the epub plugin, disable all others
        tc.configure_args.append("--enable-plugins=epub")
        tc.configure_args.append("--disable-default-plugins")
        # Skip gtk checks for plugin-only build
        tc.configure_args.append("--with-gtk2=no")
        tc.generate()

    def build(self):
        # Generate configure from configure.ac (no pre-generated configure)
        self._run_autogen()

        # Patch config.guess/config.sub for OHOS
        self._patch_config_for_ohos()

        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        # Build the plugin subdirectory only
        autotools.make(target="-C plugins/epub")

    def _run_autogen(self):
        """Run autogen.sh to generate configure and plugin configuration files."""
        self.output.info("Running autogen-common.sh to generate plugin configuration...")
        subprocess.run(
            ["bash", "autogen-common.sh"],
            cwd=self.source_folder,
            check=True,
        )
        self.output.info("Running autoreconf to generate configure...")
        subprocess.run(
            ["autoreconf", "--force", "--install"],
            cwd=self.source_folder,
            check=True,
        )

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub for OHOS (R15).

        Prefer the skill's Perl script; fall back to manual Python patching
        (mirrors addrwatch/nspr/slang) so OHOS triplet is recognized even
        when OHC_SKILL_ROOT is unset or the Perl script is absent.
        """
        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.output.info("Patching config.guess/config.sub with skill script")
                for f in ("config.guess", "config.sub"):
                    path = os.path.join(self.source_folder, f)
                    if os.path.exists(path):
                        subprocess.run(["perl", script, path], check=True)
                return

        # Fallback: manual Python patching
        self.output.info("OHC_SKILL_ROOT/Perl script unavailable, falling back to manual Python patch")
        cg_path = os.path.join(self.source_folder, "config.guess")
        cs_path = os.path.join(self.source_folder, "config.sub")
        if os.path.exists(cg_path):
            self._manual_patch_config_guess(cg_path)
        else:
            self.output.warning("config.guess not found, skipping guess patch")
        if os.path.exists(cs_path):
            self._manual_patch_config_sub(cs_path)
        else:
            self.output.warning("config.sub not found, skipping sub patch")

    def _manual_patch_config_guess(self, cg_path):
        """Manually patch config.guess for HarmonyOS detection."""
        with open(cg_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add __OHOS__ LIBC detection after __ANDROID__
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos"
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
                self.output.info("  [ok] Added __OHOS__ LIBC detection to config.guess")
            else:
                self.output.warning("  [warn] Could not find __ANDROID__/LIBC=android in config.guess")

        # 2. Add HarmonyOS case block before NetBSD
        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
                self.output.info("  [ok] Added HarmonyOS system identification to config.guess")
            else:
                self.output.warning("  [warn] Could not find NetBSD insertion point in config.guess")

        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _manual_patch_config_sub(self, cs_path):
        """Manually patch config.sub for ohos-linux support."""
        with open(cs_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add ohos-linux triplet after android-linux
        if "ohos-linux" not in content:
            import re
            pattern = r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            replacement = r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;\n'
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True
                self.output.info("  [ok] Added ohos-linux triplet to config.sub")
            else:
                self.output.warning("  [warn] Could not find android-linux in config.sub")

        # 2. Add ohos* to OS type list
        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True
            self.output.info("  [ok] Added ohos* to OS list in config.sub")

        # 3. Add linux-ohos to kernel-OS validation list
        if "linux-ohos" not in content:
            import re
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))', r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True
                self.output.info("  [ok] Added linux-ohos to kernel list in config.sub")
            else:
                self.output.warning("  [warn] Could not find linux-uclibc pattern in config.sub")

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def package(self):
        # Copy the plugin .so to the package folder via glob + copy.
        # 不用 autotools.install(target=...)：Conan 2.x 的 install/make 不追加
        # DESTDIR，配合 configure 阶段 --prefix=/ 会把 .so 装到系统目录(/lib/)
        # 而非 Conan 包目录，在非 root CI worker 上会因无写权限失败。
        # glob + copy 直接从 build_folder/.libs/ 取产物到 package_folder，正确且幂等。
        import glob
        for so in glob.glob(os.path.join(self.build_folder, "plugins", "epub", ".libs", "*.so*")):
            dst = os.path.join(self.package_folder, "lib", "abiword", "plugins")
            os.makedirs(dst, exist_ok=True)
            copy(self, os.path.basename(so), os.path.dirname(so), dst)

    def package_info(self):
        self.cpp_info.libs = []
        # Set the plugin directory for discovery
        self.runenv_info.define_path("ABIWORD_PLUGINS_DIR",
            os.path.join(self.package_folder, "lib", "abiword", "plugins"))
