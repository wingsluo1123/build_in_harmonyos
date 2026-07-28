#!/usr/bin/env python3
"""Conan recipe for Lilv 0.26.5-git."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LilvConan(ConanFile):
    name = "lilv"
    version = "0.26.5-git"
    description = "C library for loading and using LV2 audio plugins"
    license = "ISC"
    homepage = "https://drobilla.net/software/lilv"
    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lilv supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lv2/1.18.11-git")
        self.requires("serd/0.32.9-git")
        self.requires("sord/0.16.22-git")
        self.requires("sratom/0.6.22-git")
        self.requires("zix/0.8.1-git")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options.update(
            {
                "default_library": "shared",
                "bindings_cpp": "enabled",
                "bindings_py": "disabled",
                "docs": "disabled",
                "dynmanifest": "disabled",
                "html": "disabled",
                "singlehtml": "disabled",
                "tests": "enabled",
                "tools": "enabled",
                "wrap_mode": "nodownload",
            }
        )
        tc.generate()

        PkgConfigDeps(self).generate()

        # Keep Meson utilities discoverable on OHOS workers whose PATH only
        # contains the compiler wrapper directory.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "")
        if cc:
            bin_dir = os.path.dirname(cc)
            env = Environment()
            env.define("AR", os.path.join(bin_dir, "llvm-ar"))
            env.define("RANLIB", os.path.join(bin_dir, "llvm-ranlib"))
            env.define("NM", os.path.join(bin_dir, "llvm-nm"))
            env.prepend_path("PATH", bin_dir)
            env.vars(self).save_script("ohos_toolchain_env")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.compile()
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

        if str(self.settings.os) == "OHOS":
            self._sign_ohos_artifacts()

    def _sign_ohos_artifacts(self):
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"

        for directory in ("bin", "lib"):
            artifact_dir = os.path.join(self.package_folder, directory)
            if not os.path.isdir(artifact_dir):
                continue

            for root, _, files in os.walk(artifact_dir):
                for filename in files:
                    path = os.path.join(root, filename)
                    if os.path.islink(path):
                        continue
                    if directory == "lib" and ".so" not in filename:
                        continue

                    signed = path + ".signed"
                    self.run(
                        f'"{objcopy}" --remove-section .codesign "{path}" '
                        "2>/dev/null || true",
                        cwd=self.package_folder,
                    )
                    self.run(
                        f'"{sign_tool}" sign -inFile "{path}" '
                        f'-outFile "{signed}" -selfSign 1',
                        cwd=self.package_folder,
                        quiet=True,
                    )
                    os.replace(signed, path)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "lilv-0")
        self.cpp_info.libs = ["lilv-0"]
        self.cpp_info.includedirs = ["include/lilv-0"]
        self.cpp_info.bindirs = ["bin"]
