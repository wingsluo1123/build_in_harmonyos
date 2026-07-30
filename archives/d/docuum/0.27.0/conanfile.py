from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.scm import Version
import os

class DocuumConan(ConanFile):
    name = "docuum"
    version = "0.27.0"
    license = "MIT"
    url = "https://github.com/stepchowfun/docuum"
    homepage = "https://github.com/stepchowfun/docuum"
    description = "A tool for Docker disk usage"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def layout(self):
        self.folders.source = "."

    def build(self):
        self.run("cargo build --release")

    def package(self):
        copy(self, "target/release/docuum*",
             dst=os.path.join(self.package_folder, "bin"),
             src=self.source_folder,
             keep_path=False)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
