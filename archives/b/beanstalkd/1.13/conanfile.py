import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BeanstalkdConan(ConanFile):
    name = "beanstalkd"
    version = "1.13"
    description = "Beanstalkd - a simple, fast work queue service"
    license = "MIT"
    homepage = "https://github.com/beanstalkd/beanstalkd"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Run configure script (creates harmonyos.c symlink if needed)
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            self.run(f"{config_shell} ./configure", cwd=self.source_folder)

        # Build with OS=linux (OHOS is Linux-compatible, supports epoll)
        self.run("make -j1 OS=linux", cwd=self.source_folder)

    def package(self):
        copy(self, "beanstalkd", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
