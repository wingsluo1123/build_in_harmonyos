#!/usr/bin/env python3
"""Conan recipe — tdbcodbc 1.1.14 (TDBC 的 ODBC 驱动桥).

上游构建系统: TEA (autotools)。tdbcodbc 不是独立可执行程序，而是 Tcl 扩展包：
构建期需要 tcl 的 tclConfig.sh 与 tdbc 的 tdbcConfig.sh（含 stub 库/头文件规格），
运行期由 tclsh dlopen 本包共享库（OHOS 上为 libtdbcodbc1.1.14.so），并在首次 ODBC 调用时再 dlopen ODBC
驱动管理器（libodbc.so.2）与安装器库（libodbcinst.so.2）。

与 unixODBC 的关系（本包最容易误判的一点）：上游用 generic/fakesql.h 自带一份
ODBC 类型/常量声明，用 generic/odbcStubInit.c 在运行期 dlopen + Tcl_FindSymbol
逐个解析 30 个 SQL* 符号，因此**链接期完全不依赖 unixODBC**（产物 DT_NEEDED
只有 libc.so）。但运行期驱动管理器必须可 dlopen，否则 GetHEnv() 里
OdbcInitStubs() 返回 NULL，所有 tdbc::odbc::* 调用直接失败 —— 所以 unixodbc
仍然必须声明为 requires，并在 generate() 里补进 build 环境的 LD_LIBRARY_PATH。

OHOS(HarmonyOS PC) 适配点（全部在本配方 build()/generate() 内复现，见 notes.md）:
  1. autoconf 生成的 config.status 用 `umask 077` 建临时目录并写 subs1.awk ——
     HMDFS 权限归一化后不可访问，configure 直接 Permission denied（与
     tdbc/1.1.14、tcl/8.6.16 的 E011 同源）。→ patches/0001-configure.patch 改 022。
  2. TEA 的 tcl.m4 没有 HarmonyOS 分支，`uname -s` 得到
     "HarmonyOS-HongMeng Kernel ..." → SHLIB_LD/SHLIB_SUFFIX 为空，共享库链接
     命令残缺。→ 传 `tcl_cv_sys_version=Linux-6.6` 走官方 Linux 分支。
  3. TEA_PREFIX 在未显式给 --exec_prefix 时会继承 tclConfig.sh 的
     TCL_EXEC_PREFIX，导致 pkglibdir 落进 tcl 依赖包目录。→ 显式
     --prefix/--exec_prefix，安装全部经 DESTDIR 落到本包 staging。
  4. 【本包新增】tdbcConfig.sh 里记录的是 tdbc **打包时**的 prefix
     (/usr/local) 和 tdbc 构建机的 conan cache 绝对路径，不是本机构建时
     tdbc 包的真实目录：
         tdbc_INCLUDE_SPEC="-I/usr/local/include"
         tdbc_STUB_LIB_SPEC="-L/usr/local/lib/tdbc1.1.14 -ltdbcstub1.1.14"
     TEA_LOAD_CONFIG 是在 configure 内部 `.` source 该文件的，命令行覆盖会被
     source 覆盖掉，无法用 VAR=... 直接改。→ 用 CPPFLAGS/LDFLAGS 补真实路径：
     tcl.m4 会把 CPPFLAGS 并入 CFLAGS（编译规则含 $(CPPFLAGS)/$(CFLAGS)），
     MAKE_SHARED_LIB 含 ${LDFLAGS}，于是 -I/-L 都到达真实的 tdbc 包目录，
     而失效的 -I/usr/local/include、-L/usr/local/lib/tdbc1.1.14 只是无害冗余项。
  5. 【本包新增】build() 内的 `make test` 跑在 conanbuild 环境里，而 unixodbc
     没有声明 buildenv_info（tcl 声明了 LD_LIBRARY_PATH，unixodbc 没有）→
     dlopen("libodbc.so.2") 找不到驱动管理器。→ generate() 里显式把 unixodbc
     的 libdir 前置进 build 作用域的 LD_LIBRARY_PATH。
  6. OHOS 不支持 make jobserver 的 mkfifo（Operation not permitted）→ -j1。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# TEA 安装前缀（必须绝对路径）；实际安装落点由 DESTDIR=staging 决定，
# 不写入共享系统前缀（R49/PF6）
INSTALL_PREFIX = os.path.join(os.sep, "usr", "local")
# TEA 需要知道目标系统；OHOS 的 uname 输出无对应分支，显式给 Linux 缓存变量
TEA_SYS_VERSION = "Linux-6.6"
# 本机交叉验证时的 host 三元组：必须带 vendor 位，否则 host_os=ohos 不匹配
# libtool/autoconf 的 linux* 分支（见 archives/s/scws/1.2.3 notes.md）
OHOS_HOST_TRIPLET = "aarch64-unknown-linux-ohos"


class TdbcOdbcConan(ConanFile):
    name = "tdbcodbc"
    version = "1.1.14"
    description = (
        "TDBC ODBC driver — 把 Tcl Database Connectivity 桥接到任意 ODBC "
        "驱动管理器/驱动（unixODBC + 任意 ODBC 驱动）"
    )
    license = "TCL"
    homepage = "https://core.tcl-lang.org/tdbcodbc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("tcl", "database", "tdbc", "odbc")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # tcl：构建期 tclConfig.sh / tcl.h / libtclstub8.6.a，运行期 tclsh +
        # libtcl8.6.so（TclOO 内置）
        self.requires("tcl/8.6.16")
        # tdbc：构建期 tdbcConfig.sh / tdbc.h / libtdbcstub1.1.14.a，
        # 运行期 library/tdbcodbc.tcl 里 `package require tdbc`
        self.requires("tdbc/1.1.14")
        # unixODBC：纯运行期依赖。链接期不需要（fakesql.h + dlopen 符号表），
        # 但首次 ODBC 调用必须能 dlopen libodbc.so.2 / libodbcinst.so.2
        self.requires("unixodbc/2.3.12")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # build() 内 `make test` 需要 dlopen unixODBC 驱动管理器，而 unixodbc
        # 未声明 buildenv_info → conanbuild 环境里没有它的 libdir（适配点 5）
        odbc_libdir = os.path.join(
            self.dependencies["unixodbc"].package_folder, "lib"
        )
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", odbc_libdir)
        env.vars(self, scope="build").save_script("tdbcodbc_odbc_libpath")
        VirtualBuildEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def _tdbc_paths(self):
        """返回 tdbc 依赖包里真实的 pkglibdir（含 tdbcConfig.sh 与 stub 库）。"""
        tdbc_dep = self.dependencies["tdbc"]
        tdbc_version = str(tdbc_dep.ref.version)
        pkglib = os.path.join(tdbc_dep.package_folder, "lib", f"tdbc{tdbc_version}")
        if not os.path.isfile(os.path.join(pkglib, "tdbcConfig.sh")):
            raise ConanException(f"tdbc 依赖包中未找到 tdbcConfig.sh: {pkglib}")
        return pkglib, os.path.join(tdbc_dep.package_folder, "include")

    def build(self):
        # patches/0001-configure.patch：config.status 临时目录 umask 077 → 022
        apply_conandata_patches(self)

        tcl_folder = self.dependencies["tcl"].package_folder
        tdbc_pkglib, tdbc_incdir = self._tdbc_paths()
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c", "clang")
        shared = "yes" if self.options.shared else "no"

        configure_args = [
            f"--prefix={INSTALL_PREFIX}",
            f"--exec_prefix={INSTALL_PREFIX}",
            f'--with-tcl="{os.path.join(tcl_folder, "lib")}"',
            f'--with-tdbc="{tdbc_pkglib}"',
            f"--enable-shared={shared}",
            f"CC={cc}",
            # 适配点 2：TEA tcl.m4 无 HarmonyOS 分支
            f"tcl_cv_sys_version={TEA_SYS_VERSION}",
            # 适配点 4：tdbcConfig.sh 内的 /usr/local 规格失效，补真实路径
            f"CPPFLAGS=-I{tdbc_incdir}",
            f"LDFLAGS=-L{tdbc_pkglib}",
        ]
        if not can_run(self):
            # 本机（macOS 开发机）交叉验证分支。判据用 can_run() 而不是
            # cross_building()：ohc 工具链（conan-verify / W3 / build_and_test.sh）
            # 对 -pr:h 与 -pr:b 传同一个 profile，host==build 使 cross_building()
            # 恒为 False；ohos-local profile 里的
            # `tools.build.cross_building:can_run=False` 才是"产物不能在本机执行"
            # 的权威信号。CI worker 用 ci/conan/profiles/ohos-aarch64（无该 conf，
            # 原生构建）→ can_run=True → 本分支不生效，与 tdbc/1.1.14 完全一致。
            configure_args += [
                f"--host={OHOS_HOST_TRIPLET}",
                "AR=llvm-ar",
                "RANLIB=llvm-ranlib",
                # AC_CHECK_SIZEOF 在无法执行编译产物时拿不到结果，需给缓存值
                "ac_cv_sizeof_long=8",
                "ac_cv_sizeof_long_long=8",
            ]

        # HMDFS 上 configure 可能丢失执行位，统一经 bash 调用
        self.run(
            f'cd "{self.source_folder}" && bash configure {" ".join(configure_args)}',
            env="conanbuild",
        )
        # OHOS 不支持 make jobserver 的 mkfifo（Operation not permitted）→ -j1
        self.run(f'cd "{self.source_folder}" && make -j1', env="conanbuild")

        self._run_upstream_tests()

        staging = os.path.join(self.build_folder, "staging")
        self.run(
            f'cd "{self.source_folder}" && make install DESTDIR="{staging}"',
            env="conanbuild",
        )

    def _run_upstream_tests(self):
        """真实运行上游 tcltest 套件（tests/all.tcl）并校验通过率。

        上游 `make test` = test-jet + test-sqlserver + test-sqlite 三个后端，
        各自以不同的 TDBCODBC_TEST_TYPE 跑一遍 tests/all.tcl：
          - jet / sqlserver：tests/tdbcodbc.test 自身硬编码为 Windows-only，
            非 Windows 平台直接 cleanupTests + return（0 用例）；
          - sqlite：Unix 默认后端，需要一个注册进 unixODBC 的 "SQLite3" 驱动。
        制品仓没有任何 ODBC 驱动（unixODBC 只提供驱动管理器），因此 connect
        约束为假，套件在 tests/tdbcodbc.test:158 自行 return（"tests requiring
        a db connection skipped."）。清点与探测证据见 notes.md。
        """
        if not can_run(self):
            self.output.info(
                "L1_UPSTREAM_RESULT: skipped=can_run_false"
                "（本机交叉构建，OHOS 产物不可执行；CI worker 原生构建时执行）"
            )
            return

        test_log = os.path.join(self.build_folder, "upstream_test.log")
        rc = self.run(
            f'cd "{self.source_folder}" && make test TESTFLAGS="-verbose pass"'
            f" > {test_log} 2>&1",
            env="conanbuild",
            ignore_errors=True,
        )
        with open(test_log, encoding="utf-8", errors="ignore") as handle:
            log_text = handle.read()

        # 三个后端各输出一条 tcltest 汇总行；jet/sqlserver 恒为 0
        summaries = re.findall(
            r"^all\.tcl:\s+Total\s+(\d+)\s+Passed\s+(\d+)\s+"
            r"Skipped\s+(\d+)\s+Failed\s+(\d+)",
            log_text,
            re.MULTILINE,
        )
        if not summaries:
            raise ConanException(
                f"上游测试未产生 tcltest 汇总行（rc={rc}），请查看 {test_log}"
            )
        totals = [sum(int(row[i]) for row in summaries) for i in range(4)]
        total, passed, skipped, failed = totals
        cases = re.findall(r"^\+\+\+\+ (\S+) PASSED", log_text, re.MULTILINE)
        self.output.info(
            f"L1_UPSTREAM_RESULT: backends={len(summaries)} total={total} "
            f"passed={passed} skipped={skipped} failed={failed} "
            f"cases={len(cases)}"
        )
        if failed:
            raise ConanException(
                f"上游测试失败: Total={total} Passed={passed} Skipped={skipped} "
                f"Failed={failed}（详见 {test_log}）"
            )
        # sqlite 后端必须真的跑起来（3 条无连接用例通过 + 1 条 connect 约束跳过），
        # 否则说明测试入口本身坏了，不能静默当成"全部跳过"
        if total < 4 or passed < 3:
            raise ConanException(
                f"sqlite 后端未按预期执行（total={total} passed={passed}，"
                f"期望 total>=4 且 passed>=3），详见 {test_log}"
            )

    def package(self):
        staging_prefix = os.path.join(
            self.build_folder, "staging", INSTALL_PREFIX.lstrip("/")
        )
        if not os.path.isdir(staging_prefix):
            raise ConanException(f"make install 未产生 staging 目录: {staging_prefix}")
        # staging/usr/local/{lib/tdbcodbc1.1.14,include,share/man} → 保留相对结构
        copy(self, "*", src=staging_prefix, dst=self.package_folder)
        for artifact in ("lib", "include"):
            if not os.path.isdir(os.path.join(self.package_folder, artifact)):
                raise ConanException(f"包内缺少 {artifact}/（staging={staging_prefix}）")
        pkglib = os.path.join(
            self.package_folder, "lib", f"tdbcodbc{self.version}", "pkgIndex.tcl"
        )
        if not os.path.isfile(pkglib):
            raise ConanException(f"包内缺少 Tcl 包索引: {pkglib}")

    def package_info(self):
        # Tcl 包的标准消费方式：pkgIndex.tcl 由 tclsh 经 auto_path/TCLLIBPATH 发现。
        # 纯库包（无 bin/ 可执行产物），故不声明 bindirs（R38/CI L0k 据此判库）
        self.cpp_info.includedirs = ["include"]
        # 共享库在 OHOS 原生构建下名为 libtdbcodbc1.1.14.so（tcl.m4 的
        # TEA_PLATFORM=unix 分支给 PACKAGE_LIB_PREFIX8="lib"；本机带 --host 的
        # 交叉构建会得到无前缀的 tdbcodbc1.1.14.so，pkgIndex.tcl 与产物名始终
        # 由同一次 configure 生成，两侧各自自洽）。消费者不直接链接它 —— 由
        # tclsh 经 pkgIndex.tcl 以绝对路径 dlopen，故不声明 cpp_info.libs
        self.cpp_info.libdirs.append(os.path.join("lib", f"tdbcodbc{self.version}"))
        for environment in (self.buildenv_info, self.runenv_info):
            environment.prepend_path(
                "TCLLIBPATH", os.path.join(self.package_folder, "lib")
            )
