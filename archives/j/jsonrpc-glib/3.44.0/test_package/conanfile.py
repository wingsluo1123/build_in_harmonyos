import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.build import can_run


class JsonrpcGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # Fix pre-installed .pc files from glib2 and json-glib
        for dep_name in ("glib2", "json-glib"):
            dep = self.dependencies[dep_name]
            dep_prefix = dep.package_folder
            src_pkgconfig = os.path.join(dep_prefix, "lib", "pkgconfig")
            if not os.path.isdir(src_pkgconfig):
                continue
            for pc_file in os.listdir(src_pkgconfig):
                if not pc_file.endswith(".pc"):
                    continue
                src_path = os.path.join(src_pkgconfig, pc_file)
                with open(src_path, "r") as f:
                    content = f.read()
                content = re.sub(
                    r"^prefix=.*$",
                    f"prefix={dep_prefix}",
                    content,
                    flags=re.MULTILINE,
                )
                dst_path = os.path.join(self.generators_folder, pc_file)
                with open(dst_path, "w") as f:
                    f.write(content)

        # Pin GNU binutils
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.build_folder, "test_package")
            self.run(f'"{bin_path}"', env="conanrun")
