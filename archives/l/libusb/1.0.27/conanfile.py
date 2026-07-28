#!/usr/bin/env python3
"""Conan recipe for libusb 1.0.27."""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibusbConan(ConanFile):
    name = "libusb"
    version = "1.0.27"
    description = "USB device access library"
    license = "LGPL-2.1-or-later"
    homepage = "https://libusb.info/"
    url = "https://github.com/libusb/libusb"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-udev",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        roots = {self.source_folder, self.build_folder, os.path.dirname(self.build_folder)}
        for root in roots:
            for helper in ("configure", "config.guess", "config.sub"):
                path = os.path.join(root, helper)
                if os.path.isfile(path):
                    os.chmod(path, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.options.shared:
            self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return

        libdir = os.path.join(self.package_folder, "lib")
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
                    check=True,
                )
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["usb-1.0"]
        self.cpp_info.includedirs = [os.path.join("include", "libusb-1.0")]
        self.cpp_info.set_property("cmake_file_name", "libusb-1.0")
        self.cpp_info.set_property("cmake_target_name", "libusb-1.0::libusb-1.0")
        self.cpp_info.set_property("pkg_config_name", "libusb-1.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
