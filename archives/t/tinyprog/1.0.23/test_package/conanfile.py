#!/usr/bin/env python3
"""test_package for tinyprog 1.0.23 — 消费者视角验证（R34）。

被测物是**本配方 `conan create` 产出的 tinyprog 包**，不是源码树：

1. 先断言安装布局：``bin/tinyprog`` 存在、``tinyprog/`` 平铺在包根、
   ``tinyprog-<版本>.dist-info`` 存在、``licenses/`` 随包分发；
2. 再调 ``self.run`` 执行 ``test_tinyprog.py`` —— 该脚本从包里 import 模块、
   用子进程跑 ``bin/tinyprog``、并通过脚本化的内存传输层驱动真实的 SPI 协议
   实现，内含鸿蒙特有断言（见其 docstring 的覆盖表）。

依赖解析走 ``conanrun``（VirtualRunEnv）：``PYTHONPATH`` 由本包
``package_info()`` 与依赖包（``pyserial``/``six``）的 ``runenv_info`` 共同提供。
这样验证的是「用户 ``conan install`` 完能不能用」，而不是「源码树里能不能跑」。
``test_tinyprog.py`` 的 test_05 正是据此断言 pyserial/six 来自 conan 依赖包、
而 intelhex/jsonmerge/tqdm/pyusb/packaging 随本包平铺分发。

L0d/PF3 口径：``test()`` 必须调用 ``self.run`` 执行真实测试程序。
"""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class TinyprogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        version = str(dep.ref.version)

        if not pkg:
            raise ConanException(f"{self.tested_reference_str} has no package folder")

        exe = os.path.join(pkg, "bin", "tinyprog")
        if not os.path.isfile(exe):
            raise ConanException(f"bin/tinyprog missing from package: {exe}")
        if not os.path.isdir(os.path.join(pkg, "tinyprog")):
            raise ConanException(
                f"tinyprog package dir missing — expected the flat `pip --target` "
                f"layout with tinyprog/ at the package root: {pkg}")
        if not os.path.isdir(os.path.join(pkg, "licenses")):
            raise ConanException(f"licenses/ missing from package: {pkg}")

        dist_info = sorted(
            d for d in os.listdir(pkg)
            if d.startswith(f"tinyprog-{version}") and d.endswith(".dist-info"))
        if not dist_info:
            raise ConanException(
                f"tinyprog-{version}.dist-info missing from {pkg} — found: "
                f"{sorted(d for d in os.listdir(pkg) if d.endswith('.dist-info'))}")

        script = os.path.join(os.path.dirname(__file__), "test_tinyprog.py")
        if not os.path.isfile(script):
            raise ConanException(f"test_tinyprog.py missing: {script}")

        self.output.info(f"tinyprog {version} installed at {pkg}")
        self.run(f'"{sys.executable}" "{script}" "{pkg}" "{version}"',
                 env="conanrun")
