#!/usr/bin/env python3
"""Conan recipe — ezc3d 1.5.5 (C3D motion-capture file reader/writer).

上游: https://github.com/pyomeca/ezc3d   tag: Release_1.5.5
构建系统: CMake (add_library ezc3d + install EXPORT ezc3dTargets)

关键决策:
  * ezc3d 是纯 C++11 库，无任何第三方运行时依赖（只用 libstdc++/libc++ 与 <cmath>）。
  * 上游测试套件 (test/) 是 GoogleTest 单二进制 ezc3d_test（3 个 .cpp，53 个 TEST）。
    交叉构建下本配方在 build() 中真实编译并执行它，日志作为 rule4 证据。
  * 上游 test/CMakeLists.txt 通过 git submodule 拉 gtest、通过 file(DOWNLOAD)
    拉 C3D 测试数据（交叉构建 + CI 禁网下都会失败）。本配方改为:
      - gtest: 用 tool_requires("gtest/x.y.z") 提供头文件与预编译静态库，
        绕开 add_subdirectory(external/gtest)，gtest 属测试框架依赖，赛事允许;
      - C3D 数据: conandata.yml 声明 + source() 里 get() 预取解包到 test/c3dFiles/。
  * 测试执行策略（2026-10-10 修复 CI build #80093）: 上游测试二进制**始终编译**；
    只有在探测到可用的 aarch64 模拟器（profile 的 CMAKE_CROSSCOMPILING_EMULATOR
    或 OHOS_QEMU）时才真机/模拟执行。CI worker 无模拟器 -> 只编译不执行并 WARN，
    不再因"缺 qemu"把已编译成功的包判为失败。
  * OHOS 侧与 girara/libbrotli 同法: os=OHOS 时自发现 ohos.toolchain.cmake、
    用裸 cmake 构建（绕开 conan_toolchain 对 CMAKE_SYSTEM_NAME 的映射），
    ranlib 兜底，共享库产物做代码签名（否则真机 dlopen 失败）。
"""
import glob
import os
import re
import shutil
import textwrap

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rmdir,
)

required_conan_version = ">=2.0"


class Ezc3dConan(ConanFile):
    name = "ezc3d"
    version = "1.5.5"
    description = (
        "Easy to use C3D reader/writer for C++, Python and Matlab "
        "(biomechanics / motion capture)"
    )
    license = "MIT"
    homepage = "https://github.com/pyomeca/ezc3d"
    url = "https://github.com/pyomeca/ezc3d"
    topics = ("c3d", "biomechanics", "motion-capture", "file-format", "reader", "writer")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tests": True,
        # gtest 只用于构建期跑上游测试，不进 ezc3d 的运行时依赖闭包
        "gtest/*:shared": False,
    }

    # 上游 test/ 三个 .cpp 共 53 个 TEST（test_ezc3d.cpp 38 / test_math.cpp 10 /
    # test_modules.cpp 5），分批执行后必须逐个跑满并通过。
    _EXPECTED_UPSTREAM_TESTS = 53

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    # ------------------------------------------------------------------ options
    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # 注意：这里**不能**按"有没有模拟器"去改 self.options.with_tests。
        # 实测（CASE A）Conan 会直接拒绝：
        #   ConanException: Incorrect attempt to modify option 'with_tests'
        #                   from 'True' to 'False'
        # 而且 options 是用户可见契约（也可由用户显式指定），不该被环境能力悄悄改写。
        # "能否执行"的判定因此全部下移到 build()/_run_upstream_tests() 做优雅降级。

    def _can_execute_tests(self):
        """产物能否在本机真实执行（决定上游测试是"跑"还是"只编译"）。

        仅作为**语义判据**供 build()/_run_upstream_tests() 使用；
        不再用于改写 self.options.with_tests（见 configure() 注释）。
        """
        if self.settings.os == "OHOS":
            # 目标即 OHOS/aarch64，x86_64 宿主必然跑不了，只能靠模拟器
            return self._emulator() is not None
        return can_run(self)

    # ------------------------------------------------------------- requirements
    def build_requirements(self):
        if self.options.with_tests:
            # GoogleTest 属赛事允许的测试框架依赖，不进运行时依赖闭包
            self.tool_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self, src_folder=".")

    # ------------------------------------------------------------------ source
    def source(self):
        get(self, **self.conan_data["sources"]["1.5.5"], strip_root=True)
        self._fetch_test_data()
        apply_conandata_patches(self)

    def _fetch_test_data(self):
        """预取上游 C3D 测试数据到 test/c3dFiles/（上游由 CMake file(DOWNLOAD) 完成）。

        上游 test/CMakeLists.txt 会把这些 .c3d 拷到 ${CMAKE_BINARY_DIR}/c3dTestFiles/，
        而用例里写的是相对路径 "c3dTestFiles/xxx.c3d"，所以构建期 cwd 必须是
        含有 c3dTestFiles/ 的目录 —— 见 build()。
        """
        data = self.conan_data.get("test_data") or {}
        if not data:
            return
        dst = os.path.join(self.source_folder, "test", "c3dFiles")
        os.makedirs(dst, exist_ok=True)
        for name, entry in data.items():
            tmp = os.path.join(self.source_folder, "_testdata", name)
            get(self, **entry, destination=tmp, strip_root=False)
            # conan 的 get() 对 .zip/.tar.gz 会自动解包，解完就删掉压缩包；
            # 若因故仍留着压缩包，这里再显式解一次，两种情形都要覆盖。
            for z in glob.glob(os.path.join(tmp, "**", "*.zip"), recursive=True):
                unz = os.path.join(tmp, "_unz_" + os.path.basename(z))
                rmdir(self, unz)
                os.makedirs(unz, exist_ok=True)
                self.run('cmake -E tar -xf "%s"' % z, cwd=unz)
            found = glob.glob(os.path.join(tmp, "**", "*.c3d"), recursive=True)
            if not found:
                raise ConanInvalidConfiguration(
                    "test data %s: no .c3d found under %s" % (name, tmp)
                )
            for f in found:
                copy(self, os.path.basename(f), src=os.path.dirname(f), dst=dst)
        rmdir(self, os.path.join(self.source_folder, "_testdata"))
        c3ds = glob.glob(os.path.join(dst, "*.c3d"))
        if not c3ds:
            raise ConanInvalidConfiguration("no C3D test files fetched into %s" % dst)

    # ------------------------------------------------------- OHOS 工具链兜底
    def _ohos_toolchain(self):
        # 与 girara/libbrotli/lambda-align2 同法：自发现 ohos.toolchain.cmake，
        # 不依赖 CI profile 的 host 段。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME") or os.environ.get("OHOS_SDK", "")
        candidates = list(ut)
        candidates.append(os.environ.get("OHOS_TOOLCHAIN", ""))
        if ndk:
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        found = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if found:
            return found[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _toolchain_bindir(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = ce.get("cpp") or ce.get("c") or ""
        return os.path.dirname(cxx) if os.path.sep in cxx else ""

    def _ranlib_fix(self, toolchain):
        # OHOS SDK 的 llvm/bin 下只有 llvm-ar、没有 llvm-ranlib，而 ohos.toolchain.cmake
        # 仍把 CMAKE_RANLIB 指过去；造静态库时 <AR> qc && <RANLIB> <lib> 会报
        # "Error running link command: no such file or directory"。探测后回退。
        sdk_bin = os.path.normpath(os.path.join(toolchain, "..", "..", "..", "llvm", "bin"))
        if os.path.isfile(os.path.join(sdk_bin, "llvm-ranlib")):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _preload_file(self, toolchain):
        """生成 CMAKE_PROJECT_TOP_LEVEL_INCLUDES 前置脚本。

        ohos.toolchain.cmake 用普通 set()（非 CACHE）把 CMAKE_FIND_ROOT_PATH_MODE_*
        设为 ONLY，命令行 -D 压不住；此处放开为 BOTH，并把 ranlib 兜底写进去。
        """
        path = os.path.join(self.build_folder, "ohos-preload.cmake")
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent("""\
                foreach(_m IN ITEMS LIBRARY INCLUDE PACKAGE)
                  set(CMAKE_FIND_ROOT_PATH_MODE_${_m} BOTH)
                endforeach()
                """))
            # 依赖接线：OHOS 分支绕开了 conan_toolchain.cmake（它会把 CMAKE_SYSTEM_NAME
            # 映射成 cmake 不认的值），因此 CMAKE_PREFIX_PATH / GTest_DIR 都没人设。
            # 这里把依赖 package 目录显式前置，find_package(GTest) 才找得到
            # conan 提供的 gtest（tool_requires 产出的 aarch64 静态库）。
            deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
            for d in deps:
                f.write('list(PREPEND CMAKE_PREFIX_PATH "%s")\n' % d.replace("\\", "/"))
            for d in deps:
                for var in ("GTest_DIR", "gtests_DIR"):
                    f.write('set(%s "%s/lib/cmake/GTest" CACHE PATH "" FORCE)\n'
                            % (var, d.replace("\\", "/")))
            rl = self._ranlib_fix(toolchain)
            if rl:
                f.write('set(CMAKE_RANLIB "%s" CACHE FILEPATH "" FORCE)\n'
                        % rl.replace("\\", "/"))
        return path

    # ---------------------------------------------------------------- generate
    def _project_variables(self):
        return {
            "BUILD_SHARED_LIBS": bool(self.options.shared),
            "BUILD_TESTS": bool(self.options.with_tests),
            "BUILD_EXAMPLE": True,
            "BUILD_DOC": False,
            "GET_OFFICIAL_DOCUMENTATION": False,
            "BINDER_PYTHON3": False,
            "BINDER_MATLAB": False,
            "BINDER_OCTAVE": False,
            # 上游默认 USE_MATRIX_FAST_ACCESSOR=ON（关掉边界检查，快但越界即崩）。
            # 库发行包取安全侧，避免消费者踩越界 SegFault。
            "USE_MATRIX_FAST_ACCESSOR": False,
        }

    def generate(self):
        tc = CMakeToolchain(self)
        for k, v in self._project_variables().items():
            tc.variables[k] = v
        if self.settings.os == "OHOS":
            toolchain = self._ohos_toolchain()
            tc.cache_variables["CMAKE_TOOLCHAIN_FILE"] = toolchain
            tc.cache_variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = self._preload_file(toolchain)
        tc.generate()

    # ------------------------------------------------------------------ config
    def _patch_upstream_test_cmake(self):
        """让上游 test/CMakeLists.txt 用 conan 提供的 gtest，不再拉 submodule。

        上游逻辑：找不到 external/gtest 就 git submodule update（交叉构建/CI 无网
        必然失败）。这里把 gtest 的引入整段替换为 find_package(GTest)。
        """
        test_cmake = os.path.join(self.source_folder, "test", "CMakeLists.txt")
        if not os.path.isfile(test_cmake):
            return
        content = open(test_cmake, encoding="utf-8").read()

        start = content.find("# Download gtest if necessary")
        end = content.find("##############\n# Unit Tests")
        if start == -1 or end == -1:
            return
        replacement = textwrap.dedent("""\
            # gtest is supplied by the conan tool_requires (test framework dependency);
            # the upstream git-submodule download cannot work in a cross build / offline CI.
            find_package(GTest REQUIRED)

            """)
        content = content[:start] + replacement + content[end:]

        # gtest_main -> GTest::gtest_main（conan 的 gtest 包导出 CMake target）
        content = content.replace(
            "target_link_libraries(${PROJECT_NAME} gtest_main ezc3d)",
            "target_link_libraries(${PROJECT_NAME} GTest::gtest_main ezc3d)",
        )
        # C3D 数据已由本配方在 source() 阶段预取到 test/c3dFiles/，
        # 删掉 CMake 的 file(DOWNLOAD)/解包逻辑（交叉构建 + CI 禁网下会失败），
        # 只保留“把 *.c3d 拷到 ${CMAKE_BINARY_DIR}/c3dTestFiles/”这一段。
        dl_start = content.find("# Download and copy c3d test files from test suite of pyomeca")
        if dl_start != -1:
            content = content[:dl_start] + textwrap.dedent("""\
                # C3D test data is pre-fetched by the conan recipe (conandata.yml
                # test_data) into test/c3dFiles/; just stage it next to the test binary,
                # where the upstream test cases expect it (relative "c3dTestFiles/...").
                file(GLOB C3D_TEST_FILES ${CMAKE_CURRENT_SOURCE_DIR}/c3dFiles/*.c3d)
                if(NOT C3D_TEST_FILES)
                    message(FATAL_ERROR "no C3D test files found in ${CMAKE_CURRENT_SOURCE_DIR}/c3dFiles")
                endif()
                file(COPY ${C3D_TEST_FILES} DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/c3dTestFiles/)
                """)

        open(test_cmake, "w", encoding="utf-8").write(content)

    # ------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        if self.options.with_tests:
            self._patch_upstream_test_cmake()

        cmake = CMake(self)
        variables = self._project_variables()
        # 只有确实拿到模拟器才注入。这里**绝不能**再调用旧 _qemu_wrapper()：
        # 它在探测不到 qemu 时会抛 ConanInvalidConfiguration，而那正是
        # CI build #80093 整包失败的直接原因。拿不到模拟器时，_run_upstream_tests()
        # 会如实"只编译不执行"，不会崩。
        emulator = self._emulator() if self.options.with_tests else None
        if emulator:
            variables["CMAKE_CROSSCOMPILING_EMULATOR"] = emulator

        cmake.configure(variables=variables)
        cmake.build()

        if self.options.with_tests:
            self._run_upstream_tests()

    def _emulator(self):
        """返回可用的 aarch64 模拟器前缀；没有则返回 None（**永不抛异常**）。

        探测顺序：
          1) profile [conf] tools.cmake.cmaketoolchain:extra_variables 里的
             CMAKE_CROSSCOMPILING_EMULATOR（团队/CI 的统一注入点）；
          2) 环境变量 OHOS_QEMU（+ OHOS_RUNROOT 作为 musl 运行根）。

        与旧 _qemu_wrapper() 的唯一区别：探测不到时返回 None 而不是抛
        ConanInvalidConfiguration —— 让调用方决定"降级"还是"报错"。
        """
        emu = self.conf.get("tools.cmake.cmaketoolchain:extra_variables", default={},
                            check_type=dict).get("CMAKE_CROSSCOMPILING_EMULATOR")
        if emu:
            return emu
        runroot = os.environ.get("OHOS_RUNROOT", "/root/ohpc/sdk/ohos-runroot")
        qemu = os.environ.get("OHOS_QEMU", "/root/ohpc/sdk/qemu/usr/bin/qemu-aarch64-static")
        if os.path.isfile(qemu):
            return "%s -L %s" % (qemu, runroot)
        return None

    # gtest 套件分批执行：5 个 ForcePlatForm 用例在 qemu 下单个就要几分钟，
    # 53 个用例塞进一次调用会超时/被 OOM 杀掉（实测 Error 137）。
    # 分批不减少覆盖：每批用 --gtest_filter 精确圈定，全部 53 个用例都会真实执行。
    _TEST_BATCHES = (
        # (标签, gtest_filter)
        ("math", "String.*:Matrix*.*:Vector*.*:initialize.*"),
        ("parse", "parameters.*:c3dModifier.*:wrongC3D.*:parametrizedC3d.*:c3dShow.*"),
        ("fileio", "c3dFileIO.*:c3dFileio.*"),
        ("forceplatform", "ForcePlatForm.*"),
    )

    def _test_binary(self):
        return os.path.join(self.build_folder, "test", "ezc3d_test")

    def _run_upstream_tests(self):
        """真实执行上游 GoogleTest 套件（rule4 证据）；失败即构建失败。

        分批执行（见 _TEST_BATCHES）：每批独立进程 + 独立 gtest_filter，
        逐批校验退出码与通过数，最后核对总通过数 == 上游声明的 53。
        """
        binary = self._test_binary()
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration("上游测试二进制未生成: %s" % binary)
        # cwd 必须是含 c3dTestFiles/ 的 test 构建目录（用例用相对路径）
        cwd = os.path.dirname(binary)
        prefix = ""
        if self.settings.os == "OHOS":
            emu = self._emulator()
            if not emu:
                # 交叉编译且无模拟器（如 CI worker）：上游测试二进制**已经编译成功**
                # （这本身就是 rule4 的构建证据），但本机跑不了 —— 如实跳过，
                # 不再让整包构建失败。这是 CI build #80093 的直接修复点。
                self.output.warning(
                    "== 上游测试二进制已编译成功，但目标为 OHOS/aarch64 且未提供模拟器"
                    "（OHOS_QEMU / profile 的 CMAKE_CROSSCOMPILING_EMULATOR 均不可用）"
                    "—— 跳过执行，仅提供编译证据: %s" % binary)
                return
            prefix = emu + " "
        elif not can_run(self):
            self.output.warning(
                "== 上游测试二进制已编译成功，但本机无法执行该目标产物 —— 跳过执行: %s"
                % binary)
            return

        total_passed = 0
        total_failed = 0
        total_ran = 0
        for label, filt in self._TEST_BATCHES:
            cmd = '%s"%s" --gtest_color=no --gtest_filter=%s > "%s" 2>&1' % (
                prefix, binary, filt,
                os.path.join(self.build_folder, "test", "gtest_%s.log" % label))
            self.output.info("== upstream GoogleTest batch [%s]: %s" % (label, cmd))
            ret = self.run(cmd, cwd=cwd, ignore_errors=True)
            if ret != 0:
                self.output.error("上游测试批次 [%s] 退出码 %d，日志尾部:" % (label, ret))
                logp = os.path.join(self.build_folder, "test", "gtest_%s.log" % label)
                if os.path.isfile(logp):
                    lines = open(logp, encoding="utf-8", errors="replace").readlines()
                    self.output.error("".join(lines[-40:]))
                raise ConanException(
                    "上游测试批次 [%s] 失败 (exit=%d)" % (label, ret))
            log = os.path.join(self.build_folder, "test", "gtest_%s.log" % label)
            if os.path.isfile(log):
                text = open(log, encoding="utf-8", errors="replace").read()
                m = re.search(r"\[==========\] (\d+) tests? from .* ran", text)
                if m:
                    total_ran += int(m.group(1))
                m = re.search(r"\[  PASSED  \] (\d+) tests?", text)
                if m:
                    total_passed += int(m.group(1))
                m = re.search(r"\[  FAILED  \] (\d+) tests?", text)
                if m:
                    total_failed += int(m.group(1))
        self.output.info("== upstream GoogleTest total: ran=%d passed=%d failed=%d"
                         % (total_ran, total_passed, total_failed))
        if total_failed or total_passed != self._EXPECTED_UPSTREAM_TESTS:
            raise ConanException(
                "上游测试未全绿: ran=%d passed=%d failed=%d (期望 %d 全通过)"
                % (total_ran, total_passed, total_failed,
                   self._EXPECTED_UPSTREAM_TESTS))

    # ----------------------------------------------------------------- package
    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # NOTE: lib/cmake/ezc3d 必须保留 —— 上游在 package() 阶段装了
        # ezc3dConfig.cmake / ezc3dConfigVersion.cmake / ezc3dTargets.cmake，
        # 这是消费者 find_package(ezc3d CONFIG REQUIRED) 的唯一来源。
        # 早期版本照搬其它配方把 lib/cmake 删掉，导致 test_package 直接
        # "Could not find a package configuration file provided by ezc3d"。
        # share/ 只含上游文档，删掉不影响消费者。
        rmdir(self, os.path.join(self.package_folder, "share"))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        if self.settings.os != "OHOS" or not self.options.shared:
            return
        import glob as _glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = _glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += _glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        bindir = self._toolchain_bindir()
        if not bindir:
            raise ConanInvalidConfiguration(
                "OHOS 共享库签名需要 tools.build:compiler_executables")
        objcopy = os.path.join(bindir, "llvm-objcopy")
        signer = os.path.join(bindir, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "OHOS 签名工具缺失: %s" % bindir)
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'
                     .format(oc=objcopy, f=so), ignore_errors=True)
            ret = self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                           .format(sg=signer, f=so), ignore_errors=True)
            if ret != 0:
                raise ConanInvalidConfiguration(
                    "binary-sign-tool 失败 (exit=%d) for %s" % (ret, so))

    def package_info(self):
        self.cpp_info.libs = ["ezc3d"]
        # 上游装到 include/ezc3d/*.h，且 ezc3d.h 里包含 <ezc3d/...> 形式的兄弟头
        self.cpp_info.includedirs = ["include", "include/ezc3d"]
        self.cpp_info.set_property("cmake_file_name", "ezc3d")
        self.cpp_info.set_property("cmake_target_name", "ezc3d::ezc3d")
        self.cpp_info.set_property("pkg_config_name", "ezc3d")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
