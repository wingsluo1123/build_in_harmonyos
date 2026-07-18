import os

from conan import ConanFile


class ArmnoneeabibinutilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Smoke test: verify core tools exist and report version
        tools = ["arm-none-eabi-objdump", "arm-none-eabi-objcopy",
                  "arm-none-eabi-ld", "arm-none-eabi-as",
                  "arm-none-eabi-ar", "arm-none-eabi-nm",
                  "arm-none-eabi-strip", "arm-none-eabi-size"]
        for tool in tools:
            self.run(f"{bash} -c '{tool} --version'", env="conanrun")