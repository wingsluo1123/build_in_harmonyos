#!/usr/bin/env python3
"""Conan recipe for VapourSynth 74."""

import glob
import os
import shutil
import subprocess

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
        self._inject_meson_pkg_config()
        self._wrap_nonexecutable_meson_compilers()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING.LESSER", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        Meson(self).install()
        self._ensure_unversioned_shared_libraries()
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

    def _inject_meson_pkg_config(self):
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pkg_config:
            return

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content:
            return
        if "\npkg-config =" not in content and "\npkgconfig =" not in content:
            insertion = "[binaries]\npkg-config = '{}'\n".format(str(pkg_config).replace("\\", "/"))
            content = content.replace("[binaries]\n", insertion, 1)
        if "pkg_config_path =" not in content and "[built-in options]" in content:
            pc_path = self.generators_folder.replace("\\", "/")
            content = content.replace(
                "[built-in options]\n",
                "[built-in options]\npkg_config_path = ['{}']\n".format(pc_path),
                1,
            )
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _wrap_nonexecutable_meson_compilers(self):
        if self.settings.os != "OHOS":
            return
        shell = "/system/bin/sh"
        if not os.path.exists(shell):
            return

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            lines = handle.readlines()

        changed = False
        for idx, line in enumerate(lines):
            stripped = line.strip()
            for key in ("c", "cpp"):
                prefix = "{} = '".format(key)
                if not stripped.startswith(prefix) or not stripped.endswith("'"):
                    continue
                compiler = stripped[len(prefix):-1]
                if os.path.exists(compiler) and not self._can_execute(compiler):
                    lines[idx] = "{} = ['{}', '{}']\n".format(key, shell, compiler)
                    changed = True

        if changed:
            with open(native_file, "w", encoding="utf-8") as handle:
                handle.writelines(lines)

    @staticmethod
    def _can_execute(path):
        try:
            subprocess.run(
                [path, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return True
        except OSError:
            return False

    def _ensure_unversioned_shared_libraries(self):
        if not self.options.shared:
            return
        libdir = os.path.join(self.package_folder, "lib")
        unversioned = os.path.join(libdir, "libvapoursynth.so")
        versioned = os.path.join(libdir, "libvapoursynth.so.4")
        if os.path.exists(versioned) and not os.path.exists(unversioned):
            shutil.copy2(versioned, unversioned)

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
