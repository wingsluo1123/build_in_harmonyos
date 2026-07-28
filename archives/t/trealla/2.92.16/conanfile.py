#!/usr/bin/env python3
"""Conan recipe for Trealla Prolog 2.92.16."""
import glob
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class TreallaConan(ConanFile):
    name = "trealla"
    version = "2.92.16"
    description = "Compact, efficient Prolog interpreter"
    license = "MIT"
    homepage = "https://github.com/trealla-prolog/trealla"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    win_bash = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("trealla supports POSIX platforms")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _generate_embedded_sources(self):
        # bin2c is a build-machine helper. Generate its deterministic output
        # with Conan's Python runtime so cross builds never execute a target
        # binary.
        helper = os.path.join(self.source_folder, "util", "bin2c")
        save(self, helper, "#!/usr/bin/env sh\nexit 0\n")
        library = os.path.join(self.source_folder, "library")
        for source in glob.glob(os.path.join(library, "*.pl")):
            relative = os.path.relpath(source, self.source_folder).replace("\\", "/")
            variable = re.sub(r"[^A-Za-z0-9]", "_", relative)
            with open(source, "rb") as stream:
                data = stream.read()
            rows = [
                "  " + ",".join(f"0x{byte:02x}" for byte in data[index:index + 12])
                for index in range(0, len(data), 12)
            ]
            payload = ",\n".join(rows)
            generated = (
                "#include <stddef.h>\n"
                f"unsigned char {variable}[] = {{\n{payload}\n}};\n"
                f"unsigned int {variable}_len = {len(data)};\n"
            )
            save(self, os.path.splitext(source)[0] + ".c", generated)

    def build(self):
        apply_conandata_patches(self)
        self._generate_embedded_sources()
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        cc = compiler_executables.get("c")
        compiler_arg = f' CC="{unix_path(self, cc)}"' if cc else ""
        with chdir(self, self.source_folder):
            self.run(
                "make -j1 "
                "ISOCLINE=1 NOFFI=1 NOSSL=1 EMBED=1 "
                f'GIT_VERSION="v{self.version}"{compiler_arg} release',
                env="conanbuild",
            )

    def package(self):
        copy(
            self,
            "tpl",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "tests"),
            dst=os.path.join(
                self.package_folder, "share", "trealla", "upstream-tests", "tests"
            ),
            keep_path=True,
        )
        copy(
            self,
            "tpl",
            src=self.source_folder,
            dst=os.path.join(
                self.package_folder, "share", "trealla", "upstream-tests"
            ),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
