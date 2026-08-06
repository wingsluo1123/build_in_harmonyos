import os
from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import get

class GstPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    version = "1.28.3"
    description = "GStreamer base plugins - core codec and utility plugins"
    license = "LGPL-2.1-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("glib2/2.88.0")
        self.requires("orc/0.4.40")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options.update({
            "gl": "disabled",
            "introspection": "disabled",
            "tests": "disabled",
            "examples": "disabled",
            "doc": "disabled",
            "nls": "disabled",
            "iso-codes": "disabled",
        })
        tc.generate()
        pc = PkgConfigDeps(self)
        pc.generate()

        # glib2 conan package only provides glib-2.0.pc but gstreamer needs
        # gobject-2.0, gio-2.0, gmodule-2.0, gthread-2.0 as separate pkg-config files
        glib2_root = self.dependencies["glib2"].package_folder
        if glib2_root:
            libs = "-lglib-2.0 -lgobject-2.0 -lgio-2.0 -lgmodule-2.0 -lgthread-2.0 -lffi -lintl -lm -lpthread -ldl -lrt"
            inc_flags = "-I${includedir} -I${includedir1}"
            for pc_name in ["gobject-2.0", "gio-2.0", "gmodule-2.0", "gmodule-no-export-2.0", "gthread-2.0", "gio-unix-2.0"]:
                extra_vars = ""
                if pc_name == "gio-2.0":
                    extra_vars = "giomoduledir=${libdir}/gio/modules\nschemasdir=${prefix}/share/glib-2.0/schemas\n"
                pc_content = (
                    f"prefix={glib2_root}\n"
                    f"exec_prefix=${{prefix}}\n"
                    f"libdir=${{prefix}}/lib\n"
                    f"includedir=${{prefix}}/include/glib-2.0\n"
                    f"includedir1=${{prefix}}/lib/glib-2.0/include\n\n"
                    f"Name: {pc_name}\n"
                    f"Description: GLib - {pc_name} (wrapper from conan glib2)\n"
                    f"Version: 2.88.0\n"
                    f"Requires: glib-2.0\n"
                    f"Libs: -L${{libdir}} {libs}\n"
                    f"Cflags: {inc_flags}\n"
                    f"{extra_vars}"
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
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # Use components so PkgConfigDeps generates correct .pc files
        # for gstreamer-pbutils-1.0, gstreamer-audio-1.0, etc.
        components = {
            "gstreamer-app-1.0": "gstapp-1.0",
            "gstreamer-audio-1.0": "gstaudio-1.0",
            "gstreamer-fft-1.0": "gstfft-1.0",
            "gstreamer-pbutils-1.0": "gstpbutils-1.0",
            "gstreamer-riff-1.0": "gstriff-1.0",
            "gstreamer-rtp-1.0": "gstrtp-1.0",
            "gstreamer-rtsp-1.0": "gstrtsp-1.0",
            "gstreamer-sdp-1.0": "gstsdp-1.0",
            "gstreamer-tag-1.0": "gsttag-1.0",
            "gstreamer-video-1.0": "gstvideo-1.0",
            "gstreamer-allocators-1.0": "gstallocators-1.0",
        }
        for pc_name, lib_name in components.items():
            comp = self.cpp_info.components[pc_name]
            comp.set_property("pkg_config_name", pc_name)
            comp.libs = [lib_name]
            comp.includedirs = ["include/gstreamer-1.0"]
            comp.requires = ["gstreamer::gstreamer", "glib2::glib2", "orc::orc"]
