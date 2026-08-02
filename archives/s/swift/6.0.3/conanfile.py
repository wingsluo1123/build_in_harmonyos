#!/usr/bin/env python3
"""Conan package shell for the Swift 6.0.3 OHOS toolchain.

The current adaptation has proven an OHOS-native Swift toolchain on the true
device, but the full source bootstrap is still being converted from probe
scripts into reviewable patches. Until then this recipe packages an already
assembled Swift stage directory or tarball. It deliberately fails clearly when
no stage is supplied, so downstream SwiftPM recipes do not silently depend on
absolute probe paths.
"""
import os
import shutil
import stat
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class SwiftConan(ConanFile):
    name = "swift"
    version = "6.0.3"
    description = "Swift compiler and Swift Package Manager for HarmonyOS/OHOS"
    license = "Apache-2.0"
    homepage = "https://www.swift.org/"
    url = "https://www.swift.org/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "scripts/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("This Swift package currently targets OHOS only.")
        if str(self.settings.arch) not in ("armv8", "armv8.3", "armv8.4", "aarch64"):
            raise ConanInvalidConfiguration(f"Unsupported OHOS Swift arch: {self.settings.arch}")

    def configure(self):
        self.settings.rm_safe("compiler")
        self.settings.rm_safe("build_type")
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("build_type")
        self.info.settings.rm_safe("os.version")

    def source(self):
        pass

    def build(self):
        stage = os.environ.get("SWIFT_OHOS_STAGED_ROOT")
        tarball = os.environ.get("SWIFT_OHOS_STAGED_TARBALL")
        stage_out = os.path.join(self.build_folder, "stage")
        if stage and os.path.isdir(stage):
            copy(self, "*", src=stage, dst=stage_out, keep_path=True)
        elif tarball and os.path.isfile(tarball):
            os.makedirs(stage_out, exist_ok=True)
            with tarfile.open(tarball, "r:*") as archive:
                try:
                    archive.extractall(stage_out, filter="data")
                except TypeError:
                    archive.extractall(stage_out)
            self._strip_single_root(stage_out)
        else:
            raise ConanException(
                "Swift 6.0.3 OHOS stage not supplied. Set SWIFT_OHOS_STAGED_ROOT "
                "or SWIFT_OHOS_STAGED_TARBALL after the source-bootstrap patches "
                "have produced a signed Swift toolchain stage."
            )

        self._validate_stage(stage_out)

    def _strip_single_root(self, stage_out):
        entries = os.listdir(stage_out)
        if len(entries) != 1:
            return
        root = os.path.join(stage_out, entries[0])
        if not os.path.isdir(root):
            return
        for name in os.listdir(root):
            shutil.move(os.path.join(root, name), os.path.join(stage_out, name))
        os.rmdir(root)

    def _validate_stage(self, stage):
        required = [
            os.path.join("bin", "swift"),
            os.path.join("bin", "swiftc"),
            os.path.join("bin", "swift-build"),
            os.path.join("bin", "swift-package"),
            os.path.join("lib", "swift"),
        ]
        missing = [path for path in required if not os.path.exists(os.path.join(stage, path))]
        if missing:
            raise ConanException(f"Swift OHOS stage is missing required entries: {missing}")

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        copy(self, "*", src=stage, dst=self.package_folder, keep_path=True)
        self._make_bin_executable()

    def _make_bin_executable(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bin_dir):
            return
        for name in os.listdir(bin_dir):
            path = os.path.join(bin_dir, name)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib")
        swift_lib_dir = os.path.join(lib_dir, "swift", "ohos")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", lib_dir)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", lib_dir)
        if os.path.isdir(swift_lib_dir):
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", swift_lib_dir)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", swift_lib_dir)
        self.buildenv_info.define("SWIFT_EXEC", os.path.join(bin_dir, "swiftc"))
        self.buildenv_info.define("SWIFT_OHOS_TOOLCHAIN_ROOT", self.package_folder)
