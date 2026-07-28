#!/usr/bin/env python3
"""Conan recipe for libusb 1.0.27."""
import os
import shlex
import shutil
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
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def _configure_args(self):
        args = []
        if str(self.settings.os) == "OHOS":
            args.extend([
                "--build=aarch64-unknown-linux-musl",
                "--host=aarch64-unknown-linux-musl",
            ])
        args.extend([
            "--disable-dependency-tracking",
            "--disable-udev",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        return args

    def build(self):
        apply_conandata_patches(self)
        roots = {self.source_folder, self.build_folder, os.path.dirname(self.build_folder)}
        for root in roots:
            for helper in ("configure", "config.guess", "config.sub", "install-sh"):
                path = os.path.join(root, helper)
                if os.path.isfile(path):
                    os.chmod(path, 0o755)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            ohos_build_folder = self._prepare_ohos_build_folder()
            self._configure(ohos_build_folder)
            self._use_system_install_helper(ohos_build_folder)
            self._make(ohos_build_folder, args=["-j1"])
        else:
            autotools.configure()
            autotools.make(args=["-j1"])

    def _prepare_ohos_build_folder(self):
        build_folder = self._ohos_build_folder()
        shutil.rmtree(build_folder, ignore_errors=True)
        os.makedirs(build_folder, exist_ok=True)
        return build_folder

    def _ohos_build_folder(self):
        token = os.path.basename(os.path.dirname(os.path.dirname(self.build_folder)))
        root = os.path.join(os.path.expanduser("~"), ".conan-ohos-build")
        return os.path.join(root, f"{self.name}-{self.version}-{token}")

    def _configure(self, build_folder):
        shell = self._ohos_shell()
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(shlex.quote(arg) for arg in self._configure_args())
        command = (
            f'TMPDIR="{build_folder}" CONFIG_SHELL="{shell}" SHELL="{shell}" '
            f'"{shell}" "{configure}" {args}'
        )
        self.run(command.strip(), cwd=build_folder)

    def _make(self, build_folder, target=None, args=None):
        make = self.conf.get("tools.gnu:make_program", default="make")
        command = " ".join(part for part in ([f'"{make}"', target] + (args or [])) if part)
        command = f'TMPDIR="{build_folder}" SHELL="{self._ohos_shell()}" {command}'
        self.run(command, cwd=build_folder)

    def _use_system_install_helper(self, build_folder):
        for root, _, files in os.walk(build_folder):
            if "Makefile" not in files:
                continue
            makefile = os.path.join(root, "Makefile")
            with open(makefile, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            fixed_lines = []
            for line in lines:
                if line.startswith("install_sh = "):
                    line = "install_sh = /system/bin/install\n"
                elif line.startswith("MKDIR_P = "):
                    line = "MKDIR_P = /system/bin/install -d\n"
                fixed_lines.append(line)
            with open(makefile, "w", encoding="utf-8", newline="") as handle:
                handle.writelines(fixed_lines)

    def _ohos_shell(self):
        return "/system/bin/sh" if os.path.isfile("/system/bin/sh") else "/bin/sh"

    def package(self):
        if str(self.settings.os) == "OHOS":
            self._make(
                self._ohos_build_folder(),
                target="install",
                args=[f'DESTDIR="{self.package_folder}"', "prefix="],
            )
        else:
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
