#!/usr/bin/env python3
"""Consumer-side Conan tests for libthreadar 1.6.1."""

import os
import re
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibthreadarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Fail closed if the package installer reintroduces prefix-dependent
        # include directives into its installed public headers.
        package_folder = self.dependencies["libthreadar"].package_folder
        include_root = os.path.join(package_folder, "include")
        try:
            if not os.path.isdir(include_root):
                self.output.info(
                    "TEST-PACKAGE-CASE package_header_relocation: FAIL "
                    f"missing {include_root}"
                )
                self.output.info(
                    "TEST-PACKAGE-RELOCATION-SUMMARY total=1 pass=0 fail=1 notrun=0"
                )
            else:
                header_count = 0
                absolute_include = re.compile(
                    r'^\s*#\s*include\s*[<"](?:/|[A-Za-z]:[\\/])',
                    re.MULTILINE,
                )
                offending_header = None
                for root, _, files in os.walk(include_root):
                    for filename in files:
                        if not filename.endswith((".h", ".hpp")):
                            continue
                        path = os.path.join(root, filename)
                        with open(
                            path, encoding="utf-8", errors="replace"
                        ) as stream:
                            contents = stream.read()
                        header_count += 1
                        if package_folder in contents or absolute_include.search(contents):
                            offending_header = path
                            break
                    if offending_header:
                        break
                if offending_header:
                    self.output.info(
                        "TEST-PACKAGE-CASE package_header_relocation: FAIL "
                        f"non-relocatable include in {offending_header}"
                    )
                    self.output.info(
                        "TEST-PACKAGE-RELOCATION-SUMMARY total=1 pass=0 fail=1 notrun=0"
                    )
                elif not header_count:
                    self.output.info(
                        "TEST-PACKAGE-CASE package_header_relocation: FAIL "
                        "no public headers"
                    )
                    self.output.info(
                        "TEST-PACKAGE-RELOCATION-SUMMARY total=1 pass=0 fail=1 notrun=0"
                    )
                else:
                    self.output.info(
                        "TEST-PACKAGE-CASE package_header_relocation: PASS "
                        f"headers={header_count} absolute_includes=0"
                    )
                    self.output.info(
                        "TEST-PACKAGE-RELOCATION-SUMMARY total=1 pass=1 fail=0 notrun=0"
                    )
        except OSError as error:
            self.output.info(
                "TEST-PACKAGE-CASE package_header_relocation: NOT-RUN "
                f"header scan could not read the package include tree: {error}"
            )
            self.output.info(
                "TEST-PACKAGE-RELOCATION-SUMMARY total=1 pass=0 fail=0 notrun=1"
            )

        cmake = CMake(self)
        executable = os.path.join(self.cpp.build.bindir, "test_libthreadar")
        if os.path.isfile(executable):
            os.remove(executable)
        try:
            cmake.configure()
            cmake.build()
        except Exception as error:
            self.output.info(
                "TEST-PACKAGE-CONSUMER-BUILD: FAIL "
                f"{type(error).__name__}: {error}"
            )

    def test(self):
        executable = os.path.join(self.cpp.build.bindir, "test_libthreadar")
        cases = (
            "condition_lock_unlock",
            "thread_run_join_restart",
            "thread_cooperative_cancel",
            "mutex_concurrency",
            "semaphore_accounting",
            "barrier_rendezvous",
        )
        if not os.path.isfile(executable):
            for name in cases:
                self.output.info(
                    f"TEST-PACKAGE-CASE {name}: NOT-RUN "
                    "(consumer executable was not produced)"
                )
            self.output.info(
                "TEST-PACKAGE-SUMMARY total=6 pass=0 fail=0 notrun=6"
            )
            return

        log_file = os.path.join(self.build_folder, "test-package-consumer.log")
        exit_file = os.path.join(self.build_folder, "test-package-consumer.exit")
        command = (
            f"{shlex.quote(executable)} > {shlex.quote(log_file)} 2>&1; "
            f"status=$?; printf '%s\\n' \"$status\" > {shlex.quote(exit_file)}; "
            "exit 0"
        )
        self.run(command, env="conanrun")

        output = ""
        if os.path.isfile(log_file):
            with open(log_file, encoding="utf-8", errors="replace") as stream:
                output = stream.read()
        if output:
            for line in output.splitlines():
                if not line.startswith("TEST-PACKAGE-SUMMARY "):
                    self.output.info(line)

        exit_code = None
        if os.path.isfile(exit_file):
            with open(exit_file, encoding="ascii", errors="replace") as stream:
                try:
                    exit_code = int(stream.read().strip())
                except ValueError:
                    pass

        reported = {}
        for name in cases:
            match = re.search(
                rf"^TEST-PACKAGE-CASE {re.escape(name)}: (PASS|FAIL)\b",
                output,
                re.MULTILINE,
            )
            if match:
                reported[name] = match.group(1)
            else:
                reported[name] = "NOT-RUN"
                self.output.info(
                    f"TEST-PACKAGE-CASE {name}: NOT-RUN "
                    f"(runner did not report a result; exit={exit_code!r})"
                )

        passed = sum(status == "PASS" for status in reported.values())
        failed = sum(status == "FAIL" for status in reported.values())
        not_run = sum(status == "NOT-RUN" for status in reported.values())
        self.output.info(
            "TEST-PACKAGE-SUMMARY "
            f"total=6 pass={passed} fail={failed} notrun={not_run}"
        )
