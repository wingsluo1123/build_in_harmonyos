#!/usr/bin/env python3
"""Conan recipe — uefitool 0.28.0-a73 (UEFI 固件镜像解析/提取/重建工具链)。

上游事实（对 tag `A73` 官方 tarball 实测审计：2400878 bytes，
sha256 81d9944d75e27d4afbc8559d9ba913552006fd21ce9cadf357a4a0f58e59507e）：

  * 上游有 **三个** 可执行目标：
      - `UEFITool`     —— Qt6 Widgets GUI（含内置 QHexView 子目录）
      - `UEFIExtract`  —— 纯 CLI，**不依赖 Qt**
      - `UEFIFind`     —— 纯 CLI，**不依赖 Qt**
    本包只交付后两个：OHOS PC 上没有 Qt6，而两个 CLI 才是可脚本化、
    可在无显示环境下验证的部分。
  * ★★ **零外部依赖**：`UEFIExtract/CMakeLists.txt` 与 `UEFIFind/CMakeLists.txt`
    的 `PROJECT_SOURCES` 把 zlib（`common/zlib/*.c`）、brotli（`common/brotli/**`）、
    LZMA SDK（`common/LZMA/SDK/C/*.c`）、Tiano（`common/Tiano/*.c`）、
    bstrlib（`common/bstrlib/*`）、摘要算法（`common/digest/{sha1,sha256,sha512,sm3}.c`）
    以及 Kaitai 生成代码（`common/generated/*.cpp`，**已入库**）全部内联进可执行文件。
    ⇒ 只要「编译器 + CMake >= 3.22」，不需要任何 Conan 运行时依赖。
  * C++11（`CMAKE_CXX_STANDARD 11` + `CMAKE_CXX_EXTENSIONS OFF`）。
  * 编译期四个能力开关由两个子工程各自的 `ADD_DEFINITIONS` 硬编码打开：
    `U_ENABLE_{NVRAM,ME,FIT,GUID_DATABASE}_SUPPORT`。本包保持上游默认（四个全开）。
  * 许可证：`LICENSE.md` 正文为 BSD 二条款（SPDX: BSD-2-Clause）。
  * 版本号来自 `version.h` 的 `#define PROGRAM_VERSION "NE alpha 73" " (" __DATE__ ")"`
    ⇒ 对应上游 **new_engine 分支** 的 tag `A73`（commit 29796629，2026-01-26）。
    `0.28.0` 那个版本号属于 `old_engine` 分支，**不是**本 tag，不要混用。

上游测试（★ 实测：**一个都没有**，详见 test_package/MANIFEST.yml）：
  * 全树 `meson.build` 里 **零处** `test()`；无 `tests/`、`test/` 目录；
    无 `enable_testing()` / `add_test(`。
  * 唯一沾"测试"的是 `fuzzing/ffsparser_fuzzer.cpp` —— 一个 libFuzzer 入口
    （`LLVMFuzzerTestOneInput`），不是可执行的测试套件，也不带种子语料。
  ⇒ 本包的全部功能证据来自 test_package（见下），
    PR 正文的"上游测试"列如实写 N/A，**不编造 100%**。

为什么要额外一个 `cmake/CMakeLists.txt`（适配侧新增，不改上游一个字）：
  * 上游根 `CMakeLists.txt` 无条件 `ADD_SUBDIRECTORY(UEFITool)`，而
    `UEFITool/CMakeLists.txt` 第 9 行是 `FIND_PACKAGE(Qt6 REQUIRED COMPONENTS Widgets)`
    ⇒ 在没有 Qt6 的平台上根工程 configure 阶段即 FATAL_ERROR，两个 CLI 目标
    根本到不了编译。故本包用 `exports_sources` 带一个只装两个 CLI 子工程的
    构建入口，`cmake.configure(build_script_folder="cmake")` 指向它。
    这是 CCI 的常规做法（自带构建入口而非改上游），收益是
    **patches_applied 为空、上游零改动**，也就没有坑 16.22 的补丁计数同步问题。

OHOS 适配要点（三条，均已在真机实测过同族形态）：
  * `CMAKE_SYSTEM_NAME` 保持 `Linux`：CMake 内置系统表没有 OHOS 条目，
    照上游惯例新造 `OHOS` 会让上游按 `cmake/os/${CMAKE_SYSTEM_NAME}.cmake`
    找模块而落空。OHOS 侧沿用 `Linux` + 由 conan toolchain 提供
    sysroot/编译器封装，能力差异由源码侧的 `U_ENABLE_*` 宏表达。
  * `CMAKE_SKIP_RPATH=ON` + `CMAKE_SKIP_INSTALL_RPATH=ON`：本包**不产出任何
    第三方 `.so`**（brotli / LZMA / zlib / Tiano / bstrlib / digest 全部以
    源码内联），产物的 `NEEDED` 只剩平台自带的 `libc.so` 与
    `libc++_shared.so`（真机 `readelf -d` 实测 2 条）⇒ 没有任何"要靠 RPATH
    才找得到"的库；而 OHOS 的 HMDFS 上"安装期重写 RPATH"会写坏 ELF 的签名
    信息（`.note.ohos.ident` / `.codesign` 段），导致装出来二进制
    `Operation not permitted`（rc=126，知识库 E077；qdl 2.7 实测同族）。
    关掉 RPATH 后 CMake 的 install 不再有 relink 动作，直接绕开这一类。
    （真机实测：关掉后两个产物的 `RPATH`/`RUNPATH` 条目数均为 0，而
    `.note.ohos.ident` 与 `.codesign` 段都还在。）
  * `tools.build:jobs = 1`（R9 / E074）：`/storage/Users/**` 走 HMDFS，
    GNU make 的 jobserver fifo 建不出来（`mkfifo ... Operation not permitted`），
    表现为并行子任务集体 `Error 1` 且日志里一行编译器诊断都没有。
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)

import os

# OHOS 侧 settings.arch -> CMake 目标处理器名（与 ci/conan/profiles/ohos-aarch64 一致）
_CMAKE_PROCESSOR = {
    "armv8": "aarch64",
    "armv8.3": "aarch64",
    "armv9": "aarch64",
    "aarch64": "aarch64",
    "arm64": "aarch64",
}


class UefitoolConan(ConanFile):
    name = "uefitool"
    version = "0.28.0-a73"
    description = ("UEFI firmware image toolkit: uefiextract parses and dumps the "
                   "FFS tree of a firmware image (report / dump / guids modes), "
                   "uefifind searches images for hex patterns in headers and bodies")
    license = "BSD-2-Clause"
    homepage = "https://github.com/LongSoft/UEFITool"
    url = "https://github.com/LongSoft/UEFITool"
    topics = ("uefi", "firmware", "bios", "ffs", "flash-descriptor",
              "reverse-engineering", "firmware-analysis")

    # 纯工具包：产物只有 bin/{uefiextract,uefifind}，没有库、没有公共头，
    # 也就没有 ABI 概念。同仓先例：archives/q/qdl/2.7、archives/2/2048.c/1.0.3。
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 适配侧构建入口（两个 CLI 子工程的装载器，见模块 docstring）
        copy(self, "cmake/CMakeLists.txt",
             src=self.recipe_folder, dst=self.export_sources_folder)
        # L0q：export_sources 必须覆盖 patches（本包补丁列表为空，调用仍然保留）
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS：CMake 不认识 OHOS，沿用 Linux 平台模块（见模块 docstring 第 1 条）
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            processor = _CMAKE_PROCESSOR.get(str(self.settings.arch))
            if processor:
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = processor
        # 没有任何"要靠 RPATH 才找得到"的库（第三方库全部源码内联，NEEDED
        # 只剩平台自带的 libc.so 与 libc++_shared.so）⇒ 不留 RPATH；同时
        # 绕开 OHOS 安装期 relink 写坏 ELF 签名段（E077）
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"
        tc.variables["CMAKE_SKIP_INSTALL_RPATH"] = "ON"
        # OHOS：避免 CMake 编译器探测阶段就去调用链接器
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R9 / E074：HMDFS 上 GNU make 的 jobserver fifo 建不出来（EPERM），
        # 必须固定单 job。必须在 CMake(self) 之前定义。
        self.conf.define("tools.build:jobs", 1)
        cmake = CMake(self)
        # configure 不编译任何工程代码（CMake 自己会把 try_compile 的输出收进
        # 构建目录内的日志），真机多次实测均正常，故保持直连输出。
        cmake.configure(build_script_folder="cmake")
        # 构建步骤输出绑定日志文件，跑完再回显 —— 理由见 _run_bound_step()
        self._run_bound_step(
            "build", lambda stream: cmake.build(stdout=stream, stderr=stream))
        # 上游零测试套件 ⇒ ctest 默认会因"找不到测试"返回非 0。
        # 适配侧的 cmake/CMakeLists.txt 注册了 3 个只依赖两个 CLI 自身退出码的
        # 冒烟测试，因此这里是"零测试空跑"的反面：有 3 条真实、确定的用例。
        # 它同时把 `ctest` 痕迹留在 conan create 日志里（CI 的 L1c 读取该痕迹）。
        self._run_bound_step(
            "ctest", lambda stream: cmake.test(stdout=stream, stderr=stream))

    def _run_bound_step(self, label, step):
        """执行一个构建步骤，并把该步骤的输出绑定到独立日志文件。

        ``step(stream)`` 内调用 CMake helper（configure/build/test 均支持
        ``stdout=``/``stderr=``）。OHOS 真机实测：conan 的 ``ConanFile.run()``
        会把 recipe 进程自身的输出流继承给构建子进程，在这种形态下 clang 会在
        第一个真正编译的翻译单元上静默退出（非 0 退出、零诊断，make 只报
        ``Error 1``）。把输出绑定到普通文件即可恢复正常。
        同族已合入先例：archives/r/reliable/1.3.5、archives/l/libfishcamp/1.2。

        回显是**必须**的：CI 的 L1b/L1c 要在 conan create 日志里 grep 编译痕迹
        与测试驱动痕迹，把输出全部关进文件等于把证据抹掉。
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

    def package(self):
        cmake = CMake(self)
        # 上游两个子工程各自声明了 INSTALL(TARGETS <t> RUNTIME DESTINATION bin)，
        # 装出来就是 bin/uefiextract 与 bin/uefifind。
        cmake.install()
        copy(self, "LICENSE.md",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # ★ 上游只在 GUI 的 Qt 资源里带 GUID 数据库（UEFITool/uefitool.qrc 第 3 行
        #   `<file alias="guids.csv">../common/guids.csv</file>`），**从不安装它**；
        #   而两个 CLI 的 main() 第一步就是 initGuidDatabase("guids.csv") ——
        #   它按**当前工作目录**查找，找不到就只得到一个空的 GUID 名表
        #   （guiddatabase.cpp 里读失败不报错、不中止，报告里 GUID 退回纯十六进制）。
        #   随包放一份到 share/uefitool/，使用者 `cp` 到工作目录即可让报告里出现
        #   可读的 GUID 名（例如 EFI_FIRMWARE_FILE_SYSTEM2_GUID 这种）。这是本包
        #   唯一新增的安装内容，且不改变任何上游行为。
        copy(self, "guids.csv",
             src=os.path.join(self.source_folder, "common"),
             dst=os.path.join(self.package_folder, "share", "uefitool"))

    def package_info(self):
        # 纯工具包：只有 bin/。库型包的 cpp_info.libs/includedirs 在这里都为空，
        # 只保留 bindirs（同仓先例 archives/q/qdl/2.7）。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
