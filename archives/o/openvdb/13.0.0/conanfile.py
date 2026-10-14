#!/usr/bin/env python3
"""Conan recipe for openvdb 13.0.0 — 稀疏体积数据结构库（C++）。

openvdb（AcademySoftwareFoundation）是电影工业级稀疏体积数据库（C++），
CMake 构建，上游 tag v13.0.0。

Upstream: https://codeload.github.com/AcademySoftwareFoundation/openvdb/tar.gz/refs/tags/v13.0.0

Build: CMake。依赖 tbb（制品仓 tbb/2023.0.0 ✅）、zlib（✅）、boost（✅）
       均在制品仓；blosc 制品仓无 → CMake 关 USE_BLOSC=OFF 绕过。
Install: lib/libopenvdb.a + include/openvdb。
Type: library（软件级 commands.json 登记本版本）

上游测试: openvdb/openvdb/unittest 为 gtest 套件（119 个 .cc / 738 个
         TEST 宏，清点方法见 test_package/MANIFEST.yml）。该套件是单一
         巨型二进制，OHOS 上须 make -j1，构建成本超出 CI 预算，故归档
         构建保持 OPENVDB_BUILD_UNITTESTS=OFF（与既有 openvdb/12.1.1
         归档一致）；真实执行证据由 test_package 的消费者测试提供。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get
import os


class OpenvdbConan(ConanFile):
    name = "openvdb"
    version = "13.0.0"
    description = "Sparse volume data structure and tools (VFX industry standard)"
    license = "MPL-2.0"
    homepage = "https://www.openvdb.org/"
    url = "https://github.com/AcademySoftwareFoundation/openvdb"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # tbb/zlib/boost 制品仓均有；blosc 无——CMake 关闭绕过
    requires = "tbb/2023.0.0", "zlib/1.3.1", "boost/1.90.0"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 会误判为 zip
        # （BadZipFile），显式指定 filename。
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="openvdb-13.0.0.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # blosc 制品仓无——关闭压缩后端（变量名是 USE_BLOSC，
        # 不是 OPENVDB_USE_BLOSC）
        tc.variables["USE_BLOSC"] = "OFF"
        # 只建核心库，关 Python/文档/Houdini/Maya/AX/单测/二进制
        tc.variables["OPENVDB_BUILD_PYTHON_MODULE"] = "OFF"
        tc.variables["OPENVDB_BUILD_DOCS"] = "OFF"
        tc.variables["OPENVDB_BUILD_HOUDINI_PLUGIN"] = "OFF"
        tc.variables["OPENVDB_BUILD_MAYA_PLUGIN"] = "OFF"
        tc.variables["OPENVDB_BUILD_AX"] = "OFF"
        tc.variables["OPENVDB_BUILD_UNITTESTS"] = "OFF"
        tc.variables["OPENVDB_BUILD_BINARIES"] = "OFF"
        # 只建静态库（shared=False 时上游仍默认双构建——关 shared 加速）
        tc.variables["OPENVDB_CORE_SHARED"] = "OFF"
        # DELAYED_LOADING 默认 ON 会触发 find_package(Boost) 找 CMake
        # config（conan 的 boost 包不提供）——OHOS 无意义，关闭绕过
        tc.variables["OPENVDB_USE_DELAYED_LOADING"] = "OFF"
        tc.generate()

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # oneTBB 兼容：openvdb 的 Threading.h 依赖 tbb/blocked_range.h 间接
        # 带入 tbb/version.h（该文件注释明言），但 oneTBB 的 blocked_range.h
        # 不再包含它 → TBB_INTERFACE_VERSION 未定义时走 #else 分支调用
        # tbb::task::self()（oneTBB 已移除）而编译失败。显式 include
        # <tbb/version.h> 让宏生效，走 current_context() 分支。
        # （上游 13.0.0 该注释与 include 行仍在，故与 12.1.1 同样处理。）
        th = os.path.join(self.source_folder, "openvdb", "openvdb", "thread",
                          "Threading.h")
        with open(th, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace("#include <tbb/blocked_range.h>",
                      "#include <tbb/version.h>\n#include <tbb/blocked_range.h>")
        with open(th, "w", encoding="utf-8") as f:
            f.write(s)
        cmake = CMake(self)
        cmake.configure()
        # 直接 make -j1：OHOS 禁 mkfifo jobserver，CMake.build() 的并行
        # 封装会卡死，绕开封装单线程构建
        self.run("make -j1", env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["openvdb"]
        self.cpp_info.requires = ["tbb::tbb", "zlib::zlib", "boost::boost"]
        self.conf_info.define("user.tools.openvdb:exe", "vdb_print")
