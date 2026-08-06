#!/usr/bin/env python3
"""Conan test_package — poppler 25.12.0.1.1

CI 通过 `conan create` 自动调用本测试（L1）。

与 25.12.0 的两处差异：
1. test.cpp 改为**真实调用 poppler-cpp API**（解析 PDF、抽取文本），
   而非只打印头文件里的版本宏——后者不触碰库代码，把 lib/ 删掉也照样通过，
   过不了 R34 与 CI 的 L1e 破坏性反向验证。
2. **运行期失败不再吞掉**。25.12.0 用 try/except 把运行错误降级成 warning，
   理由写的是「OHOS musl 不支持 RPATH/LD_LIBRARY_PATH」——该说法不成立
   （同仓 opencv/ffmpeg 等配方的 test_package 都以 env="conanrun" 正常跑起来）。
   正因为运行期失败被吞掉，libpoppler-cpp.so 缺 SONAME 导致 DT_NEEDED 变成
   相对路径 `../libpoppler.so` 这个缺陷才一直没被发现。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PopplerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        poppler = self.dependencies["poppler"]
        lib_dir = os.path.join(poppler.package_folder, "lib")
        if os.path.isdir(lib_dir):
            existing = tc.cache_variables.get("CMAKE_EXE_LINKER_FLAGS", "")
            if existing:
                tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = f"{existing} -Wl,-rpath,{lib_dir}"
            else:
                tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = f"-Wl,-rpath,{lib_dir}"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        test_poppler_bin = os.path.join(bindir, "test_poppler")
        test_qt5_bin = os.path.join(bindir, "test_poppler_qt5")

        # P2 修复（AI 审查 #182841779）：本 PR 的核心交付物是 Qt5 绑定，两个测试
        # 二进制都必须产出；缺任一即视为构建失败，覆盖 Qt5 绑定的链接验证，避免
        # “编译过、运行期坏”的隐身风险（参见 notes.md 的教训）。
        for _name, _b in (("test_poppler", test_poppler_bin),
                          ("test_poppler_qt5", test_qt5_bin)):
            if not os.path.exists(_b):
                raise Exception("%s binary not found - build failed" % _name)

        if cross_building(self):
            # 交叉编译（OHOS aarch64）：宿主机无法执行目标二进制，仅验产物存在。
            self.output.info("cross-building：已验证 test_poppler 与 test_poppler_qt5 均成功链接")
            return

        # 真跑。失败就是失败——不 catch、不降级为 warning。
        self.run(test_poppler_bin, env="conanrun")
        self.run(test_qt5_bin, env="conanrun")
