#!/usr/bin/env python3
"""Vamp plugin and host SDK 2.10.0 for HarmonyOS PC."""

import os
from pathlib import Path

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file
from conan.tools.layout import basic_layout


class VampSdkConan(ConanFile):
    name = "vamp-sdk"
    version = "2.10.0"
    description = "Vamp audio analysis plugin and host SDK"
    license = "BSD-3-Clause"
    homepage = "https://www.vamp-plugins.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "upstream-test-plugin/*"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # The upstream example host links libsndfile; the SDK libraries do not.
        self.requires("libsndfile/1.2.2", visible=False)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if str(self.settings.os) == "OHOS":
            apply_conandata_patches(self)

        source = Path(self.source_folder)
        plugin = source.parent / "vamp-test-plugin"
        copy(self, "*", src=os.path.join(self.export_sources_folder,
                                          "upstream-test-plugin"), dst=str(plugin))
        # Only the external test plugin's SDK search path changes. The test
        # logic and all 22 upstream expected outputs remain untouched.
        replace_in_file(self, str(plugin / "Makefile.linux"),
                        "VAMPSDK_DIR\t:= ../vamp-plugin-sdk",
                        f"VAMPSDK_DIR\t:= {source}")

        sndfile = Path(self.dependencies["libsndfile"].package_folder)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        env = Environment()
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.define("SNDFILE_CFLAGS", f"-I{sndfile / 'include'}")
        env.define("SNDFILE_LIBS", f"-L{sndfile / 'lib'} -lsndfile")
        # OHOS user storage does not implement getcwd for a newly started
        # shell. Export the verified physical path before Conan launches it.
        env.define("PWD", self.source_folder)
        with env.vars(self).apply():
            self.run(f"./configure --prefix={self.package_folder}",
                     cwd=self.source_folder)
            # GNU Make's parallel jobserver cannot create FIFOs on OHOS user
            # storage, so use the serial build that was verified on device.
            self.run("make -j1 all", cwd=self.source_folder)
            self.run("bash test/run-test-plugin-regression.sh",
                     cwd=self.source_folder)

        expected = sorted((source / "test" / "expected").glob("*.txt"))
        obtained = source / "test" / "obtained"
        failures = sorted((source / "test" / "failures").glob("*.txt"))
        if len(expected) != 22 or len(list(obtained.glob("*.txt"))) != 22 or failures:
            raise RuntimeError("Upstream regression did not produce 22 clean outputs")
        for item in expected:
            if item.read_bytes() != (obtained / item.name).read_bytes():
                raise RuntimeError(f"Upstream regression mismatch: {item.name}")
        self.output.info("UPSTREAM_REGRESSION: 22/22 exact output comparisons passed")

    def package(self):
        source = self.source_folder
        for directory in ("vamp", "vamp-sdk", "vamp-hostsdk"):
            copy(self, "*.h", src=os.path.join(source, directory),
                 dst=os.path.join(self.package_folder, "include", directory))
        for name in ("libvamp-sdk.a", "libvamp-hostsdk.a",
                     "libvamp-sdk.so", "libvamp-hostsdk.so"):
            copy(self, name, src=source,
                 dst=os.path.join(self.package_folder, "lib"))
        copy(self, "vamp-example-plugins.so",
             src=os.path.join(source, "examples"),
             dst=os.path.join(self.package_folder, "lib", "vamp"))
        copy(self, "COPYING", src=source,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["vamp-hostsdk", "vamp-sdk"]
        self.cpp_info.system_libs = ["dl"]
