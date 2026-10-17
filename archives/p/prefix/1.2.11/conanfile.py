#!/usr/bin/env python3
"""Conan recipe — prefix 1.2.11 (PostgreSQL server extension).

prefix 实现 PostgreSQL 的 ``prefix_range`` 数据类型（前缀范围 / 电话号段），
提供 @> / <@ / && / | / & 等运算符与 ``gist_prefix_range_ops`` GiST 操作符类，
用于「最长前缀匹配」类检索（最典型场景是电话呼叫路由：号码 → 归属运营商）。

构建产物是 PostgreSQL **服务端** 扩展模块 ``prefix.so``（由 postgres 进程在
``CREATE EXTENSION`` 时 dlopen），外加 ``prefix.control`` 与 ``prefix--*.sql``
安装/升级脚本。

构建策略：上游 Makefile 是标准 PGXS 扩展 Makefile（``PG_CONFIG ?= pg_config`` /
``PGXS = $(shell $(PG_CONFIG) --pgxs)`` / ``include $(PGXS)``），``prefix.c`` 直接
包含 PostgreSQL 服务端头文件（``postgres.h``、``utils/builtins.h`` 等）。服务端
头文件、PGXS 构建基础设施、可重定位的 ``pg_config`` 以及 test_package 需要的
可运行服务端（initdb/pg_ctl/psql/pg_regress）全部来自 conan ``postgresql`` 包
—— 无需在 build() 里构建 PostgreSQL 源码，也无需任何源码补丁。

已在 OHOS PC（aarch64，clang 15.0.4 + OHOS musl 工具链）实测：``make`` 一次通过
（仅上游自带的一处 unused-function 告警），上游回归套件 5/5 通过，消费者端到端
用例通过 —— 详见 notes.md 与 test_package/。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PrefixConan(ConanFile):
    name = "prefix"
    version = "1.2.11"
    description = (
        "PostgreSQL prefix_range data type and GiST operator class for "
        "longest-prefix-match lookups (telephony call routing)"
    )
    license = "PostgreSQL"
    homepage = "https://github.com/dimitri/prefix"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # PostgreSQL 扩展模块由服务端 dlopen，不存在静态链接形态。
    default_options = {"shared": True}

    def validate(self):
        # R32: 同时接受 Linux 与 OHOS 平台设置。
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"prefix is only supported on Linux/OHOS, not {self.settings.os}")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "prefix is a PostgreSQL extension module and can only be built shared")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PostgreSQL 服务端头文件 + PGXS makefile + 可重定位 pg_config，
        # 以及 test_package 启动真实实例所需的服务端程序。
        # 上游 CI 覆盖 PG 9.1–19（.github/workflows/regression.yml），
        # 与制品仓当前发布的 18.3 兼容。
        self.requires("postgresql/18.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游 1.2.11 在 OHOS 上一次编译通过，本版本无补丁；保留该调用以便
        # 将来新增补丁时无需改代码（conandata.yml 无 patches 段时为空操作）。
        apply_conandata_patches(self)

    def build(self):
        # PGXS 在 make 时通过 pg_config 解析全部路径（服务端 include、CFLAGS、
        # 安装目录），而包内 pg_config 按自身位置解析前缀（可重定位），
        # 因此构建在 conan 缓存任意位置都成立。
        pg_bindir = self.dependencies["postgresql"].cpp_info.bindirs[0]
        pg_config = os.path.join(pg_bindir, "pg_config")
        # rpath= 关闭 PGXS 默认的 -Wl,-rpath,'$(libdir)'（Makefile.global:
        # rpathdir = $(libdir)）。服务端模块由 postgres 进程 dlopen，rpath 无意义，
        # 却会把构建机 conan 缓存路径写进交付的 .so（不可复现产物）；关掉后
        # DT_NEEDED 只剩 libc.so。
        self.run(f'make PG_CONFIG="{pg_config}" rpath= -j1', cwd=self.source_folder)

    def package(self):
        # prefix.so 是服务端模块：control 文件用默认 module_pathname
        # （$libdir/prefix），由消费者部署进 PostgreSQL 的 pkglibdir。
        copy(self, "prefix.so", self.source_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "prefix.control", self.source_folder,
             os.path.join(self.package_folder, "share", "extension"))
        # 与上游 `make install` 的 DATA 列表（Makefile:4）逐项一致。
        for script in ("prefix--1.2.0.sql",
                       "prefix--unpackaged--1.2.0.sql",
                       "prefix--1.1--1.2.0.sql"):
            copy(self, script, self.source_folder,
                 os.path.join(self.package_folder, "share", "extension"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["prefix"]
        self.cpp_info.libdirs = ["lib"]
        # share/extension 存放 prefix.control 与 prefix--*.sql，
        # 由 PostgreSQL 部署复制进 sharedir。
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("cmake_file_name", "prefix")
        self.cpp_info.set_property("cmake_target_name", "prefix::prefix")
