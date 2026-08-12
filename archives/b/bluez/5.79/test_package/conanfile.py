from conan import ConanFile


class BluezTestConan(ConanFile):
    """test_package for bluez — runs bluetoothctl --version (R34: 实质调用被测包二进制)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # VirtualRunEnv 将 bluez 的 bin/ 注入 PATH (conanrun)
        self.run("bluetoothctl --version", env="conanrun")
