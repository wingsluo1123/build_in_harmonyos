#!/usr/bin/env python3
"""Conan test_package — ublock 1.70.0（消费者视角验证）

被测物 = Conan 资产包：res/ublock/ubo-core（@gorhill/ubo-core 静态网络过滤
引擎 Node 库）+ res/ublock/chromium（uBlock Origin 浏览器扩展）。

L1 smoke test 真实执行 test.sh：布局/锚点校验 + 扩展 manifest 版本 + 通过
consumer/engine_flow.mjs 真实驱动被测库 API（enableWASM / StaticNetFilteringEngine
.create / useLists / matchRequest / serialize / deserialize，R34 非空壳）。

OHOS 相关：test.sh 内 5 条 [OHOS] 用例覆盖包布局、扩展 manifest 版本、
engines.node 约束、node --jitless 兼容（E400）、引擎端到端功能与 wasm 制品分发。
"""
import glob
import os
import shutil

from conan import ConanFile


class UblockTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # 同主配方：OHOS settings.yml 为 OHOS 定义 version 子设置且无默认值，
        # 未声明 os.version 时 test_package 自身 package_id 校验会报
        # "Invalid: 'settings.os.version' value not defined"；rm_safe 移除之。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _find_node():
        """定位一个 JIT/WebAssembly 可用的 Node.js（ublock 引擎强依赖 wasm）。

        OHOS 上 /data/service/hnp/bin/node 可能是不可 lstat 的符号链接，故直接枚举
        node.org/<ver>/bin/node 真实路径；同时接受 PATH 与 OpenDesk 解释器目录。
        """
        cands = [shutil.which("node")]
        cands += sorted(glob.glob("/data/service/hnp/node.org/*/bin/node"),
                        reverse=True)
        cands += ["/data/service/hnp/bin/node",
                  os.path.expanduser("~/.opendesk/interpreters/cmd-pkgs/bin/node")]
        for cand in cands:
            if not cand:
                continue
            real = os.path.realpath(cand)
            if os.path.isfile(real) and os.access(real, os.X_OK):
                return real
        return None

    def test(self):
        pkg_folder = self.dependencies["ublock"].package_folder

        # 真实执行测试脚本（含 [OHOS] 用例与引擎端到端消费者用例）。
        # 不套 conanrun env 文件、显式给出干净 PATH：Node.js 是与 C/C++ 无关的
        # 自包含运行时，继承 conan 的 C/C++ 环境会让 node 异常终止（参照
        # archives/r/roblox-ts 的实测结论）。
        shell = (shutil.which("bash") or shutil.which("sh")
                 or "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        node = self._find_node()
        path = "/data/service/hnp/bin:/usr/bin:/bin"
        env_node = ""
        if node:
            path = os.path.dirname(node) + ":" + path
            env_node = f'UBO_NODE="{node}" '
            self.output.info(f"  test node: {node}")
        self.run(
            f'PATH="{path}" {env_node}"{shell}" "{script}" "{pkg_folder}"',
            env=None,
        )

        # python 侧兜底存在性检查
        for rel in ("res/ublock/ubo-core/index.js",
                    "res/ublock/ubo-core/package.json",
                    "res/ublock/ubo-core/build/publicsuffixlist.json",
                    "res/ublock/chromium/manifest.json",
                    "licenses/LICENSE.txt"):
            p = os.path.join(pkg_folder, rel)
            if not os.path.isfile(p) or os.path.getsize(p) == 0:
                raise AssertionError(f"Missing/empty packaged file: {p}")
            self.output.info(f"  [ok] {rel}")
