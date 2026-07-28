#!/usr/bin/env python3
"""Conan recipe for EMQX 5.8.8.

Homebrew formula source:
https://github.com/Homebrew/homebrew-core/blob/master/Formula/e/emqx.rb

EMQX is an Erlang/OTP MQTT broker. The package is a command-line
application/release, not a C/C++ library. The recipe follows the Homebrew
build entry point and disables QUIC for the first OHOS adaptation pass.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, rm, save
from conan.tools.layout import basic_layout


class EmqxConan(ConanFile):
    name = "emqx"
    version = "5.8.8"
    description = "Distributed MQTT broker for IoT messaging"
    license = "Apache-2.0"
    homepage = "https://www.emqx.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        save(self, os.path.join(self.source_folder, ".prepare"), "")
        self.run("chmod +x scripts/*.sh", cwd=self.source_folder)
        build_vars = (
            "CMAKE_POLICY_VERSION_MINIMUM=3.5 "
            "PKG_VSN=5.8.8 "
            "BUILD_WITHOUT_QUIC=1 "
            "SYSTEM=Linux "
            "PROFILE=emqx"
        )
        self.run(f"{build_vars} make emqx-rel", cwd=self.source_folder, env=["conanbuild"])

    def package(self):
        rel_dir = os.path.join(self.source_folder, "_build", "emqx", "rel", "emqx")
        copy(self, "*", src=rel_dir, dst=self.package_folder, keep_path=True)
        rm(self, "emqx.cmd", folder=os.path.join(self.package_folder, "bin"))
        rm(self, "emqx_ctl.cmd", folder=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
