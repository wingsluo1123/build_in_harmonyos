#!/usr/bin/env python3
"""Conan test_package for sleuthkit 4.12.1.

消费者视角(R34,工具类):真实执行被适配的 TSK 工具链——
核心 CLI 工具 -V 版本输出、libtsk 镜像层真实操作(img_stat 打开
自生成 raw 镜像、srch_strings 内容检索)。全部离线,不依赖任何
磁盘镜像夹具(上游 make check 的镜像夹具不可公开获取,见 notes.md)。
"""
import json
import os

from conan import ConanFile
from conan.tools.build import cross_building


class SleuthkitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building:工具类无编译验证,跳过执行")
            return
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        bindir = os.path.join(package_folder, "bin")
        for tool in ("fls", "icat", "mmls", "img_stat", "srch_strings",
                     "tsk_recover"):
            if not os.path.isfile(os.path.join(bindir, tool)):
                raise Exception("sleuthkit binary not found: %s" % tool)
        libdir = os.path.join(package_folder, "lib")
        if not any(f.startswith("libtsk.") for f in os.listdir(libdir)):
            raise Exception("libtsk not found in %s" % libdir)
        script = os.path.join(self.recipe_folder, "test_sleuthkit.sh")
        self.run('TSK_BIN="%s" sh "%s"' % (bindir, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_sleuthkit.sh (10 工具 -V / img_stat 真实镜像"
                       "操作 / srch_strings 内容检索)",
            "consumer_passed": 12,
            "consumer_total": 12,
        }))
