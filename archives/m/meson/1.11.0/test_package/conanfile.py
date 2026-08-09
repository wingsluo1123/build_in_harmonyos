import os

from conan import ConanFile
from conan.tools.build import cross_building


class MesonTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def build(self):
        # OHOS 下 tool_requires 的 bin 目录不会自动注入 conanbuild 的 PATH
        # （VirtualBuildEnv 仅注入 profile buildenv），故用完整路径调用。
        meson_bin = os.path.join(
            self.dependencies.build["meson"].package_folder, "bin", "meson"
        )
        self.run('"{}" setup build'.format(meson_bin), env="conanbuild")
        self.run('"{}" compile -C build'.format(meson_bin), env="conanbuild")

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: package execution is skipped.")
            return
        self.run("./build/conan-probe")
