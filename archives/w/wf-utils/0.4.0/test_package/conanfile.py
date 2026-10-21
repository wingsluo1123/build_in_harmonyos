import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout

class WfUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = MesonToolchain(self)
        # E1124: CI worker PATH 无 llvm-ar，meson setup 探测静态归档器失败
        ar_path = "/data/service/hnp/bin/ar"
        if os.path.isfile(ar_path):
            tc.ar = ar_path
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        # L0d: test() 必须实际调用 self.run() 运行测试程序（不能用 meson.test() 空壳）
        test_exe = os.path.join(self.build_folder, "test_wfutils")
        if can_run(self):
            self.run(test_exe, env="conanrun")
        else:
            self.output.info("Cross-building: consumer binary is run on OHOS device")
