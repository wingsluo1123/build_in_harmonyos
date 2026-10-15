#!/usr/bin/env python3
"""Conan recipe for sofia-sip 1.13.17 — Sofia-SIP 协议栈（autotools）.

FreeSWITCH 维护的 SIP 协议栈库。tag 归档无预生成 configure，需 autogen
（参照 libneurosim 先例：tool_requires 拉 automake/libtool，手动
aclocal/libtoolize/autoheader/autoconf/automake）；OHOS 沙箱 umask 022 +
config.status 临时目录改 $TMPDIR 绝对路径。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SofiaConan(ConanFile):
    name = "sofia"
    version = "1.13.17"
    description = "Sofia-SIP — open-source SIP User-Agent library"
    license = "LGPL-2.1"
    homepage = "https://github.com/freeswitch/sofia-sip"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        # tag 归档无预生成 configure，需 autogen（libneurosim 同型）
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        # 禁用可选重依赖模块：stun/nth/ntlm 探测依赖额外库（glib 等），
        # 保留核心 SIP UA + su 层即可。
        tc.configure_args.extend([
            "--disable-stun",
            "--disable-nth",
            "--disable-ntlm",
        ])
        tc.generate()

    def build(self):
        # OHOS 沙箱默认 umask 077（+SGID）→ 0700 临时目录不可写（librrd 先例）。
        os.umask(0o022)
        # TMPDIR 兜底：config.status 临时目录改走 $TMPDIR 绝对路径
        tmpdir = os.environ.get("TMPDIR", "")
        if tmpdir:
            if not os.path.isabs(tmpdir):
                tmpdir = os.path.join(os.getcwd(), tmpdir)
            if not os.path.isdir(tmpdir):
                os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        # 上游 autogen.sh 即 autoreconf -i；直接调用工具链（PATH 已注入）
        self.run("aclocal", cwd=self.source_folder)
        self.run("libtoolize --force --copy --automake", cwd=self.source_folder)
        self.run("autoheader", cwd=self.source_folder)
        self.run("autoconf", cwd=self.source_folder)
        self.run("automake --foreign --copy --add-missing", cwd=self.source_folder)

        # 生成的 configure/config.status 临时目录用 umask 077 → 替换为 022
        # （OHOS 沙箱 0700 目录不可写），并改相对路径 ./confXXXXXX 为
        # $TMPDIR/confXXXXXX（libneurosim/kimwitu 同型方案）。
        def _relax_umask(path):
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    return
                changed = False
                if "umask 077" in content:
                    content = content.replace("umask 077", "umask 022")
                    changed = True
                if "./confXXXXXX" in content:
                    content = content.replace("./confXXXXXX", "$TMPDIR/confXXXXXX")
                    changed = True
                if changed:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)

        for root, dirs, files in os.walk(self.source_folder):
            for name in files:
                if name in ("configure", "config.status") or name.endswith(".in"):
                    _relax_umask(os.path.join(root, name))

        autotools = Autotools(self)
        autotools.configure()
        # 阻止 make 重跑 config.status/autogen：-o 下传子 make + autotools
        # 工具变量 no-op（libneurosim 已验证方案）
        self.run(
            "make -j1 -o config.status -o Makefile.in "
            "AUTOCONF=true AUTOMAKE=true ACLOCAL=true AUTOHEADER=true "
            "LIBTOOLIZE=true libtoolize=true aclocal-real=true",
            env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        # install 递归同样阻止 config.status 重跑（libneurosim #67286 先例）
        autotools.install(args=[
            "-j1", "-o", "config.status", "-o", "Makefile.in",
            "AUTOCONF=true", "AUTOMAKE=true", "ACLOCAL=true",
            "AUTOHEADER=true", "LIBTOOLIZE=true", "libtoolize=true",
            "aclocal-real=true",
        ])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 符号实测归属：libsofia-sip-ua 为对外主库（su/sip/nta/soa 等）。
        self.cpp_info.libs = ["sofia-sip-ua"]
        self.cpp_info.set_property("pkg_config_name", "sofia-sip-ua")
        # 上游安装头文件位于 include/sofia-sip-1.13/（版本前缀目录），
        # 上游 .pc（sofia-sip-ua.pc）同样导出 -I${includedir}/sofia-sip-1.13，
        # 消费者以 #include <sofia-sip/su.h> 方式引用——必须导出该子目录，
        # 否则 -I<prefix>/include 找不到头文件。
        self.cpp_info.includedirs = ["include/sofia-sip-1.13"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
