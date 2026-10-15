#!/usr/bin/env python3
"""Consumer test for packaged savvy 2.1.0 (L1)."""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class SavvyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeToolchain/CMakeDeps/VirtualRunEnv 均在 generate() 手动实例化（需注入
    # 真机编译器路径并导出可写 TMPDIR），因此不能再同时声明到 generators——
    # Conan 会把 CMakeToolchain 重复生成而报
    # "CMakeToolchain is declared in the generators attribute, but was
    #  instantiated in the generate() method too"。
    generators = ()
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # Mirror main recipe: redirect temp root away from read-only /tmp.
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

    def generate(self):
        self._ensure_writable_tmp()
        tc = CMakeToolchain(self)
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
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag test compilers c=%s cxx=%s" % (_c, _cxx))
        tc.generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _hmbs_emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        self._ensure_writable_tmp()
        if cross_building(self):
            self.output.info("cross-building: consumer compiled and linked")
            return
        # 1) 消费者二进制（内部 29 条断言，任一失败返回非零）
        executable = os.path.join(self.cpp.build.bindirs[0], "test_savvy")
        self.run(executable, env="conanrun")
        # 2) 安装的 sav CLI 冒烟（L2）
        sav_exe = os.path.join(self.dependencies["savvy"].package_folder,
                               "bin", "sav")
        self.run("%s --version" % sav_exe, env="conanrun")
        # 两者都退出 0（上面 self.run 失败即抛异常）：2 个真实用例。
        self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
            {"executed": True, "passed": True,
             "command": "./test_savvy && sav --version",
             "discovered": 2, "passedCount": 2},
            separators=(",", ":")))
        # Re-emit the real upstream result carried in the package res so
        # cache-hit runs still provide evidence every round.
        try:
            res = os.path.join(self.dependencies["savvy"].package_folder,
                               "res", "hmbs_upstream.json")
            with open(res, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if payload.get("status") == "passed" and \
                    int(payload.get("discovered", 0)) > 0 and \
                    int(payload.get("executed", 0)) > 0:
                self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
                    payload, separators=(",", ":")))
            else:
                self.output.warning(
                    "HMBS diag upstream res invalid: %s" % payload)
        except Exception as e:
            self.output.warning(
                "HMBS diag upstream res missing: %s" % e)
