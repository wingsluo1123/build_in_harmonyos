#!/usr/bin/env python3
"""Conan recipe for VapourSynth 74."""

import glob
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class VapoursynthConan(ConanFile):
    name = "vapoursynth"
    version = "74"
    description = "A video processing framework with simplicity in mind"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.vapoursynth.com/"
    url = "https://github.com/vapoursynth/vapoursynth"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "vsscript": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "vsscript": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("zimg/3.0.6")

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["enable_core"] = True
        tc.project_options["enable_guard_pattern"] = False
        tc.project_options["enable_x86_asm"] = False
        tc.project_options["enable_vsscript"] = bool(self.options.vsscript)
        tc.project_options["enable_vspipe"] = False
        tc.project_options["enable_python_module"] = False
        tc.project_options["build_wheel"] = False
        tc.generate()
        self._inject_meson_archiver()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING.LESSER", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        Meson(self).install()
        self._sign_shared_libraries()

    def package_info(self):
        self.cpp_info.libs = ["vapoursynth"]
        if self.options.vsscript:
            self.cpp_info.libs.append("vsscript")
        self.cpp_info.includedirs = ["include/vapoursynth", "include"]
        self.cpp_info.set_property("cmake_file_name", "vapoursynth")
        self.cpp_info.set_property("cmake_target_name", "vapoursynth::vapoursynth")
        self.cpp_info.set_property("pkg_config_name", "vapoursynth")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

        libdir = os.path.join(self.package_folder, "lib")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)

    def _inject_meson_archiver(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        insertion = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib:
            insertion += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insertion, 1))

    def _sign_shared_libraries(self):
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.exists(objcopy) or not os.path.exists(signer):
            return
        for shared_lib in glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True):
            self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, shared_lib))
            self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, shared_lib, shared_lib))
