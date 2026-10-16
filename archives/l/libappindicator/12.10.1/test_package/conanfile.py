#!/usr/bin/env python3
"""Conan test_package — libappindicator 12.10.1（HarmonyOS PC）。

两部分（真实编译 + 真实运行，rule4/rule12）：
  1. test_package（test_consumer.c）— 鸿蒙特有消费者端到端用例：
     GTK 初始化（可用则起 broadway 显示）→ 构造 AppIndicator → 设置
     icon/attention_icon/title/label/status → 挂 GtkMenu → 事件循环驱动
     new-label/new-status/new-icon 信号 → getter 回读 → 经 "dbus-menu-server"
     属性取回 DbusmenuServer/Menuitem 树与 GtkMenu 逐项比对 → .desktop
     构建菜单往返（真实消费者流程，不是纯断言）。
  2. test-libappindicator — 上游 tests/test-libappindicator.c 逐字复制
     （未修改，sha256 见 notes.md），9 个 g_test 用例真实执行；该程序 main()
     调用 gtk_init()，必须先把显示后端（随包依赖 gtk 的 broadwayd）拉起来。
     若当前环境无法执行目标二进制或无法提供显示后端，明确打印原因并跳过，
     绝不伪造通过。

运行环境判定（与仓库既有做法一致）：
  * can_run()（本机即 OHOS，CI worker）→ 直接执行；
  * OHOS_QEMU（本地验证 harness 注入）→ "qemu -L <runroot>" 前缀执行；
  * /proc/sys/fs/binfmt_misc/qemu-aarch64（WSL binfmt）→ 直接执行。
"""
import os
import re
import shlex
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # --------------------------------------------------------------- helpers
    def _runtime_libdirs(self):
        libdirs = []
        for dependency in self.dependencies.host.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(package_folder, libdir)
                if os.path.isdir(libdir):
                    libdirs.append(libdir)
        return libdirs

    def _runner_prefix(self):
        """返回 (能否执行目标二进制, 运行前缀列表)。"""
        if can_run(self):
            return True, []
        qemu = os.environ.get("OHOS_QEMU")
        if qemu:
            runroot = os.environ.get("OHOS_RUNROOT")
            return True, [qemu] + (["-L", runroot] if runroot else [])
        if os.path.exists("/proc/sys/fs/binfmt_misc/qemu-aarch64"):
            return True, []
        return False, []

    def _prepare_broadwayd(self):
        """从 gtk 依赖包取 broadwayd（OHOS 上先自签名），返回可执行路径或 None。"""
        candidate = None
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            path = os.path.join(dependency.package_folder, "bin", "broadwayd")
            if os.path.isfile(path):
                candidate = path
                break
        if candidate is None:
            return None
        private = os.path.join(self.build_folder, "broadwayd")
        shutil.copy2(candidate, private)
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if os.path.isfile(objcopy) and os.path.isfile(signer):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", private],
                check=False, capture_output=True,
            )
            subprocess.run(
                [signer, "sign", "-inFile", private, "-outFile", private,
                 "-selfSign", "1"],
                check=False, capture_output=True,
            )
        return private

    def _start_display(self, runner, libdirs):
        """尝试拉起 broadwayd；成功返回 (Popen, 环境变量字符串, 日志句柄)，失败返回 (None, "", None)。

        依次尝试 (display, port) = (:5,8055) (:6,8056) (:7,8057)：CI worker 与本地
        runroot 上 /run/user/<uid>/broadway<N+1>.socket 可能被上一次残留进程占住，
        单个 display 失败就整体跳过 9 个上游 g_test 用例代价太大，故轮换重试。
        """
        broadwayd = self._prepare_broadwayd()
        if broadwayd is None:
            self.output.warning("broadwayd not found in gtk dependency package")
            return None, "", None
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            libdirs + [env.get("LD_LIBRARY_PATH", "")]
        ).strip(os.pathsep)
        workdir = os.path.join(self.build_folder, "broadway-work")
        os.makedirs(workdir, exist_ok=True)

        for display, port in ((":5", "8055"), (":6", "8056"), (":7", "8057")):
            env["BROADWAY_DISPLAY"] = display
            log_path = os.path.join(workdir, f"broadwayd{display[1:]}.log")
            log = open(log_path, "wb")
            try:
                process = subprocess.Popen(
                    runner + [broadwayd, "--port", port, display],
                    stdout=log, stderr=subprocess.STDOUT, env=env, cwd=workdir,
                )
            except OSError as error:
                self.output.warning(
                    f"broadwayd could not be started on display {display}: {error}"
                )
                log.close()
                continue
            time.sleep(2)
            if process.poll() is not None:
                self.output.warning(
                    f"broadwayd exited early on display {display} "
                    f"(rc={process.returncode}); log: {log_path}"
                )
                # 失败分支：先回收子进程再关日志，避免僵尸与 fd 泄漏
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                log.close()
                continue
            prefix = (
                # broadwayd 的显示名与客户端的 DISPLAY/BROADWAY_DISPLAY 必须是同一个
                # `:N`：GDK broadway 后端按它定位 /run/user/<uid>/broadway<N+1>.socket
                # （实测 `broadwayd :5` → 监听 /run/user/0/broadway6.socket）。只给
                # DISPLAY、不给 BROADWAY_DISPLAY 时 GDK 报 "cannot open display: :5"，
                # 给 localhost:<port> 则走 TCP（未 --address 绑定，必然失败）。
                f'GDK_BACKEND=broadway DISPLAY={display} BROADWAY_DISPLAY={display} '
            )
            self.output.info(
                f"broadwayd pid={process.pid} display {display} port {port} "
                f"(unix socket)"
            )
            # 日志句柄随进程一起返回（三元组），由调用方在 terminate() 后 close()，
            # 否则成功路径会一直泄漏这个 fd（失败路径已在上面显式 close）。
            return process, prefix, log

        self.output.warning(
            "broadwayd could not be started on any of :5/:6/:7 -- upstream "
            "gtk_init()-based cases will be skipped (reported explicitly)"
        )
        return None, "", None

    # ------------------------------------------------------------------ test
    def test(self):
        runnable, runner = self._runner_prefix()
        if not runnable:
            self.output.warning(
                "target binaries cannot run here (no can_run/qemu/binfmt) — "
                "compile and link success only"
            )
            return
        libdirs = self._runtime_libdirs()
        bindir = self.cpp.build.bindirs[0]
        consumer = os.path.join(bindir, "test_package")
        upstream = os.path.join(bindir, "test-libappindicator")

        display_process, display_prefix, display_log = self._start_display(
            runner, libdirs
        )
        try:
            # 1) 鸿蒙消费者端到端用例（rule12）：无显示也真实运行（菜单段自行降级）
            self.output.info("running consumer end-to-end case (rule12)")
            # conan 的 run() 不接受 stdout=PIPE，改为把输出落盘再回读，
            # 以便解析 CONSUMER_E2E_RESULT 汇总行做断言数校验。
            #
            # ★ 这里**不能**用 `... | tee log`：self.run() 默认走 `/bin/sh -c`
            #   （多数镜像上是 dash，**不支持 `set -o pipefail`**，实测直接报
            #   `set: Illegal option -o pipefail` 并返回 2）。而管道的退出码取自
            #   最后一条命令，`tee` 恒为 0 —— test_consumer.c 以
            #   `return failures == 0 ? 0 : 1` 结尾，一旦有断言 FAIL，真退出码 1
            #   会被管道吞掉，conan create 仍然报绿，恰好重新打开本 PR 要关闭的
            #   那扇门。改为**纯重定向**（无管道），退出码即被测进程的退出码。
            consumer_log = os.path.join(self.build_folder, "consumer-e2e.log")
            self.run(
                display_prefix + shlex.quote(consumer)
                + f" > {shlex.quote(consumer_log)} 2>&1",
                env="conanrun",
            )
            # 断言数直接从 test_consumer.c 数出来，不在 Python 侧再写一份字面量
            # （避免 C 文件与校验器各写一份而漂移 —— 这正是 `checks=26`/27 一度
            #  在 MANIFEST.yml 与本文件之间不一致的根因）。
            # test_consumer.c 在 gtk_init_check() 失败时会跳过整个菜单往返分支，
            # 只打印 SKIP，进程仍返回 0，checks 会静默缩水；这里显式校验断言数与
            # display 标志，禁止这种降级。
            with open(consumer_log, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            if "CONSUMER_E2E_RESULT" not in text:
                raise ConanException(
                    "consumer end-to-end case printed no CONSUMER_E2E_RESULT "
                    "summary line -- cannot confirm real execution. Output: "
                    f"{text[-800:]}"
                )
            match = re.search(r"CONSUMER_E2E_RESULT[^\n]*", text)
            summary = match.group(0)
            checks = re.search(r"checks=(\d+)", summary)
            failures = re.search(r"failures=(\d+)", summary)
            if not checks or not failures:
                raise ConanException(
                    f"malformed CONSUMER_E2E_RESULT line: {summary}"
                )
            if int(failures.group(1)) != 0:
                raise ConanException(
                    f"consumer end-to-end case reported failures: {summary}"
                )

            # 不在 Python 侧重复写"断言数"字面量 —— 这正是 26/27 一度在
            # MANIFEST.yml 与本文件之间漂移的根因。改为校验**结构性不变量**：
            # 用例每执行一条断言就打印一行 `PASS [NN] ...`，编号从 1 连续递增。
            # 于是"断言总数"由 C 用例自己决定，Python 只负责证明没有静默缩水
            # （例如无显示后端时 test_consumer.c 会跳过整个菜单往返分支，
            #   编号将出现缺口、最大编号也会变小）。
            indices = [int(m) for m in re.findall(r"PASS \[(\d+)\]", text)]
            if not indices:
                raise ConanException(
                    "consumer case printed no PASS [NN] lines -- cannot confirm "
                    f"that any assertion really executed. Output: {text[-800:]}"
                )
            expected_checks = max(indices)
            missing = sorted(set(range(1, expected_checks + 1)) - set(indices))
            if missing:
                raise ConanException(
                    "consumer assertion sequence has gaps at "
                    f"{missing[:10]} -- some assertions were skipped "
                    f"(max index={expected_checks}). Refusing a silently "
                    f"weakened run. Summary: {summary}"
                )
            if int(checks.group(1)) != expected_checks:
                raise ConanException(
                    "consumer summary disagrees with the PASS sequence: "
                    f"checks={checks.group(1)} but max PASS index="
                    f"{expected_checks}. Summary: {summary}"
                )
            if "display=yes" not in summary:
                raise ConanException(
                    "consumer end-to-end case ran without a display backend "
                    f"(display=no): rule12 evidence is incomplete. Summary: {summary}"
                )
            self.output.info(
                f"consumer e2e verified: {checks.group(1)} checks, 0 failures, "
                "display=yes"
            )

            # 2) 上游 9 个 g_test 用例（逐字复制）——gtk_init() 需要显示后端。
            #    _start_display() 轮流尝试多个 display/端口。
            #
            #    ★ 起不来时**必须让构建失败**（raise ConanException），不能只打日志
            #      再 return：那样 `conan create` 仍退出 0，9 个上游用例被整体跳过
            #      却表现为绿色通过，而 MANIFEST.yml / notes.md 仍把这些用例记为
            #      已执行 —— 这正是「静默放行」，是本 PR 最需要避免的失效模式。
            #      如实失败，让上层明确看到「上游用例未验证」。
            if display_process is None:
                raise ConanException(
                    "UPSTREAM_TESTS_NOT_EXECUTED: gtk_init() needs a display "
                    "backend and broadwayd could not be started on any of "
                    ":5/:6/:7. Upstream g_test cases: 0 executed / 9 skipped. "
                    "Refusing to report a green test run for unverified "
                    "upstream tests. Verified real executions are recorded on "
                    "qemu + OHOS musl runroot (TAP 1..9 all ok) and on the "
                    "DAYU200 device -- see PR evidence."
                )
            self.output.info("running upstream test-libappindicator (9 g_test cases)")
            self.run(
                display_prefix + shlex.quote(upstream) + " --verbose", env="conanrun"
            )
        finally:
            if display_process is not None:
                display_process.terminate()
                # 回收子进程并关闭其日志 fd（成功路径的句柄由 _start_display 附带）
                try:
                    display_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    display_process.kill()
                    display_process.wait()
                if display_log is not None and not display_log.closed:
                    display_log.close()
