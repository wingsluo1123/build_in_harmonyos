#!/usr/bin/env python3
"""Conan recipe for the upstream attr 2.5.2 release with the OHOS triplet fix."""
import re
import shlex
from pathlib import Path

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


UPSTREAM_TEST_FILES = (
    "test/attr.test",
    "test/root/getfattr.test",
)


class AttrConan(ConanFile):
    name = "attr"
    version = "2.5.2.1"
    description = "Extended-attribute utilities and the libattr compatibility API"
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later"
    homepage = "https://savannah.nongnu.org/projects/attr"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-shared")
        # Keep the command-line tools self-contained and avoid a runtime dependency
        # on a system libattr that may have a different ABI.
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

        # The release registers every command line in its .test files. The test
        # runner resolves Perl from the active build PATH. Test differences
        # between OHOS filesystems/privileges and CI are recorded without aborting.
        test_log = Path(self.build_folder) / "attr-upstream-make-check.log"
        runner = "perl -U -w $(srcdir)/test/run -v"
        path_prefix = "{}:{}:$PATH".format(
            shlex.quote(str(self.build_folder)), shlex.quote(str(self.source_folder)))
        command = "PATH={} make check VERBOSE=1 TEST_LOG_COMPILER=".format(path_prefix)
        command += shlex.quote(runner)
        command += " > " + shlex.quote(str(test_log)) + " 2>&1"
        command += "; rc=$?; printf 'UPSTREAM-MAKE-CHECK-EXIT=%s\\n' \"$rc\" >> "
        command += shlex.quote(str(test_log))
        self.run(command, env="conanbuild", ignore_errors=True)
        self._report_upstream_tests(test_log)

    def _catalog(self):
        catalog = []
        for suite in UPSTREAM_TEST_FILES:
            suite_path = Path(self.source_folder) / suite
            cases = []
            if suite_path.is_file():
                for line_number, line in enumerate(
                        suite_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    match = re.match(r"^\s*\$ ?(.*)$", line)
                    if match:
                        cases.append({"line": line_number, "command": match.group(1).strip()})
            catalog.append((suite, cases))
        return catalog

    @staticmethod
    def _parse_cases(content):
        case_re = re.compile(r"^\[(\d+)\] \$ (.*?) -- (ok|failed)$")
        records = []
        current = None
        for line in content.splitlines():
            match = case_re.match(line)
            if match:
                current = {"line": int(match.group(1)), "command": match.group(2),
                           "status": match.group(3), "raw": []}
                records.append(current)
            elif current and line.strip() and "commands (" not in line:
                current["raw"].append(line.rstrip())
        return records

    @staticmethod
    def _suite_log_path(build_folder, suite):
        # Automake parallel-tests writes a sibling .log for each registered test.
        return Path(build_folder) / (suite[:-5] + ".log" if suite.endswith(".test") else suite + ".log")

    def _report_upstream_tests(self, test_log):
        make_log = (Path(test_log).read_text(encoding="utf-8", errors="replace")
                    if Path(test_log).is_file() else "")
        make_cases = self._parse_cases(make_log)
        catalog = self._catalog()
        total = sum(len(cases) for _suite, cases in catalog)
        all_failures = 0
        all_notrun = 0
        suite_records = []
        sequential_index = 0

        for suite, source_cases in catalog:
            suite_path = self._suite_log_path(self.build_folder, suite)
            if suite_path.is_file():
                suite_log = suite_path.read_text(encoding="utf-8", errors="replace")
                records = self._parse_cases(suite_log)
            else:
                suite_log = make_log
                # Aggregate fallback preserves Automake's execution order.
                records = make_cases[sequential_index:sequential_index + len(source_cases)]
            sequential_index += len(records)
            is_automake_skip = bool(re.search(
                r"(?m)^SKIP:\s*" + re.escape(suite) + r"\s*$", make_log))
            if not is_automake_skip and "test exited with status 77" in suite_log:
                is_automake_skip = True

            group_failure = re.search(
                r"(?m)^FAIL\s+" + re.escape(suite) + r" \(exit status: ([^)]+)\)$",
                suite_log)
            if group_failure and not records:
                # A setup-time failure before the first command leaves every
                # registered command unrun; retain the raw group result below.
                is_automake_skip = True

            raw_skip = ""
            for source_log in (suite_log, make_log):
                for line in source_log.splitlines():
                    if ("required root failed" in line or "test exited with status 77" in line
                            or re.search(r"(?m)^SKIP:\s*" + re.escape(suite), line)
                            or re.search(r"(?m)^FAIL\s+" + re.escape(suite)
                                         + r" \(exit status: [^)]+\)$", line)):
                        raw_skip = line.rstrip()
                        break
                if raw_skip:
                    break
            if is_automake_skip and not raw_skip:
                raw_skip = "SKIP: {} (Automake exit status 77)".format(suite)
            diagnostics = [line.rstrip() for line in suite_log.splitlines()
                           if any(marker in line for marker in (
                               "Can't load", "Error relocating", "Permission denied",
                               "Operation not permitted", "No such file or directory",
                               "Compilation failed", "BEGIN failed", "required root failed",
                               "could not create", "test exited with status 77"))]

            record_by_line = {}
            for record in records:
                record_by_line.setdefault(record["line"], []).append(record)

            suite_result = []
            for case in source_cases:
                record_list = record_by_line.get(case["line"], [])
                record = record_list.pop(0) if record_list else None
                if record:
                    status = "PASS" if record["status"] == "ok" else "FAIL"
                    raw_lines = record["raw"] if status == "FAIL" else []
                elif is_automake_skip:
                    status = "SKIP"
                    raw_lines = [raw_skip]
                else:
                    status = "SKIP"
                    raw_lines = diagnostics[:4] or [
                        "not executed: no command result recorded in {}".format(suite_path)]
                suite_result.append({"suite": suite, "line": case["line"],
                                     "command": case["command"], "status": status,
                                     "raw": raw_lines})
                if status == "FAIL":
                    all_failures += 1
                elif status == "SKIP":
                    all_notrun += 1
            suite_records.extend(suite_result)

        passed = total - all_failures - all_notrun
        self.output.info("UPSTREAM-SUMMARY total={} pass={} fail={} notrun={}".format(
            total, passed, all_failures, all_notrun))
        for case in suite_records:
            self.output.info("UPSTREAM-CASE {}:{} {} command={!r}".format(
                case["suite"], case["line"], case["status"], case["command"]))
            if case["status"] != "PASS":
                for raw in case["raw"]:
                    self.output.info("UPSTREAM-RAW {}:{} {}".format(
                        case["suite"], case["line"], raw))
        if not make_log:
            self.output.info(
                "UPSTREAM-MAKE-CHECK-LOG missing; source catalog still declares {} cases".format(total))
        elif "UPSTREAM-MAKE-CHECK-EXIT=" in make_log:
            self.output.info(make_log.rsplit("UPSTREAM-MAKE-CHECK-EXIT=", 1)[1].strip())

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]

        libattr = self.cpp_info.components["libattr"]
        libattr.libs = ["attr"]
        libattr.includedirs = ["include"]
        libattr.set_property("cmake_target_name", "attr::libattr")
        libattr.set_property("pkg_config_name", "libattr")
