#!/usr/bin/env python3
"""Conan recipe for indi-nightscape 1.0.6-20221222181314 — INDI driver for the
Celestron Nightscape 8300 CCD camera (CMake, C++).

History-based adaptation (archives/l/libindi/2.2.2.1, W0b):
  - E092: CMake 不识别 HarmonyOS 平台 → 强制 CMAKE_SYSTEM_NAME=Linux
  - CMake toolchain 默认 CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON 会 shadow 掉本项目
    自带 Find*.cmake 的旧式变量 (CFITSIO_INCLUDE_DIR/INDI_INCLUDE_DIR 等) →
    在 toolchain 末尾强制 OFF (PreferConfigOffBlock，与 libindi 同款)
  - cmake_minimum_required(3.0) 被新 CMake 拒绝 → CMAKE_POLICY_VERSION_MINIMUM=3.5
  - libindi 2.2.x 采用新 Property API (PropertyNumber/PropertyText 类) →
    nightscape.cpp 的旧 API 用法 (TemperatureN/BayerT/.s/operator&/IDSetNumber)
    按上游 master 已适配写法迁移 (TemperatureNP/BayerTP/getState()/apply()/save())
  - OHOS musl libc 无 secure_getenv → 统一用 getenv
  - FindINDI.cmake 版本正则不匹配带引号的 "2.2.2" → 放宽正则
  - FindFTDI1.cmake 未定义 FTDI1_INCLUDE_DIRS (CMakeLists 引用复数变量) →
    补 get_filename_component 派生父目录 (ftdi.h 在 include/libftdi1/ 下)
  - /lib/udev/rules.d 在 OHOS 上不可写 → udev rules 安装默认关闭
    (NIGHTSCAPE_INSTALL_UDEV_RULES=OFF，patch 新增选项)
  - INDI_DATA_DIR 找不到时回退 share/indi，避免 install 到 *-NOTFOUND

产物: indi_nightscape_ccd (INDI 驱动可执行) + nstest (上游测试工具)，均为
CLI 可执行文件 → package_type=application + commands.json (R38)。
"""
import os
import shutil
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches


class PreferConfigOffBlock(Block):
    """toolchain 末尾强制关闭 config 优先, 让本项目自带 Find*.cmake 模块生效"""
    template = textwrap.dedent("""\
        set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
    """)


class IndiNightscapeConan(ConanFile):
    name = "indi-nightscape"
    version = "1.0.6-20221222181314"
    description = "INDI driver for the Celestron Nightscape 8300 CCD camera"
    license = "LGPL-2.1"
    homepage = "https://www.indilib.org"
    url = "https://github.com/indilib/indi-3rdparty"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libindi/2.2.2.1")
        self.requires("cfitsio/4.6.4")
        self.requires("libusb/1.0.27")
        self.requires("libftdi/1.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 官方源是 indi-3rdparty 整仓 tarball, 驱动源码位于 indi-nightscape/ 子目录。
        # 本地验证时可用 NIGHTSCAPE_SRC_TARBALL 指向预打包的源码 tarball (含子目录内容)。
        local_tarball = os.environ.get("NIGHTSCAPE_SRC_TARBALL")
        if local_tarball and os.path.isfile(local_tarball):
            # 本地预打包源码 (内容与官方 commit 的 indi-nightscape/ 子目录一致)，
            # 用于网络受限环境的验证；CI/正式构建走官方 https 源分支
            get(self, url="file://" + local_tarball, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
            # 整仓 tarball strip_root 后: 源码根 = 仓库根，其中
            # indi-nightscape/ (本驱动源码) 与 cmake_modules/ (共享 Find*.cmake)
            # 是兄弟目录。把 indi-nightscape/ 的内容提升到源码根，
            # 使 CMakeLists 引用的 "${CMAKE_CURRENT_SOURCE_DIR}/cmake_modules/"
            # 与 "${CMAKE_CURRENT_SOURCE_DIR}/../cmake_modules/" 均指向仓库根的
            # cmake_modules/（提升后 ../cmake_modules 与 ./cmake_modules 等价）。
            subdir = os.path.join(self.source_folder, "indi-nightscape")
            if os.path.isdir(subdir):
                for entry in os.listdir(subdir):
                    shutil.move(os.path.join(subdir, entry), os.path.join(self.source_folder, entry))
                os.rmdir(subdir)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake 不识别 HarmonyOS 平台，必须显式用 Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # cmake_minimum_required(3.0) 在新 CMake (>=3.28) 上被拒绝
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # /lib/udev 在 OHOS 上不可写，patch 新增选项默认关闭
        tc.variables["NIGHTSCAPE_INSTALL_UDEV_RULES"] = "OFF"
        # 强制本项目自带 Find*.cmake 生效 (toolchain 末尾覆盖默认 ON)
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        build_jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{build_jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游测试工具 nstest 未被 CMake install，但它是官方交付的一部分
        # (R51 上游测试清点)，随包一并放入 bin/ 供 test_package 与用户使用
        nstest = os.path.join(self.build_folder, "nstest")
        if os.path.isfile(nstest):
            copy(self, "nstest", src=os.path.dirname(nstest),
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # 纯 CLI 工具 (驱动 + 测试程序)，无库产物
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # OHOS libc++ 标准库 (libindi 历史验证：需链接 c++/c++abi，此处驱动
        # 在运行时由动态链接的 libindidriver 承担，仅记录供消费者参考)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self.cpp_info.system_libs = ["c++", "c++abi"]
