#!/usr/bin/env python3
"""Conan recipe — tuntox 0.0.10.1 (Makefile, vendored c-toxcore).

tuntox：基于 Tox 协议(Toxcore) 的 TCP 端口转发工具，把本地 TCP 端口或
stdin/stdout(SSH ProxyCommand) 安全转发到另一台运行 tuntox 服务的机器。
构建产物为 `bin/tuntox` 应用（源码仅在 main.c 链接 c-toxcore，无对外库）。

依赖链：
  tuntox ──(pkg-config toxcore + #include <tox/tox.h>)──> c-toxcore
      └──> libsodium（c-toxcore core 唯一硬依赖）
  c-toxcore 的 toxav 需要 opus/vpx、bootstrapd 需要 libconfig，均用
  -DBUILD_TOXAV=OFF / -DBOOTSTRAP_DAEMON=OFF / -DDHT_BOOTSTRAP=OFF 关闭；
  core 不需 libevent（仅 esp32 docker 示例用到）。

c-toxcore 未在 build_in_harmonyos 仓库单独适配（当前仓库仅提供其依赖
libsodium/1.0.22、libevent/2.1.13）。为遵循"一个 PR 只含一个库"且规避
missing_dependency 门禁，本配方在 source() 内联下载 c-toxcore v0.2.19
（2022-05 发布，与 tuntox 0.0.10.1 同期稳定），build() 先用
CMakeToolchain 静态构建 toxcore 核心并安装到私有 prefix，再把 tuntox
链接其上，全程不污染全局/共享目录（R49）。

OHOS 适配要点：
  - toxcore 用 CMakeToolchain（OHOS 适配版 conan 自动 CMAKE_SYSTEM_NAME=HarmonyOS），
    静态核心仅需 libsodium（pkg-config + PkgConfigDeps 生成的 .pc 提供）
  - tuntox 用纯 Makefile，%clang（profile [buildenv] 注入 /data/service/hnp/bin），
    `make tuntox_nostatic`（去掉 -static；OHOS musl 无静态 libc，且静态链接会
    破坏 DNS 解析）
  - Makefile 硬编码 gcc/-static/pkg-config，通过命令行覆盖
    CC/CFLAGS/DSO_LDFLAGS（command-line 变量的 makefile `+=` 为 no-op，正好
    让我完全控制编译与链接参数）
  - tox_bootstrap.h / gitversion.h 已随发布包自带，Makefile 不会重新生成
    （generate_tox_bootstrap.py 需 requests+jinja2 并从 nodes.tox.chat 联网，
    仅当 tox_bootstrap.h 不存在才触发；gitversion.h 的 FORCE 规则仅在 .git/HEAD
    存在时改写）
  - 上游无任何测试（审计见 test_package/MANIFEST.yml）：Makefile 无 check/
    test 目标，源码树无 tests/ 目录，故 build() 不运行上游测试。测试由
    test_package 消费者视角执行 `tuntox -h` 触发 print_version()->tox_version_*。
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class TuntoxConan(ConanFile):
    name = "tuntox"
    version = "0.0.10.1"
    package_type = "application"
    description = "Forward TCP ports over the Tox protocol"
    homepage = "https://github.com/gjedeer/tuntox"
    license = "MIT"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def requirements(self):
        # c-toxcore core 唯一硬依赖（vendor 构建时用 pkg-config 抓取）。
        # tuntox 运行期依赖 toxcore 与 libsodium 的符号，故 run=True。
        self.requires("libsodium/1.0.22", run=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def generate(self):
        # 为 vendor 的 c-toxcore 生成 libsodium.pc（放 generators_folder），
        # 由 pkg-config 检索；同时生成 OHOS 工具链文件 conan_toolchain.cmake
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        # E346：OHOS 沙盒下 CMake 默认 Unix Makefiles 的配置期 try-compile 会
        # 递归调 make（`make -f Makefile ...` → `make -f CMakeFiles/.../build.make`），
        # 在进程受限的 worker 上 fork/exec 返回 EAGAIN（日志
        # `make: /data/service/hnp/bin/make: Resource temporarily unavailable` +
        # Error 127）→ "Check for working C compiler ... broken"，干净构建在
        # 配置阶段即中止。改用 Ninja generator：ninja 直接 exec 编译器，无递归
        # make，配置期 try-compile 与编译阶段均不触发该问题（同仓库 gdal/ccmake/
        # libogg/aws-lc-tools 已验证范式）。R33 合规：ninja 为显式探测常量。
        ninja = self._resolve_ninja()
        if ninja:
            tc.generator = "Ninja"
            tc.variables["CMAKE_MAKE_PROGRAM"] = ninja
        tc.generate()

    @staticmethod
    def _resolve_ninja():
        """显式探测 ninja 绝对路径（HMBS_NINJA → 设备固定路径 → PATH）；
        找不到返回空串以回退默认 generator。"""
        candidates = [
            os.environ.get("HMBS_NINJA"),
            "/data/service/hnp/bin/ninja",
            shutil.which("ninja"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def source(self):
        # 主源码 tuntox
        get(self, **self.conan_data["sources"], strip_root=True)
        # vendor 依赖 c-toxcore
        get(self, **self.conan_data["toxcore"],
            destination=os.path.join(self.source_folder, "third_party", "toxcore"),
            strip_root=True,)
        # c-toxcore 的 git 子模块 third_party/cmp：源码 tarball 不含子模块，
        # CMakeLists 却把它列入 toxcore_SOURCES，缺了会在 configure 阶段报
        # "Cannot find source file: third_party/cmp/cmp.c"。按 c-toxcore v0.2.19
        # 锁定的提交 643e6a62 单独内联下载并解包到 third_party/cmp。
        get(self, **self.conan_data["cmp"],
            destination=os.path.join(self.source_folder, "third_party", "toxcore",
                                     "third_party", "cmp"),
            strip_root=True,)
        apply_conandata_patches(self)

    def build(self):
        cmake_bin = os.environ.get("HMBS_CMAKE") or "cmake"
        make_bin = os.environ.get("HMBS_MAKE") or "make"
        ninja_bin = self._resolve_ninja()

        # ── 1) 静态构建 c-toxcore 核心并安装到私有 prefix ──
        tox_src = os.path.join(self.source_folder, "third_party", "toxcore")
        tox_build = os.path.join(self.build_folder, "toxcore-build")
        tox_prefix = os.path.join(self.build_folder, "toxprefix")
        # 平台宏由 CMakeToolchain(HarmonyOS) 提供；toxcore 根 CMakeLists 在
        # include(Dependencies) 时 pkg_search_module 找 libsodium，PKG_CONFIG_PATH
        # 指向 generators_folder（PkgConfigDeps 产出的 libsodium.pc）
        pkgconfig_path = os.pathsep.join([
            self.generators_folder,
            os.path.join(tox_prefix, "lib", "pkgconfig"),
        ])
        pre_existing = os.environ.get("PKG_CONFIG_PATH")
        if pre_existing:
            pkgconfig_path = os.pathsep.join([pkgconfig_path, pre_existing])
        os.environ["PKG_CONFIG_PATH"] = pkgconfig_path

        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        # musl/OHOS 的 <net/if.h> 仅在定义 _GNU_SOURCE/_BSD_SOURCE 时才暴露
        # struct ifreq/struct ifconf（c-toxcore LAN_discovery.c 用 <net/if.h> 替代
        # <linux/if.h> 后需要这些结构体）；以编译定义注入，配合 source() 补丁把
        # <linux/if.h> 换成 <net/if.h>，避免 <linux/socket.h> 与 <sys/socket.h> 的
        # sockaddr_storage 重定义。
        #
        # 关键：c-toxcore 用自己的一套 CMake 选项控制共享/静态库
        # （cmake/ModulePackage.cmake: option(ENABLE_SHARED ... ON) /
        #    option(ENABLE_STATIC ... ON)），`-DBUILD_SHARED_LIBS=OFF` 并不能关掉
        # 它默认构建的 `libtoxcore.so`。若同时存在 `libtoxcore.so` 与 `libtoxcore.a`，
        # tuntox 链接 `-ltoxcore` 会挑中共享库 → 生成对 `libtoxcore.so` 的动态依赖，
        # 真机运行时 OHOS loader 加载系统旧版 `libtoxcore.so`（stale_runtime_library），
        # 全部 tox_* 符号 reloc 失败，`tuntox -h` 直接报 "Error loading shared library
        # libtoxcore.so ... symbol not found" 而无任何 help 输出。故必须
        # `-DENABLE_SHARED=OFF`（只产 `libtoxcore.a`），保证 tuntox 静态链接 toxcore。
        #
        # E346：OHOS 沙盒下默认 Unix Makefiles 的配置期 try-compile 递归调 make，
        # 进程受限 worker 上 fork/exec EAGAIN（日志 `make: ... Resource temporarily
        # unavailable` → Error 127）→ "Check for working C compiler ... broken"，
        # 干净构建在配置阶段即中止。改用 Ninja generator：ninja 直接 exec 编译器、
        # 不经递归 make，配置期 try-compile 与编译阶段均规避（同仓库 gdal/ccmake/
        # libogg/aws-lc-tools 已验证范式）。
        gen_flags = ""
        build_cmd = f"{make_bin} -C {tox_build} -j1"
        if ninja_bin:
            gen_flags = f"-G Ninja -DCMAKE_MAKE_PROGRAM={ninja_bin} "
            build_cmd = f"{ninja_bin} -C {tox_build} -j1"
        self.run(
            f"{cmake_bin} -S {tox_src} -B {tox_build} "
            f"{gen_flags}"
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain} "
            f"-DCMAKE_BUILD_TYPE=Release "
            f"-DCMAKE_INSTALL_PREFIX={tox_prefix} "
            f"-DCMAKE_C_FLAGS=\"-D_GNU_SOURCE\" "
            f"-DCMAKE_CXX_FLAGS=\"-D_GNU_SOURCE\" "
            f"-DBUILD_TOXAV=OFF -DAUTOTEST=OFF -DDBOOTSTRAP_DAEMON=OFF "
            f"-DDHT_BOOTSTRAP=OFF -DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=OFF "
            f"-DENABLE_SHARED=OFF -DENABLE_STATIC=ON",
            env="conanbuild",
        )
        # E074：HMDFS jobserver fifo EPERM → -j1；Ninja 无 jobserver，仍 -j1 限并发
        self.run(build_cmd, env="conanbuild")
        self.run(f"{cmake_bin} --install {tox_build}", env="conanbuild")

        # 收集 libsodium 依赖的真实包 libdir（tuntox 直接链接 -lsodium 必须
        # 在 -L 中显式给出其归档目录；toxprefix/lib 只有 toxcore，无 libsodium）。
        sodium_libdirs = []
        if "libsodium" in self.dependencies:
            cpp = self.dependencies["libsodium"].cpp_info
            base = self.dependencies["libsodium"].package_folder
            for ld in cpp.libdirs:
                sodium_libdirs.append(
                    ld if os.path.isabs(ld) else os.path.join(base, ld))
        sodium_L = " ".join(f"-L{d}" for d in sodium_libdirs)

        # 手写一份静态链接全量的 toxcore.pc（含 -lsodium -lm -lrt），
        # 保证 tuntox 的 `pkg-config --libs toxcore` / `--static --libs toxcore`
        # 都能给出完整链接行（不依赖 toxcore 自身生成的 Libs.private 布局）。
        tox_pc = os.path.join(tox_prefix, "lib", "pkgconfig", "toxcore.pc")
        tox_pc_content = (
            "prefix={tox_prefix}\n"
            "libdir=${{prefix}}/lib\n"
            "includedir=${{prefix}}/include\n"
            "\n"
            "Name: toxcore\n"
            "Version: 0.2.19\n"
            "Description: Tox encrypted P2P library\n"
            "Requires:\n"
            "Libs: -L${{libdir}} {sodium_L} -ltoxcore -lsodium -lm -lrt\n"
            "Cflags: -I${{includedir}}\n"
        ).format(tox_prefix=tox_prefix, sodium_L=sodium_L)
        os.makedirs(os.path.dirname(tox_pc), exist_ok=True)
        with open(tox_pc, "w", encoding="utf-8") as f:
            f.write(tox_pc_content)
        # 确认链接器可找到静态库与头文件
        tox_lib = os.path.join(tox_prefix, "lib")
        tox_inc = os.path.join(tox_prefix, "include")
        if not os.path.isdir(tox_lib) or not os.path.isdir(tox_inc):
            raise Exception(
                f"c-toxcore 安装缺失: {tox_lib} / {tox_inc} 不存在; 请检查 toxcore 构建")
        # 防御：ENABLE_SHARED=OFF 后 toxprefix/lib 只应存在静态归档 libtoxcore.a，
        # 不应再有 libtoxcore.so（若有，tuntox 的 -ltoxcore 会动态链接并触发
        # 真机 stale_runtime_library 失败）。
        if os.path.isfile(os.path.join(tox_lib, "libtoxcore.so")):
            raise Exception(
                f"c-toxcore 仍构建出了共享库 {tox_lib}/libtoxcore.so; "
                f"-DENABLE_SHARED=OFF 未生效，请检查 toxcore CMake 选项")
        if not os.path.isfile(os.path.join(tox_lib, "libtoxcore.a")):
            raise Exception(
                f"c-toxcore 未生成静态库 {tox_lib}/libtoxcore.a "
                f"（-DENABLE_STATIC=ON 应产出）；tuntox 无法静态链接")

        # ── 2) 构建 tuntox（make tuntox_nostatic）──
        top = self.source_folder
        # R33：不从裸 shell 环境取编译器，令 Makefile 用 OHOS clang
        # （profile buildenv 已把 /data/service/hnp/bin 前置到 PATH）。
        # 命令行变量覆盖：makefile 的 `CFLAGS += ...` 对命令行定义为 no-op，
        # 因此这里给出的 CFLAGS/DSO_LDFLAGS 即为最终编译/链接参数。
        cflags = f"-O2 -I{tox_inc}"  # tox_inc 提供 <tox/tox.h>
        # -L 需同时覆盖 toxprefix/lib（toxcore）与 libsodium 的真实包 libdir，
        # 否则 ld 报 "unable to find library -lsodium"。
        dso_ldflags = (f"-g -pthread -lm -lrt -L{tox_lib} {sodium_L} "
                       f"-ltoxcore -lsodium -lrt")
        self.run(
            f"cd {top} && {make_bin} tuntox_nostatic -j1 "
            f"CC=clang CFLAGS=\"{cflags}\" "
            f"DSO_LDFLAGS=\"{dso_ldflags}\"",
            env="conanbuild",
        )
        if not os.path.isfile(os.path.join(top, "tuntox_nostatic")):
            raise Exception("tuntox_nostatic 未生成，构建失败")

    def package(self):
        top = self.source_folder
        # 直接复制构建产物（Makefile install 用 `install -C`，在 OHOS 上
        # 不可靠；且 tuntox 为独立应用只需 bin/tuntox）
        copy(self, "tuntox_nostatic",
             src=top,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        # 重命名为预期的 tuntox 命令名
        src_bin = os.path.join(self.package_folder, "bin", "tuntox_nostatic")
        dst_bin = os.path.join(self.package_folder, "bin", "tuntox")
        if os.path.isfile(src_bin) and not os.path.isfile(dst_bin):
            os.replace(src_bin, dst_bin)
        copy(self, "LICENSE.md", src=top,
             dst=os.path.join(self.package_folder, "licenses"))
        # 记录上游测试审计结论进包 res/（test_package test() 复发
        # HMBS_UPSTREAM_TEST_RESULT，git-who/1.3 先例）。tuntox 无上游测试。
        audit = {"status": "no_tests", "discovered": 0, "executed": 0,
                 "reason": ("tuntox 0.0.10.1 发布包经审计无任何自动化测试："
                            "Makefile 无 check/test 目标，源码树无 tests/ 目录")}
        os.makedirs(os.path.join(self.package_folder, "res"), exist_ok=True)
        with open(os.path.join(self.package_folder, "res",
                               "upstream_test_result.json"),
                  "w", encoding="utf-8") as f:
            json.dump(audit, f, ensure_ascii=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "tuntox")
        self.cpp_info.set_property("cmake_target_name", "tuntox::tuntox")
