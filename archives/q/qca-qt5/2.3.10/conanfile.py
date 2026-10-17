#!/usr/bin/env python3
"""Conan recipe for QCA 2.3.10 (Qt5 lineage) on OpenHarmony PC.

Qt5 谱系变体（区别于 Qt6 谱系的 qca/2.3.10）：供 psi 1.5 等 Qt5 消费者使用。
上游 QCA 用 Qt5 构建时安装 include/Qca-qt5/QtCrypto 与 libqca-qt5，
与 psi 的 cmake/modules/FindQca.cmake（Qca_SUFFIX=-qt5）期望一致。
"""
import glob
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy


class QcaQt5Conan(ConanFile):
    name = "qca-qt5"
    version = "2.3.10"
    description = "Qt Cryptographic Architecture library (Qt5 build)"
    license = "LGPL-2.1-or-later"
    homepage = "https://userbase.kde.org/QCA"
    url = "https://download.kde.org/stable/qca/2.3.10/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
        # QCA openssl 插件（qca-ossl）：TLS 能力来源
        self.requires("openssl/3.0.16")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qca-qt5 only supports Linux and OHOS, got {}".format(self.settings.os)
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 同 qca/2.3.10（Qt6 谱系）：OHOS 下 UNIX 分支判定修正
        cmake_path = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        with open(cmake_path, "r", encoding="utf-8") as fh:
            text = fh.read()
        text = re.sub(
            r'if\(UNIX(?: OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")?\)', "if(NOT WIN32)", text
        )
        text = re.sub(
            r'IF \(UNIX(?: OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")?\)', "IF (NOT WIN32)", text
        )
        with open(cmake_path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def generate(self):
        tc = CMakeToolchain(self)
        qt_prefix = self.dependencies["qt5-qtbase"].package_folder
        self._fix_qtbase_mkspecs(qt_prefix)
        openssl_prefix = self.dependencies["openssl"].package_folder
        tc.variables["BUILD_WITH_QT6"] = False
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # E537 谱系修复：上游产物缺 DT_SONAME，消费者把构建机绝对路径
        # 烙进 DT_NEEDED（同 sonnet/kdbusaddons 6.26+ 谱系），注入 soname 标志
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # 上游单测（unittest/，Qt Test 体系）真实执行：qt5-qtbase 组件已声明
        # Qt5Test（libQt5Test.so + Qt5TestConfig.cmake），CI/本机均可构建运行
        tc.variables["BUILD_TESTS"] = True
        tc.variables["BUILD_TOOLS"] = False
        # 插件必须带 qca-ossl：psi 多处以 QCA::isSupported("tls") 作为 XMPP
        # TLS 门禁，tls/sha256/random 三项能力均由 qca-ossl 提供，
        # BUILD_PLUGINS=none 会让 psi 的加密通信路径整体不可用
        tc.variables["BUILD_PLUGINS"] = "ossl"
        tc.variables["BUILD_MANPAGES"] = False
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join([qt_prefix, openssl_prefix])
        tc.cache_variables["Qt5_DIR"] = os.path.join(
            qt_prefix, "lib", "cmake", "Qt5Core"
        )
        tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl_prefix
        tc.generate()

    def _fix_qtbase_mkspecs(self, qt_prefix):
        """qt5-qtbase 的 Qt5CoreConfigExtrasMkspecDir.cmake 硬编码了打包时
        构建目录相对路径（../b//mkspecs）——修正为包内真实 mkspecs。"""
        extras_dir = os.path.join(qt_prefix, "lib", "cmake", "Qt5Core")
        if not os.path.isdir(extras_dir):
            return
        for name in os.listdir(extras_dir):
            if not name.endswith("MkspecDir.cmake"):
                continue
            path = os.path.join(extras_dir, name)
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            fixed = re.sub(
                r"\$\{_qt5Core_install_prefix\}[^']*mkspecs",
                "${_qt5Core_install_prefix}/mkspecs",
                content,
            )
            if fixed != content:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(fixed)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests(cmake)

    def _run_upstream_tests(self, cmake):
        """真实执行上游 unittest/ 单测（Qt Test 二进制），统计并记录结果。
        部分用例依赖主机环境（如 filewatch 的文件系统通知、certs 的 PKI 路径），
        失败项按具体退出码记录，不静默吞掉。"""
        import subprocess
        import sys
        ctest = "/data/service/hnp/bin/ctest"
        if not os.path.isfile(ctest):
            ctest = "ctest"
        env = dict(os.environ)
        # 上游测试二进制依赖 Qt5Core/Qt5Test 与构建树内 libqca-qt5.so，
        # 运行前补库路径
        qt_prefix = self.dependencies["qt5-qtbase"].package_folder
        lib_paths = [
            os.path.join(self.build_folder, "lib"),
            os.path.join(self.build_folder, "bin"),
            os.path.join(qt_prefix, "lib"),
        ]
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(lib_paths + ([existing] if existing else []))
        proc = subprocess.run(
            [ctest, "--output-on-failure"],
            cwd=self.build_folder, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=1800,
        )
        output = proc.stdout.decode("utf-8", "replace")
        with open(os.path.join(self.build_folder, "upstream_test_results.log"), "w") as fh:
            fh.write(output)
        # 摘要 + 失败清单与首个失败用例详情打进 conan 日志（conan2 打包后
        # 构建目录即被清理，必须把证据落到持久日志）
        for line in output.splitlines():
            if re.search(r"tests passed|tests failed|\d+% tests", line):
                self.output.info(line.strip())
        failed_names = re.findall(r"^\s*(\d+)/\d+\s+Testing:\s+(\S+)", output, re.M)
        if failed_names:
            self.output.info("failed tests: " + ", ".join(n for _, n in failed_names[:30]))
        # --output-on-failure 的失败详情取首个用例的输出片段
        first_fail = re.search(r"(\d+)/\d+ Testing: \S+.*?(?=\d+/\d+ Testing:|\Z)", output, re.S)
        if first_fail:
            excerpt = first_fail.group(0)[:1500]
            self.output.info("first failing test excerpt:\n" + excerpt)
        return proc.returncode

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        if str(self.settings.os) != "OHOS":
            return
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = os.environ.get("HNP_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException("Required OHOS signing tool not found: {}".format(tool))
        quoted_objcopy = shlex.quote(objcopy)
        quoted_signer = shlex.quote(signer)
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            quoted_object = shlex.quote(shared_object)
            probe = self.run(
                "{} --dump-section .codesign=/dev/null {}".format(quoted_objcopy, quoted_object),
                ignore_errors=True,
            )
            if probe == 0:
                self.run("{} --remove-section .codesign {}".format(quoted_objcopy, quoted_object))
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    quoted_signer, quoted_object, quoted_object
                )
            )

    def package_info(self):
        self.cpp_info.libs = ["qca-qt5"]
        self.cpp_info.includedirs = ["include/Qca-qt5/QtCrypto", "include"]
        # qt5-qtbase 组件未声明 includedirs（CMakeDeps 生成为空）——
        # qca 头文件直接 include QMetaType 等 Qt 头，须补 Qt include 路径
        qt_prefix = self.dependencies["qt5-qtbase"].package_folder
        for sub in ("include", "include/QtCore", "include/QtGui", "include/QtNetwork"):
            qt_inc = os.path.join(qt_prefix, sub)
            if os.path.isdir(qt_inc):
                self.cpp_info.includedirs.append(os.path.relpath(qt_inc, self.package_folder))
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "openssl::openssl"]
        self.cpp_info.set_property("cmake_file_name", "Qca-qt5")
        self.cpp_info.set_property("cmake_target_name", "qca-qt5")
        self.cpp_info.set_property("pkg_config_name", "qca2-qt5")
