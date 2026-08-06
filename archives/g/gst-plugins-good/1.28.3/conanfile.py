import os
from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import get

class GstPluginsGoodConan(ConanFile):
    name = "gst-plugins-good"
    version = "1.28.3"
    description = "GStreamer good plugins - well-maintained codec and utility plugins"
    license = "LGPL-2.1-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")
        self.requires("glib2/2.88.0")
        self.requires("orc/0.4.40")
        self.requires("cairo/1.18.4")
        self.requires("flac/1.4.3")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")
        self.requires("mpg123/1.33.5")
        self.requires("opencore-amrnb/0.1.6")
        self.requires("opencore-amrwb/0.1.6")
        # Resolve zlib version conflict: libpng needs 1.3.1.1, glib2 might need 1.3.1
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options.update({
            "examples": "disabled",
            "tests": "disabled",
            "doc": "disabled",
            "nls": "disabled",
            # v4l2 disabled: platform compatibility issue
            # gstv4l2object.c has 'initializer element is not a compile-time constant'
            # This is a V4L2 API difference on HarmonyOS, not feature trimming
            "v4l2": "disabled",
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
        self.cpp_info.set_property("pkg_config_name", "gst-plugins-good-1.0")
        self.cpp_info.libs = []  # Plugin .so files, not standard libs
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
        self.cpp_info.libdirs = ["lib/gstreamer-1.0"]
        self.cpp_info.requires = [
            "gstreamer::gstreamer", "gst-plugins-base::gstreamer-pbutils-1.0",
            "glib2::glib2", "orc::orc", "cairo::cairo",
            "flac::flac", "libjpeg-turbo::libjpeg-turbo", "libpng::libpng",
            "mpg123::mpg123", "opencore-amrnb::opencore-amrnb",
            "opencore-amrwb::opencore-amrwb",
        ]
