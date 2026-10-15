#!/usr/bin/env python3
"""Conan recipe — mnxdom 3.0.1 (CMake).

MNX Document Object Model: a C++17 class framework around the MNX music
interchange format (JSON files).

上游：https://github.com/mnx-works/mnxdom （tag v3.0.1, commit 488aa8757ec602c20ff8cf599a2c6857339d8e93）
许可证：MIT

OHOS / Conan 适配要点
---------------------
1. 上游 CMakeLists 默认用 FetchContent 从 github 下载 nlohmann_json、
   json-schema-validator 与 googletest，本配方把它们全部落地为本地/制品仓依赖，
   构建期不需要联网：
     - nlohmann_json：打开上游的 USE_SYSTEM_NLOHMANN_JSON，用 ohpcd 已发布的
       3.12.0（与上游 NLOHMANN_JSON_VERSION 完全一致）
     - googletest：打开 USE_SYSTEM_GOOGLETEST，用 ohpcd 已发布的 gtest/1.17.0
     - json-schema-validator：见第 2 条，源码随本配方一起下发

2. json-schema-validator 必须用上游钉住的 commit 40af3ec3，不能用 ohpcd 的 2.1.0。
   MNX schema 是「根带 $id、子 schema 继承该 $id」的结构，2.1.0 会在此抛
   `schema with <id> # <pointer> already inserted`，使 schemaValidate() 全线异常
   （实测：上游 62 个用例全部因此失败）。制品仓只发布了 json-schema-validator/2.1.0，
   而适配并发布依赖库属于另一个 PR（W2：一个 PR 只提交一个软件），
   因此本配方在 source() 阶段按上游钉住的 commit 从官方源取该依赖源码，
   用 FETCHCONTENT_SOURCE_DIR_JSON_SCHEMA_VALIDATOR 让上游 FetchContent 直接使用
   本地目录（不联网），并把它静态编译、随本包一起交付（见 package/package_info）。

3. 链接形态：mnxdom 与内嵌的 json-schema-validator 都按静态库构建（shared=False）。
   内嵌依赖的静态/共享开关在 jsv 自己的 CMakeLists 里写错了变量名
   （option 是 JSON_VALIDATOR_SHARED_LIBS，实际读取的却是
   nlohmann_json_schema_validator_SHARED_LIBS），两个都显式置 False 才能保证静态。

4. mnxdom 对 googletest 的 CMake 目标名有白名单要求（GTest::gtest_main /
   GTest::gtest），而 CMakeDeps 只导出 gtest::gtest、且没有 gtest_main 目标，
   因此用 GTest_DIR 指向依赖包内自带的上游配置目录（可重定位，导出全套 GTest:: 目标；
   同仓库 abseil 配方同法）。

5. 上游测试套件（tests/，GoogleTest，由 gtest_discover_tests 注册到 ctest）
   在 build() 中通过 cmake.test() 全量运行。

6. MNX JSON schema 以 mnx-schema.xxd 内嵌进库，schemaValidate() 运行时不读外部文件，
   安装包无需附带 schema/示例资源。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rmdir


class MnxdomConan(ConanFile):
    name = "mnxdom"
    version = "3.0.1"
    description = ("Document object model for the MNX music interchange format "
                   "(C++17 class framework around MNX JSON)")
    license = "MIT"
    homepage = "https://github.com/mnx-works/mnxdom"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("mnx", "music-notation", "json", "dom", "music")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "patches/*"

    # 随 mnxdom 一起编译的私有依赖源码目录（相对 source_folder）
    _embedded_dir = os.path.join("third_party", "json-schema-validator")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ohpcd 已发布的预编译包（R36：依赖先发布再构建下游）
        self.requires("nlohmann_json/3.12.0")

    def build_requirements(self):
        # 上游测试套件基于 googletest（tests/CMakeLists.txt）
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _posix(path):
        return path.replace("\\", "/")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游钉住的 json-schema-validator（见文档字符串第 2 条）：官方源 + 校验和，
        # 下载后交给上游的 FetchContent 使用，构建期不再联网。
        get(self, **self.conan_data["embedded_sources"]["json-schema-validator"],
            destination=os.path.join(self.source_folder, self._embedded_dir),
            strip_root=True)

    def generate(self):
        # 生成依赖的 CMake 配置文件（nlohmann_json / googletest）
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)

        # 依赖接线：全部使用本地已有源码 / 制品仓预编译包，关闭上游的联网路径
        tc.variables["USE_SYSTEM_NLOHMANN_JSON"] = True
        tc.variables["USE_SYSTEM_GOOGLETEST"] = True
        tc.variables["USE_SYSTEM_JSON_SCHEMA_VALIDATOR"] = False

        # 内嵌依赖：静态编译 + 随包安装（见文档字符串第 2/3 条）
        tc.variables["JSON_VALIDATOR_INSTALL"] = True
        tc.variables["JSON_VALIDATOR_SHARED_LIBS"] = False
        # 上游 jsv 的 CMakeLists 把开关写错了变量名（option 是 JSON_VALIDATOR_SHARED_LIBS，
        # 第 66 行实现读的却是 nlohmann_json_schema_validator_SHARED_LIBS），
        # 两个都设才能确保静态；上游修好后这一行可以删除。
        tc.variables["nlohmann_json_schema_validator_SHARED_LIBS"] = False

        # 让上游 FetchContent 直接使用 source() 阶段下发的本地源码
        embedded = os.path.join(self.source_folder, self._embedded_dir)
        if not os.path.isdir(embedded):
            raise ConanInvalidConfiguration(
                f"内嵌依赖源码目录不存在: {embedded}（conandata.yml 的 "
                "embedded_sources.json-schema-validator 未正确下发）")
        tc.variables["FETCHCONTENT_SOURCE_DIR_JSON_SCHEMA_VALIDATOR"] = self._posix(embedded)

        # googletest：指向依赖包内自带的、可重定位的上游 CMake 配置，
        # 以拿到 mnxdom 需要的 GTest::gtest_main / GTest::gtest 目标名。
        tc.variables["GTest_DIR"] = self._posix(os.path.join(
            self.dependencies["gtest"].package_folder, "lib", "cmake", "GTest"))

        # 上游 gtest 测试套件
        tc.variables["mnxdom_BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试套件（gtest，经 gtest_discover_tests 注册到 ctest）──
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # 内嵌依赖的静态库必须真的装进来，否则静态包无法被消费端链接
        embedded_lib = os.path.join(self.package_folder, "lib",
                                    "libnlohmann_json_schema_validator.a")
        if not os.path.isfile(embedded_lib):
            raise ConanException(
                "内嵌的 json-schema-validator 未以静态库形式安装: " + embedded_lib)

        # json-schema-validator 自带的 CMake 导出文件会把安装期绝对路径写死
        # （不可重定位），本包不经它导出，删除以免消费端误用。
        jsv_cmake_dir = os.path.join(self.package_folder, "lib", "cmake",
                                     "nlohmann_json_schema_validator")
        if os.path.isdir(jsv_cmake_dir):
            rmdir(self, jsv_cmake_dir)

    def package_info(self):
        # 内嵌编译的 json-schema-validator 是静态包的一部分，消费端需一并链接
        self.cpp_info.libs = ["mnxdom", "nlohmann_json_schema_validator"]
        self.cpp_info.bindirs = []

        # 上游没有安装 CMake 导出文件（无 install(EXPORT)），消费端经 CMakeDeps 使用。
        self.cpp_info.set_property("cmake_file_name", "mnxdom")
        self.cpp_info.set_property("cmake_target_name", "mnxdom::mnxdom")
        self.cpp_info.set_property("pkg_config_name", "mnxdom")

        # 公共头会 #include <nlohmann/json.hpp>，消费端需要该 header-only 依赖的
        # include 目录。（json-schema-validator 只在库内部使用，不是公共依赖。）
        self.cpp_info.requires = ["nlohmann_json::nlohmann_json"]
