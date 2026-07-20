import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GlibConan(ConanFile):
    name = "glib"
    version = "2.84.0"
    description = "Core application building blocks for libraries and applications"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gtk.org/"
    url = "https://gitlab.gnome.org/GNOME/glib"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gettext/0.22.5")
        self.requires("libffi/3.4.4")
        self.requires("pcre2/10.45")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        staged = os.path.expanduser("~/glib-2.84.0.tar.xz")
        source = self.conan_data["sources"]
        if os.path.isfile(staged):
            source = {"url": f"file://{staged}", "sha256": source["sha256"]}
        get(self, **source, strip_root=True)

    def generate(self):
        if self.settings.os == "OHOS":
            bin_path = "/data/service/hnp/bin"
            self.buildenv_info.prepend_path("PATH", bin_path)
            self.buildenv_info.define("AR", os.path.join(bin_path, "llvm-ar"))
            self.buildenv_info.define("STRIP", os.path.join(bin_path, "llvm-strip"))

        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property("gettext", "pkg_config_name", "intl")
        pkg_config.set_property("pcre2", "pkg_config_name", "libpcre2-8")
        pkg_config.generate()

        toolchain = MesonToolchain(self)
        if self.settings.os == "OHOS":
            toolchain.ar = "/data/service/hnp/bin/llvm-ar"
            toolchain.strip = "/data/service/hnp/bin/llvm-strip"
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "static"
        toolchain.project_options["selinux"] = "disabled"
        toolchain.project_options["libmount"] = "disabled"
        toolchain.project_options["man-pages"] = "disabled"
        toolchain.project_options["documentation"] = False
        toolchain.project_options["dtrace"] = "disabled"
        toolchain.project_options["systemtap"] = "disabled"
        toolchain.project_options["sysprof"] = "disabled"
        toolchain.project_options["tests"] = False
        toolchain.project_options["installed_tests"] = False
        toolchain.project_options["nls"] = "disabled"
        toolchain.generate()
        if self.settings.os == "OHOS":
            gettext = self.dependencies["gettext"].cpp_info
            include_args = [f"-I{path}" for path in gettext.includedirs]
            link_args = [f"-L{path}" for path in gettext.libdirs]
            native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
            with open(native_file, encoding="utf-8") as stream:
                content = stream.read()
            content = content.replace(
                "c_args = [] + preprocessor_definitions",
                f"c_args = {include_args!r} + preprocessor_definitions",
            )
            content = content.replace(
                "c_link_args = []",
                f"c_link_args = {link_args!r}",
            )
            content = content.replace(
                "cpp_args = ['-stdlib=libc++'] + preprocessor_definitions",
                f"cpp_args = ['-stdlib=libc++'] + {include_args!r} + preprocessor_definitions",
            )
            content = content.replace(
                "cpp_link_args = ['-stdlib=libc++']",
                f"cpp_link_args = ['-stdlib=libc++'] + {link_args!r}",
            )
            with open(native_file, "w", encoding="utf-8") as stream:
                stream.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "glib")
        self.cpp_info.set_property("cmake_target_name", "glib::glib")
        self.cpp_info.set_property("pkg_config_name", "glib-2.0")
        self.cpp_info.includedirs = ["include/glib-2.0", "lib/glib-2.0/include"]
        self.cpp_info.libs = [
            "gio-2.0",
            "gobject-2.0",
            "gmodule-2.0",
            "glib-2.0",
        ]
        self.cpp_info.requires = ["gettext::gettext", "libffi::libffi", "pcre2::pcre2", "zlib::zlib"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
