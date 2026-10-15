#!/usr/bin/env python3
"""Conan recipe for qt5-qtserialport 5.15.2 on OpenHarmony PC.

适配方式与仓库内已通过 CI 的 Qt5 模块先例保持一致
(qtserialport-opensource-src/5.15.15、qt5-qtsvg/5.15.2.1、
qt5-qtdeclarative/5.15.2，均依赖 qt5-qtbase/5.15.2.2)：

qt5-qtbase 制品仓包内的 bin/qt.conf 与 mkspecs/modules/*.pri 残留了
原构建机的 conan 缓存绝对路径(~/.conan2/p/b/qt5-qXXXX/b)，在任何其他
缓存位置(如 CI 的 ~/.cache/conan2)均为悬空路径，导致 qmake 报
"Unknown module(s) in QT: core-private"。本配方在 build() 中按先例
重写这些文件指向当前包目录后再调用 qmake。

package() 阶段对产物 ELF 执行 binary-sign-tool 自签名（对齐
qtserialport/6.11.1 先例与 qt5-qtbase/5.15.2.2 制品的 .codesign 段），
保证 OHOS loader 可加载。
"""
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Qt5QtserialportConan(ConanFile):
    name = "qt5-qtserialport"
    version = "5.15.2"
    description = "Qt5 SerialPort module for HarmonyOS PC"
    license = "LGPL-3.0-only OR GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-5/qtserialport-index.html"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    _upstream_test_targets = ("qserialport", "qserialportinfo")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name}/{self.version} only supports Linux and OHOS, "
                f"got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data["sha256"], strip_root=True)
                return
            except ConanException as error:
                self.output.warning(f"Failed to download from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Fix qt5-qtbase package's qt.conf and .pri files to use the package
        directory instead of the original build directory (relocatability).

        先例: qtserialport-opensource-src/5.15.15 与 qt5-qtsvg/5.15.2.1
        的同名方法。
        """
        # Fix qt.conf
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
            with open(qt_conf, "w", encoding="utf-8") as f:
                f.write(
                    "[EffectivePaths]\n"
                    "Prefix=..\n"
                    f"[DevicePaths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"[Paths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"HostPrefix={qtbase_pkg}\n"
                    "Sysroot=\n"
                    "SysrootifyPrefix=false\n"
                    "TargetSpec=linux-clang\n"
                    "HostSpec=linux-clang\n"
                )

        # Fix .pri files that reference the build directory
        build_dir_pattern = re.compile(
            r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)"
        )
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(qtbase_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed_content = build_dir_pattern.sub(qtbase_pkg, content)
                if fixed_content != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        qtbase_pkg = qtbase.package_folder
        self._fix_qtbase_paths(qtbase_pkg)

        qmake = os.path.join(qtbase_pkg, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/qmake tool"
            )

        src = self.source_folder
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)

        build_env = Environment()
        build_env.define("QTDIR", qtbase_pkg)
        build_env.prepend_path("PATH", os.path.join(qtbase_pkg, "bin"))
        build_env.append_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        # 让 tests/auto 下的 qmake 能解析刚构建的 serialport 模块
        # (构建树内 mkspecs/modules/qt_lib_serialport.pri)
        build_env.append_path("QMAKEMODULES", os.path.join(src, "mkspecs", "modules"))

        with build_env.vars(self).apply():
            self.run(
                f'cd "{src}" && {shlex.quote(qmake)} -spec linux-clang '
                f"qtserialport.pro"
            )
            # QMAKE_STRIP="": OHOS loader 拒绝被 strip 的 ELF
            self.run(f'cd "{src}" && make -j{jobs} QMAKE_STRIP=""')

            # 上游测试构建 (R51): tests/auto/{qserialport,qserialportinfo}
            # 依赖物理串口对 (QTEST_SERIALPORT_SENDER/RECEIVER 环境变量)，
            # 无硬件时 initTestCase 会 QSKIP，不作为包构建的失败条件。
            test_bins = []
            for test_name in self._upstream_test_targets:
                test_dir = os.path.join(src, "tests", "auto", test_name)
                self.run(
                    f'cd "{test_dir}" && {shlex.quote(qmake)} -spec linux-clang'
                )
                self.run(f'cd "{test_dir}" && make -j{jobs} QMAKE_STRIP=""')
                test_bin = os.path.join(test_dir, f"tst_{test_name}")
                if os.path.isfile(test_bin):
                    test_bins.append(test_bin)

        # 上游测试运行 (R51): 原生环境运行；无物理串口对时
        # initTestCase QSKIP 跳过全部用例（QtTest 退出码 0），真实
        # 失败可阻断构建
        if can_run(self):
            test_env = Environment()
            test_env.append_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
            test_env.append_path("LD_LIBRARY_PATH", os.path.join(src, "lib"))
            with test_env.vars(self).apply():
                for test_bin in test_bins:
                    self.run(f'"{test_bin}"')

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Libraries (unstripped)
        copy(self, "*.so*", src=os.path.join(src, "lib"),
             dst=os.path.join(pkg, "lib"), keep_path=False)
        copy(self, "*.prl", src=os.path.join(src, "lib"),
             dst=os.path.join(pkg, "lib"), keep_path=False)
        if os.path.isdir(os.path.join(src, "lib", "pkgconfig")):
            copy(self, "*.pc", src=os.path.join(src, "lib", "pkgconfig"),
                 dst=os.path.join(pkg, "lib", "pkgconfig"), keep_path=False)

        # HMDFS 拷贝可能丢失符号链接，显式重建 .so 链接链
        # （动态查找实际库文件，不硬编码版本号尾巴）
        pkg_lib = os.path.join(pkg, "lib")
        real_so = None
        if os.path.isdir(pkg_lib):
            for name in sorted(os.listdir(pkg_lib)):
                if name.startswith("libQt5SerialPort.so") and not name.endswith(
                    (".prl", ".la", ".pc")
                ):
                    real_so = name
                    break
        if real_so:
            for link_name in ("libQt5SerialPort.so", "libQt5SerialPort.so.5",
                              "libQt5SerialPort.so.5.15"):
                link_path = os.path.join(pkg_lib, link_name)
                if os.path.lexists(link_path) and link_path != os.path.join(pkg_lib, real_so):
                    os.remove(link_path)
                if not os.path.lexists(link_path):
                    os.symlink(real_so, link_path)

        # Headers: syncqt 转发头 (include/) + 实际头文件 (src/，转发头引用)
        copy(self, "*", src=os.path.join(src, "include"),
             dst=os.path.join(pkg, "include"), keep_path=True)
        copy(self, "*.h", src=os.path.join(src, "src"),
             dst=os.path.join(pkg, "src"), keep_path=True)

        # qmake 模块 .pri (含 modules-inst)，供 qmake 消费方通过
        # QMAKEMODULES 使用；重写其中残留的构建树路径为本包目录
        mkspecs_src = os.path.join(src, "mkspecs")
        if os.path.isdir(mkspecs_src):
            copy(self, "*", src=mkspecs_src,
                 dst=os.path.join(pkg, "mkspecs"), keep_path=True)
            build_tree_pattern = re.compile(re.escape(src))
            for modules_dir_name in ("modules", "modules-inst"):
                modules_dir = os.path.join(pkg, "mkspecs", modules_dir_name)
                if not os.path.isdir(modules_dir):
                    continue
                for pri_file in os.listdir(modules_dir):
                    if not pri_file.endswith(".pri"):
                        continue
                    pri_path = os.path.join(modules_dir, pri_file)
                    with open(pri_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    fixed = build_tree_pattern.sub(pkg, content)
                    if fixed != content:
                        with open(pri_path, "w", encoding="utf-8") as f:
                            f.write(fixed)

        # CMake config (Qt5SerialPortConfig.cmake 基于 CMAKE_CURRENT_LIST_DIR
        # 相对定位，可重定位)
        cmake_src = os.path.join(src, "lib", "cmake")
        if os.path.isdir(cmake_src):
            copy(self, "*", src=cmake_src,
                 dst=os.path.join(pkg, "lib", "cmake"), keep_path=True)

        # OHOS: 产物 ELF 自签名（对齐 qt5-qtbase/5.15.2.2 制品 .codesign 段
        # 与 qtserialport/6.11.1 先例）
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
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
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _elf_type(path):
        """Return the ELF e_type value, or None for a non-ELF file."""
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        serialport = self.cpp_info.components["Qt5SerialPort"]
        serialport.libs = ["Qt5SerialPort"]
        serialport.includedirs = ["include", "include/QtSerialPort"]
        serialport.requires = ["qt5-qtbase::Qt5Core"]
        serialport.set_property("cmake_file_name", "Qt5SerialPort")
        serialport.set_property("cmake_target_name", "Qt5::SerialPort")
