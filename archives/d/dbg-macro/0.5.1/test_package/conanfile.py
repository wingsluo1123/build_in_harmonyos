#!/usr/bin/env python3
"""Conan test_package — dbg-macro 0.5.1.

两段式验证：
1. 消费者测试：链接安装后的 dbg_macro::dbg_macro，验证 6 项公开 API 行为。
2. 上游官方测试套件（rule4）：恢复上游 tests/Catch2 submodule（按上游 v0.5.1
   记录的提交钉版），真实配置、编译并执行上游 CMake/CTest 套件（19 个 CTest
   条目，含 9 个 TEST_CASE 的正常宏/DBG_MACRO_DISABLE 双配置 + demo）。
   conanfile.py 与 conandata.yml 保持零修改（R37），上游套件的执行全部由
   test_package 承载。
"""
import os
from io import StringIO
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import get


class DbgMacroTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    # 上游源码与测试依赖（sha256 与 0.5.1.1 归档一致）
    _UPSTREAM_URL = "https://github.com/sharkdp/dbg-macro/archive/refs/tags/v0.5.1.tar.gz"
    _UPSTREAM_SHA256 = "fffea75f067c69995853dc790626887788e2c4c9eb0a5a0014a4501d2b6b9909"
    _CATCH2_URL = "https://github.com/catchorg/Catch2/archive/182c910b4b63ff587a3440e08f84f70497e49a81.tar.gz"
    _CATCH2_SHA256 = "4c2dc314dd4e29fc8a5312e5223be9f8533b083c5843a9e852c96791cf1215cd"
    # worker 网络受限时的镜像 fallback（下载后均按 sha256 校验，来源无关性）
    _MIRRORS = ("https://ghfast.top/", "https://gh-proxy.com/", "https://mirror.ghproxy.com/")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _fetch(self, url, sha256, dest):
        """按 sha256 校验下载，官方源失败时依序尝试镜像。"""
        last = None
        for u in (url,) + tuple(m + url for m in self._MIRRORS):
            try:
                get(self, url=u, sha256=sha256, strip_root=True, destination=dest)
                return
            except Exception as exc:  # noqa: BLE001 — 换下一个源
                last = exc
        raise ConanException(f"download failed (all sources): {last}")

    def _run_upstream_suite(self):
        """真实执行上游 CMake/CTest 套件（19 个 CTest 条目）。"""
        up_src = os.path.join(self.build_folder, "upstream-src")
        self._fetch(self._UPSTREAM_URL, self._UPSTREAM_SHA256, up_src)
        # 上游 tarball 不含 tests/Catch2 submodule，按 v0.5.1 记录的提交恢复
        self._fetch(self._CATCH2_URL, self._CATCH2_SHA256,
                    os.path.join(up_src, "tests", "Catch2"))

        gen = self.generators_folder
        bdir = os.path.join(self.build_folder, "upstream-build")
        configure = (
            f". '{gen}/conanbuild.sh' && cmake -S '{up_src}' -B '{bdir}' "
            "-G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release "
            "-DCMAKE_CXX_STANDARD=17 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
            "-DDBG_MACRO_ENABLE_TESTS=ON -DBUILD_TESTING=ON"
        )
        self.run(configure)
        self.run(f". '{gen}/conanbuild.sh' && cmake --build '{bdir}' --parallel 2")

        # 执行并核实用例数：上游 v0.5.1 共 19 个 CTest 条目
        # 与配置/编译使用相同的 Conan shell 和 buildenv；Python 直接 exec
        # 不会激活该环境，在 OHOS worker 上曾无法启动 ctest。
        ctest_list = StringIO()
        self.run(f"ctest --test-dir '{bdir}' -N", stdout=ctest_list, env="conanbuild")
        m = None
        for line in ctest_list.getvalue().splitlines():
            if "Total Tests:" in line:
                m = re.search(r"Total Tests:\s*(\d+)", line)
        if m is None:
            raise ConanException(
                "upstream ctest -N gave no total")
        total = int(m.group(1))
        if total != 19:
            raise ConanException(
                f"upstream suite has {total} tests, expected 19")
        self.output.info(f"upstream CTest suite: {total} tests discovered")

        # 真实执行（任一失败即非零退出 → conan test 失败）
        self.run(f"ctest --test-dir '{bdir}' --output-on-failure", env="conanbuild")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise Exception("No bindirs found")
            bin_path = os.path.join(bindirs[0], "test_dbg_macro")
            if not os.path.isfile(bin_path):
                raise Exception(f"Test binary not found: {bin_path}")
            # 消费者执行失败必须保留失败，不能以编译成功代替运行成功。
            self.run(bin_path, env="conanrun")
            # rule4：上游官方测试套件真实执行（19/19）
            self._run_upstream_suite()
        else:
            self.output.warning(
                "cross-building: consumer executable compiled but not executed")
