import os

from conan import ConanFile
from conan.tools.build import can_run


class UbootTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # test_uboot.sh 从 conanrun 环境取 U_BOOT_SANDBOX / U_BOOT_MKIMAGE /
        # U_BOOT_UT_DTB / U_BOOT_UT_TESTAPP / U_BOOT_UT_PAIRS（主配方
        # package_info 的 runenv_info 定义）；夹具与 runner 脚本在
        # test_package/fixtures/ 里随本目录一起被 conan 自动导出。
        self.run("sh %s" % os.path.join(self.source_folder, "test_uboot.sh"),
                 env="conanrun")
