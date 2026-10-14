#!/usr/bin/env python3
"""test_package for xsd/4.0.0 —— 消费者侧真实执行已安装的 `bin/xsd`。

`test()` 只做一件事：把包内与依赖的绝对路径交给 `test.sh`，由它完成
「生成 → 编译 → 运行」的双模式闭环（见 test.sh 头注）。这里不写断言，
保证断言行数只有一个取数位置（PR 正文「鸿蒙特有测试」行）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class XsdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # xerces-c 在配方里是 xsd 的**传递**依赖，而 Conan 只对**直接**依赖暴露
        # package_folder（实测传递依赖的 package_folder 恒为 None、
        # cpp_info.includedirs 也停在 'include' 这种相对形态）。本 test_package
        # 要把生成出来的代码真的编译起来，必须拿到 xerces 头/库的绝对路径，
        # 因此把同一版本显式提为直接依赖；若上游升版，这里会以版本冲突报错，
        # 而不是静默用错版本。
        self.requires("xerces-c/3.2.5")

    def _dep(self, name):
        # ConanFileInterface 没有 .name（属性在 ref 上）：`getattr(dep, "name", None)`
        # 恒为 None，会把每个依赖都判成"不存在"（实测 ConanException: dependency
        # 'xsd' not found）。判据用 dep.ref.name。
        for _key, dep in self.dependencies.items():
            if getattr(getattr(dep, "ref", None), "name", None) == name:
                return dep
        raise ConanException(
            f"test_package: dependency {name!r} not found "
            f"(have: {sorted(str(k) for k, _v in self.dependencies.items())})")

    def test(self):
        xsd = self._dep("xsd")
        xerces = self._dep("xerces-c")

        exes = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = exes.get("cpp") or "/data/service/hnp/bin/clang++"

        xinc = ":".join(
            os.path.join(xerces.package_folder, d)
            for d in (xerces.cpp_info.includedirs or ["include"]))
        xlib = ":".join(
            os.path.join(xerces.package_folder, d)
            for d in (xerces.cpp_info.libdirs or ["lib"]))

        env = (
            f'XSD_BIN="{os.path.join(xsd.package_folder, "bin", "xsd")}" '
            f'XSD_INCLUDE="{os.path.join(xsd.package_folder, "include")}" '
            f'XERCES_INCLUDE="{xinc}" XERCES_LIB="{xlib}" '
            f'CXX_BIN="{cxx}"'
        )
        # env="conanrun"：VirtualRunEnv 把包内 bin/ 放进 PATH，并给出
        # CONFIG_SHELL/SHELL（设备 bash），断言脚本本身不依赖 PATH 里的 xsd。
        self.run(f"{env} sh test.sh", env="conanrun")
