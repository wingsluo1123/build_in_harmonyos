#!/usr/bin/env python3
"""Conan recipe for interception-dual-function 1.5.0.

dual-function-keys 是 interception-tools 的双功能键插件：从 stdin 读入
Linux input_event 二进制流，按 YAML 配置把「轻按 / 长按」映射到不同按键，
再把事件写回 stdout。上游是裸 Makefile 工程，产物为单个命令行可执行文件。

OHOS (aarch64-linux-ohos) 适配要点：
  1. 依赖 yaml-cpp（静态）与 libevdev（动态）；两者 OHOS binary 均已发布到
     制品仓（W0 已用 conan download 核验可消费）。
  2. 内核 UAPI 头 linux/input.h 由 OHOS clang 15 sysroot 自带，无需注入。
  3. patches/0001：build_tap()/build_hold() 对标量 YAML 节点误用
     YAML::Node::size()（yaml-cpp 对标量返回 0），calloc(0, sizeof(Mapping))
     只得到 1 字节可用堆块，随后写 ->code 越界。glibc 的 calloc(0) 返回块
     足够大而侥幸不崩，OHOS musl 下必崩（SIGSEGV，实测 rc=139）。两处标量
     分支改为 calloc(1, sizeof(Mapping))。
  4. R33：编译器取自 Conan profile（tools.build:compiler_executables）；
     Makefile 硬编码的 CC/CXX/INCS/CFLAGS/CXXFLAGS/LDFLAGS 用命令行变量覆盖
     （GNU make 命令行变量优先于 Makefile 赋值）。CFLAGS 去掉上游的 -Werror
     ——clang 15 对上游 K&R 风格函数定义报 -Wstrict-prototypes。
  5. OHOS 上新编译 ELF 必须 selfSign 后才能执行（E077/E135）。

上游无自动化测试（无 tests/ 目录，无 make test / ctest / pytest 入口），
功能验证经 test_package 的事件注入用例完成（R51 清点见
test_package/MANIFEST.yml）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

_SIGNER = "/data/service/hnp/bin/binary-sign-tool"


class InterceptionDualFunctionConan(ConanFile):
    name = "interception-dual-function"
    version = "1.5.0"
    description = ("interception-tools plugin: tap for one key, "
                   "hold for another (dual function keys)")
    license = "MIT"
    homepage = "https://gitlab.com/interception/linux/plugins/dual-function-keys"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("yaml-cpp/0.8.0")
        self.requires("libevdev/1.13.7")

    def layout(self):
        # 上游无 out-of-tree 构建，直接在源码目录内编译。
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: POSIX 平台门禁（Linux input_event 面 + libevdev）
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("dual-function-keys requires a Linux-compatible host "
                      "(Linux or OHOS)")
        apply_conandata_patches(self)

        # R33: 编译器来自 Conan conf，禁止裸用 shell 环境变量
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c", "clang")
        cxx = ce.get("cpp", "clang++")

        yaml_cpp = self.dependencies["yaml-cpp"].package_folder
        evdev = self.dependencies["libevdev"].package_folder

        # 上游 config.mk 把依赖头文件放在 INCS、库放在 LDFLAGS；
        # 这两处均用命令行变量覆盖，其余（-D_POSIX_C_SOURCE/-DVERSION）保持上游原样。
        incs = f"-I{yaml_cpp}/include -I{evdev}/include/libevdev-1.0"
        ldflags = (f"-rdynamic -L{yaml_cpp}/lib -L{evdev}/lib "
                   f"-lyaml-cpp -levdev")
        # 上游 COMPFLAGS 含 -Werror；clang 15 对 K&R 风格定义报
        # -Wstrict-prototypes，故显式覆盖 CFLAGS/CXXFLAGS 去掉 -Werror。
        cflags = "-pedantic -Wall -Wextra -O3 -std=c99"
        cxxflags = "-pedantic -Wall -Wextra -O3 -std=c++11"

        self.output.info(f"build: CC={cc} CXX={cxx} INCS={incs}")
        self.run(
            f'make -j1 CC="{cc}" CXX="{cxx}" '
            f'INCS="{incs}" '
            f'CFLAGS="{cflags}" CXXFLAGS="{cxxflags}" '
            f'LDFLAGS="{ldflags}"'
        )

    def package(self):
        # 包名（interception-dual-function）≠ 产物名（dual-function-keys）
        exe = "dual-function-keys"
        bin_dir = os.path.join(self.package_folder, "bin")
        copied = copy(self, exe, self.build_folder, bin_dir,
                      keep_path=False)
        if not copied:
            raise ConanException(
                f"built executable not found: {exe} "
                f"(build_folder={self.build_folder})")
        copy(self, "dual-function-keys.1", self.build_folder,
             os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "dual-function-keys.md", self.build_folder,
             os.path.join(self.package_folder, "share", "doc", self.name),
             keep_path=False)
        copy(self, "LICENSE.md", self.build_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        os.chmod(os.path.join(bin_dir, exe), 0o755)
        if self.settings.os == "OHOS":
            self._sign_elf(os.path.join(bin_dir, exe))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    def _sign_elf(self, binary):
        """OHOS 上为新编译 ELF 做 selfSign 并赋执行位（E077/E135）。"""
        if not os.path.isfile(_SIGNER):
            self.output.warning("binary-sign-tool not found; "
                                "skip OHOS codesign")
            return
        self.run(f'{_SIGNER} sign -inFile "{binary}" -outFile "{binary}" '
                 f'-selfSign 1')
