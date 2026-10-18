#!/usr/bin/env python3
"""Conan recipe for indi-apogee 1.9-20221223184417 — INDI 阿普奇(Apogee) CCD 相机 / 滤光轮驱动.

OHOS aarch64 适配要点（详见 notes.md）：
  - E092：CMake 不识别 HarmonyOS → CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64
  - cmake_minimum_required(3.0) → CMake>=4 需 CMAKE_POLICY_VERSION_MINIMUM=3.5，
    且**必须走命令行 -D**（cache 变量）：工具链文件要到 project() 才被 CMake 加载，
    而 CMakeLists.txt:1 的 cmake_minimum_required 早于它执行，toolchain 里 set() 的同名
    变量读不到（真机构建实测；归档内 archives/a/amqp-cpp/4.3.27 有同款注释与做法）
  - CMakeCommon.cmake 强制 C++14 → 覆写 CMAKE_CXX_STANDARD=17（libindi 2.2.2.1 头文件用 std::any）
  - FindINDI.cmake 版本正则兼容带引号 INDI_VERSION（patch）
  - libapogee3 的 cpp_info.includedirs 是 include/libapogee（其公有头互相扁平 #include），
    而上游驱动源码用 #include <libapogee/Xxx.h>（在 Debian 上靠 /usr/include 隐式路径命中），
    交叉环境必须显式补 -I<libapogee3>/include
  - INDI_DATA_DIR 由 FindINDI.cmake 的 find_path(drivers.xml) 决定；制品仓未提供该文件会得到
    <VAR>-NOTFOUND，install(FILES) 会落到垃圾目录 → 必须显式指定
  - 驱动入口 main() 由 libindi 的 libs/indibase/indidrivermain.c 提供（编进 libindidriver），
    驱动源码里本来就没有 main —— 这是 INDI 3rdparty 的通用约定，不是缺文件
  - 链接 c++/c++abi（OHOS libc++ 标准库，libindi 2.2.2.1 配方同款经验）
  - E077：产物是 bin/ 下的可执行文件，而 HarmonyOS 内核只执行带有效 .codesign 的 ELF
    （否则 execve 报 "Operation not permitted"，构建与打包成功也一样；chmod 无用）→
    在 package() 里对两个二进制做 llvm-objcopy 去旧 .codesign + binary-sign-tool -selfSign 1
"""
import os
import shlex
import shutil
import textwrap

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PreferConfigOffBlock(Block):
    """toolchain 末尾强制关闭 config 优先, 让项目自带 Find*.cmake 模块生效"""
    template = textwrap.dedent("""\
        set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
    """)


class IndiApogeeConan(ConanFile):
    name = "indi-apogee"
    version = "1.9-20221223184417"
    description = "INDI drivers for Apogee CCD cameras (indi_apogee_ccd) and filter wheels (indi_apogee_wheel)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://deb.debian.org/debian/pool/main/i/indi-apogee/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libindi/2.2.2.1")
        self.requires("libapogee3/3.2+20221221183454")
        self.requires("cfitsio/4.6.4")
        self.requires("zlib/1.3.1.1")
        # curl 版本冲突消解：libindi 钉 curl/8.15.0.1，libapogee3 钉 curl/8.15.0，
        # 二者在同一张图里直接冲突（Conflict originates from libapogee3）。
        # 统一到 8.15.0.1：它与 8.15.0 同源码，只是 R37 适配修复（修 8.15.0 在
        # HMDFS 上的日志目录问题），ABI 一致；反过来迁就 8.15.0 会把已知缺陷带回来。
        # 用 force=True 而非 override=True：libapogee3 的 generate() 走 CMakeDeps，
        # 需要 curl 是**真实节点**（有 package_folder）；override-only 节点的
        # package_folder 是 None，会让 libapogee3 那边的 CMakeDeps 失效。
        self.requires("curl/8.15.0.1", force=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake 不识别 HarmonyOS 平台，必须显式用 Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # cmake_minimum_required(3.0) 在 CMake>=4 直接报错，放行旧策略。
        # 这一行只是兜底：工具链文件由 CMake 在 project() 时才加载，而 CMakeLists.txt:1
        # 的 cmake_minimum_required 早于它执行，读不到 toolchain 里的 set()。
        # 真机实测：上一次只设了这一行，configure 仍在第 1 行报
        # 'Compatibility with CMake < 3.5 has been removed'。
        # 真正生效的是 build() 里用命令行 -D 传的 cache 变量（同归档 amqp-cpp 4.3.27）。
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CMakeCommon.cmake 强制 C++14，libindi 2.2.2.1 需要 std::any (C++17)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # OHOS libc++：链接 c++/c++abi；
        # 再把 libapogee3 的 include 根加进搜索路径 —— 上游写的是 <libapogee/Alta.h>，
        # 而 libapogee3 只暴露 include/libapogee（供其扁平公有头使用），
        # Debian 上这两条路径同时成立只因为 /usr/include 是隐式的。
        apogee_include_root = os.path.join(
            self.dependencies["libapogee3"].package_folder, "include"
        ).replace("\\", "/")
        tc.variables["CMAKE_CXX_FLAGS"] = f"-lc++ -lc++abi -I{apogee_include_root}"
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # INDI_DATA_DIR：上游 CMakeLists 用它决定 install(FILES indi_apogee.xml) 的去处，
        # 由 FindINDI.cmake 的 find_path(drivers.xml PATH_SUFFIXES share/indi) 得出。
        # 制品仓的 libindi 不装 drivers.xml，find_path 会失败并留下 <VAR>-NOTFOUND，
        # 于是 XML 会被装进名为 “INDI_DATA_DIR-NOTFOUND” 的目录。显式钉到本包内。
        data_dir = os.path.join(self.package_folder, "share", "indi").replace("\\", "/")
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM 必须走命令行（cache 变量）：CMakeLists.txt:1 的
        # cmake_minimum_required(VERSION 3.0) 早于工具链文件被加载，toolchain 里的同名
        # 变量到不了那一行。CMake 自带的报错提示也是让这样加 -D。
        cmake.configure(
            variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"},
            cli_args=[f"-DINDI_DATA_DIR={data_dir}"],
        )
        build_jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{build_jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # E077：HarmonyOS 内核只执行带有效 .codesign 数据的 ELF，否则 execve 返回
        # EPERM("Operation not permitted") —— 真机首次构建时 test_package 的探针就是
        # 这样失败的。签名必须作用于**最终 package 里的文件**，只 chmod 无效。
        self._sign_binaries()

    def package_info(self):
        # 纯 CLI 工具包：无可链接库（两个可执行文件：indi_apogee_ccd / indi_apogee_wheel）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.system_libs = []

    # ------------------------------------------------------------------ E077
    def _sign_tool(self):
        """定位 binary-sign-tool（HNP 公开工具链目录，兜底查 PATH）。"""
        candidates = [
            "/data/service/hnp/bin/binary-sign-tool",
            os.path.join(
                os.environ.get("HNP_PUBLIC_HOME", "/data/service/hnp"),
                "bin",
                "binary-sign-tool",
            ),
        ]
        for d in os.environ.get("PATH", "").split(":"):
            if d:
                candidates.append(os.path.join(d, "binary-sign-tool"))
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        return shutil.which("binary-sign-tool")

    def _sign_elf(self, elf_path, sign_tool):
        """去旧 .codesign → 自签名 → 回写并补回 0755（E077，照归档既有做法）。"""
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        # 首次签名时文件里本就没有 .codesign，objcopy 会以非 0 退出，属正常
        self.run(
            f"{shlex.quote(objcopy)} --remove-section .codesign "
            f"{shlex.quote(elf_path)} || true"
        )
        signed = elf_path + ".signed.tmp"
        self.run(
            f"{shlex.quote(sign_tool)} sign -inFile {shlex.quote(elf_path)} "
            f"-outFile {shlex.quote(signed)} -selfSign 1"
        )
        if not os.path.isfile(signed):
            raise ConanException(f"ELF signing produced no output for {elf_path}")
        os.replace(signed, elf_path)
        os.chmod(elf_path, 0o755)
        # 回读签名信息：签名工具若静默产出未签名文件，这里就能当场发现，
        # 而不是等到 test_package 再报一次 EPERM（照 jupyter-events 的做法）。
        self.run(f"{shlex.quote(sign_tool)} display-sign -inFile {shlex.quote(elf_path)}")

    def _sign_binaries(self):
        binaries = ("indi_apogee_ccd", "indi_apogee_wheel")
        bin_dir = os.path.join(self.package_folder, "bin")
        missing = [n for n in binaries if not os.path.isfile(os.path.join(bin_dir, n))]
        if missing:
            raise ConanException(f"expected binary not installed: {', '.join(missing)}")
        sign_tool = self._sign_tool()
        if sign_tool is None:
            if self.settings.os == "OHOS":
                raise ConanException(
                    "OHOS: binary-sign-tool not found, cannot sign ELF (E077)"
                )
            # 非 OHOS 目标（如本地语法检查）不要求签名工具在场
            self.output.warning("binary-sign-tool not found; skip ELF signing (E077)")
            return
        for name in binaries:
            path = os.path.join(bin_dir, name)
            self._sign_elf(path, sign_tool)
            self.output.info(f"ELF signed: {path}")
