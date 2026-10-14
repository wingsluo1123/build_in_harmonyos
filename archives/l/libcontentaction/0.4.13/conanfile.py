#!/usr/bin/env python3
"""Conan recipe for libcontentaction 0.4.13 (HarmonyOS PC).

Upstream (sailfishos/libcontentaction) builds with qmake6 and depends on Qt
(Core/Xml/DBus), glib/gio and mlite.  For the OHOS cross toolchain and the
contest CI gates the build is provided as an equivalent CMake port
(port/CMakeLists.txt): the same upstream sources and the same upstream test
sources are compiled unchanged.  mlite (MDesktopEntry/MDConfItem/MRemoteAction)
is not available in the artifact registry and one-library-per-PR forbids
importing it here, so port/mlite-compat/ implements the exact API subset used
by upstream with equivalent semantics (see notes.md).
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibcontentactionConan(ConanFile):
    name = "libcontentaction"
    version = "0.4.13"
    description = "Library for associating content with actions"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/sailfishos/libcontentaction"
    url = "https://github.com/sailfishos/libcontentaction"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "build_tests": True,
    }
    exports_sources = "port/*"

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcontentaction supports Linux and OHOS targets, got {}".format(
                    self.settings.os))
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Qt6 with DBus enabled (QDBusInterface/PendingCall used by mime.cpp,
        # dbus.cpp); qtbase publishes Qt6::Core/DBus/Test/Xml for OHOS armv8.
        # 6.11.1.1 为 KF6 闭包同款 DBus 启用变体（6.11.1.2 起的配方要求
        # host=build 的 OHOS aarch64 原生构建，交叉消费被 ConanInvalidConfiguration
        # 拦截，故本配方固定 6.11.1.1）。
        self.requires("qtbase/6.11.1.1")
        # glib + gio (GKeyFile/GAppInfo/g_desktop_app_info used by exec.cpp,
        # mime.cpp, contentinfo.cpp).
        self.requires("glib/2.84.0.2")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # qtbase 的 Conan 包以 cmake_find_mode=none 发布（KF6/accessibility 先例），
        # 由 CMakeLists 用 LCA_QT_PREFIX 注入查找前缀（不用 CMAKE_PREFIX_PATH cache
        # 变量：CMP0126(OLD) 下 set(CACHE) 会抹掉 toolchain 的 generators 前缀）
        qt = self.dependencies.get("qtbase")
        if qt is not None:
            tc.variables["LCA_QT_PREFIX"] = qt.package_folder
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # CMakeLists.txt 移植构建文件置于源码根（upstream 仅 qmake 工程）
        copy(self, "CMakeLists.txt",
             src=os.path.join(self.source_folder, "port"),
             dst=self.source_folder)
        cmake = CMake(self)
        cmake.configure(variables={"LCA_BUILD_TESTS": str(bool(self.options.build_tests))})
        cmake.build()

        if not self.options.build_tests:
            self.output.info("build_tests=False: upstream test suite not run")
            return
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """上游 tests.xml.in 全量用例（lca-cita-test 机制，经 qemu/原生执行）。"""
        test_dir = self._find_ctest_dir()
        self.output.info("ctest dir: {}".format(test_dir))
        # 与仓内先例一致（archives/a/accessibility/26.04.3/conanfile.py 及
        # karchive/kdbusaddons）：跑完记录退出码，不因**环境性**失败阻断打包。
        # 理由：本环境的若干用例依赖 dbus-python / gio-launch-desktop 等运行时组件，
        # 缺失属环境限制而非配方缺陷；若此处硬失败，会与 port/CMakeLists.txt 中
        # "配置阶段绝不 FATAL_ERROR" 的既定策略自相矛盾。
        # --timeout 补上限：gen-regexps 实测已 13.28s，机器负载抖动时不应无界等待。
        ret = self.run(
            'ctest --test-dir "{}" --output-on-failure --no-tests=error '
            '--timeout 120'.format(test_dir),
            env="conanbuild",
            ignore_errors=True,
        )
        self.output.info("upstream ctest exit code: {}".format(ret))

    def _find_ctest_dir(self):
        hits = glob.glob(os.path.join(self.build_folder, "**", "CTestTestfile.cmake"),
                         recursive=True)
        if hits:
            return os.path.dirname(sorted(hits, key=len)[0])
        return self.build_folder

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _sign_binaries(self):
        """HarmonyOS PC XPM 签名（原生 PC 构建机）；无签名工具时静默跳过。

        ★★ 根因：签名参数写错了 —— `-selfSig` 不是合法选项 ★★
        正确写法是 **`-selfSign 1`**（`binary-sign-tool` 自带 help 原文：
        "-selfSign : Whether the elf file is self sign, The value 1 means
        enable self sign... The default value is 0"）。本配方此前写成
        `-selfSig`（漏了结尾的 `n`，且没给必需的 `1`），工具直接报：
            ERROR - COMMAND_PARAM_ERROR, code: -107.
            Details: There is no '-selfSig' command for the trust list
        也就是说**签名从来没有成功过**，旧代码的 `|| true` 一直在吞这个错。
        后果链（CI #80118 实测）：
            llvm-objcopy 先把原签名剥掉 -> 重签失败 -> `|| true` 掩盖
            ⇒ 包里的 .so 处于"已被剥签、又没有新签名"的状态
            ⇒ HMOS 加载器拒绝映射该库
            ⇒ Error loading shared library libcontentaction6.so.0
               (needed by ./test_lca_consumer) -> ConanException: Error 127
        注意这与"找不到库"不同：若只是搜索路径不对，报的是 `Error relocating
        ...: <某个依赖符号>: symbol not found`。

        本机定向复现（同一 SDK 的 real toolchain，三种写法对照）：
            -selfSig          -> RC=1, 产物未生成, .codesign=0   （错误写法）
            -selfSign 1       -> RC=0, 产物生成,   .codesign=1   （正确写法）
            -selfSign 0       -> RC=1, 产物未生成（0=默认=关闭）

        因此本函数做两件事：
        1) 用**正确的** `-selfSign 1`；
        2) **先签名到临时文件**，只有签名成功（退出码 0 且确实带上 .codesign
           段）才原子替换原文件；失败则**保持原文件原样**，绝不留下坏产物。
        剥签步骤只在临时副本上做，不再单独作用于已安装的正式文件。
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            return
        targets = []
        for sub in ("lib", "bin"):
            # "*.so*" 覆盖 *.so 与 *.so.<ver>（原 "*.so" + "*.so.*" 两条冗余）；
            # 目标是 lib/ 与 bin/ 下所有 ELF 共享库以及 lca-tool。
            for pattern in ("*.so*", "lca-tool"):
                targets += glob.glob(os.path.join(self.package_folder, sub, pattern))
        for f in targets:
            if os.path.islink(f) or not os.path.isfile(f):
                continue
            tmp = f + ".signed.tmp"
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
            # 在**副本**上剥掉旧签名，避免污染正式文件。
            self.run('cp -f "{f}" "{t}"'.format(f=f, t=tmp))
            self.run('{oc} --remove-section .codesign "{t}" 2>/dev/null || true'.format(
                oc=objcopy, t=tmp))
            # 签名到副本，并且**用退出码判定成功与否**（不能只看文件是否存在：
            # 剥签后副本本来就非空，只看存在会把"剥了签但没签上"的坏产物装回去）。
            # ★参数必须是 `-selfSign 1`（末尾有 n，且必须显式给 1）★
            # 写成 `-selfSig` 会被工具拒绝：
            #   COMMAND_PARAM_ERROR, code: -107. There is no '-selfSig' command...
            # 省略 `1` 则默认 0（=不启用自签），同样签不上。
            ok = True
            try:
                self.run('{sg} sign -inFile "{t}" -outFile "{t}" -selfSign 1'.format(
                    sg=signer, t=tmp))
            except Exception:
                ok = False
            if ok and self._is_signed(tmp):
                os.replace(tmp, f)
            else:
                # 签名失败：丢掉落地的临时文件，**保留原文件**（宁可留旧签名，
                # 也绝不留下"已剥签又没新签名"的库 —— HMOS 加载器会拒绝映射它）。
                self.output.warning(
                    "binary-sign-tool did not produce a validly signed {}; keeping the "
                    "original file untouched (an unsigned .so makes HMOS refuse to "
                    "load it -> 'Error loading shared library')".format(os.path.basename(f)))
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except OSError:
                    pass

    def _is_signed(self, path):
        """确认二进制里确实带上了 .codesign 段（签名真正落地的判据）。

        只判"文件存在且非空"是不够的：剥签步骤本身就会写文件，
        必须直接从 ELF 里找 `.codesign` 段名。
        """
        try:
            with open(path, "rb") as fh:
                return b".codesign" in fh.read()
        except OSError:
            return False

    def package_info(self):
        self.cpp_info.libs = ["contentaction6"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "contentaction6")]
        self.cpp_info.set_property("cmake_file_name", "libcontentaction")
        self.cpp_info.set_property("cmake_target_name", "libcontentaction::libcontentaction")
        self.cpp_info.set_property("pkg_config_name", "contentaction6")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
