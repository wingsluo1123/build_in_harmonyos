#!/usr/bin/env python3
"""Conan recipe — gstreamer 1.28.3 (meson)

Core GStreamer multimedia framework library.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class GStreamerConan(ConanFile):
    name = "gstreamer"
    version = "1.28.3"
    description = "GStreamer — open source multimedia framework"
    license = "LGPL-2.1-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
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
        tc.generate()

        pkg = PkgConfigDeps(self)
        pkg.generate()

        # Generate missing pkg-config files that meson needs
        # (Conan's PkgConfigDeps doesn't generate all glib sub-components)
        self._generate_missing_pc_files()

    def _generate_missing_pc_files(self):
        """Generate pkg-config files that Conan's PkgConfigDeps doesn't create."""
        import os
        from conan.tools.files import save

        gen_dir = self.generates_folder

        # Find glib's package path from the glib-2.0.pc file
        glib_pc = os.path.join(gen_dir, "glib-2.0.pc")
        if not os.path.exists(glib_pc):
            return

        with open(glib_pc) as f:
            content = f.read()

        # Extract prefix from glib-2.0.pc
        prefix = ""
        for line in content.split("\n"):
            if line.startswith("prefix="):
                prefix = line.split("=", 1)[1]
                break

        if not prefix:
            return

        libdir = f"{prefix}/lib"
        includedir = f"{prefix}/include/glib-2.0"
        includedir2 = f"{prefix}/lib/glib-2.0/include"

        # gmodule-no-export-2.0.pc (meson dependency)
        gmodule_no_export = f"""prefix={prefix}
libdir={libdir}
includedir={includedir}
includedir2={includedir2}

Name: gmodule-no-export-2.0
Description: GObject module support (no export)
Version: 2.84.0.1
Requires: glib-2.0
Libs: -L{libdir} -lgmodule-2.0
Cflags: -I{includedir} -I{includedir2}
"""
        save(self, "gmodule-no-export-2.0.pc", gmodule_no_export)

        # gio-unix-2.0.pc (needed by some meson projects)
        gio_unix = f"""prefix={prefix}
libdir={libdir}
includedir={includedir}
includedir3={prefix}/include/gio-unix-2.0

Name: gio-unix-2.0
Description: GIO Unix support
Version: 2.84.0.1
Requires: glib-2.0 gio-2.0
Cflags: -I{prefix}/include/gio-unix-2.0
"""
        save(self, "gio-unix-2.0.pc", gio_unix)

        # Add glib_mkenums to glib-2.0.pc if missing
        if "glib_mkenums" not in content:
            with open(glib_pc, "a") as f:
                f.write(f"\nglib_mkenums={prefix}/bin/glib-mkenums\n")

        # Add -lintl to Libs lines in all glib .pc files
        for pc_file in os.listdir(gen_dir):
            if pc_file.endswith(".pc") and "glib" in pc_file or "gio" in pc_file or "gmodule" in pc_file or "gobject" in pc_file or "gthread" in pc_file:
                pc_path = os.path.join(gen_dir, pc_file)
                with open(pc_path) as f:
                    pc_content = f.read()
                if "-lintl" not in pc_content and "Libs:" in pc_content:
                    pc_content = pc_content.replace("Libs: ", "Libs: -lintl ")
                    with open(pc_path, "w") as f:
                        f.write(pc_content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.compile()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["gstreamer-1.0"]
        self.cpp_info.set_property("pkg_config_name", "gstreamer-1.0")
