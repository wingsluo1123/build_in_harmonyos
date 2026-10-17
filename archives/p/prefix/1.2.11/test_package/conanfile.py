#!/usr/bin/env python3
"""Conan test_package for prefix 1.2.11 —— 真实服务端消费者 + 上游回归测试。

PostgreSQL 扩展只有在运行中的服务端里才能被验证：模块由 postgres 进程在
``CREATE EXTENSION`` 时 dlopen，所有 PostgreSQL 符号都在该进程中解析。因此本
测试启动一个一次性的 PostgreSQL 18.3 实例（从 conan 缓存整体拷贝出来，保持缓存
干净），把**本配方安装后的** prefix.so / prefix.control / prefix--*.sql 装进去，
先用 pg_regress 重放上游回归套件（5 组），再执行鸿蒙特有断言——其中 CONSUMER-1
是完整的端到端业务用例（号码前缀路由）。见 MANIFEST.yml 与 run_pg_test.sh。
"""
import os

from conan import ConanFile


class PrefixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 服务端二进制（initdb/pg_ctl/psql/pg_regress/pg_config）与扩展构建所需的头文件。
        self.requires("postgresql/18.3")

    @staticmethod
    def _abs(base, path):
        return path if os.path.isabs(path) else os.path.join(base, path)

    def test(self):
        pg = self.dependencies["postgresql"]
        pkg = self.dependencies["prefix"]
        pg_bindir = self._abs(pg.package_folder, pg.cpp_info.bindirs[0])
        # 模块、control 与 SQL 一律取自被测包（绝不使用系统 PostgreSQL 的安装），
        # 这样 CI 的 L1e 负向破坏性验证（破坏包产物后重跑）才会真实失败。
        pkg_libdir = self._abs(pkg.package_folder, pkg.cpp_info.libdirs[0])
        pkg_sharedir = self._abs(pkg.package_folder, pkg.cpp_info.resdirs[0])
        # 整个 test_package 目录会被复制进 conan 缓存，因此上游测试树就紧邻本文件。
        here = self.recipe_folder
        tests_dir = here if os.path.isfile(os.path.join(here, "run_pg_test.sh")) \
            else os.path.join(here, "test_package")
        script = os.path.join(tests_dir, "run_pg_test.sh")
        self.run(
            f'bash "{script}" "{pg_bindir}" "{pkg_libdir}" "{pkg_sharedir}" "{tests_dir}"',
            env="conanrun")
