import os
import shlex
import subprocess
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout


class LibiodbcConan(ConanFile):
    name = "libiodbc"
    version = "3.52.16"
    description = "iODBC (Independent Open Database Connectivity) Driver Manager"
    license = "LGPL-2.1"
    homepage = "https://www.iodbc.org/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libiodbc only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        src_dir = self.source_folder
        build_dir = self.build_folder
        os.makedirs(build_dir, exist_ok=True)

        # HMDFS workaround: create a writable temp dir for config.status
        # The conan cache is owned by a different uid, and umask 077 in
        # config.status blocks access. Symlink TMPDIR to a home-owned dir.
        writable_tmp = os.path.join(os.path.expanduser("~"), "tmp", "libiodbc-build")
        os.makedirs(writable_tmp, exist_ok=True)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        shared_flag = (
            "--enable-shared --disable-static"
            if self.options.shared
            else "--disable-shared --enable-static"
        )

        # 1. autoreconf
        self.run(f'cd "{src_dir}" && autoreconf --force --install', env="conanbuild")

        # HMDFS workaround: patch configure to use umask 022 instead of 077
        # The conan cache is owned by a different uid; umask 077 blocks access.
        configure_script = os.path.join(src_dir, "configure")
        if os.path.isfile(configure_script):
            with open(configure_script, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_script, "w") as f:
                f.write(content)

        # 2. configure
        configure_cmd = (
            f'cd "{build_dir}" && '
            f'TMPDIR="{writable_tmp}" '
            f'CC={shlex.quote(cc)} '
            f'CXX={shlex.quote(cxx)} '
            f'bash {shlex.quote(os.path.join(src_dir, "configure"))} '
            f'--prefix={shlex.quote(self.package_folder)} '
            f'{shared_flag} '
            f'--disable-gtk '
            f'--with-iodbc-inidir=/etc'
        )
        self.run(configure_cmd, env="conanbuild")

        # Fix config.status umask issue on HMDFS
        config_status = os.path.join(build_dir, "config.status")
        if os.path.isfile(config_status):
            with open(config_status, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(config_status, "w") as f:
                f.write(content)

        # 3. make
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
        self.run(f'cd "{build_dir}" && make -j{jobs}', env="conanbuild")

    def package(self):
        build_dir = self.build_folder
        # make install directly into package folder (prefix already set)
        self.run(f'cd "{build_dir}" && make install', env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = ["iodbc", "iodbcinst"]
