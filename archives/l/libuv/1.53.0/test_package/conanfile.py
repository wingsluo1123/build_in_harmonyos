#!/usr/bin/env python3
"""Conan test_package — libuv 1.53.0

R34: 实质依赖被测包 API（调用 uv_version_string / uv_default_loop /
uv_timer_init / uv_os_get_passwd / uv_loop_close）。

test() 输出两个 HMBS 机器证据标记：
- HMBS_TEST_PACKAGE_RESULT: 运行 ./test_libuv，从 stdout 的确定性
  `PASS: <name>` 行计数（discovered/passedCount），禁止字符串数数修补。
- HMBS_UPSTREAM_TEST_RESULT: 复发 build() 中 uv_run_tests_a 的 TAP 结果
  JSON（持久化于 <package>/res/upstream_test_result.json，包缓存命中时
  build() 不重跑，仅 test_package 每轮必跑，保证标记每轮出现）。
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibuvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _fix_toolchain_for_preflight(self):
        # 与主包同因：profile 编译器绝对路径在预检机不可用，cmake 不识
        # HarmonyOS。os.walk 全量定位工具链，缺失编译器回退 PATH，
        # 系统名回退 Linux，保证 test_package configure 与主包一致。
        import os
        import re
        import shutil
        hits = []
        for root, _d, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" in files:
                hits.append(os.path.join(root, "conan_toolchain.cmake"))
        for f in sorted(set(hits)):
            try:
                t = open(f, encoding="utf-8").read()
            except Exception:
                continue
            orig = t
            if "HarmonyOS" in t:
                t = t.replace("HarmonyOS", "Linux")
            try:
                comp = self.conf.get("tools.build:compiler_executables",
                                     default={}, check_type=dict) or {}
            except Exception:
                comp = {}
            def _usable(x):
                return bool(x) and os.path.isfile(x) and os.access(x, os.X_OK)
            pairs = [("CMAKE_C_COMPILER", (comp.get("c", "") or "").strip(), ["clang", "cc"]),
                     ("CMAKE_CXX_COMPILER", (comp.get("cpp", "") or "").strip(), ["clang++", "c++"])]
            for var, cur_raw, names in pairs:
                m = re.search(r"set\(" + var + r"\s+\"([^\"]+)\"", t)
                cur = m.group(1) if m else cur_raw
                if _usable(cur):
                    continue
                target = cur if _usable(cur) else ""
                if not _usable(target) and cur_raw:
                    w = shutil.which(os.path.basename(cur_raw))
                    if w and _usable(w):
                        target = w
                if not _usable(target):
                    for nm in names:
                        w = shutil.which(nm)
                        if w and _usable(w):
                            target = w
                            break
                if _usable(target) and m:
                    t = re.sub(r"set\(" + var + r"\s+\"[^\"]+\"",
                               "set(" + var + ' "%s"' % target, t, count=1)
            if t != orig:
                open(f, "w", encoding="utf-8", newline="\n").write(t)

    def _find_test_binary(self):
        # CI 证据 (#95928)：test 二进制实际位于
        # test_package/build/clang-15-armv8-17-release/test_libuv，
        # 而旧 test() 先以脆弱 cwd 猜测 `./test_libuv` 直接运行，
        # 失败抛 127 后兜底 walk 永远执行不到。
        # 本方法改走先定位后运行单一路线，不猜 cwd。
        import os
        cands = []
        for root, _d, files in os.walk(self.build_folder):
            for nm in ("test_libuv", "test_libuv.exe"):
                if nm in files:
                    cands.append(os.path.join(root, nm))
        cands = sorted(set(cands))
        if not cands:
            return None
        # 优先可执行位已置的候选，否则取首个
        for c in cands:
            if os.access(c, os.X_OK):
                return c
        return cands[0]

    def _sign_file_for_exec(self, path):
        import os
        import shutil as _sh
        if not path or not os.path.isfile(path):
            return False
        try:
            os.chmod(path, 0o755)
        except Exception:
            pass
        objcopy = "/data/service/hnp/bin/llvm-objcopy" if os.path.isfile("/data/service/hnp/bin/llvm-objcopy") else (_sh.which("llvm-objcopy") or "")
        signer = "/data/service/hnp/bin/binary-sign-tool" if os.path.isfile("/data/service/hnp/bin/binary-sign-tool") else (_sh.which("binary-sign-tool") or "")
        if not objcopy or not signer:
            self.output.info("[libuv] test sign tools absent, skip codesign")
            return False
        try:
            _oc_cmd = '{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=objcopy, f=path)
            _run_opts = {'ignore_errors': True}
            self.run(_oc_cmd, **_run_opts)
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=path))
            self.output.info("[libuv] signed test binary: %s" % path)
            return True
        except Exception as e:
            self.output.warning("[libuv] test codesign failed %s: %r" % (path, e))
            return False

    def build(self):
        self._fix_toolchain_for_preflight()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        try:
            _b = self._find_test_binary()
            if _b:
                self._sign_file_for_exec(_b)
        except Exception as e:
            self.output.warning("[libuv] post-build sign hook error: %r" % (e,))

    def test(self):
        # 1) 冒烟测试：先定位二进制绝对路径并签名，再单次运行；
        #    从 `PASS: <name>` 确定性行解析真实计数。
        bin_path = self._find_test_binary()
        if not bin_path or not os.path.isfile(bin_path):
            raise ConanException(
                "[libuv] test_libuv binary not found under %s" % self.build_folder)
        try:
            self._sign_file_for_exec(bin_path)
        except Exception as e:
            self.output.warning("[libuv] sign hook error: %r" % (e,))
        log = os.path.join(self.build_folder, "test_libuv.log")
        # 共享库运行时路径：OHOS loader 在无 rpath 时需 LD_LIBRARY_PATH
        try:
            dep_lib = os.path.join(self.dependencies["libuv"].package_folder, "lib")
            _ld = os.environ.get("LD_LIBRARY_PATH", "")
            if os.path.isdir(dep_lib) and dep_lib not in _ld:
                os.environ["LD_LIBRARY_PATH"] = dep_lib + (":" + _ld if _ld else "")
                self.output.info("[libuv] test LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"])
        except Exception as e:
            self.output.warning("[libuv] LD_LIBRARY_PATH setup failed: %r" % (e,))
        bin_dir = os.path.dirname(bin_path)
        self.run('"%s" > "%s" 2>&1' % (bin_path, log),
                 cwd=bin_dir,
                 ignore_errors=False)
        with open(log, encoding="utf-8", errors="replace") as f:
            out = f.read()
        print(out, end="" if out.endswith("\n") else "\n")
        if os.path.getsize(log) == 0:
            raise ConanException("[libuv] test_libuv produced empty output (fixture missing?)")
        passes = re.findall(r"^PASS: (\S+)\s*$", out, re.M)
        fails = re.findall(r"^FAIL: (\S+)", out, re.M)
        discovered = len(passes) + len(fails)
        passed_count = len(passes) if not fails else 0
        tp_ok = (discovered == 5 and not fails)
        tp_result = {
            "executed": True,
            "passed": tp_ok,
            "command": bin_path,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result), flush=True)
        if not tp_ok:
            raise ConanException(
                "[libuv] test_package smoke test failed: %s"
                % json.dumps(tp_result))

        # 2) 复发上游测试结果（build() 已执行 uv_run_tests_a 并持久化进包）。
        dep = self.dependencies["libuv"]
        jf = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(jf):
            raise ConanException(
                "[libuv] upstream_test_result.json missing from package; "
                "upstream tests did not run in build()")
        with open(jf, encoding="utf-8") as f:
            up_result = json.load(f)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up_result), flush=True)
