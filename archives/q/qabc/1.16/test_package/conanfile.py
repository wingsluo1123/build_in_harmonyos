#!/usr/bin/env python3
"""test_package for qabc — offscreen CLI 冒烟 + Qt6 Widgets 渲染快照自检。

qabc 是纯可执行包（Qt6 Widgets GUI，无库产物），无法做"链接被测包"
测试；按 R34 验证真实交付物，按 R40 覆盖 UI 框架适配完整性：

1. offscreen CLI 冒烟（test.sh）：--version 版本串 + --help 帮助文本。
2. Qt6 Widgets 渲染快照自检（test_render）：offscreen 平台创建
   QWidget+QLabel 并 grab 渲染一帧，保存 PNG 且校验图像尺寸非零——
   防止"仅 --version/--help 可用但渲染栈不可用"的空壳通过验收。

qabc 二进制与 test_render 的 DT_NEEDED 含 libc++_shared.so 与 Qt6 动态库，
运行期注入 OHOS SDK libc++ 目录（fingerterm 同款）与 qtbase/qttools lib。
"""
import glob
import os

from conan import ConanFile
from conan.tools.env import Environment


class QabcTestConan(ConanFile):
    """test_package for executable packages — runs test.sh + test_render."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 运行期 DT_NEEDED 链：Qt6 库与 SDK libc++ 必须可解析
        self.requires("qtbase/6.11.1")
        self.requires("qttools/6.11.1")

    def test(self):
        env = Environment()
        # 编译器目录必须在 PATH（下面用 clang++ 编译 test_render）；CI
        # 构建环境不保证其存在，显式注入（与主配方同款处理），否则报
        # `clang++: not found`。
        for bin_dir in self._toolchain_bin_dirs():
            env.prepend_path("PATH", bin_dir)
        # OHOS SDK runtime：qabc 与 Qt 库链接 libc++_shared.so，只有 SDK
        # 提供（llvm/lib/aarch64-linux-ohos/，fingerterm 同款布局）。
        for sdk_lib in self._ohos_sdk_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.test.values()
        ):
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        # 运行期也需要 Qt 插件（offscreen 平台插件）
        qtbase = self.dependencies["qtbase"]
        if qtbase and qtbase.package_folder:
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(qtbase.package_folder, "plugins")
            )

        # 1) Qt6 Widgets 渲染快照自检（R40：offscreen 渲染链路可用性）
        #    用 qtbase 的 include/lib 编译 test_render.cpp（qmake 工程同源
        #    工具链，不引入 CMake）。编译产物与渲染快照均输出到工作树外
        #    的临时目录（test_package 无 layout，conan 默认 build_folder
        #    即源码目录，直接用会在工作树落盘）。
        qtbase_pkg = qtbase.package_folder
        inc = os.path.join(qtbase_pkg, "include")
        lib = os.path.join(qtbase_pkg, "lib")
        src_cpp = os.path.join(self.source_folder, "test_render.cpp")
        tmpdir = self._test_tmpdir()
        out_bin = os.path.join(tmpdir, "test_render")
        with env.vars(self).apply():
            self.run(
                "clang++ -std=c++17 -fPIC "
                f"-I{inc} -I{inc}/QtCore -I{inc}/QtGui -I{inc}/QtWidgets "
                f"{src_cpp} -L{lib} "
                f"-Wl,-rpath,{lib} -lQt6Widgets -lQt6Gui -lQt6Core "
                f"-o {out_bin}",
                env="conanbuild",
            )
            self.run(
                f"TMPDIR={tmpdir} QT_QPA_PLATFORM=offscreen {out_bin}",
                env="conanrun",
            )

        # 2) qabc 二进制 offscreen CLI 冒烟
        #    OHOS: /system/bin/sh (mksh) cannot execute ELF binaries；
        #    用 bash 包裹执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        with env.vars(self).apply():
            self.run(f"{bash} test.sh", env="conanrun")

    @staticmethod
    def _test_tmpdir():
        """可写的临时目录（工作树外）：优先 TMPDIR，其次 $HOME/tmp。

        test_package 无 layout 时 conan 以源码目录作 build_folder，直接
        落盘会在工作树产生 test_render 二进制与渲染快照，故显式分离。
        """
        cand = os.environ.get("TMPDIR")
        if cand and os.path.isdir(cand) and os.access(cand, os.W_OK):
            return cand
        home_tmp = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(home_tmp, exist_ok=True)
        return home_tmp

    @staticmethod
    def _ohos_sdk_lib_dirs():
        """Locate OHOS SDK llvm lib dirs providing libc++_shared.so.

        glob 覆盖全部已安装 SDK 版本目录，不硬编码具体版本
        （fingerterm 先例有首项硬编码，此处按 W4 审计意见去除）。
        """
        dirs = []
        for cand in sorted(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"
            )
        ):
            if os.path.isdir(cand) and cand not in dirs:
                dirs.append(cand)
        return dirs

    def _toolchain_bin_dirs(self):
        """Locate compiler bin dirs that must be on PATH.

        test() 用裸名 clang++ 编译 test_render；CI 构建环境不保证编译器
        目录在 PATH 中（CMake 类配方用绝对路径，本包 test 步骤须显式注入），
        否则报 `clang++: not found`。优先 profile conf
        tools.build:compiler_executables 的目录，并兜底 glob OHOS SDK bin
        与 HNP bin。
        """
        dirs = []
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        if isinstance(compilers, dict):
            for key in ("c", "cpp"):
                path = compilers.get(key)
                d = os.path.dirname(path) if path else ""
                if d and d not in dirs:
                    dirs.append(d)
        for cand in sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")
        ) + ["/data/service/hnp/bin"]:
            if os.path.isdir(cand) and cand not in dirs:
                dirs.append(cand)
        return dirs