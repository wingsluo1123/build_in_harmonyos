import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AprConan(ConanFile):
    name = "apr"
    version = "1.7.6"
    description = "Apache Portable Runtime Library"
    license = "Apache-2.0"
    homepage = "https://apr.apache.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Fix apr-1-config to use correct prefix (DESTDIR install leaves prefix=/)
        apr_config = os.path.join(self.package_folder, "bin", "apr-1-config")
        if os.path.exists(apr_config):
            replace_in_file(self, apr_config, "prefix=\"/\"", f"prefix=\"{self.package_folder}\"")
        # Fix apr_rules.mk build directory paths
        rules_mk = os.path.join(self.package_folder, "build-1", "apr_rules.mk")
        if os.path.exists(rules_mk):
            builddir = f"{self.package_folder}/build-1"
            replace_in_file(self, rules_mk, "apr_builddir=//build-1", f"apr_builddir={builddir}")
            replace_in_file(self, rules_mk, "apr_builders=//build-1", f"apr_builders={builddir}")
            replace_in_file(self, rules_mk, "top_builddir=//build-1", f"top_builddir={builddir}")

    def package_info(self):
        self.cpp_info.libs = ["apr-1"]
        # Expose build directory for downstream packages (e.g. apr-util needs apr_rules.mk)
        builddir = os.path.join(self.package_folder, "build-1")
        if os.path.isdir(builddir):
            self.cpp_info.builddirs = [builddir]
