#!/usr/bin/env python3
"""Conan test_package for jalv/1.10.0 — 真实消费者用例.

jalv 是 LV2 插件宿主：它的“消费者契约”不是链接某个库，而是**真的把第三方
插件加载起来**。因此这里不只跑 `-V`，还用 mda-lv2 的真实插件 bundle
（.so + TTL）驱动 jalv 的发现/加载/端口初始化链路，覆盖
lilv + lv2 + sord + sratom + serd + zix + suil 全栈动态链接。

没有音频服务器时的期望行为（OHOS CI 即此环境）：
  - 插件被成功解析（输出 `Plugin: <uri>`）
  - 连接音频后端失败时**优雅退出 rc=1**，打印
    `Failed to connect to audio system`
  - 绝不允许 SIGSEGV（rc=139）—— 这正是 patches/ 里 NULL 守卫补丁修的
    上游缺陷，本测试把它作为回归守卫（开启 SKILL/补丁前此用例 rc=139）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import load


class JalvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 真实被宿主加载的插件（含 .so 与 TTL，不是空壳断言）
        self.requires("mda-lv2/1.2.12")

    def test(self):
        if not can_run(self):
            self.output.info("skipped: cannot run on this build machine")
            return

        log_dir = self.build_folder

        # 真实被宿主加载的插件 bundle 路径（.so + TTL，不是空壳断言）
        lv2_dir = os.path.join(
            self.dependencies["mda-lv2"].package_folder, "lib", "lv2")
        assert os.path.isdir(lv2_dir), f"mda-lv2 bundle missing: {lv2_dir}"

        # 消费者契约全部断言在 test_app.sh（真实执行型测试源，L0c/R34）：
        # 版本串、usage 宿主契约参数、插件发现/加载、无音频服务优雅失败
        # （rc=1）而非 SIGSEGV（rc=139，NULL 守卫补丁的回归守卫）、
        # 有音频服务时 20s guard timeout（rc=124）视为通过。
        test_app = os.path.join(os.path.dirname(__file__), "test_app.sh")
        rc = self.run(
            f'sh "{test_app}" "{lv2_dir}" "{log_dir}/jalv_test" '
            f'> {log_dir}/test_app.out 2>&1',
            env="conanrun",
            ignore_errors=True)
        out = load(self, os.path.join(log_dir, "test_app.out"))
        assert rc == 0, f"consumer test failed (rc={rc}):\n{out}"
        for line in out.strip().splitlines():
            self.output.info(line)
