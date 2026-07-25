from conan import ConanFile
from conan.tools.build import can_run


class RisCV64ElfBinutilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: 必须实际调用被测包的可执行文件
        self.run("riscv64-elf-ld --version")
        self.run("riscv64-elf-as --version")
        self.run("riscv64-elf-ar --version")
        self.run("riscv64-elf-nm --version")
        self.run("riscv64-elf-objdump --version")
        self.run("riscv64-elf-readelf --version")
        self.run("riscv64-elf-objcopy --version")
        self.run("riscv64-elf-ranlib --version")
        self.run("riscv64-elf-strip --version")
        self.run("riscv64-elf-size --version")
        self.run("riscv64-elf-strings --version")
        self.run("riscv64-elf-c++filt --version")
        self.run("riscv64-elf-addr2line --version")
