#!/usr/bin/env python3
"""Conan recipe — abiword-plugin-eml 3.0.8

AbiWord EML (Outlook Express Email) export plugin.
Part of the AbiWord 3.0.8 source tree.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AbiwordPluginEmlConan(ConanFile):
    name = "abiword-plugin-eml"
    version = "3.0.8"
    description = "AbiWord EML (Outlook Express Email) export plugin"
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
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Enable only the eml plugin, disable all others
        tc.configure_args.append("--enable-plugins=eml")
        tc.configure_args.append("--disable-default-plugins")
        # Skip gtk checks for plugin-only build
        tc.configure_args.append("--with-gtk2=no")
        # OHOS 不被 config.guess 识别,显式传 --build/--host 跳 config.guess
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
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
        autotools.make(target="-C plugins/eml")

    def _run_autogen(self):
        """Run autogen.sh to generate configure and plugin configuration files.

        OHOS HMDFS 环境下 autoreconf 链存在 autoconf.m4f 加载冲突
        (AC_DEFINE/AC_MSG_ERROR 等基础宏报"未定义",实为 warning 被
        当 hard error),改用 autoconf + automake 直跑链绕过。
        """
        import shutil

        self.output.info("Running autogen-common.sh to generate plugin configuration...")
        subprocess.run(
            ["bash", "autogen-common.sh"],
            cwd=self.source_folder,
            check=True,
        )

        # 先跑 aclocal 生成 aclocal.m4(提供 AM_* 宏)
        self.output.info("Running aclocal to generate aclocal.m4...")
        subprocess.run(
            ["aclocal", "--force"],
            cwd=self.source_folder,
            check=False,  # aclocal 有 warning 不影响
        )

        # autoconf 直接编译 configure.ac → configure(绕 autoreconf 链冲突)
        self.output.info("Running autoconf to generate configure...")
        subprocess.run(
            ["autoconf", "-o", "configure", "configure.ac"],
            cwd=self.source_folder,
            check=False,  # AC_DEFINE 等 warning 非硬错,configure 仍生成
        )
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoconf failed to generate configure")

        # autoheader 生成 config.h.in
        self.output.info("Running autoheader to generate config.h.in...")
        subprocess.run(
            ["autoheader"],
            cwd=self.source_folder,
            check=False,
        )
        _cfg_h_in = os.path.join(self.source_folder, "config.h.in")
        if not os.path.exists(_cfg_h_in):
            # autoheader 靡输出时 touch 兜底
            open(_cfg_h_in, "w").close()

        # automake 补 Makefile.in + install-sh 等(--add-missing)
        self.output.info("Running automake to generate Makefile.in...")
        subprocess.run(
            ["automake", "--add-missing", "--copy", "--no-force"],
            cwd=self.source_folder,
            check=False,  # 部分 Makefile.am 有 GNU make 扩展 warning
        )

        # 补 ltmain.sh(libtool build-aux,automake 要求)
        _ltmain = os.path.join(self.source_folder, "ltmain.sh")
        if not os.path.exists(_ltmain):
            _libtool_aux = os.path.join(
                os.path.dirname(shutil.which("libtool") or ""),
                "..", "share", "libtool", "build-aux", "ltmain.sh"
            )
            if os.path.exists(_libtool_aux):
                shutil.copy(_libtool_aux, _ltmain)
                self.output.info("  [ok] Copied ltmain.sh from libtool build-aux")
            else:
                self.output.warning("  [warn] ltmain.sh not found, libtool macros may fail")

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub for OHOS (R15)."""
        # Check if the skill's perl script is available
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
        # 不用 autotools.make(target="... install")：Conan 2.x 的 make() 不追加
        # DESTDIR，配合 configure 阶段 --prefix=/ 会把 .so 装到系统目录(/lib/)
        # 而非 Conan 包目录，在非 root CI worker 上会因无写权限失败。
        # glob + copy 直接从 build_folder/.libs/ 取产物到 package_folder，正确且幂等。
        import glob
        for so in glob.glob(os.path.join(self.build_folder, "plugins", "eml", ".libs", "*.so*")):
            dst = os.path.join(self.package_folder, "lib", "abiword", "plugins")
            os.makedirs(dst, exist_ok=True)
            copy(self, os.path.basename(so), os.path.dirname(so), dst)

    def package_info(self):
        self.cpp_info.libs = []
        # Set the plugin directory for discovery
        self.runenv_info.define_path("ABIWORD_PLUGINS_DIR",
            os.path.join(self.package_folder, "lib", "abiword", "plugins"))