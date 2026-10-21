#!/usr/bin/env python3
"""Conan test_package — xwiimote 2 (libxwiimote + xwiishow)。

三层真实消费者验证，全部 fail-closed（任一断言不成立即 raise，绝不静默通过）：

  1. ``test.c``（CMake 目标 ``test_xwiimote``）——编译链接打包的 libxwiimote，
     调用公共 API：``xwii_iface_new`` 的 NULL 入参 / 不存在路径错误路径，以及
     监视器构造 / 引用计数 / 轮询 / 释放。库、SONAME、头文件或 libudev 链接任一
     破损该程序都无法编译或运行。

  2. ``test_xwiishow_cli.py``——执行打包的 ``bin/xwiishow`` 的无头 ``list`` 路径
     与 ``-h``，断言真实 stdout 与退出码（在 conanrun 环境下加载打包的
     libxwiimote.so.2）。

  3. ELF 契约 + HarmonyOS 特有断言——用 ``readelf`` 对 ``bin/`` 与 ``lib/`` 下
     **每个实体 ELF**（跳过符号链接）断言：架构为 AArch64、段表恰含 1 个
     ``.codesign`` 段；并断言 ``bin/xwiishow`` 的 DT_NEEDED 与打包库一致。
     ``.codesign`` 只由 HarmonyOS ``binary-sign-tool`` 写入（主配方 ``package()``
     调用），通用 Linux ELF 不存在该段，故为真正的平台特有属性。

上游测试：xwiimote 2 无测试套件（无 tests/ 目录，Makefile.am 无 TESTS/
check_PROGRAMS），清点结论见 ``test_package/MANIFEST.yml``。

File location: archives/x/xwiimote/2/test_package/conanfile.py
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class XwiimoteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()

        package = self.dependencies[self.tested_reference_str]
        package_folder = package.package_folder

        # 1. C 消费者：直接执行链接了打包库的测试二进制（CTest 与 conanrun 环境
        #    相互独立，这里再执行一次以验证运行期动态库可被加载）。
        consumer = os.path.join(self.cpp.build.bindirs[0], "test_xwiimote")
        if not os.path.isfile(consumer):
            raise ConanException("consumer test binary is missing: {}".format(consumer))
        self.run('"{}"'.format(consumer), env="conanrun")

        # 2. CLI 消费者：驱动打包的 bin/xwiishow（无头 list 路径 + -h）。
        tool = os.path.join(package_folder, "bin", "xwiishow")
        if not os.path.isfile(tool):
            raise ConanException("packaged xwiishow binary is missing: {}".format(tool))
        python = shutil.which("python3") or "python3"
        script = os.path.join(self.source_folder, "test_xwiishow_cli.py")
        if not os.path.isfile(script):
            raise ConanException("CLI test script is missing: {}".format(script))
        self.run('"{}" "{}" "{}"'.format(python, script, tool), env="conanrun")

        # 3. ELF 契约 + 鸿蒙特有签名断言（对每个实体 ELF，fail-closed）。
        self._verify_elf_contract(package_folder)

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _readelf(self, *arguments):
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            raise ConanException("readelf is required for the OHOS ELF contract test")
        return subprocess.run(
            [readelf, *arguments], check=True, capture_output=True,
            text=True, timeout=60).stdout

    def _collect_artefacts(self, package_folder):
        """bin/ 与 lib/ 下的**实体** ELF（跳过符号链接与目录）。

        与主配方 package() 的签名范围一致：共享库的 .so/.so.2 是符号链接，
        只有 .so.2.0.0 是实体文件，故按实体文件断言而非重复断言同一 inode。
        """
        artefacts = []
        for subdir in ("bin", "lib"):
            base = os.path.join(package_folder, subdir)
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                candidate = os.path.join(base, name)
                if os.path.islink(candidate) or not os.path.isfile(candidate):
                    continue
                if self._is_elf(candidate):
                    artefacts.append(candidate)
        return artefacts

    def _verify_elf_contract(self, package_folder):
        artefacts = self._collect_artefacts(package_folder)
        if not artefacts:
            raise ConanException(
                "no ELF artefact found under {}/bin|lib — cannot verify the "
                "OHOS ELF contract".format(package_folder))

        tool = os.path.join(package_folder, "bin", "xwiishow")
        if not self._is_elf(tool):
            raise ConanException("packaged xwiishow is not an ELF: {}".format(tool))

        # 架构断言：每个实体 ELF 必须为 AArch64。
        for binary in artefacts:
            if "AArch64" not in self._readelf("-h", binary):
                raise ConanException("{} is not an AArch64 ELF".format(binary))
        self.output.info(
            "OHOS AArch64 ELF contract: PASS ({} artefact(s))".format(len(artefacts)))

        # DT_NEEDED 断言（按当前链接形态适配）：
        #   动态构建 → lib/ 有 libxwiimote.so，此时 xwiishow 必须记录
        #              libxwiimote.so 的 DT_NEEDED；
        #   静态构建 → 改为必须记录 libudev.so。
        dynamic_lib = os.path.join(package_folder, "lib", "libxwiimote.so")
        needed = self._readelf("-d", tool)
        if os.path.exists(dynamic_lib):
            if "libxwiimote.so" not in needed:
                raise ConanException(
                    "bin/xwiishow does not record a libxwiimote.so DT_NEEDED — "
                    "the dynamic link to the packaged library is broken")
            self.output.info("libxwiimote.so DT_NEEDED present in bin/xwiishow: PASS")
        elif "libudev.so" not in needed:
            raise ConanException(
                "bin/xwiishow records neither libxwiimote.so nor libudev.so in its "
                "DT_NEEDED — the libudev link is broken")
        else:
            self.output.info("libudev.so DT_NEEDED present in bin/xwiishow: PASS")

        # HarmonyOS 特有：每个实体 ELF 必须由 binary-sign-tool 签名，
        # 段表恰含 1 个 .codesign 段。
        if self.settings.os == "OHOS":
            for binary in artefacts:
                codesign = self._readelf("-S", binary).count(".codesign")
                if codesign != 1:
                    raise ConanException(
                        "HarmonyOS signature check failed: expected exactly 1 "
                        "'.codesign' section in {}, found {} — the packaged ELF "
                        "is not signed for HarmonyOS".format(
                            os.path.basename(binary), codesign))
            self.output.info(
                "HarmonyOS .codesign segment on {} ELF artefact(s): PASS".format(
                    len(artefacts)))
