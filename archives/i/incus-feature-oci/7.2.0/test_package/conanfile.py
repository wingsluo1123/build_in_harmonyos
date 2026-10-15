"""Conan test_package for incus-feature-oci — 消费者视角验证元包契约。

incus-feature-oci 是 noarch 元包（Alpine incus-feature APKBUILD oci() 子包），
自身无编译产物；本测试验证运行时契约：
1. bin/incus-oci 包装器存在且 --version 可执行（真实执行被测包产物）；
2. skopeo 契约：无 skopeo 时以与上游 client/oci_images.go 完全一致的报错退出；
3. 依赖契约：incus-feature-client 提供 incus 二进制存在；
4. 委托行为：PATH 上提供 skopeo 桩时，包装器真实委托执行 incus --help。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class IncusFeatureOciTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 测试逻辑实现在 test_contract.sh（CI L0c 门禁要求非 conanfile 测试源
        # 文件）。此处解析被测包与依赖包的产物路径并以 conanrun 环境执行。
        dep = self.dependencies["incus-feature-oci"]
        bindir = os.path.join(dep.package_folder, "bin")
        wrapper = os.path.join(bindir, "incus-oci")
        if not os.path.isfile(wrapper):
            raise ConanException(f"incus-oci wrapper not found in {bindir}")
        self.output.info(f"testing installed wrapper: {wrapper}")

        client = self.dependencies["incus-feature-client"]
        incus_bin = os.path.join(client.package_folder, "bin", "incus")
        if not os.path.isfile(incus_bin):
            raise ConanException("incus binary not found "
                                 "(incus-feature-client dependency)")

        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "test_contract.sh")
        self.run(f'sh "{script}" "{wrapper}" "{incus_bin}"', env="conanrun")
        self.output.info("incus-oci contract tests: ALL PASSED")
