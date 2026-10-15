#!/usr/bin/env python3
"""Conan recipe for shaderc 2026.3.

shaderc 是 Google 的着色器编译工具集（libshaderc 库 + glslc 命令行）。
其源码树不含子模块，glslang / SPIRV-Tools / SPIRV-Headers 三个依赖的提交
由上游 DEPS 文件固定，本配方按同源提交拉取并摆放成上游要求的 third_party 布局。
"""
import os
import shutil
import tarfile
import tempfile
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    download,
    export_conandata_patches,
    get,
)

# key → third_party 下的目标目录（键名对应 conandata.yml 的 resources）
THIRD_PARTY_DIRS = {
    "glslang": "glslang",
    "spirv_tools": "spirv-tools",
    "spirv_headers": "spirv-headers",
}

# 静态链接 libshaderc 时需要用到的 vendored 静态库（顺序与上游链接顺序一致）
PREFERRED_LIBS = [
    "shaderc",
    "shaderc_util",
    "glslang",
    "SPIRV",
    "MachineIndependent",
    "OSDependent",
    "GenericCodeGen",
    "glslang-default-resource-limits",
    "SPIRV-Tools-opt",
    "SPIRV-Tools-link",
    "SPIRV-Tools-lint",
    "SPIRV-Tools-reduce",
    "SPIRV-Tools-diff",
    "SPIRV-Tools",
]


# 受限 CI worker 在进程/内存压力下 fork/exec 会瞬时返回 EAGAIN，make 只把
# strerror 文本裸打到日志里；仓库既有归档同签名处置见 libcmis 0.6.3 /
# libcolord 1.4.8 / mgen 5.02.c5.1.1。
FORK_PRESSURE_MARKERS = (
    "resource temporarily unavailable",
    "can't fork",
    "cannot fork",
    "unable to fork",
    "fork failed",
    "try again",
)

# CMake 的 try-compile 输出不走 conan 的异常串（只有 "Error 1 while executing"），
# 真实的 fork/exec 报错落在 CMake 自己的诊断文件里，按此回查。
_CMAKE_DIAG_FILES = (
    os.path.join("CMakeFiles", "CMakeConfigureLog.yaml"),
    os.path.join("CMakeFiles", "CMakeError.log"),
    os.path.join("CMakeFiles", "CMakeOutput.log"),
)


class ShadercConan(ConanFile):
    name = "shaderc"
    version = "2026.3"
    description = "Toolkit for compiling GLSL/HLSL to SPIR-V (libshaderc library and glslc tool)"
    license = "Apache-2.0"
    homepage = "https://github.com/google/shaderc"
    url = ""
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} 仅支持 Linux / OHOS")

    def layout(self):
        cmake_layout(self, generator="Ninja" if self._ninja_path() else None)

    def _ninja_path(self):
        """探测可用的 ninja；未命中返回 None，此时保持 conan 默认生成器。

        cmake 本版本不会自动选 ninja（无 conf 时固定 Unix Makefiles）。CI worker
        上 Makefiles 生成器要额外 fork `/bin/sh` 执行每条规则，在进程/句柄紧张的
        worker 上是 try-compile 最先失败的环节（仓库知识 E346）；ninja 直接 exec
        编译器。探测失败时行为与改动前完全一致，不引入新的硬依赖。
        """
        candidates = (
            os.environ.get("HMBS_NINJA"),
            self.conf.get("user.hmbs:ninja_path", check_type=str),
            shutil.which("ninja"),
            "/data/service/hnp/bin/ninja",
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def export_sources(self):
        # 本版本无需平台补丁（conandata.yml 的 patches 为空），保留标准结构
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        for key, dirname in THIRD_PARTY_DIRS.items():
            self._extract_resource(
                self.conan_data["resources"][key],
                os.path.join(self.source_folder, "third_party", dirname),
            )
        # SPIRV-Tools 要求自身 external/spirv-headers 下有同源副本
        headers_dir = os.path.join(self.source_folder, "third_party", "spirv-headers")
        external_dir = os.path.join(
            self.source_folder, "third_party", "spirv-tools", "external", "spirv-headers"
        )
        if os.path.isdir(external_dir):
            shutil.rmtree(external_dir)
        shutil.copytree(headers_dir, external_dir)

    def _extract_resource(self, resource, dst):
        archive_path = os.path.join(self.source_folder, "_shaderc_third_party.tar.gz")
        download(self, url=resource["url"], filename=archive_path, sha256=resource["sha256"])
        try:
            with tempfile.TemporaryDirectory(dir=self.source_folder) as tmp_extract:
                with tarfile.open(archive_path, "r:gz") as archive:
                    archive.extractall(tmp_extract)
                roots = [
                    os.path.join(tmp_extract, name) for name in os.listdir(tmp_extract)
                ]
                roots = [path for path in roots if os.path.isdir(path)]
                if len(roots) != 1:
                    raise ConanException("第三方源码包目录结构不符合预期")
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.move(roots[0], dst)
        finally:
            if os.path.isfile(archive_path):
                os.unlink(archive_path)

    def generate(self):
        ninja = self._ninja_path()
        tc = CMakeToolchain(self, generator="Ninja" if ninja else None)
        if ninja:
            tc.cache_variables["CMAKE_MAKE_PROGRAM"] = ninja
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        # 只交付 shaderc 自身产物：跳过上游测试/示例/版权检查
        tc.cache_variables["SHADERC_SKIP_TESTS"] = "ON"
        tc.cache_variables["SHADERC_SKIP_EXAMPLES"] = "ON"
        tc.cache_variables["SHADERC_SKIP_COPYRIGHT_CHECK"] = "ON"
        # OHOS clang 驱动会向编译命令注入 --gcc-toolchain=<sdk>，shaderc 默认开启
        # 的 -Werror 会把它判为 -Wunused-command-line-argument 直接失败。
        tc.cache_variables["SHADERC_ENABLE_WERROR_COMPILE"] = "OFF"
        # vendored 的 glslang / SPIRV-Tools 只取其库，命令行与测试一律不构建
        tc.cache_variables["ENABLE_GLSLANG_BINARIES"] = "OFF"
        tc.cache_variables["SPIRV_SKIP_EXECUTABLES"] = "ON"
        tc.cache_variables["SPIRV_SKIP_TESTS"] = "ON"
        tc.cache_variables["SPIRV_WERROR"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        self._configure_with_fork_retry(cmake)
        cmake.build()

    def _configure_with_fork_retry(self, cmake, attempts=4, delay=20):
        """worker 进程耗尽导致的瞬时 EAGAIN 不判负，退避重试 CMake 配置。

        实测（PR #15630）：同一份配方在 CI-028（build #89806）用同一 `Unix
        Makefiles` 生成器完整构建且 test_package 通过；CI-010（#90378）与
        CI-022（#91195）两次都在 build() 的**第一个** make 子进程上失败——CMake
        编译器可用性探测的 try-compile 报 `resource temporarily unavailable`
        （fork/exec EAGAIN），彼时尚未执行任何本包构建逻辑。配置幂等，故按仓库
        既有惯例退避重试；**仅当命中 EAGAIN 签名时重试**，真实配置错误一次即抛。
        """
        for attempt in range(1, attempts + 1):
            try:
                return cmake.configure()
            except Exception as exc:
                if attempt >= attempts or not self._has_fork_pressure(exc):
                    raise
                wait = delay * attempt
                self.output.warning(
                    "CMake.configure 命中 worker fork/资源压力（第 {}/{} 次）：{}；"
                    "{} 秒后重试".format(attempt, attempts, exc, wait)
                )
                # 上一次失败可能留下半截探测结果，重试前清干净
                self._drop_cmake_configure_state()
                time.sleep(wait)

    def _has_fork_pressure(self, exc):
        """判断失败是否属 fork/exec EAGAIN 族（瞬时，可重试）。"""
        if any(marker in str(exc).lower() for marker in FORK_PRESSURE_MARKERS):
            return True
        for rel in _CMAKE_DIAG_FILES:
            path = os.path.join(self.build_folder, rel)
            try:
                if not os.path.isfile(path):
                    continue
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()[-12000:]
            except OSError:
                continue
            if any(marker in text.lower() for marker in FORK_PRESSURE_MARKERS):
                return True
        return False

    def _drop_cmake_configure_state(self):
        """清掉失败配置留下的状态，避免重试沿用半截探测结果。"""
        for rel in ("CMakeCache.txt", "CMakeFiles"):
            target = os.path.join(self.build_folder, rel)
            try:
                if os.path.isdir(target):
                    shutil.rmtree(target)
                elif os.path.exists(target):
                    os.unlink(target)
            except OSError:
                pass

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._install_shaderc_util()
        self._prune_vendored_artifacts()
        self._drop_soname_less_shared_lib()

    def _install_shaderc_util(self):
        """补齐上游 install 规则遗漏的 libshaderc_util.a。

        libshaderc 的公开静态库依赖 shaderc_util 组件，但上游 install 规则只安装
        libshaderc.a / libshaderc_combined.a / libshaderc_shared.so，不安装
        libshaderc_util.a，静态链接的消费者会报 shaderc_util 符号未定义。
        """
        for root, _dirnames, filenames in os.walk(self.build_folder):
            if "libshaderc_util.a" in filenames:
                shutil.copy2(
                    os.path.join(root, "libshaderc_util.a"),
                    os.path.join(self.package_folder, "lib", "libshaderc_util.a"),
                )
                return
        raise ConanException("构建树中未找到 libshaderc_util.a")

    def _prune_vendored_artifacts(self):
        """只保留 shaderc 对外产物：shaderc 头文件、静态库、glslc 命令行。

        vendored 的 glslang / SPIRV-Tools 仅作为静态库实现被本包消费，
        它们的头文件、CMake 包配置、pkgconfig 与共享库不对外交付
        （同名成品库在制品仓内另有独立配方）。
        """
        pkg = self.package_folder
        for rel in (
            os.path.join("include", "glslang"),
            os.path.join("include", "spirv-tools"),
            os.path.join("lib", "cmake"),
        ):
            target = os.path.join(pkg, rel)
            if os.path.isdir(target):
                shutil.rmtree(target)
        for rel in (
            os.path.join("lib", "libSPIRV-Tools-shared.so"),
            os.path.join("lib", "libSPIRV-Tools-shared.so.1"),
            os.path.join("lib", "pkgconfig", "SPIRV-Tools-shared.pc"),
            os.path.join("lib", "pkgconfig", "SPIRV-Tools.pc"),
        ):
            target = os.path.join(pkg, rel)
            if os.path.exists(target):
                os.unlink(target)

    def _drop_soname_less_shared_lib(self):
        """不交付未携带 DT_SONAME 的 libshaderc_shared.so。

        本包声明为 static-library，对外只交付静态库与 glslc（glslc 已静态链接，
        DT_NEEDED 仅 libc++_shared.so / libc.so）。conan 构建侧 CMAKE_SYSTEM_NAME
        被映射为 HarmonyOS，CMake 无对应 platform module，上游 libshaderc 的
        SOVERSION 1 因此不生效，产物既无版本后缀也无 DT_SONAME。此类共享库在
        链接期无法按 SONAME 定位，且会被 collect_libs 收进链接项，故从包内剔除；
        指向它的 pkgconfig 条目同步改写为静态库。
        """
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for name in os.listdir(lib_dir):
                if name.startswith("libshaderc_shared.so"):
                    os.unlink(os.path.join(lib_dir, name))
        pc = os.path.join(lib_dir, "pkgconfig", "shaderc.pc")
        if os.path.isfile(pc):
            with open(pc, encoding="utf-8") as handle:
                content = handle.read()
            content = content.replace("-lshaderc_shared", "-lshaderc  -lshaderc_util")
            with open(pc, "w", encoding="utf-8") as handle:
                handle.write(content)

    def package_info(self):
        installed = collect_libs(self)
        # libshaderc_combined.a 已内联全部依赖，与组件式静态库同时链接会产生重复符号，
        # 故不作为默认链接项（需要单档案链接时可直接取用该文件）。
        usable = [lib for lib in installed if lib != "shaderc_combined"]
        self.cpp_info.libs = [name for name in PREFERRED_LIBS if name in usable]
        self.cpp_info.libs.extend(name for name in usable if name not in PREFERRED_LIBS)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "shaderc")
        self.cpp_info.set_property("cmake_target_name", "shaderc::shaderc")
        self.cpp_info.system_libs = ["m"] if self.settings.os == "OHOS" else ["m", "pthread", "dl"]
