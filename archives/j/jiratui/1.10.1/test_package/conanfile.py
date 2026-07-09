import os
from conan import ConanFile


class TestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test 必须实质依赖被测包
        pkg_folder = self.conf_info.get("user.jiratui:package_folder",
                                        self.dependencies["jiratui"].package_folder
                                        if "jiratui" in self.dependencies else "")
        bin_dir = os.path.join(pkg_folder, "bin") if pkg_folder else ""
        jiratui_bin = os.path.join(bin_dir, "jiratui") if bin_dir else ""

        if jiratui_bin and os.path.exists(jiratui_bin):
            self.output.info(f"Testing jiratui at {jiratui_bin}")
            self.run(f'"{jiratui_bin}" version', env="conanrun")
            self.output.success("jiratui version command executed")
        else:
            self.output.info(f"Testing jiratui import at {pkg_folder}")
            self.run(
                f'python -c "import jiratui; print(\'jiratui imported OK\')"',
                env="conanrun",
            )
            self.output.success("jiratui package import: OK")
