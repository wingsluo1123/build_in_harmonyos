#!/usr/bin/env python3
"""Conan test_package — tdbcodbc/1.1.14 消费者测试。

tdbcodbc 是 Tcl 扩展包（不是可直接链接的 C 库）：消费方式是 tclsh 经
auto_path / TCLLIBPATH 找到 lib/tdbcodbc1.1.14/pkgIndex.tcl 并 dlopen
libtdbcodbc1.1.14.so；扩展自身再 dlopen unixODBC 的 libodbc.so.2 /
libodbcinst.so.2 并解析 SQL* 符号。因此这里不编译 C 程序，而是真实加载被测包、
调用其 ODBC API，并校验驱动管理器确实被加载进进程（R34）。

入口为 test_tdbcodbc.sh（CI L0c 要求的测试源文件），其内部以 tclsh8.6 执行
test_tdbcodbc.tcl 中的断言。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TdbcOdbcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            # 开发机（macOS）交叉构建：OHOS 产物无法在构建机执行。
            # CI worker 为原生 OHOS 构建（can_run=True），本测试照常运行。
            self.output.warning(
                "test_package 未执行：交叉构建（can_run=False），"
                "断言在原生 OHOS 构建上运行"
            )
            return

        script = os.path.join(self.recipe_folder, "test_tdbcodbc.sh")

        # TCLLIBPATH 必须是 Tcl 列表（空格分隔）：init.tcl 里就是
        # `set auto_path $env(TCLLIBPATH)`，而 Conan 的 prepend_path 用
        # os.pathsep(":") 拼接且对 path 型变量忽略自定义 separator。依赖图里有
        # 两个 Tcl 扩展（tdbcodbc + tdbc）时，Tcl 会把 "a/lib:b/lib" 当成一个
        # 不存在的目录，pkgIndex.tcl 扫不到 → "can't find package tdbc::odbc"
        # （CI #91604 实测）。这里按 Tcl 语义显式重设为空格分隔列表。
        tcl_dirs = []
        for dep in self.dependencies.host.values():
            if str(dep.ref.name) in ("tdbcodbc", "tdbc"):
                tcl_dirs.append(os.path.join(dep.package_folder, "lib"))
        if len(tcl_dirs) != 2:
            # 宁可显式失败，也不要退化成一条难懂的 "can't find package"
            raise ConanException(
                f"期望从依赖图取到 tdbcodbc 与 tdbc 两个 lib/ 目录，实际: {tcl_dirs}"
            )
        tcllibpath = " ".join(tcl_dirs)

        # unixODBC 通过 ODBCSYSINI 定位 odbcinst.ini / odbc.ini。依赖包自带
        # 一份（空）配置目录，显式指向它可让 SQLDriversW / SQLDataSourcesW
        # 的行为与部署环境无关（否则回落到编译期 sysconfdir 或 ~/.odbc.ini）
        odbc_etc = os.path.join(self.dependencies["unixodbc"].package_folder, "etc")
        odbc_ini = os.path.join(odbc_etc, "odbc.ini")
        # 环境来源（均由 Conan 依赖链注入）：
        #   tcl/8.6.16 runenv       → PATH += <tcl>/bin（tclsh8.6）、TCL_ROOT、
        #                              LD_LIBRARY_PATH += <tcl>/lib
        #   tdbc + tdbcodbc runenv  → TCLLIBPATH（Conan 用 ":" 拼接，上面按 Tcl
        #                              语义重设为空格分隔列表）
        #   unixodbc/2.3.12 libdirs → LD_LIBRARY_PATH（dlopen libodbc.so.2 用）
        self.run(
            f'TCLLIBPATH="{tcllibpath}" ODBCSYSINI="{odbc_etc}" '
            f'ODBCINI="{odbc_ini}" sh "{script}"',
            env="conanrun",
        )
