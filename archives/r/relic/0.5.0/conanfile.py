#!/usr/bin/env python3
"""Conan recipe — relic 0.5.0（RELIC 密码学元工具箱，CMake 构建）。

上游：relic-toolkit/relic，tag `relic-toolkit-0.5.0`（源码与 sha256 见
conandata.yml）。上游无任何依赖，纯 C + CMake。

五处适配点**全部落在配方 cache 变量与 package_info() 层，未修改上游任何源文件**：

1. **CMake 4 拒绝老策略版本**：上游首行 `cmake_minimum_required(VERSION 3.1)`，
   设备 CMake 4.1.2 直接
   `CMake Error at CMakeLists.txt:1 (cmake_minimum_required)` ⇒
   注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4 的官方兼容逃生口）。
   必须走 `cache_variables`（= 命令行 `-D`，在解析任何 CMakeLists 之前生效）；
   写进 `tc.variables` 会落进 conan_toolchain.cmake，那是在
   `cmake_minimum_required()` **之后** include 的，救不了首行。

2. **HarmonyOS 系统名使上游平台探测落空（本包核心适配点）**：
   `ci/conan/profiles/ohos-aarch64` 的 `os=OHOS` 经 CMakeToolchain 映射为
   `CMAKE_SYSTEM_NAME=HarmonyOS`，而上游 `CMakeLists.txt:183` 是
   `if(CMAKE_SYSTEM_NAME STREQUAL Linux)` ⇒ 分支不命中，`OPSYS` 为空，
   连带三处退化：
     * `CMakeLists.txt:194` `add_definitions(-D_GNU_SOURCE)` 丢失；
     * `CMakeLists.txt:199` `TIMER` 落到 `else()` 分支 = `ANSI`
       （原本应为 `HPROC`，即 `getrusage`/`clock_gettime` 高精度计时器）；
     * `src/CMakeLists.txt:172` `LINK_LIBS` 不再 `target_link_libraries(rt)`。
   实测对照（同源同参数，仅差一个 `-DOPSYS`）：
     - 不注入：`-- Configured operating system: `（空）、`TIMER:STRING=ANSI`、
       全部 `flags.make` 中 **0 处** `_GNU_SOURCE`；
     - 注入：`-- Configured operating system: LINUX`、`TIMER:STRING=HPROC`、
       `relic.dir/flags.make` 等 36 个 `flags.make` 全部带上 `_GNU_SOURCE`。
   ⇒ 配方注入 `-DOPSYS=LINUX`。`OPSYS` 上游声明为 `set(... CACHE STRING ...)`，
   命令行已存在的 cache 项不会被它覆盖，且该行在 `if()` 判定**之前**执行，
   因此一处注入即同时恢复三处。

3. **上游默认 `TESTS=100`**（每条用例跑 100 遍）会把构建时间顶爆 ⇒ 取 `TESTS=1`
   （每条用例跑一遍）。同时 `BENCH=0` 关掉基准目标、`DOCUM=OFF` 关掉 doxygen
   文档目标（两者都不进包，纯耗时）。

4. **`ARITH` 保持上游默认 `easy`（可移植 C 后端）**：⛔ 不用 `arm-asm-254` ——
   它确实会被选中（Linker flags 指向 `src/low/arm-asm-254/`），但那些 `.s`
   是 **AArch32** 指令（`MOV pc, lr`、`LDMIA sp!, {r4-r12, r14}`），
   在 aarch64 上编译即 `error: invalid operand`。

5. **`shared` 默认 False**：上游默认同时产出 `librelic.so` 与 `librelic_s.a`，
   但 HarmonyOS 平台模块缺失使 `CMAKE_SHARED_LIBRARY_SONAME_*` 未定义 ⇒
   `.so` **不带 SONAME**（实测 `llvm-readelf -d` 无 `(SONAME)` 条目），
   消费者 `DT_NEEDED` 只能记裸 `librelic.so`、必须靠 `LD_LIBRARY_PATH`
   才能加载（实测：不带环境 `Error loading shared library librelic.so`；
   带上则正常运行）。静态包无此运行期装载问题，故默认取静态；
   `shared=True` 时按上游原样产出 `.so`（同一份源码，两种产物）。
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class RelicConan(ConanFile):
    name = "relic"
    version = "0.5.0"
    description = "RELIC toolkit - an efficient library for cryptography"
    license = ("LGPL-2.1-or-later", "Apache-2.0")
    homepage = "https://github.com/relic-toolkit/relic"
    url = ""  # CI fills this
    topics = ("relic", "cryptography", "bignum", "elliptic-curves", "pairing")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: 判断用 in ("Linux", "OHOS")，不能 == "Linux"
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "relic/0.5.0 只在 Linux / OHOS 上适配与验证过，当前 os=%s"
                % self.settings.os)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # (1) CMake 4.x 拒绝 cmake_minimum_required(< 3.5) 的老工程。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # (2) 上游 CMakeLists.txt:183 `if(CMAKE_SYSTEM_NAME STREQUAL Linux)`
        #     在 CMAKE_SYSTEM_NAME=HarmonyOS 下落空 ⇒ 显式给该分支唯一的
        #     输出变量，恢复 OPSYS=LINUX / TIMER=HPROC / -D_GNU_SOURCE /
        #     LINK_LIBS 的 -lrt（见模块 docstring 第 2 条的实测对照）。
        tc.cache_variables["OPSYS"] = "LINUX"

        # (3) 上游默认 TESTS=100、BENCH=100（各跑 100 遍）、DOCUM=on。
        #     本包只要「每条用例跑一遍」的真实上游测试，其余两项不进包。
        tc.cache_variables["TESTS"] = "1"
        tc.cache_variables["BENCH"] = "0"
        tc.cache_variables["DOCUM"] = "OFF"

        # 上游 SHLIB/STLIB 都是 option()，命令行已存在 cache 项即不覆盖。
        # 上游 test/CMakeLists 的 `if (STLIB) … else if (SHLIB)` 决定测试
        # 可执行文件链接静态还是动态产物，两个开关互斥即可保持语义单一。
        tc.cache_variables["SHLIB"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["STLIB"] = "OFF" if self.options.shared else "ON"

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试在配方 build() 里真实执行（上游 CMake 的 ctest 注册）：
        # 18 个 add_test 目标（err/bn/dv/fp/fpx/fb/fbx/ep/epx/eb/ed/ec/
        # pc/pp/md/cp/rand/core），TESTS=1 ⇒ 每条用例跑一遍。
        # 失败时先把 ctest 日志尾部打出来再抛，不吞错误。
        try:
            cmake.ctest(cli_args=["--output-on-failure", "--timeout", "1800"])
        except Exception:
            for rel in ("Testing/Temporary/LastTest.log",
                        "Testing/Temporary/LastTestsFailed.log"):
                path = os.path.join(self.build_folder, rel)
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        lines = fh.read().splitlines()
                except OSError:
                    continue
                self.output.error(
                    "ctest failed — tail of %s:\n%s"
                    % (rel, "\n".join(lines[-60:])))
            raise

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游把 cmake/relic-config.cmake 装到 <prefix>/cmake/（非
        # find_package 标准位置）。Conan 消费链走 CMakeDeps 生成的配置，
        # 上游这份 Find 风格脚本不参与其中，原样保留、不做搬运。
        #
        # 签名：默认静态包只产出 .a（非可执行产物，无需签名）。shared=True
        # 时产出的 librelic.so 实测**未签名即可被动态加载器接受**
        # （`LD_LIBRARY_PATH=<libdir> ./consumer` 正常跑通），故本包不引入
        # 签名步骤；若日后发现加载被拒，按仓库 sign 流程补即可。

    def package_info(self):
        # 上游 CMakeLists.txt:262-267：有 LABEL 时是 relic_<label>/
        # relic_s_<label>，无 LABEL（默认）时是 relic / relic_s。
        self.cpp_info.libs = ["relic"] if self.options.shared else ["relic_s"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]

        # 上游 src/CMakeLists.txt 的 LINK_LIBS()：`OPSYS STREQUAL LINUX`
        # 时给目标追加 `rt`。本包就是按 OPSYS=LINUX 构建的，静态消费者
        # 侧同样要带上（OHOS 上 librt.a 提供 clock_gettime 的兼容实现，
        # glibc 2.17+ 上 librt 是空壳，两侧都无害）。
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["rt"]

        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "relic")
        self.cpp_info.set_property("cmake_target_name", "relic::relic")
        self.cpp_info.set_property("pkg_config_name", "relic")
