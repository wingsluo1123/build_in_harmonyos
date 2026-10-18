#!/usr/bin/env python3
"""pizzly 0.37.3 —— OpenHarmony PC (OHOS aarch64) 的 Conan 2 配方。

上游：https://github.com/pmelsted/pizzly
基于 SeqAn 2 的 RNA-Seq 融合基因检出命令行工具（需 kallisto >= 0.43.1 的 --fusion 输出）。
构建系统 CMake，唯一外部依赖 zlib（SeqAn 的 gzip 支持）。

本配方相对上游的四处必要调整（全部在配方侧完成，**无源码补丁**）：

1. CMAKE_POLICY_VERSION_MINIMUM=3.5
   上游 `cmake_minimum_required (VERSION 3.0.0)`，CMake 4.x 已移除对 <3.5 的兼容，
   配置期直接报 "Compatibility with CMake < 3.5 has been removed"。用 CMake 官方提供的
   兼容下限变量保留上游声明本身（仓库通用做法，不改上游源码）。

2. compiler.cppstd = 14
   上游 CMakeLists 把 CMAKE_CXX_FLAGS 固定为 `-std=c++14`（内置 SeqAn 2.2.0 是 C++14
   时代代码）。若沿用 profile 默认的 cppstd=17，libc++ 的 `std::empty`（C++17）会与
   `seqan::empty` 在 `seqan/arg_parse/*.h` 内产生二义性：
   `error: call to 'empty' is ambiguous`。本包据此按上游声明固定为 C++14。

3. SEQAN_ASYNC_IO=0
   OHOS 的 `<aio.h>` 只提供 `struct aiocb` 与 `AIO_*`/`LIO_*` 常量，**不声明任何
   `aio_read`/`aio_write`/`aio_suspend`/`aio_return`/`aio_error` 函数**，而 SeqAn 的平台探针
   `#if __has_include(<aio.h>)` 只看头文件是否存在，因此假阳性地把 SEQAN_ASYNC_IO 置 1，
   编译 `seqan/system/file_async.h` 时报 `use of undeclared identifier 'aio_read'`。
   `SEQAN_ASYNC_IO` 是 SeqAn 官方支持的平台能力开关（`seqan/platform.h` 的
   `#ifndef SEQAN_ASYNC_IO`），OpenBSD 等无 AIO 平台即走此分支。pizzly 自身不使用
   SeqAn 异步 IO（main.cpp/FilterFusions.hpp/GeneModel.hpp 无任何 async* 调用），
   故显式声明该平台能力为 0——这是如实声明平台能力，不是 stub 掉功能。

4. package() 从构建目录安装可执行文件
   上游 v0.37.3 的 CMakeLists.txt **没有 install() 规则**（该规则是上游后续在 master
   新增的），`cmake --install` 不会产出任何文件，包会变成空壳。因此按仓库既有做法，
   直接把构建出的 `pizzly` 从构建目录复制到 `<package>/bin`。

zlib 的解析方式：本配方只用 CMakeToolchain（不引入 CMakeDeps），CMakeToolchain 会为
依赖注入 `CMAKE_LIBRARY_PATH`/`CMAKE_INCLUDE_PATH`，上游的 `find_package (ZLIB)` 因此走
FindZLIB 模块模式并取到 Conan 的 libz.a（实测 `-- Found ZLIB: .../zlib56af09fbb4346/p/lib/libz.a`）。

上游测试：无。CMakeLists.txt 中不存在 enable_testing()/add_test()，仓库内唯一的测试入口是
`test/` 下的 snakemake 示例流水线（依赖外部 kallisto，不是自动化测试套件），因此上游自动化
测试用例数 = 0。消费者验证由 test_package/ 承担（见 MANIFEST.yml 与 notes.md）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)


class PizzlyConan(ConanFile):
    name = "pizzly"
    version = "0.37.3"
    description = ("Fast fusion detection using kallisto — "
                   "gene fusion caller for RNA-Seq data of cancer samples")
    license = "BSD-2-Clause"
    homepage = "https://github.com/pmelsted/pizzly"
    url = "https://github.com/pmelsted/pizzly"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 系统无同名 zlib（`ls /lib*/libz.so*` 为空），由 Conan 提供；SeqAn 的 gzip 支持
        # 需要 zlib 头与库。
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def configure(self):
        # 上游 CMakeLists 显式以 -std=c++14 编译内置 SeqAn 2.2.0（理由见模块 docstring 第 2 条）。
        self.settings.compiler.cppstd = "14"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.preprocessor_definitions["SEQAN_ASYNC_IO"] = "0"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 上游 v0.37.3 无 install() 规则，不能让 cmake.install() 交出空包（docstring 第 4 条）。
        copy(self, "pizzly", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_elf(os.path.join(self.package_folder, "bin", "pizzly"))

    def _sign_elf(self, path):
        """OHOS 上安装态的 ELF 需要自签名后才能被加载器执行（仓库通用做法）。"""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.exists(path):
            return

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.exists(sign_tool):
            self.output.warning("pizzly: binary-sign-tool not found, skip signing")
            os.chmod(path, 0o755)
            return

        if os.path.exists(objcopy):
            # 构建产物上通常没有 .codesign 段，objcopy 此时返回非零且报 "section does not
            # exist"，属预期，忽略其退出码（真正的签名结果由后续 sign + os.replace 决定）。
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" || true', quiet=True)
        signed = path + ".signed"
        self.run(f'"{sign_tool}" sign -inFile "{path}" -outFile "{signed}" -selfSign 1',
                 quiet=True)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
