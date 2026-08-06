#!/usr/bin/env python3
"""Conan recipe for jack (JACK Audio Connection Kit) — waf build system.

jack2 uses waf (Python-based build system), not autotools or cmake.
This recipe calls waf directly via self.run().

R32: settings.os check includes both "Linux" and "OHOS"
R33: Compiler executables obtained from Conan conf, not shell env vars
R38: jackd executable — commands.json required at software level
"""
import os
import json

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class JackConan(ConanFile):
    name = "jack"
    version = "1.9.22"
    description = "JACK Audio Connection Kit - low-latency audio server"
    license = "GPLv2+"
    homepage = "https://jackaudio.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: Get compiler executables from Conan conf, not shell env vars
        env = Environment()
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compiler_executables, str):
            compiler_executables = json.loads(compiler_executables)
        cc = compiler_executables.get("c")
        cxx = compiler_executables.get("cpp")
        if cc:
            env.define("CC", cc)
        if cxx:
            env.define("CXX", cxx)
        envvars = env.vars(self)
        envvars.save_script("jack_build_env")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # waf configure — OHOS is not recognized by waf, use --platform=linux
        # Disable libsamplerate (not available on OHOS)
        self.run(f"cd {src} && python3 waf configure --platform=linux --samplerate=no --prefix=/usr",
                 env="conanbuild")
        # waf build
        self.run(f"cd {src} && python3 waf build -j1", env="conanbuild")

    def package(self):
        src = self.source_folder
        # waf install to staging directory
        staging = os.path.join(self.build_folder, "staging")
        self.run(f"cd {src} && python3 waf install --destdir={staging}", env="conanbuild")
        # Copy from staging/usr/ to package root
        usr_dir = os.path.join(staging, "usr")
        copy(self, "*.h", os.path.join(usr_dir, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "*.so*", os.path.join(usr_dir, "lib"),
             os.path.join(self.package_folder, "lib"))
        copy(self, "jackd", os.path.join(usr_dir, "bin"),
             os.path.join(self.package_folder, "bin"))
        # jack modules (drivers, internal clients)
        copy(self, "*.so", os.path.join(usr_dir, "lib", "jack"),
             os.path.join(self.package_folder, "lib", "jack"))
        # pkgconfig
        copy(self, "*.pc", os.path.join(usr_dir, "lib", "pkgconfig"),
             os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["jack", "jackserver"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
