#!/usr/bin/env python3
"""Conan recipe for the upstream i2c-tools v4.4 userspace package."""

import os
import shlex
import sys

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class I2cToolsConan(ConanFile):
    name = "i2c-tools"
    version = "4.4"
    description = "Linux I2C utilities and libi2c userspace support library"
    license = ["GPL-2.0-or-later", "LGPL-2.1-or-later"]
    homepage = "https://git.kernel.org/pub/scm/utils/i2c-tools/i2c-tools.git"
    url = "https://git.kernel.org/pub/scm/utils/i2c-tools/i2c-tools.git"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        dynamic = 1 if self.options.shared else 0
        static = 0 if self.options.shared else 1
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            '{"status":"no_tests","framework":"plain Makefile",'
            '"command":"none (v4.4 has no test/check target)",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,'
            '"skipped":0,"xfail":0,"broken":0}'
        )
        self.run(
            "umask 022 && make -j2 "
            f"BUILD_DYNAMIC_LIB={dynamic} BUILD_STATIC_LIB={static} "
            f"USE_STATIC_LIB={static}",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        installer = os.path.join(self.build_folder, "i2ct15486-install")
        installer_source = f'''#!{sys.executable}
import os
import shutil
import sys

args = sys.argv[1:]
mode = "755"
make_directories = False
while args and args[0].startswith("-"):
    flag = args.pop(0)
    if flag == "-m":
        mode = args.pop(0)
    elif flag == "-d":
        make_directories = True
    else:
        raise SystemExit("unsupported install option: " + flag)

if make_directories:
    for directory in args:
        os.makedirs(directory, mode=int(mode, 8), exist_ok=True)
        os.chmod(directory, int(mode, 8))
else:
    if len(args) < 2:
        raise SystemExit("install requires a source and destination")
    destination = args[-1]
    sources = args[:-1]
    if len(sources) > 1 and not os.path.isdir(destination):
        os.makedirs(destination, exist_ok=True)
    for source in sources:
        target = os.path.join(destination, os.path.basename(source)) if os.path.isdir(destination) else destination
        shutil.copy2(source, target)
        os.chmod(target, int(mode, 8))
'''
        with open(installer, "w", encoding="utf-8") as stream:
            stream.write(installer_source)
        os.chmod(installer, 0o755)
        destdir = shlex.quote(self.package_folder)
        installer = shlex.quote(installer)
        self.run(
            f"umask 022 && make install INSTALL={installer} DESTDIR={destdir} PREFIX=",
            cwd=self.source_folder,
        )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["i2c"]
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "i2c-tools")
