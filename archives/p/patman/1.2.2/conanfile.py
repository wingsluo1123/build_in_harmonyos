import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PatmanConan(ConanFile):
    name = "patman"
    version = "1.2.2"
    description = "PatMaN: fast approximate pattern matcher for short nucleotide sequences"
    license = "GPL-2.0-or-later"
    homepage = "https://bioinf.eva.mpg.de/patman/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("patman supports Linux/OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("popt/1.16")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # 上游 Makefile 无 configure：编译器/标志由 Toolchain 以环境变量传入，
        # popt 的 -I/-L/-l 由 AutotoolsDeps 注入 CPPFLAGS/LDFLAGS/LIBS。
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # 上游 Makefile 位于源码根目录，就地构建；
        # 不走上游 install 目标：它用 `install -s`，会调用构建机 strip 处理 aarch64 ELF
        self.run("make patman -j4", cwd=self.source_folder)

    def package(self):
        copy(self, "patman", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "patman.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
