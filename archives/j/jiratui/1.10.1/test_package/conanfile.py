from conan import ConanFile
import os


class TestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test 必须实质依赖被测包
        pkg_folder = self.dependencies["jiratui"].package_folder
        jiratui_bin = os.path.join(pkg_folder, "bin", "jiratui")

        if os.path.exists(jiratui_bin):
            self.output.info(f"Testing jiratui at {jiratui_bin}")
            self.run(f'"{jiratui_bin}" version', env="conanrun")
            self.output.success("jiratui version command executed")
        else:
            self.output.info(f"Testing jiratui import at {pkg_folder}")
            self.run(
                'python -c "import jiratui; print(\'jiratui imported OK\')"',
                env="conanrun",
            )
            self.output.success("jiratui package import: OK")
