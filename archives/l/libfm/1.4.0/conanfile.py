#!/usr/bin/env python3
"""Conan recipe — libfm 1.4.0 (core library + libfm-extra, CMake build)

libfm is a GLib/GIO-based library for file managers. This recipe builds the
full libfm core library (base + job + extra, i.e. upstream libfm.la without
the GTK-dependent parts: libfm-gtk / modules / udisks / dbus / exif are
disabled). GTK-dependent components (libfm-gtk) require GTK which is out of
scope for this adaptation.

Upstream tests: src/tests/test-fm-path.c and
src/tests/libfm-file-search-cli-demo.c only require the core library and are
built and executed in test_package. The remaining upstream test/demo files
(src/demo/libfm-demo.c, src/gtk/exo/test.c) require GTK/libfm-gtk and are not
buildable in this scope (see notes.md R51).

Build uses CMake (hand-written CMakeLists.txt) because the upstream autotools
tarball from GitHub auto-archive lacks generated configure scripts and requires
autoreconf with multiple missing m4 macros. fm-marshal.h/.c are pre-generated
with glib-genmarshal (shipped in generated/) to avoid a CI tool dependency.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibfmConan(ConanFile):
    name = "libfm"
    version = "1.4.0"
    description = "GLib-based library for file managers (core + libfm-extra)"
    license = "LGPL-2.1"
    homepage = "https://github.com/lxde/libfm"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        copy(self, "generated/*", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("glib/2.88.0")
        # glib 静态链接依赖 pcre2/zlib/ffi/intl，需显式声明（CMakeDeps 自动解析）
        self.requires("pcre2/10.45")
        self.requires("zlib/1.3.1")
        # fm-file-info.c unconditionally includes <menu-cache.h>;
        # static libmenu-cache is linked into libfm.so (R36: in registry)
        self.requires("menu-cache/1.1.0")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        src = self.conan_data["sources"]
        # get() 下载、sha256 校验、strip 顶层目录解压一步完成（CI 安全，无本机路径）
        get(self, src["url"], sha256=src["sha256"], strip_root=True)
        self.output.info(f"Source extracted to {self.source_folder}")

    def generate(self):
        tc = CMakeToolchain(self)
        glib = self.dependencies["glib"]
        tc.variables["GLIB_ROOT"] = glib.package_folder.replace("\\", "/")
        deps_roots = []
        for dep_name in ("pcre2", "zlib", "menu-cache"):
            if dep_name in self.dependencies:
                deps_roots.append(self.dependencies[dep_name].package_folder.replace("\\", "/"))
        tc.variables["DEPS_ROOTS"] = ";".join(deps_roots)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "BOTH"
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "BOTH"
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # License files
        for fname in ("COPYING", "COPYING.LIB", "COPYING.LESSER"):
            src_path = os.path.join(self.source_folder, fname)
            if os.path.exists(src_path):
                copy(self, fname, self.source_folder,
                     os.path.join(self.package_folder, "licenses"))
        # AUTHORS, NEWS, README
        for fname in ("AUTHORS", "NEWS", "README", "README.md"):
            src_path = os.path.join(self.source_folder, fname)
            if os.path.exists(src_path):
                copy(self, fname, self.source_folder,
                     os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["fm", "fm-extra"]
        self.cpp_info.includedirs = ["include/libfm-4"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("pkg_config_name", "libfm")
        self.cpp_info.set_property("cmake_file_name", "libfm")
