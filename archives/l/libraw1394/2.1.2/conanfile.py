import os
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout

class Libraw1394Conan(ConanFile):
    name = "libraw1394"
    version = "2.1.2"
    description = "Linux IEEE 1394 (FireWire) raw access library"
    license = "LGPL-2.1"
    homepage = "https://sourceforge.net/projects/linux1394/"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The bundled config.sub predates the OHOS triplet. Use the compatible
        # Linux triplet while Conan supplies the OHOS clang toolchain.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # HarmonyOS shared storage rejects configure's umask-077 temp files.
        configure = os.path.join(self.source_folder, "configure")
        self.run(f"sed -i 's|(umask 077 && mktemp -d \"./confXXXXXX\")|mktemp -d \"./confXXXXXX\"|g' \"{configure}\"")
        self.run(f"sed -i 's|(umask 077 && mkdir \"$tmp\")|mkdir \"$tmp\"|g' \"{configure}\"")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING.LIB", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["raw1394"]
        self.cpp_info.set_property("pkg_config_name", "libraw1394")
