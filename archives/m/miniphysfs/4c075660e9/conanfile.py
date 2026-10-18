#!/usr/bin/env python3
"""Conan recipe — miniphysfs 4c075660e9 (header-only).

miniphysfs is a single-file port of PhysFS: the entire public API and
implementation live in one header (miniphysfs.h). Consumers create the
implementation by defining PHYSFS_IMPL and PHYSFS_PLATFORM_IMPL in one
C file before including the header (upstream ships exactly that as
test/physfs.c + test/physfs_platform.c).

Zero runtime dependencies; only the public header is packaged.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os
import shutil
import subprocess
from conan.errors import ConanException

required_conan_version = ">=2.0"


class MiniphysfsConan(ConanFile):
    name = "miniphysfs"
    version = "4c075660e9"
    package_type = "header-library"

    description = (
        "Single-file port of PhysFS, a library that provides abstract "
        "access to various archives (ZIP, 7Z, GRP, PAK, HOG, MVL, WAD, "
        "SLB, ISO9660, VDF) through a unified filesystem-like API."
    )
    homepage = "https://github.com/edubart/miniphysfs"
    license = "ZLIB"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("physfs", "filesystem", "archive", "header-only", "single-header")

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # Header-only: identical package for every build configuration.
        self.info.clear()

    def source(self):
        # codeload commit URLs end in the commit SHA (no file extension), so
        # Conan's get() would fall back to the zip decoder → BadZipFile.
        # Pass an explicit *.tar.gz filename so unzip() selects the right decoder.
        get(self, **self.conan_data["sources"][self.version], strip_root=True,
            filename="miniphysfs-4c075660e9.tar.gz")

    def build(self):
        # 应用 conandata.yml 声明补丁（当前 patches: {}，无实际补丁，保留调用以合规）。
        apply_conandata_patches(self)
        # Header-only library: nothing to link. But the upstream official test
        # suite (test/test_physfs.c, a self-contained REPL exercising the REAL
        # PhysFS API) is compiled and executed here as the L1 upstream-test
        # gate so CI verifies the actual upstream tests run in the OHOS aarch64
        # environment — not merely the consumer test_package.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        src = self.source_folder
        test_dir = os.path.join(src, "test")
        build_dir = os.path.join(self.build_folder, "upstream_tests")
        os.makedirs(build_dir, exist_ok=True)

        cc = shutil.which("clang") or shutil.which("cc") or "cc"

        # 编译上游官方测试程序（Makefile 硬编码 CC=gcc，环境无 gcc，用 clang 覆盖）。
        make_cmd = f"make clean >/dev/null 2>&1; make CC=clang CFLAGS='-O2 -Wall -I{src}'"
        self._run(["sh", "-c", make_cmd], cwd=test_dir)

        test_bin = os.path.join(test_dir, "test_physfs")
        if not os.path.exists(test_bin):
            raise ConanException("upstream test_physfs not built")

        from conan.tools.build import can_run
        if can_run(self):
            # 脚本化驱动上游测试 REPL：help + init + getbasedir 后退出，
            # 验证库初始化/基础目录查询在 OHOS 目标上真实运行。
            script = "help\ninit /tmp\ngetbasedir\nquit\n"
            env = dict(os.environ)
            result = subprocess.run(
                [test_bin], input=script, capture_output=True, text=True, env=env
            )
            out = (result.stdout or "") + (result.stderr or "")
            self.output.info("UPSTREAM test_physfs output tail:\n" + out[-2000:])
            if result.returncode != 0:
                raise ConanException(
                    "upstream test_physfs failed (exit %d): %s"
                    % (result.returncode, out[-1000:])
                )
            self.output.info("UPSTREAM test_physfs passed (exit 0)")
        else:
            self.output.warning(
                "Upstream tests compiled but not executed (can_run=False)."
            )

    def _run(self, cmd, cwd=None):
        self.output.info(f"$ {' '.join(cmd)}")
        env = dict(os.environ)
        result = subprocess.run(cmd, cwd=cwd, env=env,
                                capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        if out.strip():
            self.output.info(out.strip()[-3000:])
        if result.returncode != 0:
            raise ConanException(
                f"Command failed (exit {result.returncode}): {' '.join(cmd)}\n{out}"
            )

    def package(self):
        # 打包唯一公共头文件与许可证（ZLIB，同 PhysFS）。
        copy(
            self,
            "miniphysfs.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "miniphysfs")
        self.cpp_info.set_property("cmake_target_name", "miniphysfs::miniphysfs")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]