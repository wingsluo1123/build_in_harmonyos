#!/usr/bin/env python3
"""Conan recipe for gstreamer 1.28.3 on OpenHarmony."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class GstreamerConan(ConanFile):
    name = "gstreamer"
    version = "1.28.3"
    description = "GStreamer core library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
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
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["nls"] = "disabled"
        tc.project_options["ptp-helper"] = "disabled"
        tc.project_options["bash-completion"] = "disabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["libdw"] = "disabled"
        tc.project_options["gst_parse"] = "false"

        # Build pkg-config search path
        # The conan glib package's .pc files use prefix=/ causing wrong paths.
        # Fix: copy glib's .pc files to generators folder with corrected prefix.
        pkg_config_paths = [self.generators_folder]

        # Fix conan glib .pc files by copying with correct prefix
        if "glib" in self.dependencies:
            glib_pkg = self.dependencies["glib"].package_folder
            glib_pc_dir = os.path.join(glib_pkg, "lib", "pkgconfig")
            if os.path.isdir(glib_pc_dir):
                for pc_file in os.listdir(glib_pc_dir):
                    if pc_file.endswith(".pc"):
                        src = os.path.join(glib_pc_dir, pc_file)
                        dst = os.path.join(self.generators_folder, pc_file)
                        with open(src) as f:
                            content = f.read()
                        # Fix prefix=/ to actual package path
                        content = content.replace("prefix=/", f"prefix={glib_pkg}")
                        with open(dst, "w") as f:
                            f.write(content)

        # Also fix pcre2 and libffi .pc files
        for dep_name in ["pcre2", "libffi"]:
            if dep_name in self.dependencies:
                dep_pkg = self.dependencies[dep_name].package_folder
                dep_pc_dir = os.path.join(dep_pkg, "lib", "pkgconfig")
                if os.path.isdir(dep_pc_dir):
                    for pc_file in os.listdir(dep_pc_dir):
                        if pc_file.endswith(".pc"):
                            src = os.path.join(dep_pc_dir, pc_file)
                            dst = os.path.join(self.generators_folder, pc_file)
                            if not os.path.exists(dst):
                                with open(src) as f:
                                    content = f.read()
                                content = content.replace("prefix=/", f"prefix={dep_pkg}")
                                with open(dst, "w") as f:
                                    f.write(content)

        # Also add system paths as fallback (for system-installed glib)
        sys_pc = os.environ.get("PKG_CONFIG_PATH", "")
        system_paths = sys_pc.split(":") if sys_pc else []
        for sp in system_paths:
            if sp and os.path.isdir(sp):
                pkg_config_paths.append(sp)

        tc.pkg_config_path = ":".join(pkg_config_paths)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["gstreamer-1.0", "gstbase-1.0", "gstcontroller-1.0", "gstnet-1.0"]
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
