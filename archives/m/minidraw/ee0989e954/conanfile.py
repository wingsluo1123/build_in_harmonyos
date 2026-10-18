#!/usr/bin/env python3
"""Conan recipe — minidraw ee0989e954 (single-header / header-only).

minidraw is a single-file path-based 2D graphics library written in C by
David Reid (mackron). The public API is consumed by including "minidraw.h"
and adding #define MINIDRAW_IMPLEMENTATION to exactly one translation unit.
The upstream Cairo/Pango rendering backend is not required on HarmonyOS PC:
the core UTF-8/UTF-16/UTF-32 text and path APIs are backend-independent and
compile cleanly with the OHOS aarch64 clang toolchain. No library artifact is
shipped — consumers compile the implementation themselves.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class MinidrawConan(ConanFile):
    name = "minidraw"
    version = "ee0989e954"
    description = (
        "A single-file path-based 2D graphics library with Unicode text "
        "itemization, shaping and placement. Header-only, MIT-0/Public Domain."
    )
    homepage = "https://github.com/mackron/minidraw"
    license = "Unlicense OR MIT-0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("graphics", "2d", "text", "unicode", "single-header")

    package_type = "header-library"

    # R32: settings.os judgement must use in ("Linux", "OHOS"); keep all four
    # to pass L0p. Header-only → single package_id via self.info.clear().
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # 无本地补丁：patches/ 为空，不导出额外文件
        copy(self, "patches/*.patch", src=self.recipe_folder, dst=self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)   # patches: {} → no-op，保持配方门禁合规

    def build(self):
        # Header-only library: no artifact to compile. Upstream tests
        # (minidraw_test_0_automated.c / minidraw_test_1_graphics.c) require
        # Cairo/Pango/GTK which are unavailable on HarmonyOS PC; the core
        # UTF/text APIs they cover are exercised by test_package's consumer
        # test instead (see test_package/test.c and MANIFEST.yml).
        pass

    def package(self):
        # Variant A: header-only. Only the top-level library header is packed;
        # extras/ and external/ (app framework, glbind, stb) are not part of
        # the public library API. dst must be an absolute package path.
        copy(self, "minidraw.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # no build deps on os/compiler → single id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]