from conan import ConanFile
from conan.tools.files import (
    collect_libs, get, apply_conandata_patches, export_conandata_patches
)
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class ApacheArrowGlibConan(ConanFile):
    name = "apache-arrow-glib"
    version = "homebrew"
    description = "GLib bindings for Apache Arrow"
    license = "Apache-2.0"
    homepage = "https://arrow.apache.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("apache-arrow/24.0.0")
        self.requires("glib/2.84.0")

    def layout(self):
        # 源码是 Apache Arrow 完整 tarball，arrow-glib 构建入口在 c_glib/ 子目录
        basic_layout(self, src_folder="c_glib")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 最小化构建：关闭文档和 Vala 绑定，降低依赖要求
        tc.project_options["doc"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["vapi"] = "false"
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
        self.cpp_info.libs = collect_libs(self)

        import glob, os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if pcs:
            pkg_name = os.path.splitext(os.path.basename(pcs[0]))[0]
            self.cpp_info.set_property("pkg_config_name", pkg_name)

        self.cpp_info.set_property("cmake_file_name", "ArrowGLib")
        self.cpp_info.set_property("cmake_target_name", "ArrowGLib::ArrowGLib")

        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
