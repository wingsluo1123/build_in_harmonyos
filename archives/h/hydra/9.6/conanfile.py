from conan import ConanFile
from conan.tools.make import Make
from conan.tools.files import get, copy
import os


class HydraConan(ConanFile):
    name = "hydra"
    version = "9.6"
    description = "THC Hydra - fast network logon cracker supporting many protocols"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/vanhauser-thc/thc-hydra"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        make = Make(self)
        make.make()

    def package(self):
        copy(self, "*", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
