#!/usr/bin/env python3
"""Conan 2 recipe — istgt 0.4-20111008 (iSCSI target daemon, autotools).

istgt 是 userspace iSCSI target（RFC 3720）+ SPC-3 逻辑单元仿真：预生成的
2011 年代 autotools tarball（configure + Makefile.in，无需 autogen），构建
两个可执行文件 bin/istgt（守护进程）与 bin/istgtcontrol（uctl 控制工具），
make install 另带 etc/istgt 样例配置与 share/man/man1/istgt.1。

上游依赖检查（configure.in）：pthread / crypto(MD5_Update) / cam(可选,
FreeBSD)；唯一外部 conan 依赖是 openssl（libcrypto，MD5_Init/MD5_Update/
MD5_Final 见 src/istgt_md5.c）。

OHOS 适配要点：
- configure.in 无 AC_CANONICAL_HOST → 不运行 config.guess/config.sub，
  无需 E007 补丁（与 icecast 2.4.4 的关键差异）。
- 本仓 AutotoolsToolchain 不聚合依赖 cpp_info 进 CPPFLAGS/LDFLAGS
  （house 先例 callisto/rawtran）→ 显式注入 openssl 的 -L/-I，并把依赖
  libdir 以 RPATH 嵌入（house 先例 icecast：L2 smoke 裸跑无
  LD_LIBRARY_PATH）。
- openssl 固定 1.1.1w：2011 代码用经典 MD5_Init/MD5_Update/MD5_Final
  底层 API（OpenSSL 3.x deprecated 但保留，4.0 移除）。
- AC_CHECK_LIB([cam])（FreeBSD CAM）在 OHOS 缺失且可选（HAVE_LIB_CAM
  守卫）；AC_PATH_PROG(MKDEP) 为空，src/Makefile.in 第 100 行有空值守卫。
- OHOS musl 不导出 POSIX 线程取消族：<pthread.h> 不声明、libc.so 不导出
  pthread_cancel/setcancelstate/testcancel，且 sysroot 的 libpthread.a 是
  空壳（-lpthread 解不了符号）→ 补丁 0001 引入 HAVE_PTHREAD_CANCEL 特性宏，
  配方对 OHOS 传 -DHAVE_PTHREAD_CANCEL=0（补丁内不含平台宏；缺省 1 = 上游
  原行为）。house 先例 xmcd 3.3.2，知识条目
  knowledge/drafts/musl-pthread-cancel-gap/。
- build() 末尾 _smoke()：直接执行 in-tree 的 aarch64 二进制（binfmt qemu）
  验证 istgt -V / istgtcontrol -V（CI L1c 口径；上游无测试套件）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IstgtConan(ConanFile):
    name = "istgt"
    version = "0.4-20111008"
    description = ("istgt iSCSI target daemon (RFC 3720) with SPC-3 logical "
                   "unit emulation")
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/istgt/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # conandata.yml 无补丁段（上游零修改）；保留钩子（L0q 口径）
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"istgt supports Linux and OHOS, not {self.settings.os}"
            )
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "istgt currently verified on OHOS armv8 (aarch64)"
            )

    def requirements(self):
        # libcrypto（MD5）：1.1.1w 保留 2011 代码所用的经典 MD5_* 底层 API
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)
        # 2011 年代的 src/Makefile.in 用 .SUFFIXES 后缀规则（.c.o），后缀规则
        # 不查 VPATH：out-of-tree 构建找不到源码（W3 第 1 轮实测
        # "No rule to make target 'istgt.c'"）。in-source 布局（quagga 1.2.4
        # 先例同法）同时规避 CI worker 的 HMDFS getcwd 风暴（E386）。
        self.folders.build = ""
        self.folders.generators = "conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # House 规则：本仓 AutotoolsToolchain 不聚合依赖 cpp_info 进
        # CPPFLAGS/LDFLAGS（先例 callisto/rawtran）：
        #  - AC_CHECK_LIB(crypto, MD5_Update) 探测需要 -L<openssl>/lib；
        #  - <openssl/md5.h> 需要 -I<openssl>/include；
        #  - 最终链接的 libcrypto.so 由 RPATH 兜底（L2 smoke 裸跑无
        #    LD_LIBRARY_PATH，先例 icecast）。
        try:
            openssl = self.dependencies["openssl"]
            agg = openssl.cpp_info.aggregated_components()
            for ld in agg.libdirs:
                tc.extra_ldflags.append("-L%s" % ld)
                tc.extra_ldflags.append("-Wl,-rpath,%s" % ld)
            for inc in agg.includedirs:
                tc.extra_cflags.append("-I%s" % inc)
        except KeyError:
            pass
        # -fcommon: 2011 代码在头文件里以 tentative definition（无 extern）声明
        # 共享全局（ISTGT_LU_TASK_RESULT 等），每个包含该头的 .c 各出一份强
        # 符号；老 GCC 默认 -fcommon 由链接器合并 COMMON 符号，OHOS clang 15
        # 默认 -fno-common → ld.lld "duplicate symbol"（W3 第 2 轮实测）。
        # house 先例 quagga 1.2.4 同因同法。
        tc.extra_cflags.append("-fcommon")
        # OHOS musl 不导出 POSIX 线程取消族（pthread_cancel /
        # pthread_setcancelstate / pthread_testcancel：<pthread.h> 不声明且
        # libc.so 不导出；sysroot 的 libpthread.a 为空壳，加 -lpthread 无效）
        # → 特性宏 HAVE_PTHREAD_CANCEL=0 走补丁 0001 的语义降级分支；
        # Linux/glibc 保持缺省 1（上游原行为）。
        # 知识库：knowledge/drafts/musl-pthread-cancel-gap/（策略 S1）。
        if self.settings.os == "OHOS":
            tc.extra_cflags.append("-DHAVE_PTHREAD_CANCEL=0")
        tc.generate()

    def build(self):
        # 补丁 0001：HAVE_PTHREAD_CANCEL 特性宏（OHOS musl 无 POSIX 线程取消
        # 族）。应用后取消点 call site 走 ISTGT_* 间接层，配方的
        # -DHAVE_PTHREAD_CANCEL=0 使其不再产生未定义符号。
        apply_conandata_patches(self)
        # 上游：./configure + make（预生成 configure，无 check 目标）
        autotools = Autotools(self)
        try:
            autotools.configure()
        except ConanException:
            # ── FUSE(HMDFS) umask-077 临时目录陷阱（2026-10-16，CI #93912 实测）─────
            # autoconf 生成的 config.status 里有：
            #   tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`
            # 在 FUSE + uid 映射错位环境下，077 umask 建出的目录**创建者自己也写不进**，
            # 于是写 subs1.awk 时被拒、config files machinery 起不来：
            #   ./config.status: line 618: ./conffpNLDD/subs1.awk: Permission denied
            #   config.status: error: could not setup config files machinery
            # chmod 补救被静默忽略；唯一有效修复是把脚本内部的 umask 077 改写成 000 ——
            # 本仓已有实证 SKILL：skills/fuse-tmp-write-guard（策略②，oddjob 0.34.7 验证）。
            # 只在本包自己的 config.status 上原地改写，再重跑它完成文件生成。
            cs = os.path.join(self.build_folder, "config.status")
            if not os.path.isfile(cs) or not self._fix_config_status_umask():
                raise            # 不是这个陷阱形态 → 原样抛出，绝不掩盖真因
            self.output.warning(
                "istgt: configure 失败于 config.status 阶段；已按 skills/fuse-tmp-write-guard "
                "策略②把 config.status 内的 umask 077 改写为 000，重跑 config.status")
            self.run("bash ./config.status", cwd=self.build_folder)
            # 完整性校验：重跑必须真的产出 Makefile。否则说明 configure 的失败另有真因
            # （例如 openssl 头文件/交叉工具链问题），此时绝不能当成“已修好”继续往下走。
            if not os.path.isfile(os.path.join(self.build_folder, "Makefile")):
                raise ConanException(
                    "istgt: 改写 umask 并重跑 config.status 后仍未生成 Makefile —— "
                    "configure 的失败另有真因，见上方 configure 输出")
            self.output.info("istgt: 重跑 config.status 成功，Makefile 已生成")
        autotools.make(args=["-j1"])
        self._smoke()

    def _fix_config_status_umask(self):
        """按仓库既有 SKILL 修复 config.status 的 umask-077 临时目录陷阱。

        只做一件事：把 `(umask 077 && mktemp -d "./confXXXXXX")` 改成 umask 000。
        幂等；无该模式时返回 False（表示不是本陷阱，交给调用方决定是否上抛）。
        改写后自校验（不得残留 077 模式、必须出现 000 模式），失败即回滚并抛错。
        """
        cs = os.path.join(self.build_folder, "config.status")
        text = open(cs, encoding="utf-8", errors="surrogateescape").read()
        if "umask 077 && mktemp" not in text:
            return False
        bak = cs + ".umaskbak"
        if not os.path.exists(bak):
            shutil.copyfile(cs, bak)
        fixed = text.replace("umask 077 && mktemp", "umask 000 && mktemp")
        open(cs, "w", encoding="utf-8", errors="surrogateescape").write(fixed)
        check = open(cs, encoding="utf-8", errors="surrogateescape").read()
        if "umask 077 && mktemp" in check or "umask 000 && mktemp" not in check:
            shutil.copyfile(bak, cs)          # 回滚
            raise ConanException("istgt: config.status umask 改写后自校验失败，已回滚")
        self.output.info("istgt: config.status 的 umask 077 已改写为 000（备份 %s）" % bak)
        return True

    def _smoke(self):
        """Substantive integrity check that EXECUTES the built binaries
        (aarch64 ELF via binfmt qemu on the WSL build host):
        1) `istgt -V` rc=0 + "istgt version 0.4" + extra version 20111008;
        2) `istgtcontrol -V` rc=0 + "istgtcontrol version 0.4".
        上游无测试套件，此冒烟满足 CI L1c 的 make check 口径。"""
        import subprocess
        exe = os.path.join(self.build_folder, "src", "istgt")
        ctl = os.path.join(self.build_folder, "src", "istgtcontrol")
        for path in (exe, ctl):
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise RuntimeError(
                    "istgt make check FAILED: binary missing: %s" % path)
        env = dict(os.environ)
        try:
            libdirs = self.dependencies["openssl"].cpp_info \
                .aggregated_components().libdirs
        except KeyError:
            libdirs = []
        if libdirs:
            env["LD_LIBRARY_PATH"] = os.pathsep.join(libdirs) + \
                (os.pathsep + env["LD_LIBRARY_PATH"]
                 if env.get("LD_LIBRARY_PATH") else "")
        r = subprocess.run([exe, "-V"], env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=30)
        out = (r.stdout + r.stderr).decode(errors="replace")
        if r.returncode != 0 or "istgt version 0.4" not in out \
                or "20111008" not in out:
            raise RuntimeError("istgt make check FAILED: istgt -V rc=%d out=%s"
                               % (r.returncode, out[:300]))
        self.output.info("istgt make check: istgt -V rc=0, version 0.4/20111008 OK")
        r = subprocess.run([ctl, "-V"], env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=30)
        out = (r.stdout + r.stderr).decode(errors="replace")
        if r.returncode != 0 or "istgtcontrol version 0.4" not in out:
            raise RuntimeError(
                "istgt make check FAILED: istgtcontrol -V rc=%d out=%s"
                % (r.returncode, out[:300]))
        self.output.info("istgt make check: istgtcontrol -V rc=0 OK")

    def package(self):
        # make install（DESTDIR=package_folder）：bin/istgt、bin/istgtcontrol、
        # etc/istgt/*.sample、etc/rc.d/istgt、share/man/man1/istgt.1
        # 不用顶层 `make install`（2026-10-16 二次修，CI #94874/#94886 实测）：
        #   ① 顶层 install 默认带 tools.build:jobs（worker 上 -j20）→ make 要建 jobserver
        #      fifo，而 worker 禁止该操作（CI #94783: "jobserver mkfifo ... Operation not
        #      permitted"）；换成 -j1 后仍失败。
        #   ② 换 -j1 后拿到的输出是 `make: 'install' is up to date.` —— 一个文件都没装。
        #      原因是上游 tarball 自带大写 `INSTALL` 文本文件，而顶层目标名是 `install`；
        #      worker 的 /storage（HMDFS）大小写不敏感，make 把 `install` 当成已存在的
        #      文件目标（无依赖）⇒ 判定 up to date、不跑 recipe。本地 ext4 区分大小写，
        #      故永远复现不出来。
        # 处置：显式进 src/etc/doc 三个子目录安装 —— 每个子目录的 install 规则都真实存在、
        # 且 honor DESTDIR（本地实测 rc=0，产出 bin/istgt、bin/istgtcontrol、
        # etc/istgt/*.sample、etc/rc.d/istgt、man/man1/istgt.1.gz）。仍用 -j1 避开 ①。
        for _sub in ("src", "etc", "doc"):
            self.run('make -C "%s" -j1 install DESTDIR="%s"'
                     % (_sub, self.package_folder), cwd=self.build_folder)
        # 兜底断言：安装产物必须真实落盘，否则当场失败。「静默成功但包是空壳」是
        # 本次事故最危险的部分，不能只依赖 test_package 事后发现。
        for rel in ("bin/istgt", "bin/istgtcontrol",
                    "etc/istgt/istgt.conf.sample",
                    "etc/istgt/auth.conf.sample"):
            if not os.path.isfile(os.path.join(self.package_folder, rel)):
                raise RuntimeError(
                    "make install did not install %s — check the jobserver "
                    "mkfifo / prefix handling (see notes.md)" % rel)
        if not any(os.path.isfile(os.path.join(self.package_folder, "man",
                                               "man1", name))
                   for name in ("istgt.1", "istgt.1.gz")):
            raise RuntimeError(
                "make install did not install the istgt.1 man page")
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # G4/L5 口径：声明二进制位置的 pc 文件（先例 rawtran）
        pcdir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        with open(os.path.join(pcdir, "istgt.pc"), "w", encoding="utf-8") as f:
            f.write("prefix=%s\n" % self.package_folder)
            f.write("bindir=${prefix}/bin\n")
            f.write("Name: istgt\n")
            f.write("Description: iSCSI target daemon (RFC 3720) with SPC-3 "
                    "logical unit emulation\n")
            f.write("Version: %s\n" % self.version)

    def package_info(self):
        # 命令行工具包：为下游 VirtualRunEnv 暴露 bin/（用相对目录，
        # 不写 package_folder 绝对路径，保持制品元数据可重定位）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.system_libs = ["pthread"]
