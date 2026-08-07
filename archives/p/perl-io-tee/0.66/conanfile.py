import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlIoTeeConan(ConanFile):
    name = "perl-io-tee"
    version = "0.66"
    description = "IO::Tee - Multiplex output to multiple output handles"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/IO-Tee"
    url = ""
    topics = ("perl", "cpan", "io", "tee")

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2")

    def build_requirements(self):
        self.tool_requires("perl/5.42.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        perl = Path(self.dependencies.host["perl"].package_folder)
        privlibs = sorted((perl / "lib" / "perl5").glob("5.*"))
        if not privlibs:
            raise ConanException("Cannot locate Perl privlib in perl/5.42.2 package")
        privlib = privlibs[-1]
        cores = sorted(privlib.glob("*/CORE"))
        if not cores:
            raise ConanException("Cannot locate Perl CORE headers in perl/5.42.2 package")
        archlib = cores[-1].parent
        env.define("CONAN_PERL_PRIVLIB", str(privlib))
        env.define("CONAN_PERL_ARCHLIB", str(archlib))
        env.define("PERL_SRC", str(archlib / "CORE"))
        env.vars(self).save_script("perl_io_tee")

    def _makefile_pl(self, args=""):
        perl_args = (
            'PERL_LIB="$CONAN_PERL_PRIVLIB" '
            'PERL_ARCHLIB="$CONAN_PERL_ARCHLIB" '
            'PERL_INC="$PERL_SRC"'
        )
        command = f"perl Makefile.PL {perl_args} {args}".strip()
        self.run(command, cwd=self.source_folder, env=["conanbuild", "conanrun", "perl_io_tee"])

    def build(self):
        apply_conandata_patches(self)
        self._makefile_pl()
        self.run("make -j1", cwd=self.source_folder, env=["conanbuild", "conanrun", "perl_io_tee"])
        self.run("make test TEST_VERBOSE=1", cwd=self.source_folder, env=["conanbuild", "conanrun", "perl_io_tee"])

    def package(self):
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        copy(self, "*", src=os.path.join(self.source_folder, "lib"), dst=perl_lib, keep_path=True)
        share = os.path.join(self.package_folder, "share", self.name)
        copy(self, "README", src=self.source_folder, dst=share)
        copy(self, "Changes", src=self.source_folder, dst=share)
        copy(self, "Makefile.PL", src=self.source_folder, dst=share)
        copy(self, "META.json", src=self.source_folder, dst=share)
        copy(self, "META.yml", src=self.source_folder, dst=share)
        copy(self, "*", src=os.path.join(self.source_folder, "t"), dst=os.path.join(share, "t"), keep_path=True)

    def package_info(self):
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PERL5LIB", perl_lib)
        self.buildenv_info.prepend_path("PERL5LIB", perl_lib)
