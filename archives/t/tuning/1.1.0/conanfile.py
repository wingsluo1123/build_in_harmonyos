#!/usr/bin/env python3
"""Conan recipe — tuning 1.1.0.

上游工程 = Surge Synth Team **Tuning Library**
（仓库 github.com/surge-synthesizer/tuning-library，发布 tag `release_1.1.0`；
Debian 源码包 `tuning-library` 1.1.0+ds-4，二进制包 `libtuning-library-dev`）。

库本体是 **header-only C++14** 库：CMake `add_library(tuning-library INTERFACE)`，
两个头文件 `include/Tunings.h` + `include/TuningsImpl.h`（Scala `.scl` / `.kbm`
调律文件读写、MIDI 音高 ↔ 频率换算），**零第三方运行时依赖** —— 头文件只
`#include` C++ 标准库头。

OHOS 平台适配要点：
  * E092 —— CMake 没有 HarmonyOS platform module（实测 `CMAKE_SYSTEM_NAME=HarmonyOS`
    时 CMake 打印 `System is unknown to cmake, create: Platform/HarmonyOS`，且对象文件
    扩展名退化为 `.obj`）。generate() 显式映射 `CMAKE_SYSTEM_NAME=Linux` +
    `CMAKE_SYSTEM_PROCESSOR=aarch64`（conan `arch=armv8` 不是合法 CMake processor 名），
    让上游走 CMake 的 POSIX 分支。
  * E266 —— OHOS SDK 的 lld 动态依赖 `libxml2.so.16`，前置 SDK `llvm/lib` 到
    `LD_LIBRARY_PATH`，避免部分 worker 上链接器启动失败。
  * **库本体零补丁**：头文件不碰 POSIX/Linux 专有接口，OHOS 的 libc++ / clang 15
    直接编译通过。
  * 上游测试用源码包**自带**的 `libs/catch2/catch2.hpp`（Catch2 2.9.2 单头文件），
    因此本配方不需要 `catch2` conan 包（与 `ableton-link` 使用内置 catch 同口径）。
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# 上游测试的用例总数（tests/alltests.cpp 里 18 个 TEST_CASE），见 MANIFEST.yml 申报表
UPSTREAM_TEST_CASES = 18
# 上游 tests/alltests.cpp 的 SECTION 声明数（sections 覆盖率分母；实际值运行期从源码统计）
UPSTREAM_SECTIONS = 62
# 上游测试套件读取 tests/data/*.scl|*.kbm，要求 cwd = 源码根（同上游 run-all-tests 的 WORKING_DIRECTORY）
TEST_LOG_SUBDIR = "upstream-test-logs"
# OHOS SDK 目录（其 llvm/lib 内含 lld 依赖的 libxml2.so.16；E266）
OHOS_SDK_LLVM_GLOB = "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"

# 官方源（R39）。CI 与本地工具链会把 conandata.yml 里的 github.com 地址改写为镜像
# （CI: gh-proxy.com / 本地 conan-verify: ghfast.top）。镜像只做加速、不应成为单点：
# 下方 source() 在镜像 URL 之后追加官方源作为回退（与 CI get_mirror_list 的
# "[mirror, url]" 口径一致），sha256 强校验，回退不降低完整性。
OFFICIAL_SOURCE_URL = (
    "https://github.com/surge-synthesizer/tuning-library/archive/refs/tags/release_1.1.0.tar.gz"
)


class TuningConan(ConanFile):
    name = "tuning"
    version = "1.1.0"
    description = ("Tuning Library (upstream: tuning-library) — header-only C++14 Scala "
                   ".scl/.kbm tuning file reader/writer and MIDI note to frequency mapping")
    license = "MIT"
    homepage = "https://github.com/surge-synthesizer/tuning-library"
    url = "https://github.com/surge-synthesizer/tuning-library"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        src = dict(self.conan_data["sources"])
        urls = src.pop("url")
        if isinstance(urls, str):
            urls = [urls]
        # 镜像不可达时回退官方源（sha256 强校验，内容完整性由 conandata.yml 保证）
        if OFFICIAL_SOURCE_URL not in urls:
            urls.append(OFFICIAL_SOURCE_URL)
        get(self, url=urls, sha256=src["sha256"], strip_root=True)

    def _find_ohos_llvm_lib(self):
        """探测 OHOS SDK 的 llvm/lib（内含 lld 依赖的 libxml2.so.16；E266）。

        优先级：环境变量 `OHOS_SDK_LLVM_LIB` > `ohos-sdk_*` 版本目录 glob（取版本号最大者）。
        探测不到返回空串 —— 调用方跳过注入，避免把不存在的路径塞进 LD_LIBRARY_PATH
        （硬编码某个 SDK 版本目录会在 SDK 升级/换 worker 后静默失效）。
        """
        cand = os.environ.get("OHOS_SDK_LLVM_LIB", "")
        if cand and os.path.isdir(cand):
            return cand

        def _ver(path):
            m = re.search(r"ohos-sdk_([0-9]+(?:\.[0-9]+)*)", path)
            return tuple(int(x) for x in m.group(1).split(".")) if m else ()

        hits = [p for p in glob.glob(OHOS_SDK_LLVM_GLOB) if os.path.isdir(p)]
        return sorted(hits, key=_ver)[-1] if hits else ""

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake 不识别 HarmonyOS 目标平台；映射到 Linux/aarch64，
        # 让上游走 POSIX 分支（上游唯一平台分支 if(WIN32) 只影响 run-all-tests 的 shell 形态）。
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        elif self.settings.os == "Linux":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        # 上游默认构建全部目标：INTERFACE 库 + tuning-library-tests(Catch2) +
        # tuning-library-symbolcheck + showmapping/parsecheck 两个 CLI 样例。
        # 测试需要真实源码树 cwd（tests/data 相对路径），因此不在测试里 chdir 而是显式指定 cwd。
        tc.variables["CMAKE_CXX_STANDARD"] = "14"
        tc.generate()

        # E266: OHOS SDK 的 lld 动态依赖 libxml2.so.16（二进制已 strip、无 RUNPATH），
        # 部分 worker 默认库搜索路径找不到它 → 链接阶段 "Error loading shared library
        # libxml2.so.16"。前置 SDK llvm/lib 到 LD_LIBRARY_PATH 让 lld 正常启动
        # （expected-lite / aeolus 同方案）。SDK 路径**运行期探测**，不硬编码版本目录。
        if self.settings.os == "OHOS":
            llvm_lib = self._find_ohos_llvm_lib()
            if llvm_lib:
                env = Environment()
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
                env.vars(self).save_script("conanbuildenv_ohos_llvm")
                self.output.info(f"[E266] LD_LIBRARY_PATH += {llvm_lib}")
            else:
                self.output.info("[E266] 未探测到 OHOS SDK llvm/lib，跳过 LD_LIBRARY_PATH 注入")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 层 1: 上游官方测试套件（失败 → conan create 失败）──
        self._run_upstream_tests()

    # ────────────────────────────────────────────────────────────────
    # 上游测试执行
    # ────────────────────────────────────────────────────────────────
    def _run(self, cmd, cwd, log_path, env_extra=None, timeout=3600):
        """在 OHOS 上用 bash 执行（/system/bin/sh 是 mksh，不能直接 exec ELF），
        原始 stdout+stderr 落盘到 log_path，返回 (returncode, output)。"""
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = shutil.which("bash") or "/bin/bash"
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)
        proc = subprocess.run([bash, "-c", cmd], cwd=cwd, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=timeout)
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"$ {cmd}\n# cwd={cwd}\n# rc={proc.returncode}\n\n")
                f.write(proc.stdout or "")
        except Exception:
            pass
        return proc.returncode, (proc.stdout or "")

    def _find_bin_dir(self):
        """定位上游测试可执行文件所在目录（CMake 单配置生成器下 = build 根目录）。"""
        for root, _dirs, files in os.walk(self.build_folder):
            if "tuning-library-tests" in files and "tuning-library-symbolcheck" in files:
                return root
        return None

    def _data_root(self):
        """上游测试套件以 "tests/data/..." 相对路径读样本，cwd 必须是含 tests/data 的源码根。"""
        for cand in (self.source_folder, self.build_folder,
                     os.path.dirname(self.build_folder)):
            if cand and os.path.isdir(os.path.join(cand, "tests", "data")):
                return cand
        raise RuntimeError("tests/data not found — upstream test suite cannot run")

    def _count_upstream_sections(self):
        """从上游 `tests/alltests.cpp` 统计 SECTION 声明数（sections 覆盖率的分母）。

        取实际值而非硬编码，避免上游升级后申报数字失真；读不到源码时回退申报常量。
        """
        path = os.path.join(self._data_root(), "tests", "alltests.cpp")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                n = len(re.findall(r"\bSECTION\s*\(", f.read()))
            return n or UPSTREAM_SECTIONS
        except OSError:
            return UPSTREAM_SECTIONS

    @staticmethod
    def _parse_summary(out):
        """解析 Catch2 v2 summary → (assertions, executed, passed, failed, skipped)。"""
        m = re.search(r"All tests passed\s*\(\s*(\d+)\s+assertions?\s+in\s+(\d+)\s+test cases?\s*\)", out)
        if m:
            n = int(m.group(2))
            return int(m.group(1)), n, n, 0, 0
        m = re.search(r"test cases:\s*(\d+)\s*\|\s*(\d+)\s+passed\s*\|\s*(\d+)\s+failed"
                      r"(?:\s*\|\s*(\d+)\s+failed as expected)?", out)
        if m:
            executed = int(m.group(1))
            passed = int(m.group(2))
            failed = int(m.group(3))
            return 0, executed, passed, failed, executed - passed - failed
        return 0, 0, 0, 0, 0

    def _run_upstream_tests(self):
        bin_dir = self._find_bin_dir()
        if bin_dir is None:
            raise RuntimeError("upstream test executables (tuning-library-tests/symbolcheck) "
                               "not found in build tree")
        data_root = self._data_root()
        log_dir = os.path.join(self.build_folder, TEST_LOG_SUBDIR)
        os.makedirs(log_dir, exist_ok=True)
        tb = os.path.join(bin_dir, "tuning-library-tests")
        sc = os.path.join(bin_dir, "tuning-library-symbolcheck")

        # 1) 用例清单 + 用例总数（discovered）
        rc, out = self._run(f"{tb} --list-tests",
                            data_root, os.path.join(log_dir, "00_list_tests.log"))
        m = re.search(r"^(\d+) test cases?$", out, re.MULTILINE)
        if not m:
            raise RuntimeError("--list-tests did not report a test case count")
        discovered = int(m.group(1))
        if discovered != UPSTREAM_TEST_CASES:
            self.output.warning(f"[upstream] discovered {discovered} != 申报值 {UPSTREAM_TEST_CASES}")
        self.output.info(f"[upstream] discovered test cases = {discovered}")

        # 2) 权威运行（compact reporter，默认宿主 locale）
        rc, out = self._run(tb, data_root, os.path.join(log_dir, "01_tests_default.log"))
        assertions, executed, passed, failed, skipped = self._parse_summary(out)
        if executed == 0 and rc == 0:
            raise RuntimeError("upstream test suite produced no parseable Catch2 summary")
        if rc != 0 or failed:
            self.output.error(f"[upstream] tuning-library-tests FAILED rc={rc}\n{out[-4000:]}")
            raise RuntimeError(f"upstream test suite failed: rc={rc} failed={failed}")

        # 3) per-section 明细（JUnit reporter → 逐项通过/失败/跳过证据）
        rc_j, _ = self._run(f"{tb} -r junit -o upstream_junit.xml",
                            data_root, os.path.join(log_dir, "02_tests_junit.log"))
        sections = []
        junit_path = os.path.join(data_root, "upstream_junit.xml")
        if os.path.isfile(junit_path):
            try:
                with open(junit_path, "r", encoding="utf-8", errors="ignore") as f:
                    xml = f.read()
                sections = re.findall(r'<testcase\s+classname="[^"]*"\s+name="([^"]*)"', xml)
                shutil.copyfile(junit_path, os.path.join(log_dir, "upstream_junit.xml"))
                os.remove(junit_path)
            except Exception as exc:
                self.output.warning(f"[upstream] junit parse failed: {exc}")

        # 4) 上游 CMake run-all-tests 的 LANG 矩阵（es_ES / fr_FR / zh_CN / 空）
        lang_matrix = {}
        for tag, env_extra in (("es_ES", {"LANG": "es_ES"}),
                               ("fr_FR", {"LANG": "fr_FR"}),
                               ("zh_CN", {"LANG": "zh_CN"}),
                               ("empty", {"LANG": ""})):
            rc_l, out_l = self._run(tb, data_root,
                                    os.path.join(log_dir, f"03_lang_{tag}.log"),
                                    env_extra=env_extra)
            _a, _e, _p, _f, _s = self._parse_summary(out_l)
            lang_matrix[tag] = {"rc": rc_l, "executed": _e, "passed": _p, "failed": _f}
            if rc_l != 0 or _f:
                self.output.error(f"[upstream] LANG={tag} run FAILED rc={rc_l}\n{out_l[-3000:]}")
                raise RuntimeError(f"upstream test suite failed under LANG={tag}")

        # 5) 上游符号重复检测样例（两个 TU 链接同头文件，验证无重复符号）
        rc_s, out_s = self._run(sc, data_root, os.path.join(log_dir, "04_symbolcheck.log"))
        sym_ok = rc_s == 0 and "100 and 200 are 100 and 200" in out_s
        if not sym_ok:
            self.output.error(f"[upstream] tuning-library-symbolcheck FAILED rc={rc_s}\n{out_s[-2000:]}")
            raise RuntimeError("upstream symbolcheck failed")

        # 6) 上游 CLI 样例：parsecheck（全部 .scl/.kbm 样本）+ showmapping（映射表）
        cli = {}
        parse_cmd = (f"cd '{data_root}' && '{os.path.join(bin_dir, 'parsecheck')}' "
                     f"tests/data/*.scl tests/data/*.kbm tests/data/bad/*")
        rc_p, out_p = self._run(parse_cmd, data_root, os.path.join(log_dir, "05_parsecheck_samples.log"))
        n_pass = out_p.count("PASSED")
        n_fail = out_p.count("FAILED")
        n_skip = out_p.count("SKIPPED")
        cli["parsecheck"] = {"rc": rc_p, "passed": n_pass, "failed": n_fail, "skipped": n_skip}
        # showmapping（SCL 无 KBM / SCL+KBM 两种上游用法）
        for tag, args in (("scl_only", "tests/data/12-intune.scl"),
                          ("scl_kbm", "tests/data/12-intune.scl tests/data/mapping-whitekeys-a440.kbm")):
            rc_m, out_m = self._run(f"{os.path.join(bin_dir, 'showmapping')} {args}",
                                    data_root, os.path.join(log_dir, f"06_showmapping_{tag}.log"))
            lines = len([ln for ln in out_m.splitlines() if re.match(r"^\s*\d+,", ln)])
            cli[f"showmapping_{tag}"] = {"rc": rc_m, "mapped_note_rows": lines}
            if rc_m != 0 or lines != 128:
                raise RuntimeError(f"upstream showmapping ({tag}) unexpected: rc={rc_m} rows={lines}")

        sections_total = self._count_upstream_sections()
        upstream = {
            "status": "passed" if (failed == 0 and skipped == 0 and passed == discovered) else "incomplete",
            "framework": "catch2",
            "command": "./tuning-library-tests  (cwd=源码根; junit/compact 双 reporter)",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "assertions": assertions,
            "sections_executed": len(sections),
            "sections_total": sections_total,
            "sections_skipped": max(sections_total - len(sections), 0),
            "sections": sections,
            "lang_matrix": lang_matrix,
            "symbolcheck": {"rc": rc_s, "output": out_s.strip()},
            "cli_samples": cli,
            "log_dir": log_dir,
        }
        assert upstream["passed"] + upstream["failed"] == upstream["executed"], upstream
        assert upstream["executed"] <= upstream["discovered"], upstream
        if upstream["status"] != "passed":
            raise RuntimeError(f"upstream test suite incomplete: {json.dumps(upstream)[:1500]}")

        self.output.info(f"[upstream] {passed}/{discovered} TEST_CASEs passed, "
                         f"{assertions} assertions, {upstream['sections_executed']}/"
                         f"{upstream['sections_total']} sections executed")
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"), "w",
                      encoding="utf-8") as f:
                json.dump(upstream, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    # ────────────────────────────────────────────────────────────────
    def package(self):
        # header-only：仅导出 include/ 与 LICENSE（上游无 install 规则）。
        # Conan 2 的 copy() 按文件相对路径 fnmatch，需用通配符保留目录结构。
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "tuning")
        self.cpp_info.set_property("cmake_target_name", "tuning::tuning")
