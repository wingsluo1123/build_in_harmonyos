#!/usr/bin/env python3
"""Conan recipe for gstreamer 1.28.3 on HarmonyOS PC (arm64).

Build system: meson
R28: test_package/ exists
R32: settings.os judgment uses in ("Linux", "OHOS")
Patches: 0001-fix-python-script-execution.patch (fix Python script execution on HMDFS)
Dependencies: glib/2.84.0.1 (from conan remote)
Libraries: gstreamer-1.0, gstbase-1.0, gstcontroller-1.0, gstnet-1.0, gstcheck-1.0
Binaries: gst-inspect-1.0, gst-stats-1.0, gst-typefind-1.0, gst-plugin-scanner
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GstreamerConan(ConanFile):
    name = "gstreamer"
    version = "1.28.3"
    description = "GStreamer multimedia framework core library"
    license = "LGPL-2.0-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("glib/2.84.0.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS"), not == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gstreamer/1.28.3 is only supported on Linux and OHOS"
            )

    def generate(self):
        # Generate pkg-config files first so Meson can find dependencies
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        # Meson options for gstreamer
        tc.project_options["nls"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["benchmarks"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["libdw"] = "disabled"
        tc.project_options["bash-completion"] = "disabled"
        tc.project_options["ptp-helper"] = "disabled"
        tc.project_options["gst_parse"] = "false"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()

        # Inject ar/ranlib into meson native/cross files (from glib conanfile.py)
        self._inject_meson_archive_tools()

    def _inject_meson_archive_tools(self):
        """Inject ar and ranlib into Meson native/cross ini files.

        MesonToolchain omits ar/ranlib; this ensures the correct LLVM
        archiver and ranlib from the OHOS SDK are used during static
        archiving steps.
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")

        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            native_file = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(native_file):
                continue
            if not bindir or not os.path.isfile(ar):
                continue
            with open(native_file, encoding="utf-8") as native:
                content = native.read()
            # Skip if ar is already set or [binaries] section is missing
            if "\nar =" in content or "[binaries]" not in content:
                continue
            tools = f"[binaries]\nar = '{ar}'\n"
            if os.path.isfile(ranlib):
                tools += f"ranlib = '{ranlib}'\n"
            with open(native_file, "w", encoding="utf-8") as native:
                native.write(content.replace("[binaries]\n", tools, 1))

    def build(self):
        # Apply all patches declared in conandata.yml (R3)
        apply_conandata_patches(self)

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GStreamer")
        self.cpp_info.set_property("cmake_target_name", "GStreamer::GStreamer")
        self.cpp_info.set_property("pkg_config_name", "gstreamer-1.0")

        # Main gstreamer libraries
        self.cpp_info.libs = [
            "gstreamer-1.0",
            "gstbase-1.0",
            "gstcontroller-1.0",
            "gstnet-1.0",
            "gstcheck-1.0",
        ]

        # Binary directories (gst-inspect-1.0, gst-stats-1.0,
        # gst-typefind-1.0, gst-plugin-scanner)
        self.cpp_info.bindirs = ["bin"]

        # Include path: gstreamer headers are in include/gstreamer-1.0/
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]

        # Express dependency on glib components for pkg-config Requires
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0"]

        # System dependencies
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl", "rt"]
