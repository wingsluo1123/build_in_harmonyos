#!/usr/bin/env python3
"""Conan test_package for qmf: consumer links QmfClient and exercises QMailAddress."""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import replace_in_file


class QmfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtcore5compat/6.11.1")

    def layout(self):
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
        # Repo convention (bzrtp/5.3.105 precedent): the ohos-aarch64 profile
        # pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang(++), but that file is missing on some
        # preflight workers while CMakeToolchain still bakes the stale path
        # into conan_toolchain.cmake, so project() dies with "CMAKE_CXX_COMPILER
        # ... is not able to compile a simple test program". Resolve conf ->
        # PATH in order and force the existing binary (R33: no bare env).
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def generate(self):
        # Consumer-side file/target-name overrides (maeparser precedent for
        # target names; file-name part from previous round): both Qt providers
        # opt out of CMakeDeps file generation (cmake_find_mode=none, Qt ships
        # its own configs), yet qmf's generated qmf-config.cmake emits
        # find_dependency(<ref-name>) for each public dep and qmf-Target-*.cmake
        # links qtbase-sql-dbus::qtbase-sql-dbus / qtcore5compat::qtcore5compat.
        # Redirect the file edges to the real Qt configs that this test_package
        # finds first (no-op re-find) AND the link targets to the real Qt6
        # targets (Qt6::Core / Qt6::Core5Compat, provided by the single
        # find_package(Qt6 COMPONENTS Core Core5Compat) below, qtcore5compat
        # test_package precedent). Without the target redirect the file fix
        # alone still dies at qmf-Target-release.cmake:15 with 'target ...
        # qtbase-sql-dbus::qtbase-sql-dbus ... was not found'. Otherwise
        # find_package(qmf) dies with 'did not find Findqtbase-sql-dbus.cmake'.
        self.dependencies["qtbase-sql-dbus"].cpp_info.set_property(
            "cmake_file_name", "Qt6")
        self.dependencies["qtbase-sql-dbus"].cpp_info.set_property(
            "cmake_target_name", "Qt6::Core")
        self.dependencies["qtcore5compat"].cpp_info.set_property(
            "cmake_file_name", "Qt6Core5Compat")
        self.dependencies["qtcore5compat"].cpp_info.set_property(
            "cmake_target_name", "Qt6::Core5Compat")
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase-sql-dbus"].package_folder
        tc.cache_variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        qtcompat = self.dependencies["qtcore5compat"].package_folder
        tc.cache_variables["Qt6Core5Compat_DIR"] = os.path.join(
            qtcompat, "lib", "cmake", "Qt6Core5Compat")
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
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
        if not can_run(self):
            self.output.info("cross-building: consumer compiled and linked")
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_qmf executable directory was not produced")
        exe = os.path.join(bindirs[0], "test_qmf")
        env = Environment()
        for dep in self.dependencies.values():
            try:
                folder = dep.package_folder
            except Exception:
                continue
            if folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(folder, "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        logfile = os.path.join(self.build_folder, "test_package.log")
        self.run("%s > %s 2>&1" % (exe, logfile), env="conanrun", ignore_errors=True)
        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_qmf log:\n" + "\n".join(out.splitlines()[-20:]))
        m = re.search(r"RESULT:\s*(\d+)\s*passed,\s*(\d+)\s*failed", out)
        if not m:
            raise ConanException("test_qmf produced no RESULT line - harness broken")
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = (failed == 0 and discovered > 0)
        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_qmf",
            "discovered": discovered,
            "passedCount": passed,
        }
        self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, separators=(",", ":")))
        if not ok:
            raise ConanException("test_qmf failed: %d/%d cases failed" % (failed, discovered))
        # Re-emit upstream evidence for cache-hit rounds.
        try:
            res = os.path.join(
                self.dependencies["qmf"].package_folder, "res", "hmbs_upstream.json")
            with open(res, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if payload.get("status") == "passed" and int(payload.get("discovered", 0)) > 0:
                self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(payload, separators=(",", ":")))
            else:
                self.output.warning("HMBS diag upstream res invalid: %s" % payload)
        except Exception as e:
            self.output.warning("HMBS diag upstream res missing: %s" % e)
        self.output.info("qmf consumer test_package passed")
