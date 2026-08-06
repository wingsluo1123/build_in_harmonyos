import os
from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

class GstreamerConan(ConanFile):
    name = "gstreamer"
    version = "1.28.3"
    description = "GStreamer core library - multimedia framework"
    license = "LGPL-2.1-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0")
        self.requires("orc/0.4.40")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        from conan.tools.gnu import PkgConfigDeps
        tc = MesonToolchain(self)
        tc.project_options.update({
            "introspection": "disabled",
            "tests": "disabled",
            "examples": "disabled",
            "doc": "disabled",
            "nls": "disabled",
            "ptp-helper": "disabled",
            "bash-completion": "disabled",
            "libunwind": "disabled",
            "libdw": "disabled",
            "check": "disabled",
        })
        tc.generate()
        pc = PkgConfigDeps(self)
        pc.generate()

        # glib2 conan package only provides glib-2.0.pc but gstreamer needs
        # gobject-2.0, gio-2.0, gmodule-2.0, gthread-2.0 as separate pkg-config files
        # Also need to add glib_mkenums/glib_genmarshal variables to glib-2.0.pc
        glib2_info = self.dependencies["glib2"].cpp_info
        glib2_inc = glib2_info.includedirs
        glib2_libdirs = glib2_info.libdirs
        glib2_root = self.dependencies["glib2"].package_folder
        if glib2_root:
            inc_flags = " ".join(f"-I{glib2_root}/{d}" for d in glib2_inc)
            lib_flags = " ".join(f"-L{glib2_root}/{d}" for d in glib2_libdirs)
            libs = " ".join(f"-l{l}" for l in glib2_info.libs)
            sys_libs = " ".join(f"-l{s}" for s in getattr(glib2_info, "system_libs", []))
            for pc_name in ["gobject-2.0", "gio-2.0", "gmodule-2.0", "gmodule-no-export-2.0", "gthread-2.0", "gio-unix-2.0"]:
                pc_content = (
                    f"prefix={glib2_root}\n"
                    f"exec_prefix=${{prefix}}\n"
                    f"libdir=${{prefix}}/lib\n"
                    f"includedir=${{prefix}}/include\n\n"
                    f"Name: {pc_name}\n"
                    f"Description: GLib - {pc_name} (wrapper from conan glib2)\n"
                    f"Version: 2.88.0\n"
                    f"Requires: glib-2.0\n"
                    f"Libs: {lib_flags} {libs} {sys_libs}\n"
                    f"Cflags: {inc_flags}\n"
                )
                pc_path = os.path.join(self.generators_folder, f"{pc_name}.pc")
                with open(pc_path, "w") as f:
                    f.write(pc_content)

            # Add glib_mkenums and glib_genmarshal variables to glib-2.0.pc
            glib_pc_path = os.path.join(self.generators_folder, "glib-2.0.pc")
            glib_mkenums_path = os.path.join(glib2_root, "bin", "glib-mkenums")
            glib_genmarshal_path = os.path.join(glib2_root, "bin", "glib-genmarshal")
            with open(glib_pc_path, "a") as f:
                f.write(f"glib_mkenums={glib_mkenums_path}\n")
                f.write(f"glib_genmarshal={glib_genmarshal_path}\n")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # Use conan components so PkgConfigDeps generates correct .pc files
        # for gstreamer-1.0, gstreamer-base-1.0, etc.
        gst = self.cpp_info.components["gstreamer"]
        gst.set_property("pkg_config_name", "gstreamer-1.0")
        gst.libs = ["gstreamer-1.0"]
        gst.includedirs = ["include/gstreamer-1.0"]
        gst.requires = ["glib2::glib2", "orc::orc"]

        base = self.cpp_info.components["base"]
        base.set_property("pkg_config_name", "gstreamer-base-1.0")
        base.libs = ["gstbase-1.0"]
        base.includedirs = ["include/gstreamer-1.0"]
        base.requires = ["gstreamer"]

        controller = self.cpp_info.components["controller"]
        controller.set_property("pkg_config_name", "gstreamer-controller-1.0")
        controller.libs = ["gstcontroller-1.0"]
        controller.includedirs = ["include/gstreamer-1.0"]
        controller.requires = ["gstreamer"]

        net = self.cpp_info.components["net"]
        net.set_property("pkg_config_name", "gstreamer-net-1.0")
        net.libs = ["gstnet-1.0"]
        net.includedirs = ["include/gstreamer-1.0"]
        net.requires = ["gstreamer"]
