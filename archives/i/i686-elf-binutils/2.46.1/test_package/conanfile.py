import os

from conan import ConanFile


class I686elfbinutilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Smoke test: verify core tools exist and report version
        tools = ["i686-elf-objdump", "i686-elf-objcopy",
                  "i686-elf-ld", "i686-elf-as",
                  "i686-elf-ar", "i686-elf-nm",
                  "i686-elf-strip", "i686-elf-size"]
        for tool in tools:
            self.run(f"{bash} -c '{tool} --version'", env="conanrun")