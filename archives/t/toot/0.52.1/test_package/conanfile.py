#!/usr/bin/env python3
"""test_package for toot 0.52.1 — 消费者视角验证（R34）。

被测物是**本配方 `conan create` 产出的 toot 包**，不是源码树：

1. 先断言安装布局：``bin/toot`` 存在、``toot/`` 平铺在包根、
   ``toot-<版本>.dist-info`` 存在（toot 的版本由 setuptools_scm 动态生成，
   dist-info 的版本号就是适配正确性的直接证据）；
2. 再调 ``self.run`` 执行 ``test_toot.py`` —— 该脚本直接 import 包内模块，
   并用子进程运行 ``bin/toot``，内含鸿蒙特有断言（见其 docstring）。

依赖解析走 ``conanrun``（VirtualRunEnv）：``PYTHONPATH`` 由本包
``package_info()`` 与各依赖的 ``runenv_info`` 共同提供。这样验证的是
「用户 ``conan install`` 完能不能用」，而不是「源码树里能不能跑」。

L0d 口径：``test()`` 必须调用 ``self.run`` 执行真实测试程序。
"""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class TootTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        version = str(dep.ref.version)

        exe = os.path.join(pkg, "bin", "toot")
        if not os.path.isfile(exe):
            raise ConanException(f"bin/toot missing from package: {exe}")
        if not os.path.isdir(os.path.join(pkg, "toot")):
            raise ConanException(
                f"toot package dir missing — expected the flat `pip --target` "
                f"layout with toot/ at the package root: {pkg}")

        dist_info = sorted(
            d for d in os.listdir(pkg)
            if d.startswith(f"toot-{version}") and d.endswith(".dist-info"))
        if not dist_info:
            raise ConanException(
                f"toot-{version}.dist-info missing from {pkg} — found: "
                f"{sorted(d for d in os.listdir(pkg) if d.endswith('.dist-info'))}")

        script = os.path.join(os.path.dirname(__file__), "test_toot.py")
        if not os.path.isfile(script):
            raise ConanException(f"test_toot.py missing: {script}")

        self.output.info(f"toot {version} installed at {pkg}")
        self.run(f'"{sys.executable}" "{script}" "{pkg}" "{version}"',
                 env="conanrun")
