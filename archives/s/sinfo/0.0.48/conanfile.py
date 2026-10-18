#!/usr/bin/env python3
"""Conan recipe — sinfo 0.0.48

sinfo — distributed system information (Jürgen Rinas): the sinfod daemon
measures and broadcasts/serves per-host system load, memory usage and top
processes; `sinfo` is the ncurses/CLI client that queries and displays them.
Upstream homepage is dead (http://www.ant.uni-bremen.de/whomes/rinas/sinfo/
302s to the faculty page since ~2016); the pristine orig tarball preserved
in the Debian pool is the canonical distribution and is used here (R39),
sha256 cross-checked against the signed Debian .dsc.

License: GPL-2.0 (upstream COPYING is the plain GPLv2 text).

适配要点：
- 上游 2014 年 orig tarball 已预生成 configure/Makefile.in（免 autoreconf）；
- tarball 内的 config.guess/config.sub（2014 版）不认识 HarmonyOS /
  linux-ohos → 补丁 0002 给 config.guess 注入自终止的 *:HarmonyOS:*:*
  分支，补丁 0003 让 config.sub 两处 pattern 接受 linux-ohos
  （jpegoptim 同款三补丁组合）；
- configure 里 `umask 077 && mktemp -d ./confXXXXXX` 在 HMDFS 上触发
  E011（临时目录属主映射 UID 与进程 UID 不同 → config.status 写
  subs1.awk Permission denied）→ 补丁 0001 改 umask 022；
- configure.ac 的 AX_BOOST_SIGNALS/AX_BOOST_SYSTEM 是 autoconf-archive
  老宏，对 Boost 1.84 已无意义：
  * Signals v1（boost/signals.hpp）已在 Boost 1.74 删除，代码实际只用
    header-only 的 Boost.Signals2（boost/signals2.hpp）；
  * Boost.System 自 1.69 起 header-only，制品仓 boost/1.84.0 也只构建
    filesystem/regex/program_options/iostreams 四个编译库（无
    libboost_system）；
  两个宏找不到库都会 AC_MSG_ERROR → 传 --with-boost-signals=no
  --with-boost-system=no 跳过这两次已废弃的找库检查；
- Boost 1.84 bind 严格化：ServerConnectorBase::sendMessageSignal 是全库唯一
  的按值 signals2 信号（void (Message)），它连接的成员槽
  queueAndSendMessageSlot(Message&) 以非 const 左值引用收参——信号以右值
  调用槽，Boost 1.84 的 bind 对 mf1<void, C, Message&> 无可行重载（编译
  错误）→ 补丁 0004 把槽签名改为 const Message&（全库唯一一处该形态，
  其余信号/槽组合均为左值引用信号 → 引用/const 引用/按值槽，天然兼容）；
- AC_FUNC_MALLOC 交叉编译时默认按 malloc(0)==NULL 处理，config.h 会
  `#define malloc rpl_malloc`，sinfo/ 下 7 个包含 config.h 的翻译单元
  链接期炸 rpl_malloc 未定义 → configure_vars 注入
  ac_cv_func_malloc_0_nonnull=yes（musl/glibc malloc(0) 语义一致）；
- MP_WITH_CURSES（AX_WITH_CURSES 的 AU_ALIAS）探测 conan ncurses
  （平铺 ncurses.h + 仅 libncursesw）：-lncursesw 链接通过 +
  ncurses.h 头文件测试通过 → CURSES_LIB=-lncursesw、HAVE_NCURSES_H，
  与 sinfocurses.h 的 #ifdef 分支吻合；其后 AC_CHECK_LIB(ncurses,
  use_default_colors) 因包内只有宽字符库而失败 → HAVEDEFAULTCOLORS
  不定义，use_default_colors() 走 #ifdef 守卫优雅降级（仅终端底色）；
- 上游布局 sinfo(客户端) → bin/、sinfod(守护) → sbin/；Conan 2
  AutotoolsToolchain 默认以 --sbindir=${prefix}/bin 重定向，两二进制同落
  bin/（package_info 以 bindirs=["bin"] 暴露）；lib/sinfo/ 下的 pkglib
  静态归档是上游内部支持库，不作为公开链接接口（libs=[]、libdirs=[]）；
- R9: make -j1（HMDFS 不允许 jobserver FIFO，E074）。
"""
import io
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class SinfoConan(ConanFile):
    name = "sinfo"
    version = "0.0.48"
    description = "Distributed system information: sinfod daemon broadcasts/serves per-host load, memory usage and top processes; sinfo is the ncurses/CLI client"
    license = "GPL-2.0"
    homepage = "http://www.ant.uni-bremen.de/whomes/rinas/sinfo/"
    url = "http://www.ant.uni-bremen.de/whomes/rinas/sinfo/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        # R32: settings.os must accept Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only asio/signals2/system/bind/date_time → boost/1.84.0
        # （configure.ac AX_BOOST_BASE([1.36]) 强制检查，制品仓已有 OHOS 二进制）
        self.requires("boost/1.84.0")
        # sinfo 客户端 ncurses 界面（AX_WITH_CURSES 探测到 -lncursesw，静态，R26）
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Debian pool 保留的 pristine orig tarball（与签名 .dsc 的 sha256 一致）
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 终端工具默认静态链接（依赖链由 Conan 管理）
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 跳过两个对 Boost 1.84 已无意义的找库检查（详见类注释）
        tc.configure_args.append("--with-boost-signals=no")
        tc.configure_args.append("--with-boost-system=no")
        # AC_FUNC_MALLOC 交叉编译默认会把 malloc 宏替换成 rpl_malloc（链接期未定义）；
        # ac_cv_* 缓存变量按 autoconf 惯例以 VAR=VALUE 命令行参数形式传入
        tc.configure_args.append("ac_cv_func_malloc_0_nonnull=yes")
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9/E074: HMDFS 不允许创建 jobserver FIFO
        autotools.make(args=["-j1"])
        self._run_upstream_check()

    def _run_upstream_check(self):
        """上游 `make check` 的实质用例：**全部 3 个** noinst_PROGRAMS 测试程序。

        上游树里的测试程序共 3 个（评审 2026-10-15 实测 N=3，此前本 PR 只申报 1 个，
        属少报，现改正）：

          1. libmessage/testmessage/testmessage        —— check_DATA 规则消费它，
             输出与 testmessage.out.approved 黄金文件逐字 diff；
          2. libmessage/testmessage/testmessage2       —— 同为 noinst_PROGRAMS，
             不被 check_DATA 消费，无黄金文件；
          3. libsinfotypes/teststringandnumericcomparison —— 同为 noinst_PROGRAMS，
             无黄金文件。

        为什么不由 conan 直接调 `make check`：automake 生成的 check_DATA 规则依赖
        `tee` 与 `diff` 两个外部程序，运行时走的还是 libtool 包装脚本（/bin/sh 脚本）；
        本仓既有结论是 OHOS CI worker 的 PATH 不保证有系统 bin 目录（sh/curl 都找不到）。
        这里改为用 Python subprocess 直接执行 build 树里**真链接出来的** ELF 并自行比对：
        第 1 个按上游判据做黄金文件逐字 diff，第 2/3 个按「退出码 0 且输出非空」判定
        （它们没有黄金文件，这是上游能给的全部判据）。
        """
        import subprocess

        # (相对路径, 说明, 黄金文件相对路径或 None)
        cases = [
            ("libmessage/testmessage/testmessage",
             "libmessage 消息序列化回归（上游 check_DATA：与 testmessage.out.approved 逐字 diff）",
             os.path.join("libmessage", "testmessage", "testmessage.out.approved")),
            ("libmessage/testmessage/testmessage2",
             "libmessage testmessage2（noinst_PROGRAMS，无黄金文件）",
             None),
            ("libsinfotypes/teststringandnumericcomparison",
             "libsinfotypes 字符串/数值比较回归（noinst_PROGRAMS，无黄金文件）",
             None),
        ]

        env = dict(os.environ)
        libdirs = [os.path.join(self.build_folder, "libmessage", ".libs"),
                   os.path.join(self.build_folder, "libsinfotypes", ".libs")]
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d for d in libdirs if os.path.isdir(d)] + ([prev] if prev else []))

        passed, failures = 0, []
        for rel, desc, approved_rel in cases:
            base = os.path.join(self.build_folder, rel)
            exe = None
            for cand in (base, os.path.join(os.path.dirname(base), ".libs",
                                            os.path.basename(base))):
                if os.path.isfile(cand):
                    with open(cand, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            exe = cand
                            break
            if exe is None:
                failures.append("%s：未能找到可执行体（%s）" % (rel, base))
                continue

            try:
                proc = subprocess.run([exe], stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, env=env, timeout=900)
            except OSError as exc:
                failures.append("%s：无法执行（%s）" % (rel, exc))
                continue

            got = proc.stdout.decode("utf-8", "replace")
            self.output.info("sinfo upstream check [%s] rc=%d stdout=%d bytes"
                             % (rel, proc.returncode, len(proc.stdout)))
            if proc.returncode != 0:
                failures.append("%s：退出码 %d，stderr=%s"
                                % (rel, proc.returncode,
                                   proc.stderr.decode("utf-8", "replace")[:400]))
                continue
            if not got.strip():
                failures.append("%s：退出码 0 但输出为空（视为无效执行）" % rel)
                continue
            if approved_rel:
                approved = os.path.join(self.source_folder, approved_rel)
                if not os.path.isfile(approved):
                    failures.append("%s：黄金文件缺失（%s）" % (rel, approved))
                    continue
                with open(approved, encoding="utf-8", errors="replace") as fh:
                    want = fh.read()
                if got != want:
                    gl, wl = got.splitlines(), want.splitlines()
                    detail = "长度 %d vs %d" % (len(gl), len(wl))
                    for i in range(max(len(gl), len(wl))):
                        g = gl[i] if i < len(gl) else "<EOF>"
                        w = wl[i] if i < len(wl) else "<EOF>"
                        if g != w:
                            detail = "第 %d 行\n  got : %r\n  want: %r" % (i + 1, g, w)
                            break
                    failures.append("%s：与黄金文件不一致（%s）" % (rel, detail))
                    continue
                self.output.info("sinfo upstream check [%s] 与 %s 逐字一致"
                                 % (rel, approved_rel))
            passed += 1
            self.output.info("sinfo upstream check PASS [%s] %s" % (rel, desc))

        total = len(cases)
        self.output.info("sinfo upstream check SUMMARY: %d/%d passed" % (passed, total))
        if failures:
            raise ConanException(
                "sinfo: 上游测试程序未全部通过（%d/%d）：\n  - %s"
                % (passed, total, "\n  - ".join(failures)))

    def package(self):
        autotools = Autotools(self)
        # -j1（house 规则 E074）：install 阶段默认沿用 tools.build:jobs（worker 上 -j20），
        # 而并行 make 需要创建 jobserver fifo、worker 拒绝该操作（"jobserver mkfifo ...
        # Operation not permitted"），轻则报错、重则让 make 误判目标已完成而**静默什么都
        # 不装**（同批 istgt/0.4-20111008 正是这样产出空壳包，见其 CI #94874 系列）。
        # 仓内同类先例：meterec/0.9.3、smartlist/3.15、json-parser/1.1.0 均用
        # autotools.install(args=["-j1"])。只降低安装阶段并行度，不影响产物内容与测试。
        autotools.install(args=["-j1"])
        # GPL-2.0 许可证文件
        license_src = os.path.join(self.source_folder, "COPYING")
        if os.path.isfile(license_src):
            copy(self, "COPYING", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # sinfo(客户端)与 sinfod(守护)均落 bin/（Conan 工具链默认把
        # --sbindir 重定向到 ${prefix}/bin）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # lib/sinfo/ 下的 pkglib 静态归档是上游内部支持库，非公开链接接口
        self.cpp_info.libdirs = []
