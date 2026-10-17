#!/usr/bin/env python3
"""Conan test_package for xdg-utils 1.2.1 — script suite smoke test.

Runs the installed `xdg-mime --version` (real upstream script, dispatcher in
xdg-utils-common.in prints "@NAME@ 1.2.1" and exits 0). This is a real
executable invocation (R34): no stub, no print("ok").
"""
import os
import platform

from conan import ConanFile


class XdgUtilsTestConan(ConanFile):
    settings = "os", "arch", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["xdg-utils"].cpp_info.bindirs[0]
        script = os.path.join(os.path.dirname(__file__), "test_xdg.sh")
        assert os.path.isfile(script), f"test_xdg.sh missing: {script}"
        # 真实脚本执行（R34）：断言逻辑在 test_xdg.sh 内（无 grep 管道依赖）。
        # HMDFS 新建脚本无 exec 权（hishell_hap MAC），必须经 /bin/sh 解释执行
        self.run(f'/bin/sh "{script}" "{bindir}"')
