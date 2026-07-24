#!/usr/bin/env python3
"""Conan recipe for the Boost.Build b2 command-line tool from Boost 1.85.0."""
import hashlib
import os
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class BoostConan(ConanFile):
    name = "boost"
    version = "1.85.0"
    description = "Boost.Build b2 command-line build tool for OpenHarmony"
    license = "BSL-1.0"
    homepage = "https://www.boost.org"
    url = "https://github.com/boostorg/boost"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "Boost.Build 1.85.0 recipe contains OpenHarmony compatibility patches"
            )

    def source(self):
        source = self.conan_data["sources"]
        archive = os.path.join(self.source_folder, source["filename"])
        self.run(f'curl -L -sS --fail -o "{archive}" "{source["url"]}"')
        digest = hashlib.sha256()
        with open(archive, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != source["sha256"]:
            raise RuntimeError("Boost source SHA256 mismatch")
        with tarfile.open(archive, "r:bz2") as tar:
            root = "boost_1_85_0/"
            for member in tar.getmembers():
                if member.name.startswith(root) and member.name != root.rstrip("/"):
                    member.name = member.name[len(root):]
                    tar.extract(member, self.source_folder)

    def _cxx(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = executables.get("cpp")
        if not cxx or not os.path.isabs(cxx):
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables.cpp must be an absolute path"
            )
        return cxx

    def build(self):
        apply_conandata_patches(self)
        engine = os.path.join(self.source_folder, "tools", "build", "src", "engine")
        self.run(
            f'./build.sh clang --cxx="{self._cxx()}" --cxxflags="-DNO_VFORK"',
            cwd=engine,
        )

    def package(self):
        engine = os.path.join(self.source_folder, "tools", "build", "src", "engine")
        copy(self, "b2", engine, os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "b2"), 0o755)
        copy(
            self,
            "*",
            os.path.join(self.source_folder, "tools", "build", "src"),
            os.path.join(self.package_folder, "share", "b2", "src"),
        )
        copy(self, "LICENSE_1_0.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
