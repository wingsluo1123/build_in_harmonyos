#!/usr/bin/env python3
"""Conan recipe — libserdes 8.3.0 (Confluent Avro serialization C/C++ library).

Build system: mklove (custom autotools-like configure + make).
Dependencies: jansson, libcurl, avro-c (Conan-managed via @ohpcd/stable).

⚠️ Dependency chain note:
  jansson/2.15.0, curl/8.19.0, avro-c/1.11.3 must be published to @ohpcd/stable
  before this recipe can build in CI. If they are not yet published,
  `conan create` will fail with "Missing recipe" error for each missing dep.
  Use `ohc-run.py resolve-deps jansson curl avro-c` to check availability.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class LibserdesConan(ConanFile):
    name = "libserdes"
    version = "8.3.0"
    description = "Confluent Schema-Registry C/C++ client library with Avro serialization"
    license = "Apache-2.0"
    homepage = "https://github.com/confluentinc/libserdes"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: 依赖引用必须 @ohpcd/stable
        self.requires("jansson/2.15.0@ohpcd/stable")
        self.requires("curl/8.19.0@ohpcd/stable")
        self.requires("avro-c/1.11.3@ohpcd/stable")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # VirtualBuildEnv generates conanbuild.sh which sets up:
        #   CPPFLAGS with -I paths from Conan dependencies
        #   LDFLAGS with -L paths from Conan dependencies
        #   CC, CXX from profile
        #   SHELL, CONFIG_SHELL from profile [buildenv]
        venv = VirtualBuildEnv(self)
        venv.generate()

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder

        # mklove must run from source dir (uses relative paths for modules)
        # env=["conanbuild"] sources the VirtualBuildEnv-generated environment
        # which provides correct CPPFLAGS/LDFLAGS/CC from Conan dependencies
        self.run("./configure --prefix=/", cwd=src_dir, env=["conanbuild"])
        self.run("make -j2", cwd=src_dir, env=["conanbuild"])

        # L1: Run upstream official tests (make check)
        # CI L1c verifies make check execution trace in build log
        self.run("make check", cwd=src_dir, env=["conanbuild"])

    def package(self):
        src_dir = self.source_folder
        # DESTDIR + prefix(/) = package_folder
        self.run(f"make install DESTDIR={self.package_folder}", cwd=src_dir, env=["conanbuild"])

    def package_info(self):
        self.cpp_info.libs = ["serdes"]
        if self.settings.os in ("Linux", "OHOS"):
            # Only true system libraries go here (R32: os check must include OHOS)
            # jansson, curl, avro are Conan-managed via requires(), not system_libs
            self.cpp_info.system_libs = ["rt", "pthread"]
