#!/usr/bin/env python3
"""Conan test_package for overtls 0.3.12 — 消费者侧端到端测试。

跑的是**已打包交付物** `bin/overtls-bin`，不是源码树：
  A CLI 契约 → B 配置校验负向 → C 服务端/客户端真实监听 →
  D SOCKS5 → overtls WebSocket 隧道 → 服务端 TCP 转发 → 回显目标 的字节往返

上游 `cargo test` 在配方 `build()` 内用 `source()` 已下载校验的源码离线执行，
标记从 conan create 日志采集；本 test_package 只做消费者测试，两者统计独立
（hf-mount / rainfrog 先例）。

**不放 can_run 守卫**：本平台 host 与 build 同为 OHOS，放守卫只会增加一条
「静默跳过 → 0 断言 → rule12 假绿」的路径；不可运行时应当响亮失败。
"""
import os

from conan import ConanFile


class OvertlsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_overtls.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 必须用 self.run(...)，不能用 subprocess.run(...)：
        # CI 门禁 L0d 对 test_package/conanfile.py 做静态检查——
        #   grep -q "self\.run" 否则判 "stub_test_method" 并拦截整个构建。
        # self.run 同时会应用 conanrun 运行期环境（generators = VirtualRunEnv），
        # 非零返回码直接抛错。
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_overtls.sh")
        self.run(f'sh "{script}" "{pkg_folder}"', env="conanrun")
