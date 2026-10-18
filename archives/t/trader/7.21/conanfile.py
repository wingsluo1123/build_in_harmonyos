#!/usr/bin/env python3
"""Conan recipe for Star Traders (trader) 7.21 — HarmonyOS PC (aarch64).

Star Traders is a terminal-based interstellar trading game written in C,
built with the GNU Autotools (configure + make). It links against a
wide-character Curses library (NcursesW) and bundles a gnulib
replacement library (lib/libgnu.a).

OHOS adaptation notes (validated by a full local Linux configure+make,
see notes.md):
  - --disable-nls: 上游通过 AM_GNU_GETTEXT([external]) 引入外部 gettext
    (autopoint/msgfmt/libintl)。OHOS 无该工具链，且 --disable-nls 会让
    po/ 与 data/ 目录的 .desktop/.metainfo 生成目标变成 no-op（实测
    "Nothing to be done for all"），故直接禁用 NLS，避免外部 gettext 依赖。
  - --with-ncurses: 触发 AX_WITH_CURSES 的 NcursesW 检测分支。ncurses/6.6
    conan 依赖通过 PkgConfigDeps 暴露 ncursesw.pc（pkg_config_name=ncursesw），
    configure 经 pkg-config 找到宽字符 Curses。
  - settings.os 判断用 in ("Linux", "OHOS")（R32）。
  - 编译标志/编译器取自 Conan Toolchain（R33），不裸用 shell ${CC}。
  - --build/--host=aarch64-unknown-linux-gnu：trader 自带 config.guess
    (2024-07-27) 未含 HarmonyOS 分支；显式给 GNU 族主机三元组，让 AC_PROG_CC
    的编译器探针(conftest)在真机上能正常命中（与 anubis 配方同模式）。
    OHOS 编译器/ABI 由 Conan OHOS profile 提供。

R26: 终端游戏按静态链接约定，ncurses 配方默认 shared=False。
上游无自动化测试套件（无 TESTS/check_PROGRAMS/tests 目录，make check
为 no-op），见 test_package/MANIFEST.yml 的 upstream_test_audit。
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

import shlex


class TraderConan(ConanFile):
    name = "trader"
    version = "7.21"
    description = (
        "Star Traders: A Game of Interstellar Trading (terminal game, ncurses)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://www.zap.org.au/projects/trader/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 宽字符 Curses（NcursesW，含 colour）—— AX_WITH_CURSES 需要
        self.requires("ncurses/6.6", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"trader only supports Linux/OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 把 ncurses/6.6 的 ncursesw.pc 写入 generators folder，
        # 供 configure 内 AX_WITH_CURSES 的 pkg-config 探测使用。
        PkgConfigDeps(self).generate()
        # AutotoolsDeps 把 ncurses 依赖的 CPPFLAGS/LDFLAGS 注入 conanbuild env，
        # 供 configure 编译器探针与最终链接使用（与 anubis 配方同模式）。
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        # 平台诊断 [readonly_tmp]：OHOS 的 /tmp 只读，configure 编译器探针与
        # make 的临时文件若落到 /tmp 会失败（"C compiler cannot create
        # executables" / conftest 相关）。统一指到 Conan 构建目录下的私有 tmp，
        # 且必须显式创建该目录（仅 setenv 不会自动 mkdir；abx/anubis 同款）。
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        tc.generate(env=env)

    def _restore_helper_modes(self):
        # E490: 源码在 HMDFS 上解包可能丢失 autotools 辅助脚本的可执行位；
        # 恢复 configure/install-sh/config.guess/config.sub/missing 的 +x。
        for relative in (
            "configure",
            "config.guess",
            "config.sub",
            "install-sh",
            "missing",
            "depcomp",
            "mkinstalldirs",
        ):
            path = os.path.join(self.source_folder, relative)
            if os.path.isfile(path):
                os.chmod(
                    path,
                    os.stat(path).st_mode
                    | stat.S_IXUSR
                    | stat.S_IXGRP
                    | stat.S_IXOTH,
                )

    @staticmethod
    def _configure_args():
        # config.guess(2024-07-27) 未识别 HarmonyOS；显式给 GNU 族主机三元组。
        # 编译器/ABI 由 Conan OHOS profile (clang) 提供，此三元组仅供 configure
        # 的交叉判定走通（与 anubis 同模式）。
        return [
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--disable-nls",
            "--with-ncurses",
        ]

    def _fix_autoconf_umask_for_ohos(self):
        # E129/HMDFS + setgid（cyrus-sasl-scram 已验证模式）：autoconf 生成的
        # configure/config.status 用 `umask 077 && mktemp -d "./confXXXXXX"`
        # 创建临时目录，在 setgid 的 HMDFS 挂载上会得到 owner 不可写目录，
        # 于是 config.status 写 subs1.awk/subs1.sed 报 "Permission denied" /
        # "could not setup config files machinery"（真机日志即此错误，HMBS
        # 平台诊断 [unsafe_local_mktemp]）。
        #   前一轮用 mktemp PATH shim 强制 Autoconf 走 mkdir fallback 未生效：
        # ① HMBS_CAP_CHMOD=0 时新建 shim 文件无 +x，PATH 前缀解析不到它；
        # ② 即便命中，Autoconf 的 mkdir fallback 同样用 `umask 077`，会在同一
        #    setgid 挂载上再撞同墙。故改为从根因入手：把 configure/config.status
        #    里的 `umask 077` 就地改写为 `umask 022`（truncate+write 保留 inode
        #    +x，无需 chmod，HMBS_CAP_CHMOD=0 安全）。mktemp 路径照常成功，且
        #    mktemp/fallback 皆创建 owner 可写目录。
        #   只对本地 build 的源码树生效，不进安装产物，且仅当目标平台为 OHOS。
        if str(self.settings.os) != "OHOS":
            return
        for name in ("configure", "config.status"):
            path = os.path.join(self.source_folder, name)
            try:
                with open(path, "r", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    content = handle.read()
            except OSError:
                continue
            if "umask 077" not in content:
                continue
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape") as handle:
                handle.write(content.replace("umask 077", "umask 022"))
            self.output.info("autoconf umask 077->022 patched: %s" % path)

    def build(self):
        apply_conandata_patches(self)
        self._restore_helper_modes()
        # 平台诊断 [shell_getcwd]：profile buildenv 注入的 CONFIG_SHELL
        # （OHOS 系统 bash）在 HMDFS 挂载目录上 getcwd() 失败。仅写入 env 文件
        # 无法覆盖 profile 聚合 env（此前后已真机复现）；必须把
        # CONFIG_SHELL/SHELL 就近内联在 configure 命令前缀上，并在源码目录
        # (in-source build) 执行，彻底绕开 getcwd 风暴（同 anubis）。
        # 配置参数只用我们自己的静态列表，不追加 autotools._configure_args，
        # 避免工具链透传的 --host 与我方显式三元组冲突（同 anubis）。
        # 平台诊断 [unsafe_local_mktemp]：configure/config.status 内 `umask 077
        # && mktemp -d "./conf*"` 在 setgid HMDFS 上产生 owner 不可写临时目录；
        # 见 _fix_autoconf_umask_for_ohos()，把 umask 077 就地改 022（无需
        # 可执行 shim，chmod=0 安全），mktemp 路径照常建立可写目录。
        self._fix_autoconf_umask_for_ohos()
        cfg_cmd = (
            "CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh ./configure %s"
            % (" ".join(shlex.quote(a) for a in self._configure_args()))
        )
        self.run(cfg_cmd, env="conanbuild", cwd=self.source_folder)
        # 单 job 避免 HMDFS 上 make jobserver/FIFO 失败；in-source 构建
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)

    def package(self):
        # in-source 构建：install 到构建目录下的 staging，再按 Conan 应用包
        # 约定把 usr/local/bin 下的可执行文件映射到 package_folder/bin
        # （与 anubis 同模式，保证 test_package 以 bin/trader 定位安装产物）。
        staging = os.path.join(self.build_folder, "install-staging")
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging, exist_ok=True)
        self.run(
            "make install DESTDIR=%s prefix=/usr/local" % shlex.quote(staging),
            env="conanbuild",
            cwd=self.source_folder,
        )
        staging_bin = os.path.join(staging, "usr", "local", "bin")
        if os.path.isdir(staging_bin):
            copy(self, "*", src=staging_bin, dst=os.path.join(self.package_folder, "bin"))
        copy(
            self, "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # trader 是独立终端游戏二进制，不是库
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
