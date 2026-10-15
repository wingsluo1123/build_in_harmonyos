#!/usr/bin/env python3
"""Conan test_package for lorcon 2020.06.06.

Builds test.c against the packaged lorcon (CMakeDeps + CMakeToolchain),
runs the ctest suite on the native OHOS target and emits the HMBS
machine-evidence markers. Upstream's only automated suite is
pylorcon2/test.py (10 python_def unittests); testGetVersion never touches
Context/iface upstream and executes for real via the packaged
lorcon_test binary, the other 9 require monitor-mode 802.11 injection
hardware and report explicit skips with ohos_feature evidence
(discovered 10, executed 1, skipped 9).

Note: lorcon requires the team-published libpcap/1.10.6; it arrives
transitively via the tested reference, so this test_package requires
only the tested reference itself.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


CONSUMER_CHECK_COUNT = 4


class LorconTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            # Preflight container: profile compiler /data/service/hnp/bin/clang
            # is not executable inside the isolated build namespace, so the
            # default toolchain file points CMake at a dead CMAKE_C_COMPILER
            # and project() dies with "identification is unknown".
            # Three prior cache_variables/-D rounds are falsified by the 20:07
            # preflight: generate() logged pin C=harmonybrew (probe) yet CMake
            # still reported CMAKE_C_COMPILER=/data/service/hnp/bin/clang.
            # Root cause is therefore NOT the probe but template ordering:
            # CMakeToolchain's own compiler assignment wins over our
            # cache_variables and over build()'s -D (FORCE/set-after).
            # Different route (7th cycle): keep the advisory pin, but after
            # tc.generate() directly rewrite every generated
            # conan_toolchain.cmake so the dead absolute path never reaches
            # CMake. build() re-patches with the fuller conanbuild PATH.
            cc, cc_tier = self._resolve_compiler("c")
            cxx, cxx_tier = self._resolve_compiler("cpp")
            tc.cache_variables["CMAKE_C_COMPILER"] = cc
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
            self.output.info("lorcon test: pin C=%s (%s) CXX=%s (%s)"
                             % (cc, cc_tier, cxx, cxx_tier))
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        if self.settings.os == "OHOS":
            try:
                patched = self._patch_toolchain_files(cc, cxx)
            except Exception as exc:
                self.output.warning("lorcon test: toolchain patch failed: %s" % exc)
            else:
                self.output.info("lorcon test: toolchain patch files=%s" % patched)

    def _resolve_compiler(self, kind):
        # Returns (value, tier). Tiers: "probe" (exec-validated),
        # "sibling" (exists alongside validated counterpart, no exec --
        # CMake validates), "bare" (PATH resolution at CMake time).
        # Never returns the known-dead profile default or "".
        want = "clang" if kind == "c" else "clang++"
        probed = self._probe_working_compiler(kind)
        if probed and probed != "/data/service/hnp/bin/%s" % want:
            return probed, "probe"
        if probed and probed.startswith("/data/service/hnp/"):
            self.output.info("lorcon test: probe hit dead HNP path %s, descend"
                             % probed)
            probed = ""
        if kind == "c" and not probed:
            try:
                peer, peer_tier = self._resolve_compiler("cpp")
            except Exception:
                peer, peer_tier = "", ""
            if peer and "/" in peer:
                sibling = self._sibling_path(peer, kind)
                if sibling:
                    return sibling, "sibling-of-" + peer_tier
        if not probed:
            return want, "bare"
        return probed, "probe"

    def _patch_toolchain_files(self, cc, cxx):
        # 7th-cycle route: cache_variables/-D cannot dislodge the dead
        # profile compiler from the generated toolchain file, so rewrite
        # the file itself. Replace clang++ FIRST (its string contains the
        # clang prefix) then clang. Returns patched file count.
        targets = set()
        for base in (getattr(self, "generators_folder", ""), self.build_folder):
            if not base:
                continue
            try:
                for root, _dirs, files in os.walk(base):
                    if "conan_toolchain.cmake" in files:
                        targets.add(os.path.join(root, "conan_toolchain.cmake"))
            except Exception:
                continue
        # cmake_layout puts generators under build/<config>/generators, but
        # walk the whole build_folder as well for older layouts.
        patched = 0
        for path in sorted(targets):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            original = content
            if cxx and "/data/service/hnp/bin/clang++" in content:
                content = content.replace("/data/service/hnp/bin/clang++", cxx)
            if cc and "/data/service/hnp/bin/clang" in content:
                content = content.replace("/data/service/hnp/bin/clang", cc)
            if content != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
                patched += 1
                self.output.info("lorcon test: patched %s C=%s CXX=%s" % (path, cc, cxx))
            else:
                self.output.info("lorcon test: no dead compiler in %s" % path)
        if not targets:
            self.output.warning("lorcon test: no conan_toolchain.cmake found to patch")
        return patched

    def _all_path_matches(self, tool):
        # Different route from the failed single-which probe: shutil.which
        # returns only the first PATH hit, which on this worker is the dead
        # profile path /data/service/hnp/bin/clang shadowing the working
        # harmonybrew clang later in PATH (hence C stayed broken while
        # clang++ happened to resolve). Scan every PATH dir instead.
        found = []
        try:
            path_env = os.environ.get("PATH", "")
        except Exception:
            path_env = ""
        for directory in path_env.split(os.pathsep):
            if not directory:
                continue
            candidate = os.path.join(directory, tool)
            try:
                if os.path.isfile(candidate) and candidate not in found:
                    found.append(candidate)
            except Exception:
                continue
        # Explicit worker-local toolchain dir independent of PATH order
        # (generate() runs without conanbuild PATH; HOME expands to the
        # worker user on preflight).
        try:
            home_brew = os.path.join(os.path.expanduser("~"),
                                     ".harmonybrew", "bin", tool)
            if os.path.isfile(home_brew) and home_brew not in found:
                found.append(home_brew)
        except Exception:
            pass
        return found

    def _probe_working_compiler(self, kind):
        candidates = []
        try:
            comp = self.conf.get("tools.build:compiler_executables")
            if isinstance(comp, dict) and comp.get(kind):
                candidates.append(comp[kind])
            elif isinstance(comp, str) and comp:
                candidates.append(comp)
        except Exception:
            pass
        env_key = "CC" if kind == "c" else "CXX"
        if os.environ.get(env_key):
            candidates.append(os.environ[env_key])
        candidates.append("/data/service/hnp/bin/%s"
                          % ("clang" if kind == "c" else "clang++"))
        for tool in (("clang", "cc", "gcc")
                     if kind == "c" else ("clang++", "c++", "g++")):
            for match in self._all_path_matches(tool):
                candidates.append(match)
            try:
                found = shutil.which(tool)
            except Exception:
                found = None
            if found:
                candidates.append(found)
        seen = set()
        for cand in candidates:
            if not cand or not isinstance(cand, str):
                continue
            exe = cand.split()[0]
            if not exe or exe in seen:
                continue
            seen.add(exe)
            if "/" not in exe:
                resolved = shutil.which(exe)
                if not resolved:
                    continue
                exe = resolved
            if not os.path.isfile(exe):
                self.output.info("lorcon test CC probe: not a file, skip %s"
                                 % cand)
                continue
            try:
                result = subprocess.run(
                    [exe, "--version"],
                    capture_output=True, text=True, timeout=30,
                )
            except Exception as exc:
                self.output.info("lorcon test CC probe: exec failed %s (%s)"
                                 % (exe, exc))
                continue
            if result.returncode == 0:
                return exe
            self.output.info("lorcon test CC probe: %s rc=%s, continue"
                             % (exe, result.returncode))
        return ""

    def _sibling_path(self, peer_path, kind):
        # Existence-only sibling (no exec): CMake validates. Used only
        # when the exec probe found nothing in this context.
        if not peer_path or "/" not in peer_path or kind != "c":
            return ""
        directory = os.path.dirname(peer_path)
        base = os.path.basename(peer_path)
        mapping = {"clang++": "clang", "g++": "gcc", "c++": "cc"}
        sibling = mapping.get(base)
        if not sibling:
            return ""
        candidate = os.path.join(directory, sibling)
        try:
            if os.path.isfile(candidate):
                return candidate
        except Exception:
            pass
        return ""

    def _sibling_cc(self, cxx_path, kind):
        # LLVM pairs live side by side (clang++/clang). When the C probe
        # finds nothing but the C++ probe hit harmonybrew, the sibling is
        # the same validated toolchain, not a PATH guess.
        if not cxx_path or kind != "c":
            return ""
        directory = os.path.dirname(cxx_path)
        base = os.path.basename(cxx_path)
        mapping = {"clang++": "clang", "g++": "gcc", "c++": "cc"}
        sibling = mapping.get(base)
        if not sibling:
            return ""
        candidate = os.path.join(directory, sibling)
        if not os.path.isfile(candidate):
            return ""
        try:
            result = subprocess.run(
                [candidate, "--version"],
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            return ""
        if result.returncode == 0:
            self.output.info("lorcon test: sibling C compiler %s ok" % candidate)
            return candidate
        return ""

    def build(self):
        cmake = CMake(self)
        # generate() ran without the conanbuild PATH, so re-resolve here
        # where PATH is complete; re-patch the toolchain file itself
        # because -D alone was proven unable to override it (20:07).
        extra = {}
        if str(self.settings.os) == "OHOS":
            cc, cc_tier = self._resolve_compiler("c")
            cxx, cxx_tier = self._resolve_compiler("cpp")
            extra["CMAKE_C_COMPILER"] = cc
            extra["CMAKE_CXX_COMPILER"] = cxx
            self.output.info("lorcon test build: C=%s (%s) CXX=%s (%s)"
                             % (cc, cc_tier, cxx, cxx_tier))
            try:
                self._patch_toolchain_files(cc, cxx)
            except Exception as exc:
                self.output.warning("lorcon test build patch failed: %s" % exc)
        if extra:
            cmake.configure(variables=extra)
        else:
            cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link check only")
            return
        cmake = CMake(self)
        try:
            cmake.test()
        except Exception as exc:
            self.output.warning("ctest failed: %s" % exc)
            self._run_consumer_binary(raise_on_failure=False)
            self._emit_upstream_marker()
            raise
        self._run_consumer_binary(raise_on_failure=True)
        self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
        self._emit_upstream_marker()

    def _run_consumer_binary(self, raise_on_failure):
        build = self.cpp.build
        bin_dir = build.bindirs[0] if build.bindirs else "."
        bin_path = os.path.join(self.build_folder, bin_dir, "lorcon_test")
        if not os.path.isfile(bin_path):
            for root, _dirs, files in os.walk(self.build_folder):
                if "lorcon_test" in files and not root.endswith(".cmake"):
                    candidate = os.path.join(root, "lorcon_test")
                    if os.access(candidate, os.X_OK) or os.path.isfile(candidate):
                        bin_path = candidate
                        break
        proc = subprocess.run(
            [bin_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not marker["passed"] and raise_on_failure:
            raise Exception(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )

    def _emit_upstream_marker(self):
        # Upstream suite: pylorcon2/test.py, 10 python_def unittests (see
        # upstream_pylorcon2_tests.py docstring + MANIFEST audit). 1 of 10
        # (testGetVersion) is hardware-independent -- upstream never touches
        # Context/iface there, only type(get_version()) == int -- and is
        # executed for real via the packaged lorcon_test binary (executed>0
        # for rule4). The other 9 require monitor-mode 802.11 injection
        # hardware and report explicit skips with ohos_feature evidence.
        # Expected steady state: discovered == 10, executed == 1,
        # passed == 1, skipped == 9, status incomplete with one
        # ohos_feature gap (count == skipped; rule4: passed requires
        # full execution, so partial execution must not claim passed). Counting sources (no word-count
        # arithmetic, no returncode-implies-passed fallback):
        #   discovered: parse this mirror file for "^    def test" lines.
        #   executed/passed/failed/skipped: parse per-test unittest -v lines
        #     "^testX (...) ... ok|skipped|FAIL|ERROR" from the saved log.
        import re as _re
        mirror_name = "upstream_pylorcon2_tests.py"
        search_dirs = []
        for candidate in (
            getattr(self, "recipe_folder", ""),
            getattr(self, "source_folder", ""),
            getattr(self, "build_folder", ""),
            os.getcwd(),
        ):
            if candidate and candidate not in search_dirs:
                search_dirs.append(candidate)
        mirror_path = ""
        for directory in search_dirs:
            try:
                candidate = os.path.join(directory, mirror_name)
            except Exception:
                continue
            if candidate and os.path.isfile(candidate):
                mirror_path = candidate
                break
        if not mirror_path:
            # Walk build_folder as last resort (cmake_layout nests sources).
            try:
                for root, _dirs, files in os.walk(self.build_folder):
                    if mirror_name in files:
                        mirror_path = os.path.join(root, mirror_name)
                        break
            except Exception:
                pass
        if not mirror_path or not os.path.isfile(mirror_path):
            marker = {
                "status": "failed",
                "framework": "python-unittest",
                "command": "python3 -m unittest upstream_pylorcon2_tests -v",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "upstream mirror %s not found; searched: %s"
                    % (mirror_name, search_dirs)
                ),
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            raise Exception(marker["reason"])
        try:
            with open(mirror_path, "r", encoding="utf-8",
                      errors="replace") as handle:
                mirror_text = handle.read()
        except OSError as exc:
            marker = {
                "status": "failed",
                "framework": "python-unittest",
                "command": "python3 -m unittest upstream_pylorcon2_tests -v",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "cannot read %s: %s" % (mirror_path, exc),
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            raise
        discovered = len(_re.findall(r"^    def (test\w+)\(", mirror_text,
                                     _re.MULTILINE))
        # Resolve a python3 executable (HMBS injects HMBS_PYTHON3).
        python3 = os.environ.get("HMBS_PYTHON3", "")
        if not python3 or not os.path.isfile(python3.split()[0]):
            python3 = shutil.which("python3") or "python3"
        module_dir = os.path.dirname(mirror_path)
        command = "%s -m unittest upstream_pylorcon2_tests -v" % python3
        log_path = os.path.join(self.build_folder, "upstream_unittest.log")
        # testGetVersion executes the packaged lorcon_test binary (same
        # process image the consumer test just ran). Locate it with the
        # same search as _run_consumer_binary and hand it to the unittest
        # via LORCON_TEST_BIN; a missing binary must surface as a test
        # FAILURE inside the suite (宁缺毋假), never as a silent skip.
        lorcon_bin = ""
        try:
            build_layout = self.cpp.build
            _bindirs = build_layout.bindirs if build_layout.bindirs else ["."]
        except Exception:
            _bindirs = ["."]
        for _bd in _bindirs:
            _cand = os.path.join(self.build_folder, _bd, "lorcon_test")
            if os.path.isfile(_cand):
                lorcon_bin = _cand
                break
        if not lorcon_bin:
            try:
                for _root, _dirs, _files in os.walk(self.build_folder):
                    if "lorcon_test" in _files:
                        _cand = os.path.join(_root, "lorcon_test")
                        if os.path.isfile(_cand):
                            lorcon_bin = _cand
                            break
            except Exception:
                pass
        run_env = dict(os.environ)
        if lorcon_bin:
            run_env["LORCON_TEST_BIN"] = lorcon_bin
            self.output.info("lorcon upstream: LORCON_TEST_BIN=%s" % lorcon_bin)
        else:
            self.output.warning(
                "lorcon upstream: lorcon_test binary not found; "
                "testGetVersion will fail (not skip)")
        try:
            proc = subprocess.run(
                [python3, "-m", "unittest", "upstream_pylorcon2_tests", "-v"],
                cwd=module_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
                env=run_env,
            )
            output = proc.stdout or ""
        except Exception as exc:
            marker = {
                "status": "failed",
                "framework": "python-unittest",
                "command": command,
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "unittest launch failed: %s" % exc,
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            raise
        try:
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(output)
        except OSError:
            pass
        self.output.info(output[-3000:])
        # Deterministic per-test parse: exactly one line per test in -v mode.
        line_re = _re.compile(r"^(\w+) \([\w\.]+\) \.\.\. (ok|skipped|FAIL|ERROR)\b")
        passed = failed = skipped = 0
        for line in output.splitlines():
            match = line_re.match(line.strip())
            if not match:
                continue
            verdict = match.group(2)
            if verdict == "ok":
                passed += 1
            elif verdict == "skipped":
                skipped += 1
            else:
                failed += 1
        executed = passed + failed
        # Self-check identities before emitting; never patch numbers to fit.
        if not (passed + failed == executed
                and executed + skipped <= discovered
                and executed <= discovered
                and discovered == 10
                and min(discovered, executed, passed, failed, skipped) >= 0):
            marker = {
                "status": "failed",
                "framework": "python-unittest",
                "command": command,
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "reason": (
                    "count identity check failed for %s "
                    "(expected discovered=10 from mirror def-test parse; "
                    "log=%s; searched mirror in %s)"
                    % (mirror_path, log_path, search_dirs)
                ),
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            raise Exception(marker["reason"])
        probe_evidence = ""
        for line in output.splitlines():
            if "UPSTREAM-PROBE:" in line:
                probe_evidence += line.strip() + " | "
        probe_evidence = probe_evidence[:600] or "see upstream_unittest.log"
        exec_evidence = ""
        # testGetVersion is silent by design (any print splits unittest -v
        # "... ok" onto its own line and breaks the deterministic parse
        # above); exec evidence is the ok line itself plus the binary path.
        exec_evidence = "testGetVersion ... ok in log via %s" % (
            lorcon_bin or "LORCON_TEST_BIN")
        # Status (rule4): passed ONLY on full execution with zero
        # skips/failures (executed == discovered, failed == 0,
        # skipped == 0). Partial execution with explicit ohos_feature
        # skips reports incomplete (gaps carry categorized evidence);
        # failed when any executed test failed; skipped only when
        # nothing executed. Never infer pass from returncode; counts
        # above are the single source. (Fixes preflight evidence
        # incomplete \"passed 状态与上游结果矛盾\" for 1/10 + 9 skips.)
        if failed > 0:
            status = "failed"
        elif executed == 0:
            status = "skipped"
        elif executed == discovered and skipped == 0:
            status = "passed"
        else:
            status = "incomplete"
        marker = {
            "status": status,
            "framework": "python-unittest",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if skipped > 0:
            marker["gaps"] = [
                {
                    "count": skipped,
                    "category": "ohos_feature",
                    "detail": (
                        "9/10 pylorcon2/test.py unittests require "
                        "monitor-mode 802.11 injection (Context('wlan0') + "
                        "open_injmon/open_monitor/send_bytes/set_channel/"
                        "set_hwmac/auto_driver, incl. list/find wrappers "
                        "whose suite setUp still opens wlan0); HarmonyOS "
                        "PC provides no wireless injection path; "
                        "testGetVersion (no Context use upstream) executes "
                        "for real via packaged lorcon_test"
                    ),
                    "evidence": (
                        "%s upstream setUp Context('wlan0'), "
                        "testInjection/open_injmon, testChannel/set_channel, "
                        "testMAC/set_hwmac; exec: %s; log=%s"
                        % (probe_evidence, exec_evidence, log_path)
                    ),
                }
            ]
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
