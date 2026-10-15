#!/usr/bin/env python3
"""Conan recipe — picobench 2.10.0 (iboB 的单头 C++ 微基准库).

picobench 是零依赖、header-only 的 C++11 微基准测试库（含
picobench/picobench.hpp 单头，PICOBENCH_IMPLEMENT 宏激活实现）。
无编译阶段；package 仅复制头文件与 LICENSE。

上游测试（test/，doctest 套件，7 个 TEST_CASE）已原样镜像进
test_package 真跑：basic.cpp（6 用例）+ multi_cpp/（1 用例，4 TU），
doctest 框架以 ohpcd 仓 doctest/2.4.11 等价还原（上游 CPM 同版本）。
实测 7/7 test cases / 321 断言全 PASS，详见 notes.md。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class PicobenchConan(ConanFile):
    name = "picobench"
    version = "2.10.0"
    description = "picobench: A micro microbenchmarking library in a single header file for C++11 and up (iboB)"
    license = "MIT"
    homepage = "https://github.com/iboB/picobench"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata sources.url 为列表：ghfast.top 镜像在前，GitHub 官方源兜底
        # （本机双源实测同一 sha256，conan get() 支持列表回退）
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only 库无编译阶段（R34：不伪造编译日志）
        apply_conandata_patches(self)

    def package(self):
        # 精确路径复制：src=source_folder/include → dst=package_folder/include
        # （argy 教训：路径不精确会产生 include/include/ 空目录）
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only：无二进制构建差异 → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
