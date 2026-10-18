#!/usr/bin/env python3
"""test_package for refnx 0.1.62 on HarmonyOS PC (OHOS aarch64).

Two real consumers run here, both through the conanrun environment that the
recipe's package_info() builds (PYTHONPATH -> packaged site-packages,
LD_LIBRARY_PATH -> libpython3.12 + the OHOS SDK libc++_shared directory):

  test_refnx.py         17 checks against the public API. The numerical core is
                        pinned from four independent directions: `_creflect`
                        (C refcalc.c), `_cyreflect` (Cython + OpenMP) and
                        `_reflect` (pure-Python) must agree with each other and
                        with the Motofit-generated reflectivity the sdist ships,
                        through all six selectable backends; plus abeles_vectorised
                        batching, the polarised gepore kernel, OpenMP thread
                        invariance, the Spline microslabber, Objectives/CurveFitter
                        (minimiser + emcee MCMC), the Dot/ORSO dataset loaders and
                        pickle persistence.
  test_ohos_platform.py OHOS-specific checks. 6 of them are *static* ELF
                        verification of all 4 extensions (EM_AARCH64,
                        .codesign required by E077, DT_NEEDED libpython3.12
                        required by E004, musl libc.so with the meson-declared
                        libc++_shared/libomp tail, ABI tag == interpreter
                        EXT_SUFFIX, and the installed tree + meson-generated
                        refnx/version.py), 3 more are runtime checks that need
                        no more than numpy (platform identity, dlopen from the
                        package dir + mmap on the OHOS filesystem, musl
                        allocator/ABI behaviour).

Channel handling (counts are never fabricated):
  live     - `import refnx.reflect` works -> 17 + 9 = 26 checks executed.
  E212     - CI AppSpawn sandbox refuses dlopen of user-path .so (Permission
             denied, hmmac path label) -> static group only: 6 checks.
  deps     - the runtime dependencies of the platform Python (scipy, pandas,
             orsopy; OHOS wheels on the platform pip index, deliberately not
             Conan requirements) are absent -> static group only: 6 checks.
The interpreter is taken from `tool_requires('python/3.12.9')` (the registry's
OHOS CPython) and only then from REFNX_PYTHON / OHOS_PYTHON / HMBS_PYTHON3:
workers expose /data/service/hnp/bin/python3 on PATH, whose EXT_SUFFIX is
`.cpython-312.so`, i.e. not the ABI these extensions are tagged for.
The upstream pytest suite cannot run inside build() for the same reason, so it
was executed out-of-band on a real device; the counts are declared in
test_package/MANIFEST.yml, reports/test-report.md and manifest.yaml
`upstream_test_run`.
"""

import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.layout import basic_layout

_LIVE_CONSUMER = 17
_LIVE_OHOS = 9
_STATIC_OHOS = 6

# The platform-Python runtime dependencies refnx imports from its public
# modules. They are not in the OHPCD Conan registry, so a worker without the
# platform pip index falls back to the static artifact channel.
_RUNTIME_DEPS = ("scipy", "pandas", "orsopy")


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_refnx.py", "test_ohos_platform.py"

    def layout(self):
        """Route conan's generated env files (conanrun.sh …) and the scripts'
        --json evidence into build/ (gitignored) instead of the recipe tree."""
        basic_layout(self, build_folder="build")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # The target CPython itself, so the static channel never depends on an
        # env var or on what happens to be on the worker's PATH.
        self.tool_requires("python/3.12.9")

    # ── helpers ─────────────────────────────────────────────────────────────
    def _conrun_shell(self):
        """conanrun.sh carries the recipe's runenv (PYTHONPATH + LD_LIBRARY_PATH).
        Real devices have no bash, so fall back to /bin/sh."""
        env_sh = os.path.join(self.generators_folder, "conanrun.sh")
        return (shutil.which("bash") or "/bin/sh"), (env_sh
                                                     if os.path.isfile(env_sh)
                                                     else "")

    def _interp_run(self, py, code, ld=""):
        """Run `python -c code` inside the recipe's conanrun env, so LD_LIBRARY_PATH
        already points at libpython3.12 + the SDK libc++_shared directory."""
        shell, env_sh = self._conrun_shell()
        pre = ('LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH" ' % ld) if ld else ""
        if env_sh:
            cmd = [shell, "-c", '. "%s" && %s"%s" -c "%s"'
                           % (env_sh, pre, py, code)]
        else:
            cmd = [shell, "-c", '%s"%s" -c "%s"' % (pre, py, code)]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    def _ext_suffix(self, py, ld=""):
        r = self._interp_run(py, "import sysconfig;"
                                 "print(sysconfig.get_config_var('EXT_SUFFIX'))",
                             ld=ld)
        return ((r.stdout or "").strip()
                or "unreadable: " + (r.stderr or "")[-160:])

    def _dep_folder(self, name, build=False):
        """package_folder of a direct requirement (same helper as the recipe:
        tool_requires live in the *build* context)."""
        groups = ([self.dependencies.build, self.dependencies] if build
                  else [self.dependencies, self.dependencies.build])
        for grp in groups:
            try:
                return str(grp[name].package_folder)
            except Exception:
                continue
        return ""

    def _python(self):
        """Resolve the interpreter the checks run under — it must be this
        platform's CPython build.

        ohos_abi_tag compares every extension's filename tag against the
        *running* interpreter's EXT_SUFFIX, so a PATH-discovered python (this
        device's /data/service/hnp/bin/python3 reports '.cpython-312.so') would
        flag all 4 correctly tagged extensions as broken — a harness mistake
        dressed up as a package defect.  A bare PATH lookup is therefore not a
        candidate, and a candidate that is not the target interpreter is skipped
        with its EXT_SUFFIX recorded, so the error message says what was tried.

        Order: explicit REFNX_PYTHON / OHOS_PYTHON / HMBS_PYTHON3 (a developer
        pointing at a Python that also has the scipy/pandas/orsopy wheels, i.e.
        the channel where the live API checks run), then the tool_requires
        CPython from the registry — which is what a CI worker without any of
        those variables falls back to.
        """
        cands = [(os.environ.get(n), "")
                 for n in ("REFNX_PYTHON", "OHOS_PYTHON", "HMBS_PYTHON3")]
        cands.append((os.path.expanduser("~/usr/local/bin/python3"), ""))
        cands.append(("/storage/Users/currentUser/usr/local/bin/python3", ""))
        pkg = self._dep_folder("python", build=True)
        if pkg:
            # A relocated CPython is not runnable without its own lib dir on the
            # loader path (libpython3.12.so.1.0), so carry it alongside the path.
            libdir = os.path.join(pkg, "lib")
            for name in ("python3", "python3.12"):
                cand = os.path.join(pkg, "bin", name)
                if os.path.isfile(cand):
                    cands.append((cand, libdir))
        tried = []
        for c, ld in cands:
            if not (c and os.path.isfile(c)):
                continue
            suffix = self._ext_suffix(c, ld=ld)
            if "-linux-ohos" in suffix:
                return c, ld
            tried.append("%s (EXT_SUFFIX=%s)" % (c, suffix))
        raise ConanInvalidConfiguration(
            "no OHOS target python3 for the test_package%s; tool_requires "
            "'python/3.12.9' normally supplies it — otherwise set REFNX_PYTHON "
            "to the python3.12 whose EXT_SUFFIX ends in "
            "-aarch64-linux-ohos.so"
            % ("" if not tried else " — rejected: " + "; ".join(tried)))

    def _script(self, name):
        for base in (self.source_folder, self.recipe_folder,
                     self.export_sources_folder):
            cand = os.path.join(str(base), name)
            if os.path.isfile(cand):
                return cand
        raise ConanException("test script %s not found" % name)

    def _site_dir(self):
        pkg = str(self.dependencies["refnx"].package_folder)
        hits = sorted(glob.glob(os.path.join(pkg, "lib", "python*",
                                            "site-packages")))
        if not hits:
            raise ConanException("packaged site-packages dir missing under %s"
                                 % pkg)
        return hits[0]

    def _probe(self, py, ld=""):
        """Classify the worker: can the full public API be imported here?

        The modules below are exactly the ones test_refnx.py touches, so a
        worker that passes the probe can run every live check (refnx.reduce
        pulls in pandas, refnx.dataset pulls in orsopy, refnx.reflect/analysis
        pull in scipy).
        """
        code = ("import refnx, refnx._lib._cutil; print(refnx.__version__); "
                "import refnx.reflect, refnx.reduce, refnx.analysis, "
                "refnx.dataset; print('FULL')")
        r = self._interp_run(py, code, ld=ld)
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")

    def _run_script(self, py, script, argv, json_path, ld=""):
        """Execute a test script inside the conanrun environment and return the
        counts it wrote. self.run() propagates a non-zero exit as a Conan error,
        so a broken package can never report success."""
        out = os.path.join(self.build_folder, json_path)
        if os.path.exists(out):
            os.remove(out)
        pre = ('LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH" ' % ld) if ld else ""
        self.run('%s"%s" "%s" %s --json "%s"' % (pre, py, script, argv, out),
                 env="conanrun")
        with open(out, encoding="utf-8") as fh:
            return json.load(fh)

    # ── test ────────────────────────────────────────────────────────────────
    def test(self):
        py, pyld = self._python()
        site_dir = self._site_dir()
        n_so = len(glob.glob(os.path.join(site_dir, "refnx", "**", "*.so"),
                             recursive=True))
        self.output.info("refnx test_package: python=%s site=%s extensions=%d"
                         % (py, site_dir, n_so))

        ok, probe_out = self._probe(py, ld=pyld)
        results = []
        if ok:
            channel, reason = "live", "the public refnx API imports under conanrun"
            results.append(self._run_script(
                py, self._script("test_ohos_platform.py"),
                '--site-dir "%s" --runtime' % site_dir, "ohos_platform.json",
                ld=pyld))
            results.append(self._run_script(
                py, self._script("test_refnx.py"), "", "consumer.json",
                ld=pyld))
            expected = _LIVE_OHOS + _LIVE_CONSUMER
        elif "Permission denied" in probe_out:
            channel = "static-artifact-verification"
            reason = ("OHOS hmmac E212: the sandbox refuses dlopen of user-path "
                      "extension .so (Permission denied), so live API calls are "
                      "impossible here; the OHOS ELF/loading contract is "
                      "verified statically instead")
            self.output.warning("refnx: %s" % reason)
            results.append(self._run_script(
                py, self._script("test_ohos_platform.py"),
                '--site-dir "%s"' % site_dir, "ohos_platform.json", ld=pyld))
            expected = _STATIC_OHOS
        elif "No module named" in probe_out:
            missing = [m for m in _RUNTIME_DEPS
                       if "No module named '%s'" % m in probe_out]
            channel = "static-artifact-verification"
            reason = ("runtime dependency %s is not installable in this worker "
                      "(not published in the OHPCD Conan registry; OHOS wheels "
                      "are on the platform pip index) -> live API calls skipped"
                      % (missing or ["unknown"]))
            self.output.warning("refnx: %s" % reason)
            results.append(self._run_script(
                py, self._script("test_ohos_platform.py"),
                '--site-dir "%s"' % site_dir, "ohos_platform.json", ld=pyld))
            expected = _STATIC_OHOS
        else:
            raise ConanException("refnx: importing the package failed for an "
                                 "unexpected reason: %s" % probe_out[-800:])

        discovered = sum(r["discovered"] for r in results)
        passed = sum(r["passed"] for r in results)
        failed = sum(r["failed"] for r in results)
        if discovered != expected:
            raise ConanException("refnx: expected %d checks in channel %s, ran "
                                 "%d" % (expected, channel, discovered))
        test_pkg = {
            "executed": True,
            "passed": failed == 0,
            "channel": channel,
            "command": " ".join(os.path.basename(r["suite"]) for r in results),
            "discovered": discovered,
            "passedCount": passed,
            "failedCount": failed,
            "extensionsVerified": n_so,
            "reason": reason,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(test_pkg, ensure_ascii=False))
        if failed:
            raise ConanException("refnx: %d/%d test_package checks failed (%s)"
                                 % (failed, discovered, channel))
