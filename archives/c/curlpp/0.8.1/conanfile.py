#!/usr/bin/env python3
"""Conan recipe — curlpp 0.8.1 (CMake)"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CurlppConan(ConanFile):
    name = "curlpp"
    version = "0.8.1"
    description = "C++ wrapper for libcurl providing object-oriented HTTP request interface"
    license = "MIT"
    homepage = "https://github.com/jpbarrette/curlpp"
    url = "https://github.com/jpbarrette/curlpp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports = "sources/curlpp-0.8.1.tar.gz"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # CI Worker 网络受限，优先使用配方内嵌源码
        from conan.tools.files import unzip, check_sha256
        sha = self.conan_data["sources"]["sha256"]
        local_tarball = os.path.join(self.recipe_folder, "sources", "curlpp-0.8.1.tar.gz")
        if os.path.isfile(local_tarball):
            check_sha256(self, local_tarball, sha)
            unzip(self, local_tarball, strip_root=True)
            return
        # 回退: 检查 DOWNLOAD_CACHE 预缓存
        cache_dir = os.environ.get("DOWNLOAD_CACHE", "")
        if cache_dir:
            staged = os.path.join(cache_dir, "curlpp-0.8.1.tar.gz")
            if os.path.isfile(staged):
                check_sha256(self, staged, sha)
                unzip(self, staged, strip_root=True)
                return
        # 最终回退: 在线下载
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # curl 通过系统 cmd-pkgs 安装，通过 Conan conf 或 DEFAULT_PREFIX 环境变量定位
        curl_prefix = self.conf.get("user.curl:prefix", default="", check_type=str)
        if not curl_prefix:
            curl_prefix = os.environ.get("DEFAULT_PREFIX", "")
        if curl_prefix:
            tc.variables["CMAKE_PREFIX_PATH"] = curl_prefix
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["curlpp"]
        self.cpp_info.set_property("cmake_file_name", "curlpp")
        self.cpp_info.set_property("cmake_target_name", "curlpp::curlpp")
        self.cpp_info.set_property("pkg_config_name", "curlpp")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["curl"]
