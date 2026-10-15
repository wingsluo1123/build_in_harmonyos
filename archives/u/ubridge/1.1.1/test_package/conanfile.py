#!/usr/bin/env python3
"""test_package for ubridge — 消费者视角的真实验证（R34）。

不跑空壳断言：找到已安装的 ubridge 可执行文件，先核对它是 OHOS/aarch64
ELF，再真实启动它并用 GNS3 客户端所用的 TCP 控制协议驱动，校验应答码与
模块注册情况。具体断言与证据见同目录 test_consumer.py 顶部注释。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class UbridgeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        python = shutil.which("python3") or shutil.which("python")
        if python is None:
            raise ConanException("test_package 需要 python3 来驱动 ubridge 控制协议")
        self.output.info("使用解释器: %s" % python)
        self.run('"%s" "%s"' % (python, os.path.join(self.source_folder, "test_consumer.py")),
                 env="conanrun")
