#!/usr/bin/env python3
"""test_package — indi-eqmod 1.0-20230126190232 (CLI 工具包)

消费者探针（rule12 鸿蒙特有测试，参照已获认可的 indi-aok / indi-shelyak
test_package 同款模式）：通过 bash 包裹 python3 执行 test_eqmod_probe.py，
对 4 个驱动逐一遍历 53 项断言——ELF64/AArch64 身份（e_machine=183）、
DT_NEEDED 链接校验（libindidriver.so.2 / libindiAlignmentDriver.so.2 闭包）、
share/indi/indi_eqmod.xml 设备/驱动名注册交叉校验 + *-sk.xml 配套骨架。
说明：驱动为常驻进程的交叉编译产物，OHOS 加载器拒绝在本宿主执行
（PROT_EXEC/mmap 受限，E537/R49，与 shelyak 同款平台限制），故探针
采用制品静态解析而非执行二进制；任一断言失败 raise AssertionError
非零退出 → conan test FAIL。
"""
import os
import sys

from conan import ConanFile


class IndiEqmodTestConan(ConanFile):
    """test_package for executable packages — runs the consumer probe."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 被测包目录：bin/ + share/indi（驱动 + XML 注册）
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        # 驱动 DT_NEEDED 闭包指向 libindi 包内的 INDI 核心库
        indi = self.dependencies["libindi"]
        indi_libdir = os.path.join(indi.package_folder, indi.cpp_info.libdirs[0])

        # 定位探针脚本（source_folder 优先，回退 recipe_folder）
        test_dir = self.source_folder
        if not os.path.exists(os.path.join(test_dir, "test_eqmod_probe.py")):
            test_dir = self.recipe_folder
        probe = os.path.join(test_dir, "test_eqmod_probe.py")

        # OHOS: /system/bin/sh (mksh) 无法直接执行 ELF 二进制，用 bash 包裹；
        # python3 执行探针，参数携带被测包目录与 libindi 库目录
        # （与 indi-aok test() 模式一致）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        argv = [sys.executable, probe, pkg, indi_libdir]
        script = " ".join('"%s"' % item for item in argv)
        self.run(f"{bash} -c '{script}'", env="conanrun")
