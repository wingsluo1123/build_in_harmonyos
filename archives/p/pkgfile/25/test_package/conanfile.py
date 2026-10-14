#!/usr/bin/env python3
"""Conan test_package — pkgfile 25.

R34：测试源文件 test_pkgfile.sh 实质执行被测包的可执行文件，
完成一次离线端到端闭环（alpm .files --(libcurl file://)--> `pkgfile -u`
--> 本地缓存 --> `pkgfile -s` / `pkgfile -l` / `-v` 断言真实输出）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class PkgfileTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _writable_tmp_root(self):
        """挑一个可写目录作为 TMPDIR 根（OHOS 沙箱 /tmp 只读）。"""
        candidates = [
            os.path.join(self.build_folder, "tmp") if self.build_folder else None,
            os.path.join(self.generators_folder, "tmp") if self.generators_folder else None,
            os.path.join(os.path.expanduser("~"), "tmp"),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
            except OSError:
                continue
            if os.access(candidate, os.W_OK):
                return candidate
        return None

    def test(self):
        if not can_run(self):
            return
        bin_dir = os.path.join(self.dependencies["pkgfile"].package_folder, "bin")
        testdata_dir = os.path.join(self.source_folder, "testdata")
        script = os.path.join(self.source_folder, "test_pkgfile.sh")

        # OHOS 的 /bin/sh 是 mksh：它在**启动时**读取 TMPDIR 并缓存，脚本内部
        # 再 export 已经太晚（here-doc 等仍会落到只读的 /tmp）。因此必须在启动
        # 被测脚本之前把 TMPDIR 注入进程环境。test_pkgfile.sh 自身也已避免
        # here-doc，这里再兜一层。
        env = Environment()
        tmp_root = self._writable_tmp_root()
        if tmp_root:
            env.define("TMPDIR", tmp_root)
            env.define("TMPPREFIX", os.path.join(tmp_root, "zsh"))

        # libcurl 依赖为 shared，运行期需要 Conan 生成的 LD_LIBRARY_PATH；
        # env="conanrun" 提供 VirtualRunEnv（不要在脚本里手拼 LD_LIBRARY_PATH，
        # 见共性问题指南 §16）。
        with env.vars(self).apply():
            self.run(f'sh "{script}" "{bin_dir}" "{testdata_dir}"', env="conanrun")
