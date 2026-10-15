#!/usr/bin/env python3
"""Conan recipe — megactl 0.4.5（LSI/Dell PERC / MegaRAID RAID 控制器诊断工具）。

交付内容
    bin/megactl     —— PERC2/3/4/5（MegaRAID 老架构）控制器诊断与配置报告
    bin/megasasctl  —— MegaRAID SAS 架构同一程序（-DMEGA_SAS_CTL 编译变体）
    share/man/man1/{megactl,megasasctl}.1
    share/metainfo/megactl.metainfo.xml
    licenses/COPYING（GPL-2.0-or-later）

零外部依赖
    纯 C99 + libc。SCSI/MTP 结构体来自上游自带的 schily/ 头（Makefile 的
    -I./schily），megaraid ioctl 结构体来自上游 vendored 的
    kernel-2.6.9-55.0.2.EL/megaraid-2.20.4.6-rh2/（源码根的 megaraid 符号链接）。
    因此 W0 依赖闸无需任何制品仓预编译包，requirements 为空。

OHOS 适配要点（实测结论见 notes.md）
  1. 构建零补丁。GNU make + 上游 Makefile 直接可用，OHOS clang 15
     （--target=aarch64-linux-ohos）无需任何源码/patch 改动即编译通过：
     上游代码只用 POSIX 头（sys/ioctl.h、sys/sysmacros.h、netinet/in.h …），
     全部存在于 OHOS musl sysroot。
  2. 编译器从 conf 取（R33）：CC 取自 tools.build:compiler_executables，
     以 make 命令行变量传入；**不能**用 `make CFLAGS=...` 覆盖 —— 上游
     Makefile 用 `CFLAGS+=`，命令行赋值会连 `-g -Wall -I./schily` 一起清掉，
     反而编不过。附加优化选项走 CPPFLAGS（上游 `CFLAGS+= ... $(CPPFLAGS)`）。
  3. 不用 `make install`（HMDFS 用户态无 install(1)，lzip/1.24.1 已实证
     Error 127），改为 conan copy() 从 source_folder 直接落包；这同时规避了
     T105「install 落地的可执行文件在真机 worker 上带内核级不可执行标记」。
  4. ARCH= 显式置空：上游 `CFLAGS+= ... $(ARCH)` 会吸收环境里的 ARCH，
     置空保证构建可复现。
  5. 链接期剥 debug 段（-Wl,--strip-debug）：上游把 -g 硬编码进 CFLAGS，
     DWARF 会把**交叉工具链 sysroot 的构建机绝对路径**写进二进制。
  6. 链接期显式要 build-id（-Wl,--build-id=sha1）：worker 上真正的 OHOS clang
     驱动默认不生成 .note.gnu.build-id（本机 shim 会生成，所以本地绿、CI 红，
     CI #79116 实证）。而 test_package 用 build-id 证明两个 CLI 是分别编译的
     两个目标，因此显式指定，不依赖驱动默认值。

上游测试：**没有**（如实申报）
    上游 Makefile 只有 all/megactl/megasasctl/megatrace/install/clean/depend
    七个目标，无 check/test；源码树里没有任何测试目录或测试框架。megactl 的
    真实使用前提是存在 MegaRAID 硬件与 /dev/megadev0 设备节点，CI 与开发机
    都没有。证据与清点口径见 test_package/MANIFEST.yml 与 notes.md。

版本号说明（上游 quirk，不改上游源码）
    发布 tarball 是 0.4.5，但 megactl.c:91 的 `static char *version` 仍写着
    "0.4.3-hmage"（上游发布时漏改，与 rtl-sdr 2.0.2 的 VERSION_INFO_PATCH_VERSION
    同类 quirk）。`megactl -V` 因此打印 0.4.3-hmage。如实保留，测试按实测值断言。
"""
import json
import os
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# 上游 Makefile 的 PROGRAMS（= all 目标）；megatrace 不在其中
CLI_TOOLS = ("megactl", "megasasctl")


class MegactlConan(ConanFile):
    name = "megactl"
    version = "0.4.5"
    description = ("megactl/megasasctl — LSI/Dell PERC（PERC2/3/4/5）与 MegaRAID "
                   "SAS 控制器的诊断、配置报告与自检工具")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/namiltd/megactl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("raid", "megaraid", "perc", "storage", "diagnostics")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} 需要 POSIX 环境（Linux/OHOS），"
                f"当前 os={self.settings.os}")

    def requirements(self):
        # 零外部依赖：纯 C99 + libc；SCSI/MTP 头由自带 schily/ 提供，
        # megaraid ioctl 结构体由自带 kernel-2.6.9-.../ 参考头提供。
        pass

    def source(self):
        # url 可能是候选列表（CI 预下载步骤会把 conandata 的 url 改写成
        # [镜像, 官方]）—— conan 的 get() 两种形态都能处理。
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=5, retry_wait=10)

    def build(self):
        cc = self._cc()
        # -j1：HMDFS 上 GNU make jobserver 建 command FIFO 失败（既有先例）。
        # ARCH= 显式置空，避免环境里的 ARCH 被上游 `CFLAGS+= ... $(ARCH)` 吸收。
        # 刻意不传 CFLAGS：上游用 `CFLAGS+=`，命令行赋值会覆盖掉 -Wall/-I./schily。
        #
        # LDFLAGS 追加 -Wl,--strip-debug：上游 Makefile 把 `-g` 硬编码进
        # CFLAGS/LDFLAGS（面向发行版的开发者便利），而交叉工具链的 sysroot
        # 位于构建机的用户目录下（不在 /usr），DWARF 会把该**构建机绝对路径**
        # （形如 <sysroot>/usr/include …）写进 .debug_str。交付进制品仓的
        # 二进制绝不能带构建机路径（既是分发卫生，也会把私人路径带进公开 PR），
        # 因此保留上游 -g 只在链接期剥掉 debug 段（实测 .debug_str 里的
        # sysroot 路径计数由 2 降为 0，.interp/.note.ohos.ident/
        # .note.gnu.build-id 与符号表全部保留）。
        #
        # -Wl,--build-id=sha1 必须**显式**给（2026-10-10 CI #79116 实证）：
        # 本机 shim 的驱动默认会往 ld 传 `--build-id`，而 worker 上真正的 OHOS
        # clang 驱动**不传**——于是同一份配方本地绿、CI 红：交付的 bin/megactl、
        # bin/megasasctl 在 CI 上只有 .note.ohos.ident、没有 .note.gnu.build-id，
        # test_package/test_layout.py [4] 那两条（两个 CLI 都带 BuildID、且两者
        # 不同——用来证明它们是**分别编译的两个目标**而不是硬链接/副本）双双 FAIL，
        # conan create 以 Error 1 退出。显式指定 sha1 风格后不再依赖驱动默认值；
        # sha1 也**跨链接器一致**（lld 默认是 8 字节的 fast/xxHash，GNU ld 才是 sha1），
        # 便于人眼与脚本复核。build-id 由链接产物内容算出，两个不同程序必然不同。
        cmd = (f"make -j1 CC='{cc}' ARCH= "
               "LDFLAGS='-g -Wl,--strip-debug -Wl,--build-id=sha1'")
        self._run_with_spawn_retry(cmd, "make-all.log")
        for tool in CLI_TOOLS:
            path = os.path.join(self.source_folder, tool)
            if not os.path.isfile(path):
                raise ConanException(
                    f"make 结束但 {tool} 未生成；见 make-all.log")
        # 上游内核态参考源码树不进包（只是 ioctl 结构体的来源，不参与构建）
        kernel_dir = os.path.join(self.source_folder, "kernel-2.6.9-55.0.2.EL")
        if os.path.isdir(kernel_dir):
            self.output.info("vendor 参考头（不构建、不打包）: %s"
                             % os.path.relpath(kernel_dir, self.source_folder))

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        metadir = os.path.join(self.package_folder, "share", "metainfo")
        licdir = os.path.join(self.package_folder, "licenses")

        # copy() 而非 make install：HMDFS 用户态无 install(1)；同时规避
        # T105（install 落地的可执行文件在真机 worker 上带内核级 no-exec 标记）。
        for tool in CLI_TOOLS:
            copy(self, tool, src=self.source_folder, dst=bindir,
                 keep_path=False)
        for page in ("megactl.1", "megasasctl.1"):
            copy(self, page, src=self.source_folder, dst=mandir,
                 keep_path=False)
        copy(self, "megactl.metainfo.xml", src=self.source_folder,
             dst=metadir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder, dst=licdir,
             keep_path=False)

        for tool in CLI_TOOLS:
            target = os.path.join(bindir, tool)
            if os.path.isfile(target):
                os.chmod(target, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.runenv_info.append_path("PATH", bindir)

    # ── helpers ─────────────────────────────────────────────────────────

    # clang 驱动 spawn 子进程（cc1 / ld.lld）时的资源性瞬时失败签名。
    # 实测 CI #69512（worker CI-033）：7 个 .c 全部编译通过（仅 11 条
    # -Wvoid-pointer-to-int-cast 警告），链接一步报
    #   clang-15: error: unable to execute command: posix_spawn failed:
    #              Resource temporarily unavailable
    #   clang-15: error: linker command failed with exit code 1
    # 该 worker 环境对进程/并发 spawn 有配额（env 里有 AppSpawnCheckUnexpectedExitCall），
    # 属资源竞争而非代码缺陷 —— 故只对这一签名做有限次退避重试。
    _SPAWN_ERR = ("posix_spawn failed", "Resource temporarily unavailable")

    def _run_with_spawn_retry(self, cmd, logname, attempts=3, backoff=20):
        last = None
        for attempt in range(1, attempts + 1):
            try:
                self._run_logged(cmd, logname, echo_tail=(attempt == 1))
                return
            except ConanException as exc:
                last = exc
                if not self._log_has_spawn_error(logname):
                    raise                       # 真编译错误：立即抛出，不浪费轮次
                if attempt == attempts:
                    break
                self.output.warning(
                    "make 第 %d/%d 次尝试命中 posix_spawn 资源性失败，%d 秒后重试"
                    % (attempt, attempts, backoff))
                time.sleep(backoff)
        # 最后一次：把日志尾部完整抛出，便于评审定位
        self._run_logged(cmd, logname, echo_tail=True)
        raise last

    def _log_has_spawn_error(self, logname):
        log = os.path.join(self.source_folder, logname)
        if not os.path.isfile(log):
            return False
        with open(log, encoding="utf-8", errors="replace") as handle:
            body = handle.read()
        return any(sig in body for sig in self._SPAWN_ERR)

    def _cc(self):
        """从 conf 取 C 编译器（R33：不裸用 shell 的 ${CC}）。

        取不到就**直接报错**，不回落成裸 "clang" —— 回落会在 OHOS 工具链不在
        PATH 的机器上静默改用宿主架构编译器，把问题推迟到产物 ELF 检查才暴露，
        报错信息也难以定位。宁可构建期失败。
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if isinstance(compilers, str):
            try:
                compilers = json.loads(compilers)
            except ValueError:
                compilers = {}
        if isinstance(compilers, dict) and compilers.get("c"):
            return compilers["c"]
        raise ConanInvalidConfiguration(
            f"{self.ref} 无法从 conf 的 tools.build:compiler_executables 取得 C "
            "编译器（当前值 %r）。请用带 OHOS 工具链的 profile（如 "
            "ohos-aarch64 / ohos-aarch64-wsl）构建；刻意不回落裸 clang，"
            "以免在宿主架构上静默产出错误目标的二进制。" % (compilers,))

    def _run_logged(self, cmd, logname, echo_tail=True):
        """在源码目录执行 cmd，输出绑定到日志文件；失败时回显日志尾部。

        本平台上交给 conan 继承 stderr 的编译器输出可能被静默丢弃（表现是
        一个无法解释的非零退出码），因此每一步都重定向到自己的日志，
        失败时把尾部打进 conan 日志。参照 zrc/2.7 同款做法。
        """
        log = os.path.join(self.source_folder, logname)
        try:
            self.run(f"{cmd} > '{log}' 2>&1", cwd=self.source_folder)
        except ConanException:
            if echo_tail and os.path.isfile(log):
                with open(log, encoding="utf-8", errors="replace") as handle:
                    for line in handle.readlines()[-80:]:
                        self.output.error(line.rstrip())
            raise
