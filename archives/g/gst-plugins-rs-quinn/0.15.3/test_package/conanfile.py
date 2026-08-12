#!/usr/bin/env python3
"""Conan test_package — gst-plugins-rs-quinn 0.15.3 (ELF symbol verification).

R34: the L1 test must actually exercise the packaged artifact. dlopen()
is unusable on OHOS for plugins whose transitive C deps (gstreamer) live
outside the musl ldso namespace (E186), so test.c parses the packaged
libgstquinn.so ELF directly and asserts its GStreamer plugin entry points
(gst_plugin_quinn_get_desc / gst_plugin_quinn_register) are exported.

CI worker caveat (2026-08-11): CMake configure fails because the worker's
lld linker cannot load libxml2.so.16 (broken indirect dep). We bypass
CMake entirely and compile test.c with the conan-provided compiler env,
linking only against libdl (no linker involvement beyond -ldl).
"""
import os
import shutil

from conan import ConanFile


class GstPluginsRsQuinnTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile test.c directly with the conan compiler env, bypassing
        # CMake (CI worker's lld is broken: missing libxml2.so.16).
        cc = self.conf.get("tools.build:compiler_executables", {}).get("c") \
            or shutil.which("clang") or shutil.which("cc") or "clang"
        test_c = os.path.join(self.source_folder, "test.c")
        out_bin = os.path.join(self.build_folder, "test_gst-plugins-rs-quinn")
        self.run(f'{cc} -O2 -o {out_bin} {test_c} -ldl', env="conanbuild")

    def test(self):
        dep = self.dependencies["gst-plugins-rs-quinn"]
        pkg_root = dep.package_folder
        plugin = os.path.join(pkg_root, "lib", "gstreamer-1.0", "libgstquinn.so")
        if not os.path.isfile(plugin):
            self.output.error(f"packaged plugin not found: {plugin}")
            raise SystemExit(1)

        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gst-plugins-rs-quinn")
        self.run(f"{bin_path} {plugin}")
