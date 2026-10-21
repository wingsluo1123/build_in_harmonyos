#!/usr/bin/env python3
import configparser
import glob
import os
import shutil
from contextlib import contextmanager

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class QadConan(ConanFile):
    name = "qad"
    version = "0.0-git20240206.43adc42"
    description = "Quality Assurance Daemon - REST API daemon for automated hardware testing"
    license = "MIT"
    homepage = "https://gitlab.com/CodethinkLabs/qad/qad"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libmicrohttpd/1.0.1")
        self.requires("libpng/1.6.58.1")
        self.requires("libdrm/2.4.133")
        self.requires("cjson/1.7.19")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("QAD is packaged here for Linux/OHOS only")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_cjson_pkg_config_alias()
        tc = MesonToolchain(self)
        tc.project_options["backend-kms"] = "true"
        tc.project_options["backend-ilm"] = "false"
        tc.project_options["static"] = "false"
        tc.generate()
        self._inject_meson_archive_tools()

    def _create_cjson_pkg_config_alias(self):
        cjson_pc = os.path.join(self.generators_folder, "cjson.pc")
        libcjson_pc = os.path.join(self.generators_folder, "libcjson.pc")
        if os.path.isfile(cjson_pc) and not os.path.isfile(libcjson_pc):
            with open(cjson_pc, encoding="utf-8") as src:
                content = src.read()
            content = content.replace("Name: cjson", "Name: libcjson")
            with open(libcjson_pc, "w", encoding="utf-8") as dst:
                dst.write(content)

    def _inject_meson_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not bindir or not os.path.isfile(ar) or not os.path.isfile(native_file):
            return
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(native_file, encoding="utf-8")
        if not parser.has_section("binaries"):
            return
        if not parser.has_option("binaries", "ar"):
            parser.set("binaries", "ar", self._meson_string(ar))
        if os.path.isfile(ranlib) and not parser.has_option("binaries", "ranlib"):
            parser.set("binaries", "ranlib", self._meson_string(ranlib))
        with open(native_file, "w", encoding="utf-8") as f:
            parser.write(f, space_around_delimiters=True)

    @staticmethod
    def _meson_string(value):
        return "'{}'".format(str(value).replace("\\", "/").replace("'", "\\'"))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        with self._host_tool_environment():
            meson.configure()
            meson.build()

    @contextmanager
    def _host_tool_environment(self):
        if str(self.settings.os) != "OHOS":
            yield
            return
        ld_library_path = os.environ.pop("LD_LIBRARY_PATH", None)
        try:
            yield
        finally:
            if ld_library_path is not None:
                os.environ["LD_LIBRARY_PATH"] = ld_library_path

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
