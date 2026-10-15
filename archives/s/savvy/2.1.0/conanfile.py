#!/usr/bin/env python3
"""Conan recipe — savvy 2.1.0 (CMake, header-only library + sav CLI).

savvy 是 SAV 变体文件格式的官方 C++ 接口，支持 BCF/VCF 读写。上游
add_library(savvy INTERFACE) 为 header-only（include/savvy/*.hpp），
并附带 src/sav/ 的 `sav` 命令行工具。头文件 include <shrinkwrap/*.hpp>
（zstd/gz/stdio/bgzf），链接期依赖由 shrinkwrap 传递（xz/zlib/zstd）。

OHOS notes
----------
* 上游 header-only + CLI：package_type=header-library（产物含 bin/sav，经
  bindirs + software-level commands.json（R38）交付）；包无 .so/.a，consumers
  经 savvy::savvy 头文件接口使用。注意不能用 application：Conan 2 CMakeDeps
  对 application 丢弃 cpp_info.includedirs/libs，消费者会 file not found。
* 上游 find_package(shrinkwrap REQUIRED) + target_link_libraries(savvy
  INTERFACE shrinkwrap) 用裸目标名；Conan CMakeDeps 只生成
  shrinkwrap::shrinkwrap，裸名会导致 -lshrinkwrap 且无 include 目录。
  build() 用 replace_in_file 改成命名空间目标（zydis 同款 Zycore 前例）。
* 上游测试（-DBUILD_TESTS=ON）的 savvy-test 全部校验用 C 的 assert()；CI
  profile 是 Release（NDEBUG），断言会被编译掉导致"静默通过"。build() 给
  savvy-test 目标加 -UNDEBUG 使断言真实验证（c-algorithms R09 同款前例）。
* 上游测试需 test_file.vcf / test_file_missing_headers.vcf（源码树根目录）
  作 fixture（经 -DSAVVYT_VCF_FILE 编译期绝对路径注入），scratch 写到进程
  cwd（Conan build 目录，可写）。
* 真机 /tmp 只读时复用 hmbs 注入的 TMPDIR/TMP/TEMP，规避 CMake try_compile
  与 ctest 的临时文件写入失败。
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get, replace_in_file


class SavvyConan(ConanFile):
    name = "savvy"
    version = "2.1.0"
    description = (
        "Official C++ interface library for the SAV file format with "
        "seamless support for BCF and VCF variant files (header-only), "
        "plus the sav command-line utility"
    )
    license = "MPL-2.0"
    homepage = "https://github.com/statgen/savvy"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("sav", "variant", "vcf", "bcf", "genomics", "savvy",
              "bioinformatics")
    # savvy 本质是 header-only INTERFACE 库（add_library(savvy INTERFACE)，无 .a/.so），
    # 附带 bin/sav 工具。必须按 header-library 打包：Conan 2 的 CMakeDeps 对
    # package_type=application 会丢弃 cpp_info.includedirs/libs（*-data.cmake 的
    # INCLUDE_DIRS 为空），导致 test_package 消费者 `#include <savvy/varint.hpp>`
    # file not found（basisu/razercfg/pianobar 同款前例）。bin/sav 仍经 bindirs
    # + 软件级 commands.json 交付，二者互不冲突。
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # 上游仅 find_package(shrinkwrap REQUIRED)；xz/zlib/zstd 由
        # libshrinkwrap 的 requires 经 CMakeDeps 传递（transitive_headers/libs）。
        self.requires("libshrinkwrap/1.2.0")

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # HMBS true-device mounts /tmp read-only; reuse injected writable
        # TMPDIR/TMP/TEMP so CMake compiler checks, clang temp files and
        # ctest can write. Only redirects the temp root, never skips tests.
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        cap = os.getenv("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                tmpdir = json.loads(cap).get("tmpdir")
                if tmpdir and tmpdir not in candidates:
                    candidates.insert(0, tmpdir)
            except Exception:
                pass
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                os.environ["GOTMPDIR"] = cand
                return cand
            except Exception:
                continue
        return None

    def _resolve_compiler(self, configured, names):
        # Tool-specific candidates only: never fall back from C to C++ names
        # or vice versa. Prefer the profile's configured absolute path when it
        # exists (CI workers), otherwise resolve via PATH (true device migrated
        # clang to ~/usr/local/bin) or the ~/usr/local/bin fallback.
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tmpdir = self._ensure_writable_tmp()
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.define("GOTMPDIR", tmpdir)
            env.vars(self, scope="build").save_sh("hmbs_tmpdir")
        toolchain = CMakeToolchain(self)
        # True device migrated clang out of /data/service/hnp/bin; pin the
        # resolved compiler path so conan_toolchain.cmake does not reference
        # a missing tool.
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"),
                                      ("clang++", "c++"))
        if _c:
            toolchain.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            toolchain.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag compilers c=%s cxx=%s" % (_c, _cxx))
        # 打开上游官方测试（L1 证据）；其余条件特性（需要 htslib/armadillo/
        # OpenCL/xtensor-blas 等系统库）Q3 显式关闭，避免无谓依赖。
        toolchain.variables["BUILD_TESTS"] = True
        toolchain.variables["BUILD_EVAL"] = False
        toolchain.variables["BUILD_SLR_EXAMPLES"] = False
        toolchain.variables["BUILD_SPARSE_REGRESSION"] = False
        # 上层 manuals 自定义 target 依赖 help2man，非默认构建目标，无需干预。
        toolchain.generate()
        CMakeDeps(self).generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # Evidence: the cache_variables pin of CMAKE_C/CXX_COMPILER did NOT
        # override the stale profile value on the true device; correct the
        # generated conan_toolchain.cmake single file and export CC/CXX in
        # build scope -- only when the configured path is missing and the
        # resolved one exists (CI workers untouched).
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.exists(c_old) and os.path.exists(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.exists(cxx_old) and os.path.exists(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info(
                        "HMBS diag fixed generated toolchain %s" % path)
            else:
                self.output.warning(
                    "HMBS diag toolchain file not found: %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning(
                "HMBS diag compiler env export failed: %s" % e)

    def _apply_cmake_fixes(self):
        # 1) 上游 cmake_minimum_required(VERSION 3.2) 被较新的 CMake（真机
        #    cmake 4.1.2）拒绝：4.x 起移除了对 CMake < 3.5 的兼容。提升到
        #    3.5 是最小可兼容值（4.x 支持的最低版本），工程本身仅用 C++11
        #    + 旧式 INTERFACE 指令，3.5 语义完全覆盖。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "cmake_minimum_required(VERSION 3.2)",
            "cmake_minimum_required(VERSION 3.5)",
        )
        # 2) 裸 shrinkwrap 目标 → 命名空间目标（CMakeDeps 只生成前者）。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "target_link_libraries(savvy INTERFACE shrinkwrap)",
            "target_link_libraries(savvy INTERFACE shrinkwrap::shrinkwrap)",
        )
        # 3) 上游测试用 assert()，CI Release(NDEBUG) 会把断言编译掉 → 静默
        #    通过。给有且仅有的测试目标 savvy-test 加 -UNDEBUG 使断言生效
        #    （生产 sav 二进制不受影响）。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "target_link_libraries(savvy-test savvy)",
            "target_link_libraries(savvy-test savvy)\n"
            "target_compile_options(savvy-test PRIVATE -UNDEBUG)",
        )
        # 4) 上游 SAV2 writer 把 s1r 索引写到硬编码 /tmp/tmpfileXXXXXX（mkstemp），
        #    在 HMBS 真机 /tmp 只读环境下创建失败 → 索引不会追加回 SAV 文件 →
        #    reader 加载内嵌索引失败 → random_access_test 的 reset_bounds 置
        #    failbit，assert(rdr.good()) 失败。改为优先使用 TMPDIR/TMP（配方
        #    _ensure_writable_tmp 已统一注入可写目录并导出到 build 环境），并顺带
        #    修正上游 !tmp_fd 的错误判断（mkstemp 失败返回 -1 为真值，原判断
        #    永远走不到错误分支）。纯 portability，无 __OHOS__。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "include", "savvy", "writer.hpp"),
            '          std::string tmp_idx_path = "/tmp/tmpfileXXXXXX";\n'
            "          int tmp_fd = mkstemp(&tmp_idx_path[0]);\n"
            "          if (!tmp_fd)",
            '          const char* _savvy_tmpdir = std::getenv("TMPDIR");\n'
            '          if (!_savvy_tmpdir || !_savvy_tmpdir[0]) _savvy_tmpdir = std::getenv("TMP");\n'
            '          if (!_savvy_tmpdir || !_savvy_tmpdir[0]) _savvy_tmpdir = "/tmp";\n'
            '          std::string tmp_idx_path = std::string(_savvy_tmpdir) + "/tmpfileXXXXXX";\n'
            "          int tmp_fd = mkstemp(&tmp_idx_path[0]);\n"
            "          if (tmp_fd < 0)",
        )
        # 5) 上游 utility.hpp 有两处「未自包含」的潜在缺陷，仅在 consumer 独立
        #    include 时暴露（本 test_package 即触发）：
        #    a. 用 std::cerr/std::endl 却未 #include <iostream>（line 184）；
        #    b. 用 savvy::typed_value::is_end_of_vector（line 63）却未 include
        #       typed_value.hpp。
        #    savvy 是 header-only 消费库，头必须自包含，否则任何消费者
        #    include <savvy/utility.hpp>（或包含它的 <savvy/savvy.hpp>）都编译不过。
        #    为 utility.hpp 补上两个 include（typed_value.hpp 位于同目录且自身
        #    已 include <iostream>）。纯 portability，无 __OHOS__。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "include", "savvy", "utility.hpp"),
            '#include "portable_endian.hpp"\n'
            '#include "compressed_vector.hpp"\n'
            '\n'
            '#include <sys/stat.h>',
            '#include "portable_endian.hpp"\n'
            '#include "compressed_vector.hpp"\n'
            '#include "typed_value.hpp"\n'
            '\n'
            '#include <iostream>\n'
            '#include <sys/stat.h>',
        )

    def _hmbs_emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            payload, separators=(",", ":"))
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                with open(os.path.join(bf, "hmbs_upstream.json"),
                          "w", encoding="utf-8") as f:
                    json.dump(payload, f)
        except Exception as e:
            self.output.warning("HMBS diag persist upstream failed: %s" % e)
        return line

    def _parse_ctest_log(self, log_path):
        # 唯一数据源：ctest 自身的执行日志。逐行解析 `Test #N: <name>` 进度行，
        # 按该行出现的 Passed / Failed / Skipped / Not Run 关键字归类，绝不对
        # stdout 做字符串数数或算术修补。
        discovered = passed = failed = skipped = 0
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if "Test #" not in line:
                    continue
                m = re.search(r"Test #(\d+):", line)
                if not m:
                    continue
                discovered += 1
                low = line.lower()
                if "passed" in low:
                    passed += 1
                elif ("failed" in low or "exception" in low
                      or "aborted" in low or "***" in line):
                    failed += 1
                elif "skipped" in low or "not run" in low or "notrun" in low:
                    skipped += 1
        return discovered, passed, failed, skipped

    def build(self):
        self._ensure_writable_tmp()
        self._apply_cmake_fixes()
        # 上游 5 个 ctest 用例共用一个测试可执行文件 savvy-test，且 convert-file /
        # subset / random-access 都会在进程 cwd 写/读同一对 fixture 产物
        # test_file_hard.sav / test_file_dose.sav（main.cpp 的 convert_file_test +
        # file_exists 缓存判断）。ctest 并行时多个 savvy-test 进程同时写这些文件，
        # 后启动的 reader 读到半写状态 → read_header 报 "Unsupported file format"
        # → assert(rdr.good()) 失败；checksum 用例读到不同内容也失败。CI worker 未
        # 注入 tools.build:jobs，Conan 的 cmake.ctest() 会自动追加
        # `--parallel <cpu_count>`（本机 20）触发该竞态；HMBS 真机注入
        # tools.build:jobs=1 恰好串行所以此前通过。这里显式钉为串行，与上游 CI
        # 默认一致，不跳过任何用例（librtpi/neko/objfw 同款 conf 前例）。
        self.conf.define("tools.build:jobs", 1)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试（L1）──
        ctest_log = os.path.join(self.build_folder, "hmbs_ctest.log")
        with open(ctest_log, "w", encoding="utf-8") as handle:
            cmake.ctest(cli_args=["--output-on-failure"], stdout=handle,
                        stderr=handle)
        # 失败时 cmake.ctest() 抛异常，不会走到这里；因此此处日志必为全过。
        discovered, passed, failed, skipped = self._parse_ctest_log(ctest_log)
        with open(ctest_log, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                self.output.info("HMBS ctest: %s" % line.rstrip())
        if discovered <= 0:
            # 找不到可解析的用例行：如实失败，不用猜测值凑数。
            raise ConanException(
                "HMBS ctest log unparseable (no 'Test #N' lines): %s"
                % ctest_log)
        self._hmbs_emit_upstream({
            "status": "passed",
            "framework": "ctest",
            "command": "ctest --output-on-failure --parallel 1",
            "discovered": discovered,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        })

    def package(self):
        self._ensure_writable_tmp()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include", "savvy"),
             dst=os.path.join(self.package_folder, "include", "savvy"),
             keep_path=True)
        # sav CLI 产物：cmake_layout 下单配置 CMAKE_BINARY_DIR==build_folder，
        # 未设 RUNTIME_OUTPUT_DIRECTORY 时可执行文件落在二进制目录根。
        sav_exe = None
        for cand in (os.path.join(self.build_folder, "sav"),
                     os.path.join(self.build_folder, "bin", "sav")):
            if os.path.isfile(cand):
                sav_exe = cand
                break
        if sav_exe is None:
            for root, _ds, files in os.walk(self.build_folder):
                for fn in files:
                    if fn == "sav":
                        sav_exe = os.path.join(root, fn)
                        break
                if sav_exe:
                    break
        if sav_exe:
            copy(self, "sav", src=os.path.dirname(sav_exe),
                 dst=os.path.join(self.package_folder, "bin"),
                 keep_path=False)
            self.output.info("HMBS diag packaged sav from %s" % sav_exe)
        else:
            self.output.warning("HMBS diag sav executable not found")
        # Carry the real upstream result into the package so cache-hit
        # test_package runs can re-emit without re-running the build.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst_dir,
                                                  "hmbs_upstream.json"))
            else:
                self.output.warning(
                    "HMBS diag hmbs_upstream.json missing in package()")
        except Exception as e:
            self.output.warning("HMBS diag package upstream copy failed: %s"
                                % e)

    def package_info(self):
        # savvy 为 header-only INTERFACE 库：无库文件可链，consumers 经
        # 头文件 + savvy::savvy 目标使用；CLI sav 经 bindirs 暴露。
        # package_type=header-library 后 CMakeDeps 默认即把 includedirs（=include）
        # 挂到 savvy::savvy；这里再显式声明强化契约，确保
        # <savvy/varint.hpp>/<savvy/utility.hpp> 对消费者可见。
        self.cpp_info.includedirs = ["include"]
        # savvy 头文件用到 shrinkwrap（zstd/gz/stdio/bgzf）的运行时符号，
        # 必须把 libshrinkwrap 的链接信息级联给消费者（其内部再传递 xz/
        # zlib/zstd），否则链接 savvy::savvy 会缺 -lzstd 等符号。
        self.cpp_info.requires = ["libshrinkwrap::libshrinkwrap"]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "savvy")
        self.cpp_info.set_property("cmake_target_name", "savvy::savvy")
        self.cpp_info.set_property("pkg_config_name", "savvy")

