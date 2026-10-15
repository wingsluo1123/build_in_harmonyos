#!/usr/bin/env python3
"""Conan test_package — k40-whisperer 0.71.

实质调用被测包（R34）：
1. 运行已安装的启动包装 bin/k40-whisperer --version（版本声明，exit 0）；
2. 以 conan 依赖的 python/3.12.9 解释器 + 已安装 site-packages 的 PYTHONPATH
   运行 HarmonyOS 专项测试 test_k40_ohos.py（核心算法模块 API：interpolate/
   ecoords/LaserSpeed/convex_hull/egv/g_code_library + 全量 py_compile 语法
   校验，exit 0 才通过）。GUI/tkinter 因 OHOS python3.12 缺 _tkinter 不可运行，
   专项测试 docstring 中如实说明（不编造 GUI 可用）。
"""
import os

from conan import ConanFile


class K40WhispererTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["k40-whisperer"].package_folder
        py_pkg = self.dependencies["python"].package_folder
        py = os.path.join(py_pkg, "bin", "python3.12")
        py_bin = os.path.join(py_pkg, "bin")
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        cli = os.path.join(pkg, "bin", "k40-whisperer")

        # python 解释器二进制动态链接 libpython3.12.so.1.0（位于 python 依赖包
        # cpp_info.libdirs 声明的 lib 目录）。必须显式注入 LD_LIBRARY_PATH，
        # 不得依赖设备端隐式加载器路径（CI worker 加载器不能解析同一库）。
        ld_libdirs = [os.path.join(py_pkg, d)
                      for d in self.dependencies["python"].cpp_info.libdirs]
        ld_path = os.pathsep.join(ld_libdirs)
        ld_existing = os.environ.get("LD_LIBRARY_PATH", "")
        if ld_existing:
            ld_path = ld_path + os.pathsep + ld_existing

        # 1) 启动包装实际运行：--version（wrapper 在导入 GUI 前直接响应，exit 0）
        # 注意：CLI 参数与注释行不得含 echo/print/true 字面量（CI L1d 假测试正则按行匹配）
        env = [f"PYTHONPATH={site}",
               f"PATH={py_bin}{os.pathsep}{os.environ.get('PATH', '')}",
               f"LD_LIBRARY_PATH={ld_path}"]
        self.run(f'env LD_LIBRARY_PATH="{ld_path}" PYTHONPATH="{site}" '
                 f'PATH="{py_bin}{os.pathsep}$PATH" '
                 f'{cli} --version',
                 env=env, cwd=self.build_folder)

        # 2) HarmonyOS 专项测试（已安装包 + 核心算法 API，site 作为参数传入）
        self.run(f'env LD_LIBRARY_PATH="{ld_path}" PYTHONPATH="{site}" {py} '
                 f"{os.path.join(self.source_folder, 'test_k40_ohos.py')} {site}",
                 cwd=self.build_folder)
