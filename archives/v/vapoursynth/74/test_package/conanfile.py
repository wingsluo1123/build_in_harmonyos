#!/usr/bin/env python3
"""Consumer test for vapoursynth 74."""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class VapoursynthTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._resolve_tool(compilers.get("c"), "clang")
        cxx = self._resolve_tool(compilers.get("cpp"), "clang++")
        dep = self.dependencies["vapoursynth"].cpp_info

        exe = os.path.join(self.build_folder, "test_vapoursynth")
        cmd = [
            *self._exec_tool(cc),
            os.path.join(self.source_folder, "test_vapoursynth.c"),
            "-o",
            exe,
        ]
        for include_dir in dep.includedirs:
            cmd.append("-I" + include_dir)
        for lib_dir in dep.libdirs:
            cmd.append("-L" + lib_dir)
        for lib in dep.libs:
            cmd.append("-l" + lib)
        for system_lib in dep.system_libs:
            cmd.append("-pthread" if system_lib == "pthread" else "-l" + system_lib)

        self.run(" ".join(shlex.quote(part) for part in cmd))
        self._build_expr_debugger(cxx)

    def test(self):
        if can_run(self):
            exe = os.path.join(self.build_folder, "test_vapoursynth")
            self.run(shlex.quote(exe), env="conanrun")
            self._run_upstream_python_tests()

    def _run_upstream_python_tests(self):
        dep = self.dependencies["vapoursynth"]
        package_folder = dep.package_folder
        pythonpath = os.path.join(package_folder, "python")
        tests_dir = os.path.join(package_folder, "tests", "upstream")
        libdir = os.path.join(package_folder, "lib")
        module_libdir = os.path.join(pythonpath, "vapoursynth")
        self._ensure_runtime_shared_library_permissions(package_folder)
        test_modules = [
            "async_test",
            "environment_test",
            "expr_test",
            "filter_test",
            "log_test",
            "lut_test",
            "prop_dict_test",
            "range_property_compat",
            "test",
            "weakref_test",
            "zimgtest",
        ]
        env = (
            "PYTHONPATH={tests_dir}:{pythonpath} "
            "LD_LIBRARY_PATH={module_libdir}:{libdir}:$LD_LIBRARY_PATH "
        ).format(
            tests_dir=shlex.quote(tests_dir),
            pythonpath=shlex.quote(pythonpath),
            module_libdir=shlex.quote(module_libdir),
            libdir=shlex.quote(libdir),
        )
        cmd = "{} python3 -m unittest {}".format(env, " ".join(test_modules))
        self.run(cmd, env="conanrun")
        self._run_expr_compiler_harness(tests_dir)

    def _ensure_runtime_shared_library_permissions(self, package_folder):
        if self.settings.os != "OHOS":
            return
        for shared_lib in glob.glob(os.path.join(package_folder, "**", "*.so*"), recursive=True):
            if not os.path.islink(shared_lib):
                os.chmod(shared_lib, 0o755)
                self.run("chmod 755 {}".format(shlex.quote(shared_lib)), quiet=True)

    def _build_expr_debugger(self, cxx):
        dep = self.dependencies["vapoursynth"]
        dep_cpp_info = dep.cpp_info
        expr_src = os.path.join(dep.package_folder, "tests", "exprdebugger", "src", "core", "expr")
        exe = os.path.join(self.build_folder, "ExprDebugger.exe")
        cmd = [
            *self._exec_tool(cxx),
            "-std=c++17",
            os.path.join(expr_src, "expr.cpp"),
            os.path.join(expr_src, "main.cpp"),
            "-o",
            exe,
        ]
        for include_dir in dep_cpp_info.includedirs:
            cmd.append("-I" + include_dir)
        self.run(" ".join(shlex.quote(part) for part in cmd))

    def _run_expr_compiler_harness(self, tests_dir):
        expr_debugger = os.path.join(self.build_folder, "ExprDebugger.exe")
        runner = os.path.join(self.source_folder, "run_expr_compiler_test.py")
        cmd = "python3 {} {} {}".format(
            shlex.quote(runner),
            shlex.quote(os.path.join(tests_dir, "expr_compiler", "compiler_test.py")),
            shlex.quote(expr_debugger),
        )
        self.run(cmd, env="conanrun")

    def _resolve_tool(self, configured, fallback):
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if configured:
            bindir = os.path.dirname(configured) if os.path.isabs(configured) else ""
            candidate = os.path.join(bindir, fallback) if bindir else ""
            if candidate and os.path.exists(candidate):
                return candidate
        home_candidate = os.path.join(os.path.expanduser("~"), "usr", "local", "bin", fallback)
        if os.path.exists(home_candidate):
            return home_candidate
        return fallback

    def _exec_tool(self, tool):
        if self._is_script(tool):
            return ["sh", tool]
        return [tool]

    @staticmethod
    def _is_script(path):
        if not path or not os.path.isfile(path):
            return False
        try:
            with open(path, "rb") as handle:
                return handle.read(2) == b"#!"
        except OSError:
            return False
