#!/usr/bin/env python3
"""Conan recipe — XNNPACK 0.0-git20241108.4ea82e5 (CMake, C/C++/ASM).

上游快照: google/XNNPACK @ 4ea82e595b36106653175dcb04b2aa532660d0d8
          (2024-11-08T14:56:11-08:00, "Cast to float to avoid compile error")
版本号口径: 上游没有 release tag，按本仓库既有惯例使用
          `0.0-gitYYYYMMDD.<short-sha>`（同 archives/c/cpuinfo、archives/r/ruy）。

上游事实（对 commit 4ea82e5 官方 tarball 实测审计，8923022 bytes，
sha256 3ef066f2f9b8ac474cd3fd606c601a30bbab59a56406c69019610339f02b6032）：

  * 纯 CMake 项目，`PROJECT(XNNPACK C CXX ASM)`，C99 + C++14，
    `cmake_minimum_required(VERSION 3.15)`（CMake 4.1.2 可 configure）。
  * 微内核是**按架构分派**的：顶层 CMakeLists 只在
    `XNNPACK_TARGET_PROCESSOR MATCHES "^arm64"` 时把 NEON / NEONFP16 /
    NEONFMA / NEONV8 / NEON_AARCH64 / NEONFMA_AARCH64 / FP16ARITH /
    NEONFP16ARITH(+_AARCH64) / NEONDOT(+_AARCH64) / NEONDOTFP16ARITH /
    NEONI8MM 以及 AARCH64 汇编（318 个 .S）加入构建，x86 的 SSE/AVX 分支
    在 aarch64 上**完全不参与**。`CMAKE_SYSTEM_PROCESSOR=aarch64` 会被
    XNNPACK 自己映射成内部值 "arm64"（CMakeLists.txt 第 92-93 行）。
  * 生产微内核 ≈ 696 个编译单元（含 242 个 scalar）；测试/基准打开时
    XNNPACK 会强制 `XNNPACK_BUILD_ALL_MICROKERNELS=ON`，额外编 NON_PROD
    约 2603 个单元。这就是本包构建量大的原因。
  * 对外 API 只有一个头 `include/xnnpack.h`（+ experiments-config.h），
    里面**直接 `#include "pthreadpool.h"`** —— 所以 pthreadpool 是硬依赖，
    且它的头必须是本包的公开交付物（package() 显式安装）。
  * 上游测试：gtest 驱动的 ctest，`test/*.cc` 共 364 个 TU，
    源码里 TEST/TEST_F/TEST_P(test) 宏约 5932 处，注册成 100+ 个 gtest
    可执行文件（微内核测试还会按 ADD_SHARDED_TEST 分片）。
  * 上游自带的 `cmake/Download*.cmake` 用 ExternalProject 在**configure 期**
    直连 github.com / gitlab.arm.com 下载 5 个依赖 —— CI worker 网络到不了，
    必须全部压掉（见下）。

OHOS 适配要点（都是"让上游在 OHOS/Conan 环境按预期工作"，非上游 bug 修复）：
  1. **依赖改用 Conan 包 + vendor 源码**：XNNPACK 的依赖判定统一写成
     `IF(NOT TARGET <dep>)`，因此在 `project()` 结束前把同名 target 建好即可
     让上游整段跳过；配合 `XNNPACK_USE_SYSTEM_LIBS=ON` 把顶部整块配置期下载
     压掉。落地文件 `xnnpack_project_include.cmake`（经标准变量
     `CMAKE_PROJECT_XNNPACK_INCLUDE` 注入），内容：
       * cpuinfo / fxdiv → 制品仓已适配的 Conan 包（CMakeDeps 提供 config）；
       * pthreadpool → vendor 源码 add_subdirectory（**制品仓无此包**，
         `conan list -r=ohpcd pthreadpool/*` 实测 0 命中；版本不是自选，
         就是上游 cmake/DownloadPThreadPool.cmake 钉的 revision）；
       * googletest → vendor 源码，用**上游 cmake/DownloadGoogleTest.cmake 钉的
         同一 revision**（df1544bcee0c… = 1.15.2，三个 CMakeLists 都声明
         cmake_minimum_required(VERSION 3.13)，CMake 4.1.2 可 configure）。
         注意不要退回 1.14.0：它的 DoubleNearPredFormat 缺同号无穷短路分支，
         会让 ±inf 断言算成 NaN 而假失败（见 conandata.yml 的详细说明）。
  2. **KleidiAI 关闭**（`XNNPACK_ENABLE_KLEIDIAI=OFF`）：上游 arm64 默认开启，
     但源码只从 gitlab.arm.com 拉（CI 的镜像 fallback 只覆盖 github.com）；
     它是可选的第三方 GEMM 加速层，关掉之后 XNNPACK 自带的
     NEON/NEONDOT/NEONI8MM/NEONFP16ARITH 微内核与运行期 CPU 分派**不受影响**。
  3. **CMAKE_SYSTEM_NAME 必须是 Linux**：上游白名单是
     `^(Android|Darwin|iOS|Linux|Windows|CYGWIN|MSYS|QURT)$`，OHOS profile 下
     Conan 会给 `HarmonyOS` ⇒ 上游 `FATAL_ERROR`。
  4. **配置产物路径**：`cmake_layout(..., build_folder="build_dir")` 避开
     HMDFS 大小写不敏感可能造成的 `BUILD`/`build` 同名（E470 既定解法）。
  5. **构建输出绑定日志文件**：OHOS 上 conan 的构建子进程若继承 recipe 进程
     的输出流，clang 会在第一个翻译单元静默退出（make/ninja 只报 Error 1、
     零诊断）。build/ctest 两步都写日志文件再回显（同 archives/r/ruy）。
  6. **必须关闭 FP 收缩**（`xnnpack_project_include.cmake` 里对 C/CXX 加
     `-ffp-contract=off`）：XNNPACK 的标量 f32 路径把 FMA 写成 `(a*b)+c`，
     且 `f32-scalar.h` 不定义 `XNN_SIMD_HAS_NATIVE_FMA` ⇒ 微内核按"没有 FMA"
     的标定常数走；aarch64 上 clang 默认 `-ffp-contract=on` 会把该表达式收缩成
     fmadd，算术与标定不一致，`f32-vgelu` 的标量有理微内核因此在 clamp 点残余
     ~3.6e-7、超出 10*FLT_EPSILON 容差（真机 73 条断言失败）。x86/SSE2 基线无
     FMA 指令不会收缩，所以这是 aarch64 特有的适配点。
  7. **显式限制并行度**：conan 取 `os.cpu_count()`（本机 20，实际 affinity 视
     容器而定）会造成超订；配方按法定的 affinity 数封顶 6（见 `_build_jobs`）。
     注意并行度**不能用 `-c tools.build:jobs=N` 覆盖**——`build()` 里的
     `self.conf.define(...)` 会无条件覆盖调用方传入的 conf 值；要压更低只能用
     `taskset -c 0-3` 限制 affinity，让 `min(sched_getaffinity, 6)` 落到 4。
  8. 汇编微内核：本设备 clang 15 `aarch64-unknown-linux-ohos` 直接支持
     NEON/fp16arith/dotprod/i8mm 的 aarch64 汇编，未做任何裁剪。
"""
import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rmdir)


def _python_executable():
    """给上游 EXECUTE_PROCESS 用的 python 解释器绝对路径。"""
    if sys.executable:
        return sys.executable
    return shutil.which("python3") or "python3"


class XnnpackConan(ConanFile):
    name = "xnnpack"
    version = "0.0-git20241108.4ea82e5"
    description = ("XNNPACK: highly optimized low-precision floating-point "
                   "neural-network inference operators (aarch64/ARM NEON, "
                   "x86 SSE/AVX, WebAssembly)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/XNNPACK"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("neural-network", "inference", "simd", "arm", "aarch64",
              "gemm", "convolution")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    # 上层 project() 注入钩子（见模块 docstring 第 1 条）
    exports = "xnnpack_project_include.cmake"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 依赖写成**裸 ref**（不带 @user/channel）：ohpcd 制品仓发布的是裸
        # ref，写 `@ohpcd/stable` 会在依赖解析阶段直接报
        # "Unable to find in remotes"（先例：archives/r/ruy、archives/f/ffmpeg）。
        #
        # cpuinfo 是制品仓内唯一版本（registry 实测），它声明了
        # cmake_target_name = cpuinfo::cpuinfo，钩子只需做一次裸名别名。
        self.requires("cpuinfo/0.0-git20250905.877328f")
        # fxdiv 是 header-only 包（package_info.libs = []），同样被 XNNPACK
        # 与 vendor 的 pthreadpool 共用。
        self.requires("fxdiv/0.0-git63058eff77")

    def layout(self):
        # src_folder="src"：配方文件与上游源码树分离（同 CCI 的 xnnpack 配方）。
        # build_folder="build_dir"：HMDFS 大小写不敏感，默认的 `build` 在同一
        # 层遇到名为 BUILD 的文件会解析成同一 inode（官方 E470/E193）。
        cmake_layout(self, src_folder="src", build_folder="build_dir")

    # ────────────────────────────── source ──────────────────────────────
    def export_sources(self):
        """导出 conandata.yml 的 patches 段（本包 `patches: {}` ⇒ 空操作）。

        这是本仓库 7879 份配方的统一写法（cpuinfo/ruy/a52dec/jube… 都是
        `def export_sources(self): export_conandata_patches(self)`）；保留它
        使"以后要加补丁"时无需再动骨架，也让 conan-verify 的 G1 配方完整性
        检查能看到补丁通道确实接上了（`patches: {}` 时两个调用都是 no-op）。
        """
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)          # patches: {} ⇒ no-op（见上）
        deps_dir = os.path.join(self.source_folder, "third_party_src")
        # pthreadpool：上游 cmake/DownloadPThreadPool.cmake 钉的同一 revision
        get(self, **self.conan_data["pthreadpool"], strip_root=True,
            destination=os.path.join(deps_dir, "pthreadpool"))
        # googletest：上游 cmake/DownloadGoogleTest.cmake 钉的同一 revision
        # （df1544bcee0c… = 1.15.2；不用 1.14.0 的原因见 conandata.yml）
        get(self, **self.conan_data["googletest"], strip_root=True,
            destination=os.path.join(deps_dir, "googletest"))

    # ───────────────────────────── generate ─────────────────────────────
    @staticmethod
    def _build_jobs():
        """并行度：取进程 affinity（而不是 os.cpu_count()）并封顶 6。

        本包编译单元约 3700 个，实测 -j8 时共享设备在 37% 处出现
        `/bin/sh: can't fork - try again`（make 子进程 fork 被内核拒绝 ⇒
        整个构建 Error 2）。这是共享设备上的进程数预算问题
        （notes/device-facts.md §一.5 / §一.9），不是配方缺陷；降一档
        并行度可显著降低触发概率，代价只是构建时间。

        **不能靠 `-c tools.build:jobs=N` 覆盖本值**：下面 build() 里的
        `self.conf.define()` 会无条件覆盖调用方传入的 conf（Conan 2.29 的
        `Conf.define` 直接写 `_values`，真机实测）。需要更低并行度时用
        `taskset -c 0-3` 限制 affinity，本函数的 min() 会随之落到 4。
        """
        try:
            n = len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            n = os.cpu_count() or 4
        return max(1, min(n, 6))

    def generate(self):
        tc = CMakeToolchain(self)

        # 库类型：显式而不是靠 BUILD_SHARED_LIBS（上游默认值是 "default"）
        tc.cache_variables["XNNPACK_LIBRARY_TYPE"] = (
            "shared" if self.options.shared else "static")
        tc.cache_variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF")
        # 关掉上游顶部整块 configure 期 ExternalProject 下载（见 docstring）
        tc.cache_variables["XNNPACK_USE_SYSTEM_LIBS"] = True
        # 上游单测（gtest/ctest）真实执行，作为 PR 的"上游测试用例"口径
        tc.cache_variables["XNNPACK_BUILD_TESTS"] = True
        tc.cache_variables["XNNPACK_BUILD_BENCHMARKS"] = False
        tc.cache_variables["XNNPACK_BUILD_ALL_MICROKERNELS"] = True
        tc.cache_variables["XNNPACK_BUILD_LIBRARY"] = True
        # 可选第三方 GEMM 层（gitlab.arm.com 拉不到）：关闭，见 docstring
        tc.cache_variables["XNNPACK_ENABLE_KLEIDIAI"] = False
        # 装配期不要重新触发默认构建（已在 build() 里全量构建）
        tc.cache_variables["CMAKE_SKIP_INSTALL_ALL_DEPENDENCY"] = True
        # Windows 共享库导出符号（对 OHOS/Linux 无副作用）
        tc.cache_variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True

        # 钩子 + vendor 源码树（绝对路径；exports 已把钩子放进 recipe 目录）
        tc.cache_variables["CMAKE_PROJECT_XNNPACK_INCLUDE"] = os.path.join(
            self.recipe_folder, "xnnpack_project_include.cmake")
        deps_dir = os.path.join(self.source_folder, "third_party_src")
        tc.cache_variables["XNNPACK_PTHREADPOOL_SOURCE_DIR"] = os.path.join(
            deps_dir, "pthreadpool")
        tc.cache_variables["XNNPACK_GOOGLETEST_SOURCE_DIR"] = os.path.join(
            deps_dir, "googletest")
        tc.cache_variables["XNNPACK_OHOS_VENDOR_GTEST"] = True
        # fxdiv 的包目录：只为压掉 pthreadpool 的 FXdiv 下载分支（钩子里说明）
        tc.cache_variables["XNNPACK_FXDIV_SOURCE_DIR"] = \
            self.dependencies["fxdiv"].package_folder
        # 上游 CMakeLists 第 1039 行无条件用 ${CPUINFO_SOURCE_DIR}/include 做
        # hardware-config 的 include 目录，给它真值避免出现 `-I/include`。
        tc.cache_variables["CPUINFO_SOURCE_DIR"] = \
            self.dependencies["cpuinfo"].package_folder
        # 微内核清单与 build_identifier 都靠 EXECUTE_PROCESS 调 python 生成。
        # 上游那段有个 latent bug：`find_package(Python)` 失败时它写的是
        # `SET(PYTHON_EXECUTABLE "python3")`（少了个 n），而随后真正被调用的
        # 是 `${Python_EXECUTABLE}` ⇒ 空命令 ⇒ 直接 FATAL_ERROR
        # "Failed to generate microkernels.cmake"。worker 侧的 PATH 与设备
        # 不同（notes/device-facts.md §一.4），所以这里显式钉死解释器，
        # 让两边都走同一条确定路径。
        tc.cache_variables["Python_EXECUTABLE"] = _python_executable()

        # OHOS：CMake 不认 HarmonyOS（上游白名单会 FATAL_ERROR），
        # 架构也退化成 unknown ⇒ 微内核分派会全部走空。
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            arch = str(self.settings.arch)
            if arch in ("armv8", "armv8.3", "armv9", "aarch64", "arm64", "arm64e"):
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            elif arch in ("x86_64", "x86"):
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = arch
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch
            # 避免 CMake 编译器探测阶段就去调用链接器
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"

        tc.generate()
        CMakeDeps(self).generate()

    # ─────────────────────────────── build ──────────────────────────────
    def build(self):
        # 并行度：conan 默认吃 os.cpu_count()，超订会让这个超大构建更慢甚至触发
        # 进程创建失败（notes/device-facts.md §一.7）。注意 define() 会**覆盖**
        # 调用方 `-c tools.build:jobs=N`，要更低并行度只能用 taskset 限 affinity。
        self.conf.define("tools.build:jobs", self._build_jobs())

        cmake = CMake(self)
        self._run_bound_step(
            "configure", lambda stream: cmake.configure(stdout=stream, stderr=stream))
        self._run_bound_step(
            "build", lambda stream: cmake.build(stdout=stream, stderr=stream))
        self._run_upstream_tests()

    def _run_bound_step(self, label, step):
        """把一步 CMake 命令的输出绑定到 build_dir/logs/<label>.log。

        OHOS 真机实测（同 archives/r/ruy、archives/r/reliable）：conan 的
        ConanFile.run() 把 recipe 进程的输出流继承给构建子进程时，clang 会在
        第一个真正编译的翻译单元上静默退出（非 0 退出、一行诊断都没有，
        ninja/make 只能报 "Error 1"）。输出不继承时才正常。
        跑完再回显进 conan 输出，让 CI 的 L1b/L1c 能在 conan create 日志里
        grep 到编译与 ctest 痕迹（全部关进文件会让证据消失）。
        """
        log_dir = os.path.join(self.build_folder, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "{}.log".format(label))
        try:
            with open(log_path, "w", encoding="utf-8", errors="replace") as stream:
                step(stream)
        except ConanException:
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                tail = handle.read().splitlines()[-80:]
            self.output.error(
                "build step '{}' failed; last lines of {}:".format(label, log_path))
            self.output.error("\n".join(tail))
            raise
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
        self.output.info("--- {}.log ({} lines) ---".format(label, len(lines)))
        for start in range(0, len(lines), 500):
            self.output.info("\n".join(lines[start:start + 500]))

    # ───────────────────────── upstream tests ───────────────────────────
    _UPSTREAM_TEST_TIMEOUT = 1800           # 秒；G2 整体上限 3600s
    _RAN_RE = re.compile(r"\[\s*={5,}\s*\]\s+(\d+)\s+tests?\s+from\s+\d+\s+test suites? ran")
    _PASSED_RE = re.compile(r"\[\s+PASSED\s+\]\s+(\d+)\s+tests?")
    _FAILED_RE = re.compile(r"\[\s+FAILED\s+\]\s+(\d+)\s+tests?")
    _SKIPPED_SUM_RE = re.compile(r"\[\s+SKIPPED\s+\]\s+(\d+)\s+tests?")
    _SKIPPED_ONE_RE = re.compile(r"^\[\s+SKIPPED\s+\]\s+\S", re.MULTILINE)

    def _ctest_dir(self):
        """定位真正配好的 CMake 二进制目录（含 CTestTestfile.cmake）。"""
        for root, _dirs, files in os.walk(self.build_folder):
            if "CTestTestfile.cmake" in files:
                return root
        return self.build_folder

    def _registered_ctest_count(self, ctest, ctest_dir):
        """框架注册数：ctest 条目数（独立于本次运行的第二口径，仅作参考）。"""
        try:
            proc = subprocess.run([ctest, "-N"], cwd=ctest_dir,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=300)
            m = re.search(r"Total Tests:\s*(\d+)", proc.stdout or "")
            return int(m.group(1)) if m else 0
        except Exception:                                   # noqa: BLE001
            return 0

    def _discover_gtest_cases(self, ctest, ctest_dir):
        """清点 N：每个 gtest 可执行文件用 --gtest_list_tests 列出真实用例数。

        这是"框架注册数"口径下最硬的 N —— 由**已编译的二进制**自己报告，
        因此自动带上 `#if` 守卫、分片与 TEST_P 实例化的真实结果，与本次
        是否运行无关。ctest 的 --show-only=json-v1 给出每个条目的真实命令行。

        同时统计上游**自带的 DISABLED_ 用例数**：`--gtest_list_tests` 会把它们
        照常列出（DISABLED_ 前缀可以在套件行，也可以在用例行），而 gtest 永不
        执行它们 ⇒ 这部分就是 TOTAL 里 NOT_RUN 的唯一合法来源。真机实测本包
        有 3 个（`DISABLED_FULLY_CONNECTED_NC_QP8_F32_QC4W.*`）。
        """
        commands = []
        try:
            proc = subprocess.run([ctest, "--show-only=json-v1"], cwd=ctest_dir,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=300)
            data = json.loads(proc.stdout or "{}")
            for test in data.get("tests", []):
                cmd = test.get("command") or []
                # 只为真实可执行文件去重（无 .exe 的 OHOS 侧）
                for token in cmd:
                    if os.path.basename(token).endswith("-test"):
                        commands.append(token)
                        break
        except Exception as exc:                            # noqa: BLE001
            self.output.warn("ctest --show-only=json-v1 failed: %r" % (exc,))
        commands = sorted(set(commands))
        total = 0
        disabled = 0
        binaries = 0
        for binary in commands:
            if not os.path.isfile(binary):
                continue
            try:
                proc = subprocess.run([binary, "--gtest_list_tests"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL,
                                      text=True, timeout=120)
            except Exception:                               # noqa: BLE001
                continue
            binaries += 1
            suite_disabled = False
            for line in (proc.stdout or "").splitlines():
                # gtest_list_tests: 套件行 "Suite." 顶格，用例行缩进两格
                if line.startswith("  ") and line.strip():
                    total += 1
                    if suite_disabled or line.strip().startswith("DISABLED_"):
                        disabled += 1
                elif line.strip():
                    suite_disabled = line.strip().startswith("DISABLED_")
        return total, binaries, disabled

    def _run_upstream_tests(self):
        """在 build() 内真实执行上游 ctest，并结构化输出真实计数。

        跑法说明：`ctest -V`（不是 --output-on-failure）——后者会把 PASSING
        用例的 stdout 吞掉，gtest 的 "[  PASSED  ] N tests" 汇总行就看不到了，
        计数会系统性偏低（cpuinfo 实测 132/137）。`ctest -V` 每个套件只打印
        一次（而 `-V --output-on-failure` 会把失败的再打一遍 ⇒ 重复计数）。
        """
        ctest = shutil.which("ctest") or "ctest"
        ctest_dir = self._ctest_dir()
        log_path = os.path.join(self.build_folder, "logs", "ctest.log")

        discovered, binaries, upstream_disabled = self._discover_gtest_cases(
            ctest, ctest_dir)
        registered = self._registered_ctest_count(ctest, ctest_dir)

        try:
            proc = subprocess.run([ctest, "-V"], cwd=ctest_dir,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=self._UPSTREAM_TEST_TIMEOUT)
            output = proc.stdout or ""
            rc = proc.returncode
        except Exception as exc:                            # noqa: BLE001
            raise ConanException("ctest harness could not run: %r" % (exc,))

        # 归档原始证据（绑定到 build_folder，供 finish/证据链回读）
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8", errors="replace") as handle:
            handle.write(output)
        # 回显尾部，保证 ctest 痕迹留在 conan create 日志里
        tail = output.splitlines()[-400:]
        self.output.info("--- ctest.log tail ({} lines total) ---".format(
            len(output.splitlines())))
        self.output.info("\n".join(tail))

        ran = sum(int(n) for n in self._RAN_RE.findall(output))
        passed = sum(int(n) for n in self._PASSED_RE.findall(output))
        failed = sum(int(n) for n in self._FAILED_RE.findall(output))
        skipped = sum(int(n) for n in self._SKIPPED_SUM_RE.findall(output))
        skipped += len(self._SKIPPED_ONE_RE.findall(output))
        not_run = max(0, discovered - ran)

        # NOT_RUN 的唯一合法来源是上游自带的 DISABLED_ 用例（gtest 列出但不执行）。
        # 任何**解释不了**的 NOT_RUN 仍然判失败（反假绿：不许拿"少跑了"当通过）。
        unexplained = max(0, not_run - upstream_disabled)

        # 反假绿：rc=0 + 有输出 + 解析到 0 条判定 ⇒ 判定没真跑
        if rc == 0 and output.strip() and ran == 0:
            raise ConanException(
                "ctest returned 0 but no gtest verdict lines were parsed "
                "from {} - upstream tests did not really run".format(log_path))

        status = "passed" if (rc == 0 and failed == 0 and unexplained == 0
                              and discovered > 0) else "failed"
        result = {
            "status": status,
            "framework": "ctest+gtest",
            "command": "ctest -V",
            "counting_method": "N = sum of --gtest_list_tests cases over all "
                               "registered gtest binaries (framework registration)",
            "declared_total": discovered,
            "total": ran,                    # TOTAL = PASS + FAIL + SKIP + NOT_RUN
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "not_run": not_run,
            "not_run_upstream_disabled": upstream_disabled,
            "not_run_unexplained": unexplained,
            "gtest_binaries": binaries,
            "ctest_registrations": registered,
            "ctest_rc": rc,
        }
        # TOTAL 必须自洽（§3.5：TOTAL = PASS + FAIL + SKIP + NOT_RUN）
        if passed + failed + skipped + not_run != discovered:
            result["status"] = "failed"
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream_result.json"),
                      "w", encoding="utf-8") as handle:
                handle.write(json.dumps(result, ensure_ascii=False, indent=1))
        except OSError:
            pass
        if result["status"] != "passed":
            raise ConanException(
                "xnnpack upstream tests did not fully pass: rc={} passed={}/{} "
                "failed={} skipped={} not_run={} (see {})".format(
                    rc, passed, discovered, failed, skipped, not_run, log_path))

    # ────────────────────────────── package ─────────────────────────────
    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # include/xnnpack.h 里 `#include "pthreadpool.h"` ⇒ 该头必须随包安装
        # （pthreadpool 自己的 INSTALL(FILES ...) 规则通常已经装好，这里是兜底）
        copy(self, "pthreadpool.h",
             src=os.path.join(self.source_folder, "third_party_src",
                              "pthreadpool", "include"),
             dst=os.path.join(self.package_folder, "include"))
        # 上游/依赖不会写 cmake 导出文件，防御性清理
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        # 组件化：静态构建时 libXNNPACK.a 里的未定义符号分布在
        # microkernels-prod / pthreadpool / fxdiv / cpuinfo 上，链接顺序由
        # conan 按组件 requires 做拓扑排序，因此这里用组件而不是单一 libs。
        self.cpp_info.components["xnnpack"].libs = ["XNNPACK"]
        self.cpp_info.components["xnnpack"].includedirs = ["include"]
        self.cpp_info.components["xnnpack"].requires = [
            "microkernels-prod", "pthreadpool", "cpuinfo::cpuinfo", "fxdiv::fxdiv",
        ]
        self.cpp_info.components["microkernels-prod"].libs = ["microkernels-prod"]
        self.cpp_info.components["microkernels-prod"].includedirs = ["include"]
        self.cpp_info.components["microkernels-prod"].requires = [
            "pthreadpool", "fxdiv::fxdiv",
        ]
        self.cpp_info.components["pthreadpool"].libs = ["pthreadpool"]
        self.cpp_info.components["pthreadpool"].includedirs = ["include"]
        self.cpp_info.components["pthreadpool"].requires = ["fxdiv::fxdiv"]
        # OHOS/clang 驱动不隐式链接 libm/libpthread（R32：判据必须含 OHOS）
        if str(self.settings.os) in ("Linux", "OHOS"):
            for comp in ("xnnpack", "microkernels-prod", "pthreadpool"):
                self.cpp_info.components[comp].system_libs = ["m", "pthread"]
