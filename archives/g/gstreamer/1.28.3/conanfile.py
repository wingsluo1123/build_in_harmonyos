from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, rmdir, rm, replace_in_file
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
import os


class GstreamerConan(ConanFile):
    name = "gstreamer"
    version = "1.28.3"
    description = "GStreamer is a development framework for creating applications like media players, video editors, streaming media broadcasters and so on"
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
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    # meson 1.11.1 and pkg-config 0.29.2 are installed system-wide

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

        # Add glib_mkenums and glib_genmarshal variables to glib-2.0.pc
        # Required by meson gnome module for enum/marshal generation
        glib_pkg_folder = self.dependencies["glib"].package_folder
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.exists(glib_pc):
            with open(glib_pc, "a") as f:
                f.write(f"\nglib_mkenums={glib_pkg_folder}/bin/glib-mkenums\n")
                f.write(f"glib_genmarshal={glib_pkg_folder}/bin/glib-genmarshal\n")

        tc = MesonToolchain(self)
        tc.project_options["tools"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["benchmarks"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["nls"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["libdw"] = "disabled"
        tc.project_options["bash-completion"] = "disabled"
        tc.project_options["ptp-helper"] = "disabled"
        tc.project_options["gst_parse"] = "false"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # gmodule-no-export-2.0 not available in OHOS glib recipe, use gmodule-2.0
        replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
            "gmodule_dep = dependency('gmodule-no-export-2.0')",
            "gmodule_dep = dependency('gmodule-2.0')")
        # gio-unix-2.0 not available in OHOS glib recipe, make it optional
        replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
            "dependency('gio-unix-2.0')",
            "dependency('gio-unix-2.0', required: false)")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "gstreamer-1.0", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        gst_plugin_path = os.path.join(self.package_folder, "lib", "gstreamer-1.0")

        self.cpp_info.components["gstreamer-1.0"].set_property("pkg_config_name", "gstreamer-1.0")
        self.cpp_info.components["gstreamer-1.0"].requires = ["glib::glib-2.0", "glib::gobject-2.0"]
        if not self.options.shared:
            self.cpp_info.components["gstreamer-1.0"].requires.append("glib::gmodule-2.0")
            self.cpp_info.components["gstreamer-1.0"].defines.append("GST_STATIC_COMPILATION")
        self.cpp_info.components["gstreamer-1.0"].libs = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.components["gstreamer-1.0"].system_libs = ["m", "dl"]

        self.cpp_info.components["gstreamer-base-1.0"].set_property("pkg_config_name", "gstreamer-base-1.0")
        self.cpp_info.components["gstreamer-base-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-base-1.0"].libs = ["gstbase-1.0"]
        self.cpp_info.components["gstreamer-base-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]

        self.cpp_info.components["gstreamer-controller-1.0"].set_property("pkg_config_name", "gstreamer-controller-1.0")
        self.cpp_info.components["gstreamer-controller-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-controller-1.0"].libs = ["gstcontroller-1.0"]
        self.cpp_info.components["gstreamer-controller-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.components["gstreamer-controller-1.0"].system_libs = ["m"]

        self.cpp_info.components["gstreamer-net-1.0"].set_property("pkg_config_name", "gstreamer-net-1.0")
        self.cpp_info.components["gstreamer-net-1.0"].requires = ["gstreamer-1.0", "glib::gio-2.0"]
        self.cpp_info.components["gstreamer-net-1.0"].libs = ["gstnet-1.0"]
        self.cpp_info.components["gstreamer-net-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]

        self.cpp_info.components["gstreamer-check-1.0"].set_property("pkg_config_name", "gstreamer-check-1.0")
        self.cpp_info.components["gstreamer-check-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-check-1.0"].libs = ["gstcheck-1.0"]
        self.cpp_info.components["gstreamer-check-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.components["gstreamer-check-1.0"].system_libs = ["rt", "m"]

        if self.options.shared:
            self.runenv_info.define_path("GST_PLUGIN_PATH", gst_plugin_path)
        gst_plugin_scanner = os.path.join(self.package_folder, "bin", "gstreamer-1.0", "gst-plugin-scanner")
        self.runenv_info.define_path("GSTREAMER_ROOT", self.package_folder)
        self.runenv_info.define_path("GST_PLUGIN_SCANNER", gst_plugin_scanner)
