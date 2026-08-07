#!/usr/bin/env python3
"""Conan recipe for ncurses 6.5 — HarmonyOS PC (aarch64) 静态编译.

关键适配点:
- R26/R4: ncurses 是**系统同名库**(鸿蒙自带 libncursesw.so), 必须静态编译
  (--without-shared), 禁止构建 .so 动态库 (会污染系统 /lib /lib64 导致系统崩溃)
- E160: config.guess/sub 补丁识别 HarmonyOS (uname -s = HarmonyOS)
- HMDFS expr bug: 本平台 /usr/bin/expr 对 BRE 交替模式 "\\|" 返回垃圾字节,
  导致 config.status 计算 ac_dir/ac_top_srcdir 出错、子目录 Makefile 变量行
  被写坏 (随机高字节乱码, 含 "kk" 模式, 每次运行不同)。方案: configure 中
  as_expr="expr" -> as_expr="false", 强制走 echo|sed fallback (已本地验证)。
- HMDFS 权限: config.status 用 "umask 077 && mktemp" 建临时目录, HMDFS UID
  映射使 0700 目录对进程不可写 (Permission denied)。方案: 移除 umask 077,
  TMPDIR 指向预创建的可写目录。
- /system/bin/sh 执行 configure, 规避 hnp bash 兼容问题。
"""
import os

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "The ncurses (new curses) library - terminal handling for character-cell terminals"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    url = "https://github.com/mirror/ncurses"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0: ncurses 无外部依赖
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26/R4: 系统同名库强制静态编译 (禁止 .so 污染系统 /lib /lib64)
        if self.options.shared:
            tc.configure_args.append("--with-shared")
        else:
            tc.configure_args.append("--without-shared")
        tc.configure_args.append("--with-normal")
        tc.configure_args.append("--without-debug")
        tc.configure_args.append("--without-ada")
        tc.configure_args.append("--without-manpages")
        tc.configure_args.append("--without-cxx-binding")
        tc.configure_args.append("--enable-widec")
        tc.configure_args.append("--enable-overwrite")
        tc.generate()
        self._configure_args = list(tc.configure_args)

    def build(self):
        src = self.source_folder
        # E160: config.guess/sub 识别 HarmonyOS
        self.run("sed -i '/case $UNAME_SYSTEM in/a HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl ;;' config.guess", cwd=src)
        self.run("sed -i 's/ironclad\\*)/ironclad* | ohos*)/' config.sub", cwd=src)
        self.run("sed -i 's/uclibc\\*- )/uclibc*- | linux-ohos*- )/' config.sub", cwd=src)
        # HMDFS expr bug: /usr/bin/expr 对 "\\|" 交替模式返回垃圾,
        # 强制 as_expr=false 走 sed fallback (修复子目录 Makefile 变量行乱码)
        self.run("sed -i 's/^  as_expr=\"expr\"/  as_expr=\"false\"/' configure", cwd=src)
        # HMDFS 权限: 移除 config.status 建临时目录时的 umask 077
        self.run("sed -i 's/umask 077 && mktemp/mktemp/; s/umask 077 && mkdir/mkdir/' configure", cwd=src)
        # TMPDIR 指向可写目录 (HMDFS UID 映射限制)
        tmpdir = os.path.join(self.build_folder, ".ncurses-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        cfg = 'TMPDIR="{t}" /system/bin/sh ./configure {args}'.format(
            t=tmpdir, args=" ".join(self._configure_args))
        self.run(cfg, cwd=src)
        self.run("make -j1", cwd=src)

    def package(self):
        # 手动运行 make install (cwd 必须在源码目录, 那里有 Makefile)
        # --prefix=/ + DESTDIR=package_folder => 安装到 package/{bin,lib,include,share}
        # 必须 -j1: 并发会触发 GNU make jobserver (mkfifo), HMDFS 不支持
        self.run('make install DESTDIR="{d}" -j1'.format(d=self.package_folder),
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "ncursesw")
