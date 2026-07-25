from conan import ConanFile
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches, get, rmdir
from conan.errors import ConanInvalidConfiguration
import os

class RisCV64ElfBinutilsConan(ConanFile):
    name = "riscv64-elf-binutils"
    version = "2.46.0"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Only OHOS/Linux is supported")

    def layout(self):
        self.folders.source = "src"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--target=riscv64-elf",
            f"--host={self.settings.os.lower()}-unknown-linux-ohos",
            f"--build={self.settings.os.lower()}-unknown-linux-ohos",
            "--disable-gprofng",
            "--disable-nls",
            "--disable-shared",
            "--enable-static",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []

        bin_path = os.path.join(self.package_folder, "bin")
        self.buildenv_info.define("RISCV64_ELF_BINUTILS_PATH", bin_path)
        self.buildenv_info.define("RISCV64_ELF_LD",
                                   os.path.join(bin_path, "riscv64-elf-ld"))
        self.buildenv_info.define("RISCV64_ELF_AS",
                                   os.path.join(bin_path, "riscv64-elf-as"))
        self.buildenv_info.define("RISCV64_ELF_OBJDUMP",
                                   os.path.join(bin_path, "riscv64-elf-objdump"))
        self.buildenv_info.define("RISCV64_ELF_AR",
                                   os.path.join(bin_path, "riscv64-elf-ar"))

        # R38: 命令行工具，已在 commands.json 声明
        self.conf_info.define("user.riscv64-elf-binutils:tools",
                               "riscv64-elf-addr2line,riscv64-elf-ar,riscv64-elf-as,"
                               "riscv64-elf-c++filt,riscv64-elf-ld,riscv64-elf-nm,"
                               "riscv64-elf-objcopy,riscv64-elf-objdump,riscv64-elf-ranlib,"
                               "riscv64-elf-readelf,riscv64-elf-size,riscv64-elf-strings,"
                               "riscv64-elf-strip")
