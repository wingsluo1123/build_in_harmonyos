#!/usr/bin/env python3
"""Conan recipe — fdm 2.2（终端邮件过滤/读取器，Autotools 自举类）。

适配要点（详见 notes.md）：
  1. 上游 tag 归档只有 configure.ac、没有 configure ⇒ build() 内 autoreconf 自举；
     构建工具面按 OHOS SDK 实况声明：只 tool_requires automake(提供 aclocal/automake)、
     libtool(提供 libtoolize)、bison(提供 yacc，parse.y → parse.c)；
     **不声明 autoconf/m4** —— conan 的 autoconf 会拉入 OHOS 构建的 perl/5.42.2，
     其 XS 模块与 SDK autoreconf 使用的 perl 5.42.0 解释器不兼容
     （`Perl_my_cxt_init: symbol not found`），而 SDK 已自带 autoconf 2.72/m4。
  2. musl regex.h 没有 REG_STARTEND（GNU/BSD 扩展），上游 re.c 编译期即报
     `use of undeclared identifier 'REG_STARTEND'`；按上游 MANUAL 的官方建议改用
     PCRE2 后端（`--enable-pcre2`，pcre.c），不做源码补丁、不引入平台宏。
  3. config.status 在 HMDFS 上以 `(umask 077 && mktemp -d ...)` 建临时目录，
     目录属主被映射、当前进程写不进 ⇒ E011：autoreconf 之后把 configure 里的
     `umask 077` 改为 `umask 022`（必须放在 autoreconf 之后，否则被重新生成覆盖）。
  4. config.guess 认不出 HongMeng/HarmonyOS 内核 ⇒ 显式传
     `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`。
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FdmConan(ConanFile):
    name = "fdm"
    version = "2.2"
    description = (
        "Terminal mail filtering and reading agent: fetches POP3/IMAP/NNTP/"
        "maildir/mbox/stdio mail and applies a filter rule tree"
    )
    license = "ISC"
    homepage = "https://github.com/nicm/fdm"
    url = "https://github.com/nicm/fdm"
    topics = ("mail", "pop3", "imap", "maildir", "filter")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"fdm supports Linux/OHOS, got {self.settings.os}")

    def requirements(self):
        # configure.ac 里 AC_SEARCH_LIBS 的硬依赖：tdb_open / gzflush / BIO_new / OPENSSL_init_ssl
        self.requires("tdb/1.4.15")
        self.requires("zlib/1.3.1.1")
        self.requires("openssl/3.5.6")
        # musl regex 无 REG_STARTEND ⇒ 走上游自带的 PCRE2 后端（见文件头 2.）
        self.requires("pcre2/10.48")

    def build_requirements(self):
        # CI/SDK 无 aclocal/automake/libtoolize；yacc 用于 parse.y → parse.c。
        # autoconf 与 m4 故意不声明（perl ABI 冲突，见文件头 1.）：由 SDK /data/service/hnp 提供。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("bison/3.8.2")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # 本版本无补丁（patches: {}），保留标准挂点以兼容补丁管线
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            # 上游官方提供的 PCRE2 后端（MANUAL: "I'm building on Linux and it
            # complains about REG_STARTEND ... or use PCRE"）
            "--enable-pcre2",
        ])
        tc.generate()

    def build(self):
        # ⓪ 无补丁时为空操作；保留标准调用以兼容补丁管线（G1/CI 一致性）
        apply_conandata_patches(self)

        # ① tag 归档无 configure：在源码目录内自举（AC_CONFIG_AUX_DIR(etc) 需要该目录已存在）。
        #    conanbuild 环境已由 automake/1.18 的 buildenv 提供只含纯 Perl 模块的
        #    PERL5LIB（其 share/automake-*），与 SDK perl 5.42.0 兼容；autoreconf/autoconf
        #    由 SDK 提供（PATH 首位），aclocal/automake 由 conan automake 提供（$ACLOCAL/$AUTOMAKE）。
        self.run(
            'mkdir -p etc && autoreconf -fi',
            cwd=self.source_folder,
            env="conanbuild",
        )

        # ② E011：HMDFS 上 config.status 的 `(umask 077 && mktemp -d ...)` 临时目录不可写。
        #    必须在 autoreconf 之后修改，否则会被重新生成的 configure 覆盖。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # 上游无测试套件（Makefile.am 无 TESTS/check_PROGRAMS、无 tests/ 目录）：
        # make check 目标存在但无用例，仍执行以给出"上游 N=0"的实测证据。
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # 纯命令行工具：无头文件、无库
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
