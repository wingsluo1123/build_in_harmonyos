#!/usr/bin/env python3
"""Conan recipe — cdo 2.4.0 (Climate Data Operators, autotools).

CDO is a command-line tool for processing climate and forecast data.
Uses autotools build system. config.guess/config.sub are patched
with patch-ohos.sh for HarmonyOS platform recognition (E007).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import copy, get, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdoConan(ConanFile):
    name = "cdo"
    version = "2.4.0"
    description = "Climate Data Operators — command-line tools for processing climate and forecast data"
    license = "GPL-2.0-only"
    homepage = "https://code.mpimet.mpg.de/projects/cdo"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_shell(self):
        for candidate in [
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
        ]:
            if candidate and os.path.isabs(candidate) and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
            if candidate and not os.path.isabs(candidate):
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        return "/bin/sh"

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Static build for system-name libraries
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--without-netcdf")
        tc.configure_args.append("--without-hdf5")
        tc.configure_args.append("--without-szlib")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

        env = Environment()
        shell_path = self._resolve_shell()
        env.define("CONFIG_SHELL", shell_path)
        env.define("SHELL", shell_path)
        env.vars(self).save_script("ohos_env")

    def build(self):
        shell_path = self._resolve_shell()
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.exists(conanbuild_sh):
            with open(conanbuild_sh, "r", encoding="utf-8") as f:
                content = f.read()
            fix = (
                "\n# Override invalid CONFIG_SHELL/SHELL from Conan profile\n"
                f'export CONFIG_SHELL="{shell_path}"\n'
                f'export SHELL="{shell_path}"\n'
            )
            if fix not in content:
                with open(conanbuild_sh, "w", encoding="utf-8") as f:
                    f.write(content + fix)
        # E007: Patch config.guess/config.sub for HarmonyOS via helper script
        script = os.path.join(self.export_sources_folder, "patches", "patch-ohos.sh")
        if os.path.exists(script):
            self.run(f'"{shell_path}" "{script}" "{self.source_folder}"', env="conanbuild")
        # Build with autotools
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Ensure binary has execute permission
        self.run(f"chmod +x {self.package_folder}/bin/cdo")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
