import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class IspcTestConan(ConanFile):
    """test_package — 真跑被测 ispc：编译真实 SPMD 内核 → 用设备 clang++ 链接 → 执行并校验数值。

    R34 反空壳：不打印字符串了事，必须调用被测产物产出的符号并断言结果。
    """
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        # 把测试产物与 conan 生成的 env 脚本限制在 test_package/build/ 子目录内。
        # 不加 layout() 时 Conan 2 的 test_package build_folder == test_package 目录本身，
        # 会在源码目录里留下 test.o / ispc_probe.h / host_probe.s / ispc_probe 等未跟踪文件
        # （设备轮实测：`git status` 出现 `?? …/test_package/{host_probe.s,ispc_probe.h}`）。
        # `build/` 已被仓库 .gitignore 覆盖。
        self.folders.build = "build"
        self.folders.generators = "build"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_cxx(self):
        """确定性选择链接用 C++ 编译器（CI 与设备两侧同口径、可复现）。

        优先级（全部要求**绝对路径且存在**，否则继续）：
        1. conan 工具链注入的 `tools.build:compiler_executables["cpp"]`
           （profile `ohos-aarch64` 给出 `/data/service/hnp/bin/clang++`；conan 原生口径，
           两侧用同一 profile ⇒ 同一编译器）；
        2. 环境变量 `CXX`（仅当为已存在的绝对路径时采纳，作为显式逃生口）；
        3. 设备工具链绝对路径 `/data/service/hnp/bin/clang++`（OHOS SDK clang，
           自带默认 target/sysroot，`conanfile.build()` 的 CMAKE_CXX_COMPILER 同款）。

        **绝不按裸名走 PATH**（本轮 CI 红根因，build#91471）：CI worker 上环境变量
        `CXX` 是裸 `clang++`，而 `test()` 里 `self.run(..., env="conanrun")` 会把依赖包
        `llvm-project` 的 `bin/` **前置**进 PATH（conan `runenv_from_cpp_info`:
        `_prepend_path("PATH", cpp_info.bindirs)`），其中的 clang++ 是 LLVM 20 工具链、
        无 OHOS sysroot、无 libc++ 头文件搜索路径 ⇒ 裸名必被它遮蔽，报
        `fatal error: 'cmath' file not found`。本地设备能过只是因为 CXX 未设置时旧代码
        恰好落到绝对路径默认值——确定性不能依赖环境运气。
        """
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        candidates = [
            compilers.get("cpp"),
            os.environ.get("CXX"),
            "/data/service/hnp/bin/clang++",
        ]
        for cand in candidates:
            if cand and os.path.isabs(cand) and os.path.exists(cand):
                return cand
        raise ConanException(
            "no usable absolute C++ compiler found: tools.build:compiler_executables['cpp']={!r}, "
            "CXX={!r}, /data/service/hnp/bin/clang++ missing. Bare-name compilers are deliberately "
            "not resolved via PATH: env=\"conanrun\" prepends the llvm-project dependency bin/ "
            "(sysroot-less LLVM clang++) which shadows the device toolchain — CI build#91471 "
            "failed with \"fatal error: 'cmath' file not found\".".format(
                compilers.get("cpp"), os.environ.get("CXX")))

    def test(self):
        pkg = self.dependencies["ispc"].package_folder
        ispc = os.path.join(pkg, "bin", "ispc")
        if not os.path.exists(ispc):
            raise ConanException("ispc binary missing in package: {}".format(ispc))

        src = self.source_folder
        work = self.build_folder
        kernel = os.path.join(src, "test.ispc")
        driver = os.path.join(src, "test.cpp")
        obj = os.path.join(work, "test.o")
        header = os.path.join(work, "ispc_probe.h")
        exe = os.path.join(work, "ispc_probe")
        cxx = self._resolve_cxx()
        q = shlex.quote

        # 1) 产物自报版本（L2 等价 smoke）
        self.run("{} --version".format(q(ispc)), env="conanrun")

        # 2) 真实 codegen：neon-i32x4（本平台 aarch64）+ 生成 C 头
        self.run(
            " ".join([
                q(ispc), q(kernel), "--arch=aarch64", "--target=neon-i32x4", "--pic",
                "-o", q(obj), "-h", q(header),
            ]),
            env="conanrun",
        )
        for f in (obj, header):
            if not os.path.exists(f):
                raise ConanException("ispc did not produce {}".format(f))

        # 3) 宿主目标可用性（--target=host 在 aarch64 上应可编译）
        host_asm = os.path.join(work, "host_probe.s")
        self.run(
            " ".join([q(ispc), q(kernel), "--target=host", "--emit-asm", "-o", q(host_asm)]),
            env="conanrun",
        )
        if not os.path.exists(host_asm) or os.path.getsize(host_asm) == 0:
            raise ConanException("ispc --target=host produced no asm")

        # 4) 链接并执行：真实消费 codegen 产物
        self.run(
            " ".join([
                q(cxx), q(driver), q(obj), "-I", q(work), "-o", q(exe), "-lm",
            ]),
            env="conanrun",
        )
        self.run(q(exe), env="conanrun")
