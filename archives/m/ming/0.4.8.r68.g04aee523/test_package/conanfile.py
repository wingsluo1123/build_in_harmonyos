#!/usr/bin/env python3
"""Conan test_package for ming (libming) — 消费者视角功能验证（R34）。

真实链接并调用 libming 的 <ming.h> 公开 API 生成一个 SWF，再用被测包安装的
命令行工具 `listswf` 回读该 SWF，从两个方向证明产物可用：
  - 库方向：编译 + 链接 + 运行 test_ming.c（生成并校验 .swf 文件头/尺寸）
  - 工具方向：执行安装到 bin/ 的 listswf 解析同一份 .swf
L1e 破坏性反向验证（mv 产物目录后重跑）会因找不到库/头文件而失败，
故本测试无法被空壳化。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class MingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("目标平台二进制不可运行，跳过功能测试")
            return

        dep = self.dependencies["ming"]

        # 汇总依赖（含传递依赖）的 include/lib 目录——静态链接时需要
        incs, libdirs = [], []
        for _ref, d in self.dependencies.items():
            incs.extend(d.cpp_info.includedirs)
            libdirs.extend(d.cpp_info.libdirs)

        # R33：编译器从 Conan conf 取，禁止裸用 ${CC}/${CFLAGS}
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        src = os.path.join(self.source_folder, "test_ming.c")
        exe = os.path.join(self.build_folder, "test_ming")
        swf = os.path.join(self.build_folder, "test_package.swf")

        inc_flags = " ".join(f"-I{i}" for i in incs)
        lib_flags = " ".join(f"-L{l}" for l in libdirs)
        # 运行期搜索路径写进 ELF（RUNPATH）：与主配方同一结论——本平台上
        # LD_LIBRARY_PATH 在子进程链路不可靠，RUNPATH 由 loader 直接读 ELF。
        # 另：-I/-L 路径不能带引号（引号会被当成路径字面量的一部分）。
        rpath_flags = " ".join(f"-Wl,-rpath,{l}" for l in libdirs)

        # 库方向：编译并运行真实 API 测试
        self.run(
            f'{cc} -o "{exe}" "{src}" {inc_flags} {lib_flags} {rpath_flags} -lming',
            env="conanbuild",
        )
        self.run(f'"{exe}" "{swf}"', env="conanrun")

        if not os.path.isfile(swf):
            raise ConanException(f"test_ming 未生成 {swf}")

        # 工具方向：用被测包安装的命令行工具复核产物（覆盖 bin/ 交付面）
        listswf = os.path.join(dep.package_folder, "bin", "listswf")
        if not os.path.isfile(listswf):
            raise ConanException(f"listswf 未安装到 {listswf}（bin/ 交付面缺失）")
        self.output.info(f"使用被测包命令行工具回读 SWF: {listswf}")
        # 安装后的 listswf 需要包内 libming.so.1：其 RUNPATH 由构建期的
        # --libdir=//lib 决定（构建时包目录还不存在），env="conanrun" 在本平台
        # 未能提供该目录（实测 "Error loading shared library libming.so.1"），
        # 故在命令上显式前置包 lib 目录。
        pkg_lib = os.path.join(dep.package_folder, "lib")
        run_prefix = ('LD_LIBRARY_PATH="' + pkg_lib
                      + '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ')
        self.run(run_prefix + f'"{listswf}" "{swf}"', env="conanrun")

        self.output.info("ming test_package: PASS（库 API 生成 SWF + 命令行工具回读）")

        # ── 鸿蒙特有端到端消费者用例 ──
        # 只用被测包【已安装】的产物，串起完整 SWF 工具链并逐环节断言：
        #   makeswf  ActionScript(.as) → SWF（走 clang -E 预处理，OHOS 无 cpp）
        #   listswf  SWF → 结构文本（含压缩 SWF 的解压路径，覆盖 /tmp 只读缺陷）
        #   swftocxx SWF → C++ 源码
        # 同时覆盖两项平台特性：工作目录必须落在 TMPDIR（/tmp 只读）、
        # 运行期依赖靠 ELF RUNPATH 定位（本平台 LD_LIBRARY_PATH 不可靠）。
        e2e = os.path.join(self.source_folder, "test_ohos_e2e.sh")
        if not os.path.isfile(e2e):
            raise ConanException(f"鸿蒙端到端用例脚本缺失: {e2e}")
        self.output.info(f"运行鸿蒙端到端消费者用例: {e2e}")
        self.run(f'sh "{e2e}" "{dep.package_folder}"', env="conanrun")
