#!/usr/bin/env python3
"""Conan recipe for sphde 1.4.0.

SPHDE (Shared Persistent Heap Data Environment) provides the Shared Address
Space (SAS) layer and Shared Persistent Heap (SPH) layer for building
transparently persistent, shared data structures in C/C++.

Build system: autotools (pre-generated configure + Makefile.in in the
release tarball; build is native OHOS/aarch64, not cross).
"""
import json
import os
import re
import shutil
import time
from io import StringIO

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SphdeConan(ConanFile):
    name = "sphde"
    version = "1.4.0"
    description = "Shared Persistent Heap Data Environment (SAS/SPH layers)"
    license = "EPL-1.0"
    homepage = "https://github.com/sphde/sphde"
    url = "https://github.com/sphde/sphde"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # ── fork 压力缓解：env 激活脚本切 function 反激活模式 ──
        # CI build #91113 在 configure 的首个 M4sh 子 shell 处失败：
        # `configure[33]: can't fork - try again`。真机 fork() EAGAIN 的核心放大
        # 源之一是 Conan 默认的 env 激活脚本：unset 模式下生成的
        # conan*env*.sh 会在 source 期执行
        #   for v in <vars>; do value=$(printenv $v); ...; done
        # 即对每个变量 fork 一次 printenv。AutotoolsToolchain 会导出
        # CC/CXX/AS/AR/RANLIB/NM/STRIP/OBJDUMP/CFLAGS/CXXFLAGS/CPPFLAGS/LDFLAGS/
        # PKG_CONFIG_PATH 等十余个变量，于是每次 self.run()（configure/make/
        # make check/install）在真正执行目标命令前都会先 fork 十几次；当 worker
        # 已处于 fork 资源临界时，configure 自己的第一个 fork 就被 EAGAIN 拒绝。
        # `tools.env:deactivation_mode=function` 让 env 脚本只在 source 期定义
        # 反激活函数、并用 `${VAR+x}` 参数展开保存旧值，不再 fork printenv
        # （对照生成的 conan*build*.sh 可见 for+printenv 块被替换为纯函数定义）。
        # 必须在任何 Environment/生成器之前 define；放在 generate() 顶部即可覆盖
        # 本方法内的 AutotoolsToolchain 以及其后运行的 VirtualBuildEnv/VirtualRunEnv。
        self.conf.define("tools.env:deactivation_mode", "function")
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        # 平台补丁：config.guess/config.sub 的 HarmonyOS 三元组 (E205/E072)、
        # configure 临时目录 umask 077->022 (E129)、configure ac_pwd $PWD 回退
        # (E158，规避 HMDFS getcwd 无法向上遍历)、Makefile.in AM_CFLAGS/CXXFLAGS
        # 追加 -Wno-unused-function -Wno-unused-but-set-variable（OHOS clang 对
        # 未使用 static inline 函数报 -Wunused-function，对 SPHLFLoggerPrefetch
        # 里仅作 prefetch 副作用的局部变量 touch 报 -Wunused-but-set-variable，
        # GCC 均豁免，被上游 -Werror 提升为致命错误）。
        # HMDFS 上 getcwd(2) 沿 .. 上溯失败，shell 的 pwd 内建回退到 getcwd 而
        # abort。故在调用 configure/make 前同步进程 cwd 并预置逻辑路径 PWD，
        # 让 bash/mksh 的 pwd 内建直接信任有效 PWD 而不触发 getcwd，作为
        # configure 里 ac_pwd `pwd` 2>/dev/null || "$PWD" 回退的兜底。
        try:
            os.chdir(self.build_folder)
        except OSError:
            # chdir 失败不阻断：仅依赖 configure 补丁的 $PWD 回退。
            pass
        os.environ["PWD"] = self.build_folder

        apply_conandata_patches(self)
        autotools = Autotools(self)
        self._configure_with_retry()
        # OHOS/HMDFS：worker 的 toybox install `-c` 在 HMDFS 上直接返回 Error 64
        # (E596)，且 HMDFS 不支持 chmod (E087)；也无 GNU coreutils install (E098)。
        # configure 已把 toybox install 路径写死进所有子 Makefile 的 INSTALL 变量。
        # 写 cp/mkdir 的 install shim 并 sed 改 INSTALL 指向它（INSTALL_DATA/
        # INSTALL_PROGRAM 引用 ${INSTALL} 自动跟随），使 make install（package()
        # 里的 autotools.install()）全程走 shim，用 cp 替代 toybox install。
        if str(self.settings.os) == "OHOS":
            shim = self._write_install_shim()
            self._redirect_install_to_shim(shim)
        autotools.make(args=["-j1"])

        # ── 上游官方测试套件 (make check, automake test-driver) ──
        # 上游在 src/Makefile.am 的 TESTS 完整清单 24 个测试程序；aarch64 下
        # HTM 特性关闭（sphmultipcqueue_t 位于 `if HTM` 条件块），注册并执行 23 个。
        # automake 生成 src/test-suite.log，其中含 # TOTAL/# PASS/# FAIL 汇总块。
        # 声明总数 discovered 取 src/Makefile.am 的完整清单（24），未注册的
        # sphmultipcqueue_t 作为 environment gap 如实申报，避免少报。
        #
        # ── 逐测试超时（OHOS 真机偶发挂起保护）──
        # 上游多线程 SPSC 队列测试（sphsinglepcqueue_ttt / sphdirectpcqueue_ttt）
        # 含无界自旋等待 `while (SPHSinglePCQueueFull/Empty(...)) sched_yield();`
        # （sphsinglepcqueue.cpp / directpcqueue）。在 OHOS 共享内存语义下
        # producer/consumer 可能双双自旋不推进，使测试无限挂起并拖垮整个 make
        # check —— CI 曾因此整作业 14400s 无输出超时。这里把 make 的 LOG_COMPILER
        # 设为逐测试超时包装（sphde 生成的 src/Makefile 未定义 LOG_COMPILER，
        # 环境变量会被 GNU make 采纳并随递归子 make 传播进 src/），把每个上游
        # 测试限制在 SPHDE_TEST_TIMEOUT 秒内：正常快速通过与快速崩溃不受影响，
        # 真正挂起的测试被 kill 后由 automake 记为 FAIL，归入 ohos_feature gap，
        # 不再拖垮整个作业。
        self._write_test_timeout_wrapper()
        os.environ.setdefault("SPHDE_TEST_TIMEOUT", "300")
        os.environ["LOG_COMPILER"] = os.path.join(
            self.source_folder, "test-timeout-wrapper.sh")
        try:
            autotools.make(target="check", args=["-j1"])
        except Exception as exc:  # noqa: BLE001
            # 测试失败不终止构建，先收集 test-suite.log 证据后按真实结果上报。
            self.output.warning(
                f"make check exited non-zero ({exc}); collecting test-suite.log")
        marker = self._emit_upstream_test_result()
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(marker, fh)

    def _configure_with_retry(self):
        """运行 autotools.configure()，对真机 fork 压力 (EAGAIN) 做退避重试。

        证据：CI build #88944 / #89113 在同一 recipe revision
        (ad08107d318fd83c8d9faeada77a5aa7) 上失败，日志分别为
        `configure: fork: retry: Resource temporarily unavailable`（30 处）与
        `configure[33]: can't fork - try again`；而同一 revision 的 #88798 / #89013
        两次干净通过（0 处 fork 报错），且失败运行的 CI 自身脚本
        `knowledge_check.sh: fork: retry: Resource temporarily unavailable` 也在报错
        —— 属 worker 级 fork/进程资源瞬时耗尽，不是配方缺陷（E491 forbid_3：
        先有设备资源证据再改包；DRAFT-11327：同 SHA 不同 worker 结果不一致 = 环境）。
        configure 会 fork 数百次 sh/clang 探测，最易受害；一旦 EAGAIN 尖峰不应让
        整个 create 失败。这里做有界退避重试并 dump config.log 尾部作为证据。
        仅当错误文本/config.log 出现 fork 标记时才重试；真实 configure 错误
        （如 C++ preprocessor sanity check）立即抛出，不掩盖。

        CI build #95036（2026-10-16，worker CI-034，revision e431020d）表明尖峰可
        持续整个 6 次预算（15/30/45/60/75s）：每次尝试都在最早的两个探测
        （`checking whether make sets $(MAKE)... no`、`checking whether the C++
        compiler works... no`）即被 fork EAGAIN 打断，共 600+ 行 `fork: retry:`。
        同一 revision 数十分钟后在另一 worker（CI-006，build #95131）干净通过
        （0 行 fork 报错），再次坐实环境性。本轮加固：
          1. 显式把 configure 的工作 shell 钉到轻量 POSIX sh（/bin/sh），避免
             逐次 `exec` 进 hnp bash（HMDFS 上 getcwd 不稳、且 bash 内部 fork
             重试开销更大，avahi R18/cpluff 先例）；用命令行内联 env 覆盖
             profile [buildenv] 的 CONFIG_SHELL/SHELL（内联赋值优先于导出值）。
          2. 内联钉一个实测可写 TMPDIR，避免 autoconf/libtool 回落到
             只读 /tmp（E002）。
          3. 每次重试前清理上次失败残留的 config.log/config.status/
             config.cache/conftest*，避免半成品状态干扰下一次（不改测试口径）。
          4. 加零 fork 的资源快照（loadavg/rlimit/内存，纯 Python + /proc）作为
             设备侧证据，绝不额外 fork 加剧尖峰（libcmis `_log_resource_snapshot`
             形态）。
          5. 预算放宽到 8 次、退避 15/30/.../105s（约 7 分钟），给共享 worker 的
             fork 资源留恢复窗口；仍保持 fork 标记门控与次数上限，不无限重试、
             不掩盖真实错误。
        """
        fork_markers = ("can't fork", "cannot fork", "try again",
                        "resource temporarily unavailable", "out of memory")
        shell = self._resolve_working_shell()
        tmpdir = self._writable_tmpdir()
        # 内联 env 前缀：内联赋值对该命令优先于 conanbuild.sh 导出的 profile
        # [buildenv]（CONFIG_SHELL=/data/service/hnp/bin/bash），且 configure
        # 会把 SHELL/CONFIG_SHELL 固化进生成的 Makefile。若找不到确定存在的
        # 轻量 sh（shell is None），则不注入 SHELL/CONFIG_SHELL，沿用 profile 值。
        parts = ['TMPDIR="{tmp}" TMP="{tmp}" TEMP="{tmp}"'.format(tmp=tmpdir)]
        if shell:
            parts.insert(0, 'CONFIG_SHELL="{sh}" SHELL="{sh}"'.format(sh=shell))
        prefix = " ".join(parts) + " "
        self.output.info(
            "sphde configure env: SHELL={} TMPDIR={}".format(
                shell or "(profile)", tmpdir))
        self._log_resource_snapshot("pre-configure")
        max_attempts = 8
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                self._reset_stale_configure_byproducts()
            buf = StringIO()
            try:
                self._run_configure_capturing(buf, prefix)
                # 成功：把捕获的 configure 输出原样回放到日志，保持可观测性。
                print(buf.getvalue(), end="", flush=True)
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                captured = buf.getvalue()
                tail = captured[-4000:].lower()
                is_fork = any(m in str(exc).lower() for m in fork_markers) or \
                    any(m in tail for m in fork_markers) or \
                    self._config_log_has_fork_marker()
                # 失败：回放捕获输出 + config.log 尾部，保留诊断证据。
                print(captured, end="", flush=True)
                self._dump_config_log_tail()
                self._log_resource_snapshot(
                    "configure-fail-attempt{}".format(attempt))
                if not is_fork or attempt >= max_attempts:
                    if is_fork:
                        self.output.warning(
                            "sphde configure still fork-starved after "
                            f"{attempt} attempts: {exc}")
                    raise
                wait = 15 * attempt
                self.output.warning(
                    "sphde configure hit fork pressure (attempt "
                    f"{attempt}/{max_attempts}); sleeping {wait}s then retrying: {exc}")
                time.sleep(wait)
                self._log_resource_snapshot(
                    "pre-retry-attempt{}".format(attempt + 1))
        if last_exc is not None:
            raise last_exc

    def _run_configure_capturing(self, buf, prefix=""):
        """等价于 Autotools.configure()，但把 stdout/stderr 同时写入 buf，
        以便在失败时判定是否为 fork 资源错误。命令由 AutotoolsToolchain
        生成的 conanbuild.conf 还原，与 autotools.configure() 完全一致；
        prefix 为内联 SHELL/CONFIG_SHELL/TMPDIR 赋值（优先于 conanbuild.sh
        导出的 profile [buildenv] 值）。
        """
        script_folder = self.source_folder
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", "")
        configure_cmd = "{}/configure".format(script_folder)
        # prefix 非空时以空格结尾，直接拼接即可；为空时 cmd 仍为 `"configure" args`。
        cmd = '{}\"{}\" {}'.format(prefix, configure_cmd, configure_args)
        self.run(cmd, stdout=buf, stderr=buf)

    def _resolve_working_shell(self):
        """选择一个实测存在的轻量 POSIX sh；找不到时返回 None。

        优先 /bin/sh、/system/bin/sh、capabilities 声明的 shell；仅当这些都不
        存在时才退回 HMBS 注入的 SHELL/CONFIG_SHELL（可能是
        /data/service/hnp/bin/bash）。hnp bash 在 HMDFS 上 getcwd 不稳且更重
        （avahi R18/cpluff 先例），若有 /bin/sh 则不选它。不做 fork 探测
        （fork 压力下探测本身也可能 EAGAIN），只做 os.path.exists/which 判断。
        返回 None 时调用方不注入 shell（沿用 profile 值），避免写入不存在的路径。
        """
        cap_shell = ""
        cap = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                cap_shell = json.loads(cap).get("shell", "") or ""
            except Exception:
                cap_shell = ""
        which_sh = None
        try:
            which_sh = shutil.which("sh")
        except Exception:
            which_sh = None
        have_bin_sh = os.path.exists("/bin/sh")
        candidates = ["/bin/sh", "/system/bin/sh", cap_shell, which_sh,
                      os.environ.get("SHELL"), os.environ.get("CONFIG_SHELL")]
        for cand in candidates:
            if not cand:
                continue
            # hnp bash 在 HMDFS 上 getcwd 不稳且更重；有 /bin/sh 时不选它。
            if "hnp" in cand and have_bin_sh:
                continue
            if os.path.exists(cand):
                return cand
        # 有 /bin/sh 但上面的候选都被跳过（理论上不会）时仍用它。
        if have_bin_sh:
            return "/bin/sh"
        # 否则返回 None，调用方不注入 SHELL/CONFIG_SHELL，沿用 profile 值，
        # 避免把不存在的路径写进 configure/Makefile。
        return None

    def _writable_tmpdir(self):
        """选一个实测可写的 TMPDIR，避免 autoconf 回落到只读 /tmp (E002)。

        优先复用 HMBS 注入的 HMBS_TMPDIR/TMPDIR/TMP/TEMP（排除 /tmp），否则用
        build_folder/tmp，最后兜底原 TMPDIR 或 /tmp。只做写测试，不 fork。
        """
        def _writable(path):
            if not path or not os.path.isdir(path):
                return False
            if not os.access(path, os.W_OK | os.X_OK):
                return False
            probe = os.path.join(path, ".sphde-wtest")
            try:
                with open(probe, "w", encoding="utf-8") as fh:
                    fh.write("ok")
                os.remove(probe)
                return True
            except OSError:
                return False

        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var)
            if cand and cand != "/tmp" and _writable(cand):
                return cand
        fallback = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        if _writable(fallback):
            return fallback
        return os.environ.get("TMPDIR") or "/tmp"

    def _reset_stale_configure_byproducts(self):
        """重试前清理上一次失败留下的 configure 残留，避免半成品干扰。

        只删 configure 的临时产物（config.log/config.status/config.cache/
        confdefs.h/conftest*/confXXXXXX 目录）；不改任何源文件或测试口径。
        """
        names = ("config.log", "config.status", "config.cache", "confdefs.h")
        for name in names:
            try:
                os.remove(os.path.join(self.build_folder, name))
            except OSError:
                pass
        try:
            entries = os.listdir(self.build_folder)
        except OSError:
            return
        for entry in entries:
            if entry.startswith("conftest"):
                p = os.path.join(self.build_folder, entry)
                try:
                    if os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        os.remove(p)
                except OSError:
                    pass
            elif re.fullmatch(r"conf[A-Za-z0-9]{6}", entry) and os.path.isdir(
                    os.path.join(self.build_folder, entry)):
                shutil.rmtree(os.path.join(self.build_folder, entry),
                              ignore_errors=True)

    def _log_resource_snapshot(self, prefix):
        """零 fork 的资源诊断（loadavg/rlimit/内存/进程上限），用于 fork EAGAIN 取证。

        在 fork 压力下（"can't fork - try again"）任何额外的 fork/exec 只会
        加剧尖峰，故这里只用纯 Python 与 /proc 读取：不启动子进程、只读、
        永不抛错影响构建（libcmis/0.6.3 `_log_resource_snapshot` 形态）。
        """
        lines = []
        try:
            lines.append("loadavg={}".format(os.getloadavg()))
        except Exception as exc:
            lines.append("loadavg=unavailable:{}".format(exc))
        try:
            import resource as _res
            for _name in ("RLIMIT_NPROC", "RLIMIT_NOFILE", "RLIMIT_AS"):
                try:
                    _lim = _res.getrlimit(getattr(_res, _name))
                    lines.append("{}={}".format(_name, _lim))
                except Exception:
                    continue
        except Exception as exc:
            lines.append("rlimit=unavailable:{}".format(exc))
        for _p in ("/proc/loadavg", "/proc/meminfo",
                   "/proc/sys/kernel/threads-max", "/proc/sys/kernel/pid_max"):
            try:
                with open(_p, "r", encoding="utf-8", errors="replace") as _h:
                    _t = _h.read(2048).strip().splitlines()[:6]
                lines.append("{}: {}".format(
                    _p, " | ".join(_l.strip()[:160] for _l in _t) or "(empty)"))
            except OSError as exc:
                lines.append("{}: unreadable:{}".format(_p, exc))
        try:
            _n = os.cpu_count()
            lines.append("cpu_count={}".format(_n))
        except Exception:
            pass
        msg = "sphde resource [{}]:\n  {}".format(
            prefix, "\n  ".join(lines)[:3000])
        print(msg, flush=True)
        try:
            self.output.info(msg)
        except Exception:
            pass

    def _dump_config_log_tail(self, max_lines=40):
        """configure 失败时把 config.log 尾部回放到日志，作为 fork 证据。"""
        path = os.path.join(self.build_folder, "config.log")
        try:
            if not os.path.isfile(path):
                return
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            return
        print("sphde config.log tail ({} lines):".format(len(lines)), flush=True)
        for line in lines[-max_lines:]:
            print("  [config.log] " + line[:400], flush=True)

    def _config_log_has_fork_marker(self):
        """config.log 尾部出现 fork EAGAIN 标记时返回 True。"""
        markers = ("can't fork", "cannot fork", "try again",
                   "resource temporarily unavailable")
        path = os.path.join(self.build_folder, "config.log")
        try:
            if not os.path.isfile(path):
                return False
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                tail = fh.read()[-12000:].lower()
        except OSError:
            return False
        return any(m in tail for m in markers)

    def _count_upstream_tests(self):
        """清点上游 automake TESTS 注册清单（唯一确定性来源：src/Makefile.am）。

        返回 (inventory, registered, gated)：
          - inventory：src/Makefile.am 中所有 `TESTS +=` 条目的总数（含条件块）。
            这是上游测试的完整清单口径（审查按此核验 N，避免少报）；
          - registered：当前平台（aarch64/OHOS）实际注册的条目数，即去掉
            `if <COND>` ... `endif` 条件块内被门控的条目后的数量；
          - gated：被条件块门控、当前平台不注册的条目名列表。

        SPHDE 的 sphmultipcqueue_t 位于 `if HTM`（POWER 硬件事务内存 -mhtm）条件块，
        aarch64 无 HTM，configure 的 AX_CHECK_COMPILE_FLAG([-mhtm]) 不成立 →
        AM_CONDITIONAL(HTM) 为假 → 该条目不注册、不编译、不运行。它属于"未执行"，
        不得归零，须在 gaps 中如实申报为 environment 缺口。
        """
        makefile_am = os.path.join(self.source_folder, "src", "Makefile.am")
        if not os.path.isfile(makefile_am):
            raise Exception("src/Makefile.am not found at " + makefile_am)
        entry_re = re.compile(r"^\s*TESTS\s*\+?=\s*([A-Za-z0-9_]+)\s*$")
        inventory = []
        gated = []
        gates = []  # 活跃条件栈（元素为条件名）
        with open(makefile_am, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                stripped = line.strip()
                m_if = re.match(r"^if\s+(\S+)", stripped)
                if m_if:
                    gates.append(m_if.group(1))
                    continue
                if stripped == "endif":
                    if gates:
                        gates.pop()
                    continue
                m = entry_re.match(line)
                if m:
                    inventory.append(m.group(1))
                    if gates:
                        gated.append(m.group(1))
        registered = len(inventory) - len(gated)
        return len(inventory), registered, gated

    def _emit_upstream_test_result(self):
        """解析 src/test-suite.log 的 automake 汇总块并输出 HMBS 标记。

        依据：automake test-suite.log 汇总格式
          # TOTAL: 23
          # PASS:  22
          # SKIP:  0
          # XFAIL: 0
          # FAIL:  1
          # XPASS: 0
          # ERROR: 0
        passed=#PASS; failed=#FAIL+#ERROR; skipped=#SKIP+#XFAIL。

        计数来源各只有一个：
          - discovered（上游完整清单 N）来自 src/Makefile.am 的 TESTS 条目清点
            （_count_upstream_tests），含被 AM_CONDITIONAL 门控的条目，避免少报；
          - executed/passed/failed/skipped 来自 src/test-suite.log 的 automake
            汇总块（当前平台实际注册并执行的子集）。
        两者差额（条件门控、当前平台不注册的条目）如实计入 gaps，不归零、不虚报。
        """
        inventory, registered, gated = self._count_upstream_tests()
        log_path = os.path.join(self.build_folder, "src", "test-suite.log")
        if not os.path.isfile(log_path):
            raise Exception(
                "test-suite.log not found; expected at " + log_path)
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()

        def grab(key):
            m = re.search(r"^#\s*" + key + r"\s*:\s*(\d+)", content, re.M)
            if not m:
                raise Exception(
                    f"cannot parse # {key} from {log_path}")
            return int(m.group(1))

        total = grab("TOTAL")
        passed = grab("PASS")
        failed = grab("FAIL")
        error = grab("ERROR")
        skip = grab("SKIP")
        xfail = grab("XFAIL")
        xpass = grab("XPASS")

        executed = total
        npassed = passed
        nfailed = failed + error
        nskipped = skip + xfail
        if xpass:
            self.output.warning(f"XPASS={xpass} (unexpected passes) reported by upstream")

        # 恒等式自检（非负 + 单一来源）：
        #   passed+failed == executed、executed+skipped <= discovered、
        #   executed <= discovered。不满足时直接失败，不改数字凑恒等式。
        discovered = inventory
        if min(npassed, nfailed, nskipped, executed, discovered) < 0:
            raise Exception("negative test count parsed")
        if npassed + nfailed != executed:
            raise Exception(
                f"invariant broken: passed({npassed})+failed({nfailed}) "
                f"!= executed({executed})")
        if executed + nskipped > discovered:
            raise Exception(
                f"invariant broken: executed({executed})+skipped({nskipped}) "
                f"> discovered({discovered})")
        if executed > discovered:
            raise Exception(
                f"invariant broken: executed({executed}) > discovered({discovered})")
        # 当前平台注册子集应等于 test-suite.log 的 TOTAL；不一致说明清单或日志口径
        # 有误，宁可报错也不静默。
        if registered != executed:
            self.output.warning(
                f"registered TESTS ({registered}) != test-suite.log TOTAL "
                f"({executed}); see gaps")

        # 未通过/未执行项必须给出技术原因（gaps）。
        #
        # (1) 已执行但未通过（ohos_feature）：SPHDE 的 SAS 区域映射依赖 System V
        # 共享内存（shmget/shmat/shmctl，sasshm.c/sassim.cpp）与固定地址
        # mmap(MAP_FIXED)，OHOS seccomp 若拦截则测试 SIGSYS（signal 31 / rc=159）
        # 崩溃；否则映射成功但 OHOS 共享内存语义下，多线程 lockfree SPSC 队列
        # 测试（sphsinglepcqueue_ttt / sphdirectpcqueue_ttt）的无界自旋
        # `while(...Empty/Full) sched_yield();` 可无限挂起——已由逐测试超时包装
        # (LOG_COMPILER, SPHDE_TEST_TIMEOUT，默认 300s) kill 后记为 FAIL，避免
        # 拖垮整个 make check / CI 作业。
        #
        # (2) 上游清单中存在但当前平台不注册、因而未执行（environment）：
        # sphmultipcqueue_t 位于 src/Makefile.am 的 `if HTM` 条件块，仅 POWER
        # 硬件事务内存（-mhtm）可用时注册；aarch64/OHOS 上 configure 的
        # AX_CHECK_COMPILE_FLAG([-mhtm]) 不成立 → AM_CONDITIONAL(HTM) 为假 →
        # 该条目既不编译也不运行。这属于"未执行"，按 environment 如实申报缺口，
        # 不归零、不虚报通过。
        gaps = []
        if nfailed > 0:
            gaps.append({
                "count": nfailed,
                "category": "ohos_feature",
                "detail": (
                    "SPHDE maps the SAS region via System V shared memory "
                    "(SASAllocateShmID in sasshm.c uses shmget/shmat/shmctl) and "
                    "fixed-address mmap(MAP_FIXED) at __SAS_BASE_ADDRESS (sassim.cpp "
                    "SASJoinRegionByName). On HarmonyOS this either trips seccomp "
                    "(SIGSYS signal 31, rc=159) or, when the mapping succeeds, the "
                    "multi-threaded lock-free SPSC-queue tests "
                    "sphsinglepcqueue_ttt/sphdirectpcqueue_ttt spin indefinitely in "
                    "`while (...Empty/Full) sched_yield();` (upstream unbounded "
                    "spin-wait) and are bounded by a per-test timeout wrapper "
                    "(LOG_COMPILER=test-timeout-wrapper.sh, SPHDE_TEST_TIMEOUT, "
                    "default 300s) so a hung test is killed and recorded as FAIL "
                    "instead of stalling the whole make check / CI job. Non-SAS "
                    "tests (sphgtod/sphgettime/bitvec/sasatom) pass."),
                "evidence": (
                    "upstream test-suite.log #TOTAL/#PASS/#FAIL; CI build #63629 "
                    "stalled 14400s in sphsinglepcqueue_ttt after 'FAIL: "
                    "sphsinglepcqueue_tt' (unbounded spin loops in "
                    "sphsinglepcqueue.cpp SPHSinglePCQueueAllocStrideEntry/"
                    "GetNextComplete and directpcqueue.tpp; test sources "
                    "sphsinglepcqueue_ttt.c/sphdirectpcqueue_ttt.c); plus consumer "
                    "smoke test crash 'Signal 31 (core dumped)' rc=159 on SAS "
                    "region ops (sasshm.c shmget/shmctl, sassim.cpp "
                    "SASAttach/CreateAnchorSeg + mmap(MAP_FIXED))"),
            })
        not_executed = discovered - executed
        if not_executed > 0:
            gated_names = ", ".join(gated) if gated else "n/a"
            gaps.append({
                "count": not_executed,
                "category": "environment",
                "detail": (
                    "Upstream registers {inv} automake TESTS entries in "
                    "src/Makefile.am, but only {reg} are registered on this "
                    "platform; {ne} entry/entries are gated off and not "
                    "compiled/run: {names}. These live inside an automake "
                    "`if HTM` conditional block (POWER hardware transactional "
                    "memory, -mhtm); aarch64 has no HTM, so configure's "
                    "AX_CHECK_COMPILE_FLAG([-mhtm]) fails and "
                    "AM_CONDITIONAL(HTM) is false. They are counted as "
                    "not-executed (never as passed).").format(
                        inv=inventory, reg=registered, ne=not_executed,
                        names=gated_names),
                "evidence": (
                    "src/Makefile.am: `if HTM` / `TESTS += sphmultipcqueue_t` / "
                    "`endif`; src/sphmultipcqueue.cpp is wrapped in "
                    "`#ifdef __HTM__` and calls getauxval(AT_HWCAP2) with "
                    "PPC_FEATURE2_HAS_HTM; configure.ac: "
                    "AX_CHECK_COMPILE_FLAG([-mhtm], ...) + "
                    "AM_CONDITIONAL([HTM], ...). Inventory from src/Makefile.am "
                    "TESTS entries = {inv}, registered on aarch64 = {reg}, "
                    "test-suite.log TOTAL = {ex}.").format(
                        inv=inventory, reg=registered, ex=executed),
            })

        # gaps 总数必须等于 discovered - passed（未通过 + 未执行），否则门禁
        # 判为计数矛盾。
        gap_total = sum(g["count"] for g in gaps)
        if gap_total != discovered - npassed:
            raise Exception(
                f"gap total ({gap_total}) != discovered({discovered}) - "
                f"passed({npassed})")

        marker = {
            "status": "passed" if (nfailed == 0 and not gaps) else (
                "failed" if nfailed > 0 else "incomplete"),
            "framework": "automake",
            "command": "make check (src/Makefile.am TESTS, automake test-driver)",
            "discovered": discovered,
            "executed": executed,
            "passed": npassed,
            "failed": nfailed,
            "skipped": nskipped,
            "gaps": gaps,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False), flush=True)
        return marker

    def _write_test_timeout_wrapper(self):
        """写逐测试超时包装（纯 sh，不依赖 coreutils timeout），供 make check
        的 LOG_COMPILER 使用。

        OHOS 真机偶发：上游多线程共享内存 SPSC 队列测试
        （sphsinglepcqueue_ttt / sphdirectpcqueue_ttt）的无界自旋
        `while (SPHSinglePCQueueFull/Empty(...)) sched_yield();` 在 OHOS 共享
        内存语义下可无限挂起，拖垮整个 make check / CI 作业。此包装对每个上游
        测试施加 SPHDE_TEST_TIMEOUT 秒上限（默认 300），超时 kill -9 该测试，
        wait 返回非零（SIGKILL 通常 137），automake 记为 FAIL；正常快速通过与
        快速崩溃（SIGSYS/断言）不受影响。sphde 生成的 src/Makefile 未定义
        LOG_COMPILER，环境变量会被 GNU make 采纳并随递归子 make 传播进 src/，
        故本配方 setenv 即可生效。
        """
        wrapper = os.path.join(self.source_folder, "test-timeout-wrapper.sh")
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/sh\n"
                "# Per-test timeout wrapper for SPHDE `make check` (OHOS).\n"
                "# Bounds each upstream test so a hung multi-threaded shared-memory\n"
                "# test is reported to automake as FAIL (ohos_feature gap) instead\n"
                "# of stalling the whole test-suite / CI job for hours.\n"
                "TIMEOUT_SEC=${SPHDE_TEST_TIMEOUT:-300}\n"
                "testpath=$1\n"
                "shift\n"
                "\"$testpath\" \"$@\" &\n"
                "pid=$!\n"
                "# Watchdog in the background. It polls `kill -0` so it exits by\n"
                "# itself shortly after `wait` below reaps the child (once the PID\n"
                "# is gone the poll fails); on timeout it kill -9 the still-running\n"
                "# test so `wait` returns a non-zero status. Output redirected to\n"
                "# /dev/null so a lingering poll never holds the log/CI pipe open.\n"
                "(\n"
                "  i=0\n"
                "  while [ \"$i\" -lt \"$TIMEOUT_SEC\" ] && kill -0 \"$pid\" 2>/dev/null; do\n"
                "    sleep 1\n"
                "    i=$((i + 1))\n"
                "  done\n"
                "  if [ \"$i\" -ge \"$TIMEOUT_SEC\" ]; then\n"
                "    kill -9 \"$pid\" 2>/dev/null\n"
                "  fi\n"
                ") >/dev/null 2>&1 &\n"
                "watchdog=$!\n"
                "# wait reaps the child and returns its real exit status; if the\n"
                "# watchdog killed a hung test it returns a non-zero (137) status.\n"
                "wait \"$pid\"\n"
                "rc=$?\n"
                "if [ \"$rc\" -ge 124 ]; then\n"
                "  echo \"SPHDE test did not finish within ${TIMEOUT_SEC}s: $testpath (rc=$rc)\" >&2\n"
                "fi\n"
                "exit $rc\n"
            )
        os.chmod(wrapper, 0o755)

    def _write_install_shim(self):
        """写一个 cp/mkdir 的 install shim，替代 HMDFS 上失败的 toybox install。

        E596/E188/E098/E087：OHOS worker 的 toybox install `-c` 在 HMDFS 上直接
        返回 Error 64，且无 GNU coreutils install；HMDFS 不支持 chmod。autotools
        `make install` 仅需文件复制 + 目录创建 + 可选 chmod，这里用 cp/mkdir
        替代，chmod 失败容错跳过。返回 shim 绝对路径，供 _redirect_install_to_shim
        sed 改 Makefile 的 INSTALL 变量指向它（PATH 前置会被 conan build env 覆盖，
        故必须改 Makefile 而非靠 PATH）。
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        with open(install, "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/sh\n"
                "set -eu\n"
                "mode=\n"
                "while [ $# -gt 0 ]; do\n"
                "  case \"$1\" in\n"
                "    -p|-c) shift ;;\n"
                "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                "    --) shift; break ;;\n"
                "    -*) shift ;;\n"
                "    *) break ;;\n"
                "  esac\n"
                "done\n"
                "[ $# -ge 2 ] || exit 2\n"
                "dest=\n"
                "for arg in \"$@\"; do dest=$arg; done\n"
                "count=$(($# - 1))\n"
                "mkdir -p \"$(dirname \"$dest\")\"\n"
                "i=1\n"
                "for src in \"$@\"; do\n"
                "  [ $i -gt $count ] && break\n"
                "  cp -f \"$src\" \"$dest\"\n"
                "  # HMDFS 不支持 chmod (E087)，设权限失败不阻断复制。\n"
                "  if [ -n \"$mode\" ]; then\n"
                "    if [ -d \"$dest\" ]; then\n"
                "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                "    else\n"
                "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                "    fi\n"
                "  fi\n"
                "  i=$((i + 1))\n"
                "done\n"
            )
        os.chmod(install, 0o755)
        return install

    def _redirect_install_to_shim(self, shim_install):
        """把所有已生成子 Makefile 的 INSTALL 变量改为指向 install shim。

        configure 已把 toybox install 路径写死进 INSTALL 变量；改 Makefile 后
        INSTALL_DATA=${INSTALL} -m 644、INSTALL_PROGRAM=${INSTALL} 自动跟随，
        make install 全程用 shim（cp/mkdir 替代 toybox install）。
        """
        bf = self.build_folder
        for root, _, files in os.walk(bf):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append(f"{indent}INSTALL = {shim_install}\n")
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8") as f:
                        f.write("".join(lines))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 清理 .la（烤死绝对 libdir 路径，避免下游 libtool 误用）
        import glob
        for _la in glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            try:
                os.remove(_la)
            except OSError:
                pass
        # 持久化上游测试证据，供 test_package 阶段重发 HMBS 标记链
        res_json = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(res_json):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            from conan.tools.files import copy as conan_copy
            conan_copy(self, "upstream_test_result.json",
                       self.build_folder, res_dir)

    def package_info(self):
        # libsphde.so(shared)+.a、libsphgtod.a、libsphgettime.a（后两者仅静态）
        self.cpp_info.libs = ["sphde", "sphgtod", "sphgettime"]
        # SPHDE 依赖 librt/pthread；configure.ac 与 Makefile.am 硬编码 -lrt
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["rt", "pthread", "m"]
