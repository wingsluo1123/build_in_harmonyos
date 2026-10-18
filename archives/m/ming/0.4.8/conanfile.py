#!/usr/bin/env python3
"""Conan recipe for ming 0.4.8 — libming（SWF 解析/生成库，autotools）.

tag 归档无预生成 configure，需 autogen（tool_requires automake/libtool，
手动 aclocal/libtoolize/autoheader/automake/autoconf，libneurosim 同型）；
OHOS 沙箱 umask 022 + config.status 临时目录改 $TMPDIR 绝对路径。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MingConan(ConanFile):
    name = "ming"
    version = "0.4.8"
    description = "libming — SWF parsing and generation library"
    license = "LGPL-2.1"
    homepage = "https://github.com/libming/libming"
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
        # 可选依赖 X11/gif/png/zlib configure 缺库自动置空，无需显式禁用；
        # 但 freetype 默认 ENABLED 且硬性要求 freetype-config（缺失即报错
        # "Could not detect freetype-config!"）——按最小依赖链显式禁用。
        tc.configure_args.append("--disable-freetype")
        # CI #97566 链接失败修复：flex 词法器与 bison 解析器的 --debug 符号
        # （swf4debug/swf5debug，yydebug 带 swf4/swf5 前缀）在 libming.a 内重复定义
        # （duplicate symbol）——-Wl,-z,muldefs 允许链接器取首定义（调试符号非运行时必需）
        tc.extra_ldflags.append("-Wl,-z,muldefs")
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

        # 上游 autogen.sh = libtoolize -f -c + aclocal -I macros +
        # libtoolize --automake + autoheader -f + automake --add-missing -c
        # + autoconf；直接调用工具链（PATH 已注入）。
        self.run("libtoolize -f -c", cwd=self.source_folder)
        self.run("aclocal -I macros", cwd=self.source_folder)
        self.run("libtoolize --automake", cwd=self.source_folder)
        self.run("autoheader -f", cwd=self.source_folder)
        self.run("automake --add-missing -c", cwd=self.source_folder)
        self.run("autoconf", cwd=self.source_folder)

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
        # CI #97566/#97629/#97634 链接失败修复（选项 1：修 LDFLAGS 传播）：
        # configure 的 LDFLAGS 未传播到 libtool 的 libming.la 链接，make 直接传
        # LDFLAGS="-Wl,-z,muldefs ${LDFLAGS}"（${LDFLAGS} 保留工具链原有 flags），
        # 确保 flex/bison 调试符号 swf4debug/swf5debug 重复定义时链接取首定义
        self.run(
            "make -j1 -o config.status -o Makefile.in "
            "LDFLAGS=\"-Wl,-z,muldefs ${LDFLAGS}\" "
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
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 主库 libming（src/Makefile.am lib_LTLIBRARIES = libming.la）
        self.cpp_info.libs = ["ming"]
        self.cpp_info.set_property("pkg_config_name", "ming")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
