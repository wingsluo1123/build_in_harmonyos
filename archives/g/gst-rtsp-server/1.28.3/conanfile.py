from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, rmdir, rm, replace_in_file, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
import os


class GstRtspServerConan(ConanFile):
    name = "gst-rtsp-server"
    version = "1.28.3"
    description = "GStreamer RTSP Server library"
    license = "LGPL-2.0-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("gstreamer/1.28.3", transitive_headers=True, transitive_libs=True)
        self.requires("gst-plugins-base/1.28.3", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        env = Environment()
        env.define("AR", "/data/service/hnp/bin/llvm-ar")
        env.define("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        env.define("NM", "/data/service/hnp/bin/llvm-nm")
        envvars = env.vars(self)
        envvars.save_script("conanbuildenv_extra")
        VirtualBuildEnv(self).generate()
        pkg_config_deps = PkgConfigDeps(self)
        pkg_config_deps.generate()

        # Add missing pkg-config variables for glib components
        glib_pkg_folder = self.dependencies["glib"].package_folder
        glib_bin = f"{glib_pkg_folder}/bin"
        glib_lib = f"{glib_pkg_folder}/lib"
        for pc_name, extra_vars in [
            ("glib-2.0.pc", {"glib_mkenums": f"{glib_bin}/glib-mkenums", "glib_genmarshal": f"{glib_bin}/glib-genmarshal"}),
            ("gobject-2.0.pc", {"glib_mkenums": f"{glib_bin}/glib-mkenums", "glib_genmarshal": f"{glib_bin}/glib-genmarshal"}),
            ("gio-2.0.pc", {"giomoduledir": f"{glib_lib}/gio/modules", "glib_mkenums": f"{glib_bin}/glib-mkenums"}),
            ("gmodule-2.0.pc", {"glib_mkenums": f"{glib_bin}/glib-mkenums"}),
        ]:
            pc_path = os.path.join(self.generators_folder, pc_name)
            if os.path.exists(pc_path):
                with open(pc_path, "a") as f:
                    f.write("\n")
                    for var, val in extra_vars.items():
                        f.write(f"{var}={val}\n")

        tc = MesonToolchain(self)
        tc.project_options["rtspclientsink"] = "enabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["glib_assert"] = "false"
        tc.project_options["glib_checks"] = "false"
        tc.generate()

    def build(self):
        # Compile g_libintl wrapper (glib has undefined i18n symbols)
        wrapper_src = os.path.join(self.source_folder, "g_libintl_wrapper.c")
        save(self, wrapper_src, '''#include <libintl.h>
const char *g_libintl_bindtextdomain(const char *d, const char *dir) { return bindtextdomain(d, dir); }
const char *g_libintl_bind_textdomain_codeset(const char *d, const char *c) { return bind_textdomain_codeset(d, c); }
const char *g_libintl_dcgettext(const char *d, const char *m, int cat) { return dcgettext(d, m, cat); }
const char *g_libintl_dgettext(const char *d, const char *m) { return dgettext(d, m); }
const char *g_libintl_dngettext(const char *d, const char *m1, const char *m2, unsigned long n) { return dngettext(d, m1, m2, n); }
const char *g_libintl_gettext(const char *m) { return gettext(m); }
const char *g_libintl_textdomain(const char *d) { return textdomain(d); }
''')
        wrapper_obj = os.path.join(self.build_folder, "g_libintl_wrapper.o")
        self.run(f'clang -c -I/data/service/hnp/gettext.org/gettext_0.26/include -fPIC {wrapper_src} -o {wrapper_obj}')

        # Add wrapper + libintl to global link args
        replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
            "gst_version = meson.project_version()",
            f"add_global_link_arguments(['{wrapper_obj}', '-L/data/service/hnp/gettext.org/gettext_0.26/lib', '-lintl'], language: 'c')\ngst_version = meson.project_version()")

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        gst_plugin_path = os.path.join(self.package_folder, "lib", "gstreamer-1.0")
        inc = os.path.join("include", "gstreamer-1.0")

        self.cpp_info.components["gstreamer-rtsp-server-1.0"].set_property("pkg_config_name", "gstreamer-rtsp-server-1.0")
        self.cpp_info.components["gstreamer-rtsp-server-1.0"].libs = ["gstrtspserver-1.0"]
        self.cpp_info.components["gstreamer-rtsp-server-1.0"].includedirs = [inc]
        self.cpp_info.components["gstreamer-rtsp-server-1.0"].requires = [
            "gstreamer::gstreamer-1.0", "gstreamer::gstreamer-base-1.0",
            "gstreamer::gstreamer-net-1.0",
            "gst-plugins-base::gstreamer-rtsp-1.0", "gst-plugins-base::gstreamer-sdp-1.0",
            "gst-plugins-base::gstreamer-rtp-1.0", "gst-plugins-base::gstreamer-app-1.0",
            "gst-plugins-base::gstreamer-pbutils-1.0",
            "glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.components["gstreamer-rtsp-server-1.0"].system_libs = ["m"]

        if self.options.shared:
            self.runenv_info.define_path("GST_PLUGIN_PATH", gst_plugin_path)
