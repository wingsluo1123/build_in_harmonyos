#!/usr/bin/env python3
"""cpp-peglib 1.18.0 — C++17 单头文件 PEG 解析库的 HarmonyOS PC 适配（1.17.0 → 1.18.0 版本升级）

上游：https://github.com/yhirose/cpp-peglib（本包与已合入的 1.15.0 / 1.17.0 同源同形态）

交付物（`cmake --install`，无任何编译产物）：
  * include/peglib.h —— 单头文件库全部内容（CMakeLists.txt:50
    `install(FILES peglib.h DESTINATION include)`）
  * licenses/LICENSE（MIT）
  * CMake package config（由 conan 的 CMakeDeps 提供 `cpp-peglib::cpp-peglib`）

与 1.17.0 的差异（决定本次升级要动的地方）：
  * 1.18.0 新增 `CPPPEGLIB_VERSION "1.18.0"` / `CPPPEGLIB_VERSION_NUM "0x011200"`，
    消费者可直接核对头文件版本；
  * `test/CMakeLists.txt` 仍用 FetchContent 固定 commit 的 googletest，注册
    **两个** target（`peglib-test-main` + `peglib-test-blob-roundtrip`），
    17 个 GoogleTest 源 ⇒ 展开为 **1176 条 CTest 用例**（1.17.0 是 520）；
  * `PEGLIB_BUILD_BENCHMARK` 在 1.18.0 里**默认 ON**，必须显式关掉
    （benchmark/ 会额外拉 deps），其余 PEGLIB_BUILD_* 保持默认 OFF。

OHOS/平台侧要点：
  R1 header-only ⇒ **没有 ELF、没有运行期产物**，因此签名（.codesign）/加载器/
     RUNPATH/壳层这些平台约束在结构上不适用；本包在 OHOS 上的真实验证 = 消费者
     用例在 OHOS clang + C++17 下真编译真运行 + 上游 1176 用例在 worker 上真跑。
  R2 上游测试套件是**硬门禁**：build() 内 `ctest --output-on-failure`，解析
     `N% tests passed, M tests failed out of K`；M≠0、N≠100 或 K==0（套件没真跑）
     ⇒ 直接中断构建，绝不允许「没跑就报通过」。
  R3 `package_id()` 清空（`self.info.clear()`）：包内只有一个头文件，与编译器/
     build_type/架构无关，避免每个 OS/arch 组合重复构建。
  R4 经 CMake 的 FetchContent 拉 googletest 需要网络；worker 可达 github.com
     （已合入的 1.17.0 就是这么跑完 520 用例的）。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"


class CppPeglibConan(ConanFile):
    name = "cpp-peglib"
    version = "1.18.0"
    package_type = "header-library"

    description = "A single-file C++17 header-only PEG parsing library"
    homepage = "https://yhirose.github.io/cpp-peglib/"
    license = "MIT"
    url = "https://github.com/yhirose/cpp-peglib"
    topics = ("parser", "peg", "header-only", "cpp17")

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_EXTENSIONS"] = False
        tc.variables["BUILD_TESTS"] = True
        # 1.18.0 的 benchmark 默认 ON，必须显式关掉（见 docstring）。
        tc.variables["PEGLIB_BUILD_BENCHMARK"] = False
        tc.variables["PEGLIB_BUILD_EXAMPLES"] = False
        tc.variables["PEGLIB_BUILD_LINT"] = False
        tc.variables["PEGLIB_BUILD_PL0"] = False
        # Upstream test/CMakeLists.txt FetchContents googletest, whose install
        # rules default to ON (INSTALL_GTEST). Turn them off so `cmake --install`
        # does not leak gtest/gmock headers + static libs into the package.
        tc.variables["INSTALL_GTEST"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """R2 — run upstream's CTest suite for real and audit the outcome.

        The suite is 17 GoogleTest sources registered twice
        (peglib-test-main + peglib-test-blob-roundtrip) and discovered as
        individual CTest cases, so a silent "0 tests" run has to be treated as
        a failure instead of a pass.
        """
        log = os.path.join(self.build_folder, "ctest.log")
        cmd = ('{{ ctest --test-dir "{bd}" --output-on-failure > "{log}" 2>&1; }}; '
               'echo "CTEST_RC=$?" >> "{log}"').format(
            bd=self.build_folder, log=log)
        self.run(cmd, env="conanbuild")
        with open(log, "r", errors="replace") as fh:
            text = fh.read()
        rc_match = re.search(r"CTEST_RC=(\d+)", text)
        rc = int(rc_match.group(1)) if rc_match else -1
        summary = re.search(
            r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", text)
        if not summary:
            self.output.info(text[-4000:])
            raise ConanException(
                "upstream CTest suite produced no summary line (rc={}) — "
                "refusing to report a pass".format(rc))
        percent, failed, total = (int(summary.group(1)), int(summary.group(2)),
                                  int(summary.group(3)))
        self.output.info(
            "[upstream] ctest: {}% passed, {} failed out of {} (rc={})".format(
                percent, failed, total, rc))
        if failed or percent != 100 or rc != 0:
            self.output.info(text[-4000:])
            raise ConanException(
                "upstream test failure: {}% passed, {} failed out of {} "
                "(rc={})".format(percent, failed, total, rc))
        if total < 1:
            raise ConanException(
                "upstream suite did not really run: 0 CTest cases registered")
        self.output.info(
            "[upstream] {} upstream CTest cases passed".format(total))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._purge_vendored_gtest()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def _purge_vendored_gtest(self):
        """Keep the header-only layout (`include/peglib.h` + `licenses/LICENSE`).

        googletest is pulled in by FetchContent for the upstream suite; its
        install rules are disabled in generate() (INSTALL_GTEST=False), but purge
        any residual gtest/gmock artefacts defensively so the delivery-shape
        self-checks (M5: include/ holds only peglib.h, M7: no .a residue) can
        never regress.
        """
        inc = os.path.join(self.package_folder, "include")
        if os.path.isdir(inc):
            for n in os.listdir(inc):
                if n.startswith(("gtest", "gmock")):
                    p = os.path.join(inc, n)
                    if os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        os.remove(p)
        lib = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib):
            for n in os.listdir(lib):
                if n.startswith(("libgtest", "libgmock")):
                    os.remove(os.path.join(lib, n))
            if not os.listdir(lib):
                os.rmdir(lib)

    def package_id(self):
        # R3 — a single header: independent of compiler/build_type/arch.
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "cpp-peglib")
        self.cpp_info.set_property("cmake_target_name", "cpp-peglib::cpp-peglib")
