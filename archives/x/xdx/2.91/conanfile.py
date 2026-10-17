#!/usr/bin/env python3
"""Conan recipe for xdx 2.91 — DX cluster client for amateur radio (GTK3).

xdx is a telnet DX-Cluster / Reverse Beacon Net client for the X Window
System, written in C and built with GNU Autotools on top of GTK+ 3.

Notes for the OHOS / OpenHarmony cross build:
  * The upstream release tarball already ships a generated `configure`
    script, so no autoconf/automake bootstrap is required.
  * xdx calls AM_GNU_GETTEXT([external]); the OHOS toolchain has no
    `msgfmt`, so Native Language Support is disabled (--disable-nls).
    UI strings simply fall back to their untranslated (English) form and
    the source guards <libintl.h> behind #ifdef ENABLE_NLS, so no gettext
    build/runtime dependency is pulled in.
"""
import os

from conan import ConanFile
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.files import get, copy, save


class XdxConan(ConanFile):
    name = "xdx"
    version = "2.91"
    description = "Xdx - DX cluster client for amateur radio (telnet DX-Cluster / RBN)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/N0NB/xdx"
    url = "https://github.com/N0NB/xdx"
    topics = ("hamradio", "dx-cluster", "gtk", "amateur-radio")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    requires = "gtk/3.24.43"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # No gettext (msgfmt) in the OHOS toolchain -> disable NLS.
        tc.configure_args.append("--disable-nls")
        # The 2022-era bundled config.sub/config.guess do not recognise the
        # "ohos" OS in the canonical cross triplet (aarch64-linux-ohos), so
        # autoconf aborts ("system `ohos' not recognized").  Override the host
        # triplet with a value config.sub accepts; the real OHOS clang (set via
        # tools.build:compiler_executables in the profile) is still used for
        # every compiler/linker invocation, so the produced binary targets OHOS.
        tc.configure_args.append("--host=aarch64-linux-gnu")
        # --build: CI 的真实 OHOS worker 上 `config.guess`（2018-02-24 版）跑
        # `uname -s` 得到 HarmonyOS，直接以 "unable to guess system type" 退出，
        # autoconf 随即报 "cannot guess build type; you must specify one"
        # （CI #94742, 2026-10-16 13:34）。显式给出 build 三元组即可跳过
        # config.guess；本机 WSL（uname 为 Linux）不会触发，故此前只在 CI 暴露。
        # house 先例 meterec/0.9.3 的同时给出 --build/--host 写法。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def _fix_hmdfs_umask(self, path):
        """HMDFS：config.status 在 umask 077 下创建的临时目录/脚本对构建进程不可用。

        仓内既有处置（quagga / vimpc / istgt 同款）：把 configure 与生成的 config.status
        里的 `umask 077` 改成 `umask 022`。本包在 CI #95097（2026-10-16 17:24）正是死在
        这一步：

            ./config.status: line 628: ./confGMoajN/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery

        即 config.status 在临时目录里生成并执行 awk 辅助脚本时被拒（HMDFS 的 umask/uid 映射
        场景）。只改这一处权限设置，不改上游逻辑。
        """
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if "umask 077" in content:
            save(self, path, content.replace("umask 077", "umask 022"))
            self.output.info("HMDFS umask fix applied to %s" % os.path.basename(path))

    def build(self):
        autotools = Autotools(self)
        # configure 自身也会用 `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录并在其中
        # 生成/执行 subs1.awk 这类辅助脚本，故 configure 与随后生成的 config.status 都要改。
        self._fix_hmdfs_umask(os.path.join(self.source_folder, "configure"))
        autotools.configure()
        self._fix_hmdfs_umask(os.path.join(self.build_folder, "config.status"))
        # -j1（house 规则 E074）：worker 上并行 make 需要创建 jobserver fifo，
        # 该操作在 HMDFS/worker 上被拒（"jobserver mkfifo … Operation not permitted"），
        # 轻则报错、重则让 make 误判目标已完成而**什么都不做**
        # （istgt 的 make install 就是这样静默产出空壳包的，见 CI #94783）。
        # 先例：json-parser/1.1.0、meterec/0.9.3、vfu/5.09 等。
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(self, "COPYING", self.source_folder, self.package_folder + "/licenses")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
