#!/usr/bin/env python3
"""Conan recipe — megadepth 1.2.0 (HarmonyOS PC / OHOS aarch64).

megadepth 是单翻译单元的 C++11 命令行工具（megadepth.cpp，约 154 KB），
对 BAM/CRAM/BigWig 做覆盖度、AUC、剪接位点（junctions）等统计。

构建系统：CMake。上游仓库不提供规范名 CMakeLists.txt —— 源码只带
CMakeLists.txt.ci/.static/.statlib/.windows 四个变体，构建脚本用
`ln -fs CMakeLists.txt.ci CMakeLists.txt` 取别名，并硬编码
`-L${CMAKE_SOURCE_DIR}/htslib` 等 vendored 子模块目录
（.gitmodules: htslib / libBigWig / libdeflate / zlib）。

OHOS 适配要点：
 - 依赖链改由 Conan 管理（htslib / libbigwig / zlib，传递依赖 libdeflate、xz），
   不再 vendored 编译子模块；配方自带 CMakeLists.txt 用 CMakeDeps 目标消费依赖
   （见 CMakeLists.txt 头注释，R49 禁止注入共享 prefix）。
 - 上游 megadepth.cpp 的 AVX512/AVX2/SSE2 分支均由 __AVX512F__/__AVX2__/__SSE2__
   守卫，aarch64 上全部编译期剔除并走标量尾循环（nper/nsimd 仅在这些分支内声明），
   无需补丁。
 - 上游 tests/test.sh 末段有一处未加 static 守卫的远程 HTTP 取数，本平台
   htslib(--disable-libcurl) 与 libbigwig(NOCURL) 均不支持远程读取；补丁以
   完全等价的本地 fixture（tests/test_noprefix.bam + --add-chr-prefix human）
   替换该 URL，断言与期望文件不变（见 conandata.yml）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MegadepthConan(ConanFile):
    name = "megadepth"
    version = "1.2.0"
    description = ("megadepth — computes coverage, AUC, junctions and other "
                   "summary statistics from BAM/CRAM and BigWig files")
    license = "MIT"
    homepage = "https://github.com/ChristopherWilks/megadepth"
    url = ""  # CI fills this

    # 命令行工具，非库（R38: commands.json 声明在软件级目录）
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", src=self.recipe_folder,
             dst=os.path.join(self.export_sources_folder, "cmake"))

    def requirements(self):
        self.requires("htslib/1.24-r0")
        self.requires("libbigwig/0.4.9")
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: OHOS 必须与 Linux 一同命中
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"megadepth is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游无规范名 CMakeLists.txt（只有 CMakeLists.txt.<variant>），
        # 配方提供等价构建文件，不改动上游任何源码文件（R6/R8）。
        copy(self, "CMakeLists.txt",
             src=os.path.join(self.export_sources_folder, "cmake"),
             dst=self.source_folder)
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = 11
        tc.generate()
        # 传递依赖 libdeflate 以共享库分发（其配方 build() 硬编码
        # -DLIBDEFLATE_BUILD_SHARED_LIB=ON，shared 选项不改变产物），故产物
        # DT_NEEDED 含 libdeflate.so.0。生成 conanrun 环境脚本，供 build()
        # 内的上游测试注入 LD_LIBRARY_PATH（仓库既有约定，见 E298/libharu）。
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试（TEST_QUALITY_SPEC 层 1，必做）──
        self._run_upstream_tests()

    # ------------------------------------------------------------------
    # 上游测试：tests/test.sh（shell 集成测试，52 个 fixture）
    # 以 `static` 模式运行 → 全部输入为仓库内本地文件，无网络依赖。
    # ------------------------------------------------------------------
    def _run_upstream_tests(self):
        run_dir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(run_dir, exist_ok=True)
        # test.sh 以相对路径 tests/... 读取 fixture，并把输出写进 CWD。
        # tests/ 内含相对符号链接（test.bam -> test_noprefix.bam），必须
        # 以保留链接的方式复制，否则引用 tests/test.bam 的用例会失效。
        tests_src = os.path.join(self.source_folder, "tests")
        tests_dst = os.path.join(run_dir, "tests")
        shutil.rmtree(tests_dst, ignore_errors=True)
        shutil.copytree(tests_src, tests_dst, symlinks=True)
        copy(self, "megadepth", src=os.path.join(self.build_folder),
             dst=run_dir)

        # env="conanrun"：由 generate() 的 VirtualRunEnv 生成，注入依赖
        # libdirs 到 LD_LIBRARY_PATH（产物 DT_NEEDED 含共享 libdeflate.so.0）
        self.run("bash tests/test.sh static", cwd=run_dir, env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
