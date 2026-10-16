#!/usr/bin/env python3
"""Conan test_package for userv 1.2.3 — 打包产物验证（R34，不是空壳测试）。

userv 是「setuid 客户端 + 守护进程」组合：
  * `uservd` 可以在沙箱里真正执行（参数校验在 openlog/chdir 之前，退出码 3）；
  * `userv` 客户端按设计要求以 setuid root 安装，而 Conan 包内不是 setuid root，
    client.c:248 的 setreuid(0,uid) 在 Linux 上返回 EPERM、在 OHOS 上被安全策略
    拦成 SIGSYS（真机实测 exit=159，最小 C 探针已复现）。

因此断言分两层，且都不伪装：能执行就验完整 CLI 契约；不能执行就对打包二进制做
构建身份校验（版本串/用法串/许可证串 + aarch64 ELF 头），并显式打印 SKIP 与原因。
两层都要求 <pkg>/bin 下的真实产物存在，所以 CI L1e（移走 bin/ 后测试必须失败）成立。
细节与证据见 test.sh 头部注释、test_package/MANIFEST.yml 和 ../notes.md §十。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class UservTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["userv"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        for name in ("userv", "uservd"):
            binary = os.path.join(bin_dir, name)
            if not os.path.isfile(binary):
                raise ConanException(f"packaged executable missing: {binary}")

        # OHOS 的 /system/bin/sh (mksh) 不能直接执行 ELF，统一用 profile 注入的 CONFIG_SHELL
        # （或 PATH 上的 bash/sh）包一层（与 archives/d/disktype 等 CLI 包的既有做法一致）。
        # 不写死 /data/service/hnp/bin/bash：真机实测该路径在影子 CI 设备上不存在
        # （见 ../notes.md 的真机记录），因此按 CONFIG_SHELL → bash → sh 的顺序探测。
        shell = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                 or shutil.which("sh"))
        if not shell:
            raise ConanException("no POSIX shell found (CONFIG_SHELL/bash/sh) to run test.sh")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'{shell} "{script}" "{bin_dir}"', env="conanrun")
