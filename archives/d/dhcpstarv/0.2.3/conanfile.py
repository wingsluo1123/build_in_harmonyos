#!/usr/bin/env python3
"""Conan recipe for dhcpstarv 0.2.3 — DHCP starvation utility.

Build system: autotools (autoreconf + configure + make).
No third-party C library dependency: uses Linux raw PF_PACKET sockets directly.
Patches: 0001 configure HMDFS tmpdir (applied after autoreconf), 0002/0003 OHOS musl udphdr members.
"""
import os
import shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, patch, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain


class DhcpstarvConan(ConanFile):
    name = "dhcpstarv"
    version = "0.2.3"
    description = "DHCP starvation utility (RFC2131), raw PF_PACKET sockets"
    license = "GPL-3.0"
    homepage = "https://github.com/sgeto/dhcpstarv"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/d/dhcpstarv/0.2.3"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # 0001 补丁不进入 conandata patches 列表（需在 autoreconf 后应用），手动导出
        copy(self, "0001-configure-hmdfs-tmpdir.patch",
             src=os.path.join(self.recipe_folder, "patches"),
             dst=os.path.join(self.export_sources_folder, "patches"))

    def requirements(self):
        pass

    def layout(self):
        # 上游 Makefile.am 使用 nostdinc，config.h 与源文件同目录查找；采用 in-source 构建
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-silent-rules")
        tc.generate()

    def _inject_autotools_env(self):
        """CI Worker 默认 PATH 可能缺少 aclocal/automake（autoreconf 前置依赖）。

        动态定位 aclocal 所在目录并注入 PATH；同时把对应 share/automake-*
        目录加入 PERL5LIB（否则 aclocal 报 Automake/Config.pm 缺失）。
        注意：即使 aclocal 已在 PATH，也必须校验/注入 PERL5LIB——automake
        1.17 share 目录可能为空，需指向含 Automake/Config.pm 的版本目录。
        """
        if not shutil.which("aclocal"):
            candidates = [
                "/storage/Users/currentUser/usr/local/bin",
                "/usr/local/bin",
                "/usr/bin",
                "/data/service/hnp/automake.org/bin",
            ]
            for d in candidates:
                aclocal = os.path.join(d, "aclocal")
                if os.path.isfile(aclocal) and os.access(aclocal, os.X_OK):
                    os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
                    break
        # 校验 PERL5LIB：保证 aclocal 能找到 Automake/Config.pm
        cur = os.environ.get("PERL5LIB", "")
        if "Automake" not in cur:
            for root in ("/storage/Users/currentUser/usr/local/share", "/usr/share"):
                if not os.path.isdir(root):
                    continue
                for name in sorted(os.listdir(root)):
                    if name.startswith("automake-") and os.path.isfile(
                            os.path.join(root, name, "Automake", "Config.pm")):
                        os.environ["PERL5LIB"] = os.path.join(root, name) + (
                            os.pathsep + cur if cur else "")
                        return

    def build(self):
        apply_conandata_patches(self)
        self._inject_autotools_env()
        autotools = Autotools(self)
        autotools.autoreconf()
        # configure 由 autoreconf 生成后，再应用 HMDFS 临时目录修复
        patch(self, patch_file=os.path.join(self.source_folder, "patches", "0001-configure-hmdfs-tmpdir.patch"))
        # HMDFS 上 config.status 临时目录需落在源码内 .tmp 目录（先创建）
        self.run("mkdir -p .tmp")
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
