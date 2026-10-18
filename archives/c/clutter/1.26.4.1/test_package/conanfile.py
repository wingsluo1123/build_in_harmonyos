#!/usr/bin/env python3
"""Conan test_package for clutter 1.26.4 — 消费测试 + 上游纯 CPU 测试子集。

test() 收集全部依赖包（cogl/glib/pango/atk/json-glib 及传递依赖）的
cpp_info.includedirs/libdirs 写入 CLUTTER_TEST_DEP_INCLUDES /
CLUTTER_TEST_DEP_LIBDIRS，由 test_clutter.py 编译链接 consumer.c 与
upstream_unit/ 纯 CPU 子集（17 用例）时使用（clutter.h 内部解析
glib/pango/cogl/cairo/atk/json-glib 全链头，需全依赖 include 路径；
CONAN_CFLAGS 聚合环境变量在 Conan 2 依赖 cpp_info 而非 env，实测为
空不可靠——cogl 1.22.8 test_package 同款方案）。
"""
import os

from conan import ConanFile


class ClutterTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["clutter"].package_folder
        # 收集全部依赖（含传递）的 include/lib 目录——consumer 编译
        # clutter.h 需解析全链头（glib/gobject/pango/cogl/cairo/atk/
        # json-glib/harfbuzz/freetype 等），运行需对应 .so。三点
        # 版本无关性保证（cogl test_package 同款教训固化）：
        # 1) 固定按名取，不做 `for dep_name in self.dependencies`
        #    迭代——CI 环境 Conan 2 小版本 Dependencies 迭代协议
        #    不一致（抛 TypeError，#6992 CI 34083）；按名索引在本地
        #    2.29.1 与 CI 均可用。名称 = clutter 直接 requires
        #    (cogl/glib/pango/cairo/atk/json-glib) + pango 传递
        #    (fribidi/harfbuzz) + glib 传递 (libffi/pcre2/zlib)，
        #    未安装/缺失名称兜底跳过。
        # 2) 组件包（glib recipe 用 glib-2.0/gobject-2.0 等
        #    components）顶层 dep.cpp_info.includedirs 不含组件级
        #    include——优先用 cpp_info.aggregated_components() 聚合，
        #    无该方法（旧版本）时回退顶层 cpp_info。
        # 3) cairo/json-glib/atk 包头分别位于 include/cairo、
        #    include/json-glib-1.0、include/atk-1.0——包顶层
        #    includedirs（=include）逐一补齐子目录。
        dep_names = ("cogl", "glib", "pango", "cairo", "atk",
                     "json-glib", "fribidi", "harfbuzz",
                     "libffi", "pcre2", "zlib", "expat",
                     "fontconfig", "freetype", "libpng",
                     "pixman", "pixman-1")
        dep_incs = []
        dep_libdirs = []
        for dep_name in dep_names:
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            try:
                agg = dep.cpp_info.aggregated_components()
                incs = list(agg.includedirs)
                libds = list(agg.libdirs)
            except Exception:
                incs = list(dep.cpp_info.includedirs)
                libds = list(dep.cpp_info.libdirs)
            for inc in incs:
                if inc not in dep_incs:
                    dep_incs.append(inc)
            for libd in libds:
                if libd not in dep_libdirs:
                    dep_libdirs.append(libd)
        # 包内组件头子目录补齐（cairo/json-glib/atk 的实际安装布局）
        # 包内组件头子目录补齐（cairo/cogl/json-glib/atk 的实际安装布局）
        for dep_name, subs in (("cairo", ("cairo",)),
                               ("cogl", ("cogl",)),
                               ("json-glib", ("json-glib-1.0",)),
                               ("atk", ("atk-1.0",))):
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            for sub in subs:
                d = os.path.join(dep.package_folder, "include", sub)
                if os.path.isdir(d) and d not in dep_incs:
                    dep_incs.append(d)
        os.environ["CLUTTER_TEST_DEP_INCLUDES"] = " ".join(dep_incs)
        os.environ["CLUTTER_TEST_DEP_LIBDIRS"] = " ".join(dep_libdirs)
        self.run('python3 test_clutter.py "%s"' % pkg_folder,
                 env="conanrun")
