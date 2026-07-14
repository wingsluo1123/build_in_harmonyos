from conan import ConanFile
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain

import os


class HexeditRecipe(ConanFile):
    name = "hexedit"
    version = "1.6"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"
    generators = ()
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    description = "View and edit files in hex"
    topics = ("hex", "editor", "terminal")

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            'HELP2MAN=/bin/true',
            'CFLAGS=-fPIC -O2 -I$DEFAULT_PREFIX/include',
            'LDFLAGS=-L$DEFAULT_PREFIX/lib',
            'LIBS=-lncursesw',
        ])
        tc.generate()

    def build(self):
        replace_in_file(self, os.path.join(self.source_folder, "configure"), "cross_compiling=no", "cross_compiling=maybe")
        replace_in_file(self, os.path.join(self.source_folder, "configure"), "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make("-j1")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
