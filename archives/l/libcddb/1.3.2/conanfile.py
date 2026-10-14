"""Conan 2 recipe for libcddb 1.3.2 on HarmonyOS PC.

适配要点（详见 notes.md）：
* 上游 sourceforge 源在沙箱内不可达 → 采用 Debian 归档的 pristine orig tarball（内容等同上游）；
* HarmonyOS 三元组由 patches/0001（config.guess）+ 0002（config.sub）解决；
* chars et 转换优先用 libc 内置 iconv（musl 提供），不额外引入 libiconv；
* OHOS 上旧 libtool 需要真实存在的链接器/归档器 → 显式指向 llvm-* 工具。
"""

import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcddbConan(ConanFile):
    name = "libcddb"
    version = "1.3.2"
    description = "C library to access data on a CDDB server (CD-DA metadata)"
    license = "LGPL-2.1-or-later"
    homepage = "http://libcddb.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-rpath")
        tc.configure_args.append("--enable-shared" if self.options.shared else "--disable-shared")
        tc.configure_args.append("--disable-static" if self.options.shared else "--enable-static")
        env = tc.environment()
        if str(self.settings.os) == "OHOS":
            for variable, command in (("LD", "ld.lld"), ("AR", "llvm-ar"),
                                      ("RANLIB", "llvm-ranlib"), ("NM", "llvm-nm"),
                                      ("STRIP", "llvm-strip"), ("OBJDUMP", "llvm-objdump")):
                found = shutil.which(command)
                if not found:
                    raise ConanException("required OHOS tool not found: " + command)
                env.define(variable, found)
        tc.generate(env=env)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["cddb"]
