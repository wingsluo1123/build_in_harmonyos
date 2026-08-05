#!/usr/bin/env python3
"""Conan recipe — abiword-plugin-docbook 3.0.8

AbiWord DocBook XML import/export plugin.
Part of the AbiWord 3.0.8 source tree. Depends on libgsf-1 (gsf_req).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AbiwordPluginDocbookConan(ConanFile):
    name = "abiword-plugin-docbook"
    version = "3.0.8"
    description = "AbiWord DocBook XML import/export plugin"
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
        # docbook plugin needs libgsf-1 (gsf_req) per upstream plugin.m4
        self.requires("libgsf/1.14.53")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Enable only the docbook plugin, disable all others
        tc.configure_args.append("--enable-plugins=docbook")
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
        autotools.make(target="-C plugins/docbook")

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
        """Patch config.guess and config.sub for OHOS (R15)."""
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
        self.output.info("OHC_SKILL_ROOT not set or script not found, skipping autotools patch")

    def package(self):
        # Copy the plugin .so to the package folder via glob + copy.
        # 不用 autotools.install(target=...)：Conan 2.x 的 install/make 不追加
        # DESTDIR，配合 configure 阶段 --prefix=/ 会把 .so 装到系统目录(/lib/)
        # 而非 Conan 包目录，在非 root CI worker 上会因无写权限失败。
        # glob + copy 直接从 build_folder/.libs/ 取产物到 package_folder，正确且幂等。
        import glob
        for so in glob.glob(os.path.join(self.build_folder, "plugins", "docbook", ".libs", "*.so*")):
            dst = os.path.join(self.package_folder, "lib", "abiword", "plugins")
            os.makedirs(dst, exist_ok=True)
            copy(self, os.path.basename(so), os.path.dirname(so), dst)

    def package_info(self):
        self.cpp_info.libs = []
        # Set the plugin directory for discovery
        self.runenv_info.define_path("ABIWORD_PLUGINS_DIR",
            os.path.join(self.package_folder, "lib", "abiword", "plugins"))
