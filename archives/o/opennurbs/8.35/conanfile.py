#!/usr/bin/env python3
"""Conan recipe for opennurbs 8.35 on HarmonyOS PC (aarch64).

OpenNURBS 是 Robert McNeel & Associates 开源的 **NURBS 几何内核**（Rhino 的
几何库开源版）：`ON_3dPoint` / `ON_Curve` / `ON_Brep` / `ON_Mesh` 等 C++ 类，
读写 3DM 文件。本仓中它是 **Trilinos `percept`（Monty）** 的可选几何 TPL
（`LIB_OPTIONAL_TPLS OpenNURBS`），故作为独立制品包提供。

## 上游形态与「引用固定」的已知瑕疵

上游仓库 (`mcneel/opennurbs`) **没有 release / tag**，只有分支（本包取 `8.x`）；
本机到 GitHub 的 ref 查询通道（`api.github.com` / `git ls-remote` /
`commits.atom`）均不可达，无法取 commit sha 来钉永不变更的归档 URL。
故 conandata 钉的是**分支归档 + sha256**（2026-10-16 实测 74943888 字节），
漂移风险与后续钉法写在 conandata.yml 的注释里。

## 构建面（实测自上游 CMakeLists）

- `cmake_minimum_required(VERSION 3.16)`，`project(opennurbs CXX)`；
- 同时产出**两个**库目标：`opennurbsStatic`（STATIC）与 `OpenNURBS`（SHARED），
  二者都被 `install()` 到 `lib/`；公共头装到 `include/opennurbsStatic` 与
  `include/OpenNURBS`（上游布局如此，两处内容相同）；
- **零外部依赖**：zlib 与 freetype263 均为**仓内 vendored**
  （`add_subdirectory(zlib)` / `freetype263`），故本配方没有 `requires()`；
- 编译定义 `-DUNICODE -D_UNICODE -DON_CMAKE_BUILD` 由项目自身设置；
- 无 `enable_testing()`/`add_test()` 注册（上游没有 CTest 套件），
  故 R51 侧以**消费侧端到端测试**作为验证（见 test_package）。
"""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, download, replace_in_file, unzip


class OpenNurbsConan(ConanFile):
    name = "opennurbs"
    version = "8.35"
    description = ("OpenNURBS 3DM geometry kernel (NURBS curves/surfaces/breps) "
                   "for HarmonyOS PC")
    license = "Zlib"
    homepage = "https://github.com/mcneel/opennurbs"

    # Conan 2 校验：package_type="library" 必须声明 shared 选项。而上游
    # CMakeLists 是**一次构建同时产出**静态（opennurbsStatic）与动态（OpenNURBS）
    # 两个目标，无法用选项切换 ⇒ 按主交付物如实标为 shared-library，
    # 附带产出的静态库在 notes.md 中说明。
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload 的归档 URL 末段是分支名（`…/tar.gz/refs/heads/8.x`），**没有
        # 扩展名**，Conan 无从判断格式，会按 zip 处理并报
        # `BadZipFile: File is not a zip file`（实测）。故显式落成 .tar.gz 再解包。
        data = self.conan_data["sources"][self.version]
        url = data["url"]
        if isinstance(url, list):
            url = url[0]
        archive = os.path.join(self.source_folder, "opennurbs-8.35.tar.gz")
        # 源包 75MB，实测 codeload 会出现读超时（Read timed out, timeout=30）⇒
        # 显式重试；CI 侧受限 Worker 更需要。
        download(self, url=url, filename=archive,
                 sha256=data.get("sha256", ""),
                 retry=5, retry_wait=15)
        # 本机 Conan 2.29.1 的 conan.tools.files **没有 untar**，解包统一走 unzip
        # （按扩展名分发，支持 .tar.gz/.tgz/.tar.bz2/.tar.xz 与 .zip）——
        # 故下载时显式落成 .tar.gz 名字，才能被正确识别。
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.unlink(archive)
        # opennurbs_defines.cpp 的 ON::CloseAllFiles() 在非 MSVC/非 Apple-Android-WASM
        # 分支调用 fcloseall()——它是 glibc 扩展，musl（OHOS）不提供，编译直接报
        # `use of undeclared identifier 'fcloseall'`。上游本就为无 fcloseall 的平台
        # 备了 EOF 回退，只是没覆盖 HarmonyOS；这里把条件扩到 __OHOS__ 与配方显式
        # 定义的 ON_RUNTIME_NO_FCLOSEALL（双保险）。
        # 用 replace_in_file 而非 .patch 文件：该文件是 2881 行、源自 Windows 的历史
        # 文件，逐行上下文对补丁格式过于敏感（实测 hunk 无法命中），单行替换更稳。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "opennurbs_defines.cpp"),
            "#elif defined(ON_RUNTIME_APPLE) || defined(ON_RUNTIME_ANDROID) "
            "|| defined(ON_RUNTIME_WASM)",
            "#elif defined(ON_RUNTIME_APPLE) || defined(ON_RUNTIME_ANDROID) "
            "|| defined(ON_RUNTIME_WASM) || defined(__OHOS__) "
            "|| defined(ON_RUNTIME_NO_FCLOSEALL)",
        )

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake **没有** HarmonyOS 平台文件（日志反复提示 "System is unknown to cmake,
        # create: Platform/HarmonyOS"）⇒ CMake 的 `LINUX` 变量为假，而上游的
        #   if (LINUX AND NOT ANDROID) target_link_libraries(OpenNURBS zlib
        #       opennurbs_public_freetype android_uuid)
        # 因此**不成立** → 共享库 libOpenNURBS.so 里 z_deflate*/uuid_generate 等
        # 符号未解析、也没有对应 DT_NEEDED（实测 readelf -d 只有 libc/libc++），
        # 消费方链接即报 `--no-allow-shlib-undefined: undefined reference`。
        # 本机编译器 target 就是 aarch64-unknown-linux-ohos，按本仓既有做法把系统名
        # 呈现为 Linux 即可（与 bliss/trilinos 注入 user_toolchain 的做法同源）；
        # 用 cache var 传递以确保覆盖 conan toolchain 里的 set()。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # 系统名呈现为 Linux 后，vendored 的 android_uuid/ 子目录被纳入配置，而它的
        # `cmake_minimum_required` 低于 3.5，CMake 4 直接报
        #   Compatibility with CMake < 3.5 has been removed from CMake.
        # （报错本身给出了官方开关。）同一坑在 kdevelop-pg-qt 上也踩过。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游 opennurbs_defines.cpp:502 的 fcloseall() 是 glibc 扩展，musl（OHOS）
        # 不提供；补丁把上游自带的 EOF 回退分支扩到 __OHOS__ / ON_RUNTIME_NO_FCLOSEALL，
        # 这里显式定义后者（双保险，不依赖工具链预定义宏）。
        tc.variables["CMAKE_CXX_FLAGS"] = (
            "${CMAKE_CXX_FLAGS} -DON_RUNTIME_NO_FCLOSEALL=1")
        # 上游没有 CTest 套件；关掉 BUILD_TESTING 免得它额外生成测试头。
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ------------------------------------------------------------------ #
    #  OHOS ELF 自签（E318）
    # ------------------------------------------------------------------ #
    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as handle:
                ident = handle.read(18)
            if len(ident) < 18 or ident[:4] != b"\x7fELF":
                return 0
            return int.from_bytes(ident[16:18], "little")
        except (OSError, IndexError):
            return 0

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=120)
        except subprocess.TimeoutExpired:
            raise ConanInvalidConfiguration(f"Timed out while trying to {action}")
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"Failed to {action}: {result.stderr.strip()}"
            )
        return result.stdout

    def _resolve_tool(self, env_name, default):
        tool = os.environ.get(env_name, "") or default
        resolved = shutil.which(tool)
        if resolved:
            return resolved
        for candidate in (f"/data/service/hnp/bin/{tool}",
                          f"/data/service/hnp/{tool}"):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanInvalidConfiguration(
            f"Required tool '{tool}' ({env_name}) was not found"
        )

    def _has_codesign_section(self, objdump, path):
        table = self._run_tool([objdump, "-h", path],
                               f"inspect ELF sections in {path}")
        return any(".codesign" in line.split() for line in table.splitlines())

    def _sign_installed_elfs(self):
        binaries = []
        for root, _dirs, filenames in os.walk(self.package_folder):
            for name in filenames:
                path = os.path.join(root, name)
                if not os.path.islink(path) and self._elf_type(path) in (2, 3):
                    binaries.append(path)
        if not binaries:
            self.output.warning("no shared/executable ELF in the package to sign")
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    f"sign {binary}",
                )
                if (not os.path.isfile(signed)
                        or self._elf_type(signed) not in (2, 3)):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, mode)
        self.output.info(f"signed {len(binaries)} ELF(s)")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 opennurbs_system.h 在 ON_RUNTIME_LINUX（OHOS 走该分支）下
        # `#include "android_uuid/uuid.h"`，但 android_uuid 的头**不在上游 install
        # 规则里**（只有构建树可见）⇒ 消费方编译必然报
        #   fatal error: 'android_uuid/uuid.h' file not found   （实测）
        # 故把该目录的头随包安装到两个已装头目录下（与上游头布局一致）。
        for sub in ("OpenNURBS", "opennurbsStatic"):
            copy(self, "*.h",
                 src=os.path.join(self.source_folder, "android_uuid"),
                 dst=os.path.join(self.package_folder, "include", sub,
                                  "android_uuid"))
        # 上游的 OPENNURBS_PUBLIC_HEADERS 安装清单**本身也不完整**：源码根目录有
        # 179 个 .h，实际安装 169 个，而被 opennurbs.h 第 43 行包含的
        # opennurbs_cpp_base.h 恰在漏装之列 ⇒ 消费方编译报
        #   fatal error: 'opennurbs_cpp_base.h' file not found   （实测）
        # 故把源码根目录的头整套补齐（与 cmake.install() 结果重合部分内容一致）。
        for sub in ("OpenNURBS", "opennurbsStatic"):
            copy(self, "*.h", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include", sub))
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # 上游不装 CMake config，消费方（含 Trilinos 的 FindTPLOPENNURBS）走
        # 「头 + 库」定位：头在 include/OpenNURBS 与 include/opennurbsStatic 两处
        # （上游布局如此，内容相同）。
        # 库只默认暴露**共享**的 libOpenNURBS.so —— 它是本包主交付物；附带的
        # libopennurbsStatic.a 与它符号重复，若一起列进 libs 会导致消费方重复符号
        # （上游一次构建同时产出两个目标，见 notes.md）。
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/OpenNURBS", "include/opennurbsStatic"]
        self.cpp_info.libs = ["OpenNURBS"]
