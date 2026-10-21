#!/usr/bin/env python3
"""Conan test_package -- swift-toolchain-ohos 6.0.3.

四层验证（断言总数见同目录 MANIFEST.yml 的 assertion_count）：
  S 层（静态，5 项）：包根 wrapper 存在 / 交付编译器存在且可执行 /
                      ring 平面本体与模块存在 / sysroot 与 resource-dir 存在 /
                      Swift 运行时闭包与 libc++_shared.so 存在
  D 层（破坏性反向，2 项）：**把 instrument/bin/swiftc 的执行位摘掉后，S2 必须失败**
                      —— 证明 S2 不是恒真；随后恢复执行位。
                      （这一层是 L1e 口径：验证"编译真的需要这个文件"，而不是只看它在不在）
  E 层（运行，3 项）：`swiftc.sh --version` 真跑；版本串含 Swift 版本；
                      真编译并运行一个 Swift 程序（真链接 ring 平面）
  R 层（运行时自证，1 项）：编译产物在**不带 LD_LIBRARY_PATH** 时能跑
                      —— 这正是环 RUNPATH 契约的可执行形式

★ 为什么用 .sh 而不是 .swift：`test_package` 测试源白名单现为
  .c/.cpp/.cc/.cxx/.sh/.py（preflight.py:431），暂不含 .swift。
  故本脚本是 .sh 外壳，**内部真调 swiftc 编译并运行 Swift 程序**（PENDING-P2-5/P2-6）。
"""
import os
import shlex

from conan import ConanFile


class SwiftToolchainOhosTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/system/bin/sh")
        script = os.path.join(self.source_folder, "test_swift_toolchain.sh")
        # 工具链的 PATH/T2_* 由 tool_requires 注入构建环境；
        # 路径可能含空格/括号，必须 shlex.quote（先例 rust-toolchain 同口径）。
        env = dict(os.environ)
        env.setdefault("T2_ENV_QUIET", "1")
        self.run(f"{shlex.quote(bash)} {shlex.quote(script)}", env="conanbuild")
