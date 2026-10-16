#!/usr/bin/env python3
"""Conan test_package — xhk 1.2 消费者测试

xhk 是可执行程序（非库），因此验证方式为真实执行打包的 bin/xhk（R34：
二进制即被测 API）。两个脚本各司其职：

1. `test_xhk.sh`（确定性断言面）：`-v` / `-h` / `-z` 三条 CLI 路径 + ELF 平台属性
   （AArch64 / OHOS musl 解释器 / NEEDED 三个 X 库）。
2. `test_xhk_consumer.sh`（鸿蒙消费者端到端用例，rule12）：真实执行打包的 bin/xhk，
   在一台真实运行的 X server 上跑通 xhk 的核心业务工作流——半键盘镜像状态机
   （ProcessKeycode 的 Start/Pressed/Modified 三态 + mirror_key 映射）经 XTest 真
   注入 X server，并对业务输出断言（`Exiting Test Loop with 0 errors`、无 keycode
   比对失败、独立 X 客户端旁路观测到注入的按键）。环境无 X server 时该用例显式
   SKIP（绝不把没跑记成通过），不阻塞构建；OHOS 无 X server 属平台能力限制
   （规则 7），xhk 运行期功能仍归真机验证。
"""
import os
import shutil

from conan import ConanFile


class XhkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _shell(self):
        """承载测试脚本的 shell：优先 CONFIG_SHELL / OHOS hnp bash，
        否则退回 PATH 上的 bash（本地 WSL 无 /data/service/hnp 时）。
        OHOS: /system/bin/sh（mksh）执行 ELF 不可靠，故不用 sh。"""
        candidates = [
            os.environ.get("CONFIG_SHELL", ""),
            "/data/service/hnp/bin/bash",
            shutil.which("bash") or "",
            "/bin/bash",
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        return "sh"

    def test(self):
        pkg = self.dependencies["xhk"].package_folder
        binary = os.path.join(pkg, "bin", "xhk")
        if not os.path.isfile(binary):
            raise Exception(f"xhk binary missing in package: {binary}")
        self.output.info(f"xhk binary: {binary}")
        shell = self._shell()
        self.output.info(f"test shell: {shell}")
        # 1) 确定性 CLI + ELF 平台属性断言
        self.run(f"{shell} test_xhk.sh", env="conanrun")
        # 2) 鸿蒙消费者端到端用例（半键盘镜像工作流，需真实 X server；无则显式 SKIP）
        self.run(f"{shell} test_xhk_consumer.sh", env="conanrun")
        self.output.info("xhk test_package PASS")
