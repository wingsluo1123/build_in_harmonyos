#!/usr/bin/env python3
"""test_package — fdm 2.2 消费者验证（含端到端 fetch → deliver）。

R34：必须真实调用被测包。fdm 是纯命令行工具（无库、无头文件），消费者验证 = 在
conanrun 环境下真实执行安装出来的 bin/fdm：

  build()  编译平台垫片 libfdmtestpasswd.so（见 test_package/fdm-test-passwd.c
           头注释）：OHOS /etc/passwd 只有系统账号，当前 uid 无条目 ⇒ fdm 的
           getpwuid(getuid()) 必返 NULL、在配置解析之前就 `unknown user` + exit(1)；
           垫片只补这一条缺失，其余一行代码都不拦截。垫片只用于测试，不进交付产物。
  test()   跑 test_package/test.sh 四组断言：
             1. 随包二进制存在且可执行；
             2. `fdm -h` 真实执行，断言上游 usage 文本（fetch|poll|cache）与退出码 1；
             3. **端到端核心流程**：本地 maildir 源 → `fdm fetch` 真实抓取 → 规则匹配
                → 投递到 mbox 目标；断言投递内容（From/Subject/正文 sentinel/fdm
                生成的 Received 痕迹）与源 maildir 已被取空；
             4. 反例对照：同一规则集下主题不匹配的邮件不得投递到任何目标，
                也不得在磁盘上留下正文副本。
           断言计数由脚本自身打印（`ASSERTIONS: N passed, 0 failed`）。

平台边界（见 notes.md 五/六）：① 交互/构建 uid 不在 /etc/passwd（垫片补齐）；
② HMDFS 拒硬链接，而 fdm 的 safemove() 用 link() ⇒ 投递侧用 mbox 动作
（maildir 动作会在 rename/link 处 EPERM）。两处都是平台事实，不是配方问题。
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.gnu import AutotoolsToolchain


class FdmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        """编译运行期垫片（仅测试用）。

        用与主配方同一套 conan 工具链（AutotoolsToolchain ⇒ 取 profile 的
        tools.build:compiler_executables，即 OHOS clang）。产物落在 build_folder，
        不写入 package_folder，不进交付产物。
        """
        if not can_run(self):
            self.output.info("跳过垫片编译：当前环境无法执行目标平台二进制")
            return

        src = os.path.join(self.source_folder, "fdm-test-passwd.c")
        shim = self._shim_path
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        with env.vars(self).apply():
            self.run(f'${{CC:-clang}} ${{CFLAGS:-}} -shared -fPIC -O2 -Wall '
                     f'-o "{shim}" "{src}"')
        assert os.path.isfile(shim), f"垫片未编译出: {shim}"

    @property
    def _shim_path(self):
        return os.path.join(self.build_folder, "libfdmtestpasswd.so")

    def test(self):
        package_folder = self.dependencies["fdm"].package_folder
        fdm = os.path.join(package_folder, "bin", "fdm")
        assert os.path.isfile(fdm), f"fdm 未随包安装: {fdm}"
        assert os.access(fdm, os.X_OK), f"fdm 不可执行: {fdm}"

        if not can_run(self):
            self.output.info("跳过运行期验证：当前环境无法执行目标平台二进制")
            return

        shim = self._shim_path
        assert os.path.isfile(shim), f"平台垫片缺失（build() 未产出）: {shim}"

        work = os.path.join(self.build_folder, "fdm-e2e")

        # OHOS /system/bin/sh 无法直接 exec ELF，用 bash 包装（同 SKILL 模板口径）
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f'FDM_BIN="{fdm}" FDM_TEST_SHIM="{shim}" FDM_TEST_WORK="{work}" '
                 f'"{bash}" "{test_sh}"', env="conanrun")
        # 仅在成功时清理：失败时保留 $WORK 供定位（成功路径不留制品在配方目录里）
        shutil.rmtree(work, ignore_errors=True)
