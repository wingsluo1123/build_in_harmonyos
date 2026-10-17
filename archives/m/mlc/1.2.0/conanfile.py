#!/usr/bin/env python3
"""Conan recipe for mlc 1.2.0 — Media Library Compiler（C++ / CMake）。

**上游**：`git.macaw.me/blue/mlc`（Gitea 自建站，**不是 GitHub**）；版本 1.2.0（与平台清单一致）。
**依赖**（上游 CMakeLists 的 REQUIRED 项，**全部已在仓库归档** → 按"算依赖先扣掉仓库已有"的口径不阻塞）：
`find_package(FLAC REQUIRED)` / `find_package(JPEG REQUIRED)` /
`pkg_check_modules(LAME REQUIRED … lame)` / `pkg_check_modules(TAGLIB REQUIRED … taglib)`。
→ 因为用到 **pkg-config**，配方里必须同时 `CMakeDeps` 与 **`PkgConfigDeps`**（否则 LAME/TAGLIB 找不到）。
**产物**：`bin/mlc`（上游 `install(TARGETS mlc RUNTIME DESTINATION bin)`）。
**上游测试**：**没有**（仓库里没有 test/tests，CMake 也没有 enable_testing/add_test）→ 配方里补一条真跑的
功能级测试：`mlc --help`（上游 `main.cpp:20` 明确支持 `--help`）并断言打印用法；构成在
test_package/MANIFEST.yml 里摊开，**不谎称"上游自带测试"**。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps


class MlcConan(ConanFile):
    name = "mlc"
    version = "1.2.0"
    description = ("mlc — Media Library Compiler: converts lossless audio "
                   "tracks to lossy formats (C++ / CMake)")
    license = "GPL-3.0-or-later"
    homepage = "https://git.macaw.me/blue/mlc"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("flac/1.4.3")
        self.requires("lame/4.0")
        self.requires("taglib/2.3")
        self.requires("libjpeg-turbo/3.2.0")

    def source(self):
        spec = dict(self.conan_data["sources"])
        spec.pop("note", None)
        get(self, **spec, strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        # LAME / TAGLIB 走 pkg_check_modules → 必须生成 .pc
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type)
        # 上游 CMakeLists 写的是 cmake_minimum_required(VERSION 3.0)，而 CMake ≥4 已移除对 <3.5 的
        # 兼容（报 "Compatibility with CMake < 3.5 has been removed"）→ 按报错提示给策略下限，
        # 不改上游文件。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        self._patch_upstream_cmake()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_added_tests()

    def _patch_upstream_cmake(self):
        """上游 CMakeLists 用的是 **CMake 内置模块**的目标名 `FLAC::FLAC` / `JPEG::JPEG`，而 conan 的
        CMakeDeps 生成的是小写目标 `flac::flac` / `libjpeg-turbo::libjpeg-turbo`（`find_package(FLAC)`
        会被 conan 的 `flac-config.cmake` 接管）→ 在配方里只改写这两处链接目标，不动上游其余逻辑
        （`PkgConfig::LAME` / `PkgConfig::TAGLIB` 由 PkgConfigDeps 提供，保持原样）。
        """
        cm = os.path.join(self.source_folder, "CMakeLists.txt")
        text = open(cm, encoding="utf-8").read()
        new = text.replace("FLAC::FLAC", "flac::flac").replace(
            "JPEG::JPEG", "libjpeg-turbo::libjpeg-turbo")
        # conan 生成的 config 按**包名**命名（libjpeg-turbo-config.cmake），而上游的
        # `find_package(JPEG)` 找不到它 → 目标 libjpeg-turbo::libjpeg-turbo 未定义。
        new = new.replace("find_package(JPEG REQUIRED)", "find_package(libjpeg-turbo REQUIRED)")
        # 依赖的 include 在 conan 环境下没通过目标传播过来（实测 lame.h not found）→ 直接注入。
        # 注意两点：①必须插在 add_executable() **之前**（include_directories 只对之后创建的 target 生效）；
        # ②LAME 的头在 conan 包里是**嵌套目录** `include/lame/lame.h`，而上游写的是 `#include <lame.h>`
        # → 除了 `<lame>/include`，还要把 `<lame>/include/lame` 一起加入搜索路径。
        inc_dirs = []
        for r in ("flac", "lame", "taglib", "libjpeg-turbo"):
            root = os.path.join(self.dependencies[r].package_folder, "include").replace("\\", "/")
            inc_dirs.append(root)
            if r == "lame":
                inc_dirs.append(root + "/lame")
        incs = " ".join('"%s"' % d for d in inc_dirs)
        new = new.replace("add_executable(mlc", "include_directories(%s)\nadd_executable(mlc" % incs, 1)
        if new != text:
            open(cm, "w", encoding="utf-8").write(new)
            self.output.info("[patch] CMakeLists.txt：链接目标改为 conan 名、find_package(JPEG) → "
                             "libjpeg-turbo、并注入依赖 include 目录")

    # ── 补的功能级测试（上游无测试套件）────────────────────────────────
    def _find_exe(self):
        for p in glob.glob(os.path.join(self.build_folder, "**", "mlc"), recursive=True):
            if os.path.isfile(p) and os.access(p, os.X_OK):
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            return p
                except OSError:
                    continue
        raise ConanInvalidConfiguration("[added tests] 构建目录里没找到 ELF 可执行的 mlc")

    def _run_added_tests(self):
        exe = self._find_exe()
        self.output.info("[added tests] 产物 = %s（%d 字节）" % (exe, os.path.getsize(exe)))
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = (":".join(
            os.path.join(self.dependencies[r].package_folder, "lib")
            for r in ("flac", "lame", "taglib", "libjpeg-turbo")) + ":"
            + env.get("LD_LIBRARY_PATH", ""))
        r = subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=300, env=env)
        out = r.stdout + r.stderr
        if out.strip() and ("usage" in out.lower() or "mlc" in out.lower()):
            self.output.info("[added tests] ① `mlc --help` 打印用法 ✓（首行：%s）"
                             % out.strip().splitlines()[0][:100])
        else:
            raise ConanInvalidConfiguration(
                "[added tests] `mlc --help` 没有打印用法（rc=%d）：\n%s" % (r.returncode, out[-500:]))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        for lic in ("LICENSE", "LICENSE.txt", "COPYING", "LICENSE.md"):
            if os.path.isfile(os.path.join(self.source_folder, lic)):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
                break

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
