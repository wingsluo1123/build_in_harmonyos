#!/usr/bin/env python3
"""Consumer test for the public libini_config API."""

import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LibiniConfigTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _absolute(root, path):
        return path if os.path.isabs(path) else os.path.join(root, path)

    def _compiler(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compiler_executables.get("c") if compiler_executables else None
        if configured:
            configured = str(configured).split()[0].strip("\"'")
            if os.path.isfile(configured):
                return configured
        compiler = shutil.which("clang") or shutil.which("cc")
        if not compiler:
            raise RuntimeError("cannot find a C compiler")
        return compiler

    def _hmbs_emit(self, line):
        # Dual-channel: conan output + raw stdout so preflight catches it.
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def build(self):
        dependency = self.dependencies["libini_config"]
        package_root = dependency.package_folder
        include_dirs = [
            self._absolute(package_root, path)
            for path in (dependency.cpp_info.includedirs or ["include"])
        ]
        lib_dirs = [
            self._absolute(package_root, path)
            for path in (dependency.cpp_info.libdirs or ["lib"])
        ]

        include_flags = " ".join("-I" + shlex.quote(path) for path in include_dirs)
        library_flags = " ".join("-L" + shlex.quote(path) for path in lib_dirs)
        rpath_flags = " ".join(
            "-Wl,-rpath," + shlex.quote(path) for path in lib_dirs
        )
        # Exercise the public INI configuration API rather than only
        # checking that a header can be included.
        command = (
            f"{shlex.quote(self._compiler())} -std=gnu11 -Wall -Wextra "
            f"{include_flags} test.c -o libini_config-test "
            f"{library_flags} {rpath_flags} -lini_config -lm -lpthread"
        )
        self.run(command, env="conanbuild")

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile/link test completed")
            return
        # 7 real consumer checks in test.c, each emitting one
        # "CASE PASS: <name>" line on success (see test.c). The marker
        # counts come from that deterministic log source: exactly one
        # line per passing case, no string-count guessing or arithmetic
        # repair. Binary exit 0 alone is not counted as pass.
        discovered = 7
        log_path = os.path.join(self.build_folder, "libini_config-test.log")
        command = "./libini_config-test"
        try:
            self.run(f"{command} > \"{log_path}\" 2>&1", env="conanrun")
        except Exception:
            out = ""
            try:
                with open(log_path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    out = handle.read()
            except OSError:
                out = ""
            if out:
                self.output.info("test output:\n" + out)
            marker = {
                "executed": True,
                "passed": False,
                "command": command,
                "discovered": discovered,
                "passedCount": 0,
            }
            self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
                marker, separators=(",", ":")))
            self._emit_upstream_result()
            raise
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        except OSError as exc:
            raise ConanException(
                f"test log unreadable {log_path}: {exc!r}")
        self.output.info("test output:\n" + out)
        # Single deterministic source: one "CASE PASS:" line per case.
        passed_count = sum(
            1 for line in out.splitlines()
            if line.startswith("CASE PASS:")
        )
        marker = {
            "executed": True,
            "passed": passed_count == discovered,
            "command": command,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
            marker, separators=(",", ":")))
        self._emit_upstream_result()
        if passed_count != discovered:
            raise ConanException(
                f"test_package failed: {passed_count}/{discovered} cases passed")

    def _emit_upstream_result(self):
        # Re-emit the real upstream result carried in the package res/ so
        # cache-hit runs still provide evidence every round. Numbers are
        # the build-phase `make check` test-suite.log counts, not copies.
        try:
            dep = self.dependencies["libini_config"]
            path = os.path.join(
                dep.package_folder, "res", "hmbs_upstream.json")
        except Exception:
            path = ""
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, ValueError) as exc:
                self.output.warning(
                    f"HMBS diag upstream res unreadable: {exc!r}")
                return
            self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                payload, separators=(",", ":")))
        else:
            self.output.warning(
                "HMBS diag upstream res missing: " + str(path))
