import os

from conan import ConanFile


class WdfsTestConan(ConanFile):
    """test_package for wdfs 1.4.2 — 消费者视角验证（见 test.sh / MANIFEST.yml）。

    上游 wdfs 没有任何测试套件（tarball 无 tests/、Makefile.am 仅
    bin_PROGRAMS、无 check_PROGRAMS/TESTS），故按 TEST_QUALITY_SPEC 补充
    对已安装二进制的消费者测试（R34：真实执行被测包，非空壳断言）。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能直接执行 ELF；用 bash 包装
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
