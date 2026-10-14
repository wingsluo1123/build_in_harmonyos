#!/usr/bin/env python3
"""Conan test_package for openvdb 13.0.0 — 消费者测试（真实编译+链接；原生构建下真实执行）。

交叉编译说明：OHOS SDK 不随附设备端 musl 动态加载器，本机 QEMU 执行动态
aarch64 OHOS 产物会段错误（实测连 hello-world 都 segfault），且依赖 tbb 的
制品仓包只提供共享库（无 libtbb.a），消费者无法做成全静态二进制。因此
cross_building 时只做编译+链接+符号+架构验证（仍为真实链接）；
设备端原生构建（官方 CI aarch64 worker）下才真实执行消费者程序。
"""
from conan import ConanFile
from conan.tools.build import cross_building


class OpenvdbTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["openvdb"].package_folder

        # 依赖名按 recipe requires 的固定三项取，不做 self.dependencies 迭代
        # （不同 Conan 2 小版本迭代协议不一致——见既有归档注释）。
        flags = {"include": [], "libdir": [], "lib": []}
        for dep_name in ("tbb", "zlib", "boost"):
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            for inc in dep.cpp_info.includedirs:
                flags["include"].append(inc)
            for libd in dep.cpp_info.libdirs:
                flags["libdir"].append(libd)
            for name in list(dep.cpp_info.libs) + list(dep.cpp_info.system_libs):
                if name and name not in flags["lib"]:
                    flags["lib"].append(name)

        # 一律从 profile 的 tools.build:compiler_executables 取编译器**绝对路径**：
        # 官方 CI 的 profile 是 {"c": "/data/service/hnp/bin/clang",
        # "cpp": "/data/service/hnp/bin/clang++"}，而 CI 是**原生**构建
        # （cross_building=False）——若只在交叉时读 conf，原生构建会退化成裸名 "clang++"，
        # 而 worker 的 PATH（/data/app/bin:/system/bin:/system/sbin:/vendor/bin:...）里没有它
        # → FileNotFoundError（本包 2026-09-28 构建 #63790 实测）。
        # 默认值同样用 CI 的绝对路径，而不是裸名（对照仓库内 4ti2 等已验证写法）。
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = executables.get("cpp") or executables.get("c") or "/data/service/hnp/bin/clang++"
        cross = cross_building(self)

        args = [f'--pkg "{pkg_folder}"', f'--cxx "{cxx}"']
        if cross:
            args.append("--cross")
        for kind in ("include", "libdir", "lib"):
            for v in flags[kind]:
                args.append(f'--{kind} "{v}"')

        # 必须同时应用 conanbuild 与 conanrun：
        #  · conanbuild：驱动会**直接调用编译器**，而 CI profile 把编译器目录
        #    （/data/service/hnp/bin）及其 LD_LIBRARY_PATH（HNP lld 依赖 llvm/lib/libxml2.so.16）
        #    放在 [buildenv] 里——只用 conanrun 会既找不到 clang++、也可能加载不了 lld 的库；
        #  · conanrun：原生构建下驱动要真实执行消费者二进制。
        self.run("python3 test_openvdb.py " + " ".join(args),
                 env=["conanbuild", "conanrun"])
