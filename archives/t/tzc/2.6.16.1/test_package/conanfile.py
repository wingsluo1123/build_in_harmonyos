#!/usr/bin/env python3
"""test_package for tzc 2.6.16.1 —— CLI 消费者端到端用例（HarmonyOS PC）。

真实测试逻辑在 consumer_test.sh 中执行（非空壳、非 print-only、非字符串
静态断言），入口通过 self.run() 真实运行测试脚本并校验退出码：

  A. HarmonyOS 专有非断言测试（静态）
     A1 tzc 必须是 OHOS aarch64 原生 ELF 可执行文件
     A2 tzc 的 DT_NEEDED 动态依赖闭包必须含 libzephyr.so.4
     A3 com_err 必须是已定义符号 —— e2fsprogs 的 libcom_err.a 静态链入证据

  B. 端到端消费者用例（原生进程真实执行 + 上游语义校验）
     B1 `tzc -o`：本机动态加载器须完整解析并加载整个 DT_NEEDED 闭包才能进入
        main()，随后上游真实调用 libzephyr 的 ZInitialize()/ZOpenPort()，无
        HostManager 时按源码语义输出 elisp 错误并 EXIT_FAILURE(1)
     B2 `tzc --bogus`：真实走上游 getopt/usage 路径，usage() 后 bail(1)

设计约束（对照 xsct 2.3，PR #15143 build #80198 实证）：不依赖 conan 宿主
python3 做 ctypes dlopen —— HNP 安装的 python3（CI worker 宿主）运行在受限
linker namespace 中，对缓存路径共享库 dlopen 会得到 EACCES，而 exec 时按
DT_NEEDED 加载不受此限；故「闭包真实加载」由 B 节原生执行承担，结果不随
「哪个 python3 运行 conan」而变化。

全部判定基于命令退出码（self.run / 脚本内 grep），不使用 Python assert。
"""
import os

from conan import ConanFile


class TzcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["tzc"].cpp_info.bindirs[0]
        script = os.path.join(self.recipe_folder, "consumer_test.sh")
        self.output.info(f"运行消费者端到端用例: sh {script} {bindir}")
        # 通过 sh 调用，避免 HMDFS 上脚本文件的 execve 限制
        self.run(f'sh "{script}" "{bindir}"', env="conanrun")
