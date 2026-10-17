#!/usr/bin/env python3
"""Conan test_package — parlatype 4.3 消费者验证。

parlatype 是 GTK4 桌面应用：包产物是 ``bin/parlatype`` 可执行文件、
``lib/libparlatype.so.7`` 共享库（上游为插件化而安装）、公共头文件
``include/parlatype/*.h``，以及 GSettings schema / 桌面项 / 翻译数据。

OHOS 上 parlatype 二进制无法直接执行（XPM exec 要求有效的 ``.codesign``
段，与 ghex 同因），因此消费者验证由 test_parlatype.sh 做实质性静态检查：
ELF 架构 → DT_NEEDED 动态依赖链 → **库导出符号与二进制导入符号的交叉
一致性**（等价链接期验证）→ 头文件 / pkg-config / schema / msgfmt 产出。
任一项失败即非零退出。

上游测试套件不在 test_package 中重复：7 个 meson test() 用例由主配方的
build() 直接驱动（见 parlatype/4.3/conanfile.py 的 _run_upstream_tests），
其中 2 个可在无显示器环境运行的用例强制通过。
"""
import os

from conan import ConanFile


class ParlatypeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        package_folder = dep.package_folder
        binary = os.path.join(package_folder, "bin", "parlatype")

        assert package_folder, "tested package has no package_folder"
        assert os.path.isfile(binary), "parlatype binary not found: %s" % binary
        assert os.path.getsize(binary) > 0, "parlatype binary is empty: %s" % binary
        self.output.info("[test] parlatype binary: %s (%d bytes)"
                         % (binary, os.path.getsize(binary)))

        script = os.path.join(self.source_folder, "test_parlatype.sh")
        assert os.path.isfile(script), "test_parlatype.sh not found: %s" % script
        self.run('sh "%s" "%s"' % (script, package_folder), env="conanrun")

        self.output.info("[test] test_parlatype.sh PASSED")
