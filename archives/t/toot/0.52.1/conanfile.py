#!/usr/bin/env python3
"""Conan recipe for toot 0.52.1 — Mastodon CLI client (pure Python, setuptools).

HarmonyOS PC (aarch64) adaptation notes
---------------------------------------
toot is a pure-Python application: there is no cross-compilation step and no
C/C++ toolchain involvement. Everything that matters happens at packaging time.

1. **Version pin (`SETUPTOOLS_SCM_PRETEND_VERSION`).** toot's version is
   *dynamic* — ``pyproject.toml`` declares ``setuptools_scm>=8`` with no
   fallback version. setuptools_scm derives the version from git metadata, and
   a plain install from the PyPI sdist (which ships without ``.git``) produces
   ``toot-0.0.0.dist-info`` and ``toot.__version__ == "0.0.0"`` — measured, not
   assumed. Exporting ``SETUPTOOLS_SCM_PRETEND_VERSION=0.52.1`` for the build
   fixes it: ``toot-0.52.1.dist-info`` and ``toot v0.52.1`` from the CLI.

2. **Dependencies.** Five of toot's runtime requirements already have recipes on
   the ohpcd registry and are declared in ``requirements()``. The remaining
   three (urwid, tomlkit, pysocks) have **no published recipe**, and a recipe PR
   must not bundle unrelated packages (W2/PF1), so they are pip-installed into
   the package at build time — the same approach used by ``acstore``,
   ``adb-enhanced`` and ``alot``. They are pinned to versions that resolve
   against the registry's ``wcwidth/0.2.12``: ``urwid==3.0.2`` and not 3.0.5,
   because 3.0.5 requires ``wcwidth>=0.4`` and fails
   ``tests/tui/test_rich_text.py::test_url_to_widget`` against 0.2.12
   (3.0.2 + 0.2.12 passes the whole suite — measured).

3. **`settings.os` (R32).** the HarmonyOS PC runtime reports
   ``sys.platform == "linux"`` on a HongMeng kernel, so an OS branch would have
   to accept both. This recipe needs no OS branch at all: pip installs the same
   pure-Python payload everywhere.

4. **No shared-prefix writes (R49).** the build installs into
   ``<build_folder>/stage`` and ``package()`` copies from there; nothing is
   written to ``/usr/local`` or any other shared location.

Upstream test suite
-------------------
``build()`` runs the *entire* upstream suite shipped in the sdist (``tests/``,
with ``tests/tui/`` and ``tests/integration/``) against the source tree, with
the conan-provided and pip-filled dependencies on ``PYTHONPATH``.

114 of the 152 collected cases live under ``tests/integration/`` and drive the
real CLI against a live Mastodon API: ``conftest.py`` skips the whole directory
unless ``TOOT_TEST_BASE_URL`` points at a reachable instance. A real Mastodon
stack is not obtainable here — it needs Ruby/Rails plus postgres, redis and
elasticsearch, none of which are adapted for HarmonyOS PC and none of which
exist on the CI workers (no container runtime either) — so ``build()`` starts
``test_support/mastodon_api_stub.py``, a stateful pure-stdlib implementation of
the Mastodon REST endpoints the suite exercises (apps/oauth, accounts, statuses,
scheduled statuses, media, polls, lists, tags, notifications, timelines, Link
header pagination), points ``TOOT_TEST_BASE_URL`` at it, and lets the cases run
for real. The stub is test support only: it is exported with the recipe, never
installed into the package. Same approach as the merged
``restclient-cpp/0.5.3`` (``loopback_httpbin.py``) and ``libetebase/0.5.8``
(``etebase_stub_server.py``) recipes.

Reference run on HarmonyOS PC: **150 passed, 2 skipped** (152 collected). The
only two skips are upstream's own — ``tests/test_config.py::test_save_app`` and
``::test_delete_app`` call ``pytest.skip("TODO: fix mocking")`` as their first
statement, so they are skipped on upstream CI too and are not masked failures.

``tests/test_utils.py`` imports ``PIL`` at module level (upstream keeps pillow
in its dev dependency group), so PIL availability is probed explicitly by
``_pil_site()`` rather than the file being silently dropped. The packaged
artifact is exercised separately by ``test_package/`` (real consumer test, R34).
"""

import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from importlib.machinery import EXTENSION_SUFFIXES

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# Runtime requirements with a published ohpcd recipe. Single source of truth:
# ``requirements()`` iterates this mapping.
#
# The second group is the *runtime* transitive closure of ``requests`` /
# ``python-dateutil`` / ``beautifulsoup4``. They are declared as direct
# requirements even though pip would resolve them indirectly, because of a
# Conan-2 trait gap for pure-Python packages:
#
#   requires.Requirement.process_package_type() forces ``run=True`` for
#   ``application`` / ``shared-library`` / ``build-scripts`` dependencies, but
#   it has no branch for ``python-require``. A transitive ``python-require``
#   therefore keeps its default ``run=False``, ``Requirement.files`` stays
#   False, and ``graph_binaries._skip_binaries()`` marks it BINARY_SKIP — no
#   package_folder, no ``runenv_info`` PYTHONPATH.
#
# Escalating them to direct requirements (with ``run=True``) puts them in
# toot's own ``transitive_deps``, where ``files`` is True and the node is kept.
# This is not cosmetic: measured on a plain external consumer
# (``conan install --requires=toot/0.52.1``) the same six nodes were skipped,
# i.e. an installed ``toot`` could not import ``requests`` at run time.
CONAN_REQUIRES = {
    # direct from PyPI requires_dist
    "beautifulsoup4": "4.15.0",
    "click": "8.4.2",
    "python-dateutil": "2.9.0.post0",
    "requests": "2.22.0",
    "wcwidth": "0.2.12",
    # transitive runtime closure, promoted to direct (see note above)
    "chardet": "5.2.0",           # requests -> chardet
    "idna": "3.18",               # requests -> idna
    "urllib3": "2.7.0",           # requests -> urllib3
    "six": "1.17.0",              # python-dateutil -> six
    "soupsieve": "2.4.1",         # beautifulsoup4 -> soupsieve
    "typing-extensions": "4.16.0",  # beautifulsoup4 -> typing-extensions
}

# Runtime requirements without a published ohpcd recipe (pip-filled at build
# time). Pinned against registry wcwidth 0.2.12 — see the module docstring.
PIP_REQUIRES = (
    "urwid==3.0.2",
    "tomlkit==0.15.1",
    "PySocks==1.7.1",
)

# ``tests/integration/conftest.py`` skips the whole directory unless
# ``TOOT_TEST_BASE_URL`` points at a reachable Mastodon instance, and
# ``tests/integration/test_auth.py`` asserts on the literal
# ``http://localhost:3000`` — so the stub in ``test_support/`` has to listen on
# port 3000 on loopback for the 114 integration cases to execute at all.
STUB_HOST = "127.0.0.1"
STUB_PORT = 3000

# OHOS wheels are tagged with the full platform triplet, e.g.
# ``_imaging.cpython-312-aarch64-linux-ohos.so``, whereas the interpreter only
# considers names ending in one of its own ``EXTENSION_SUFFIXES``
# (``.cpython-312.so`` / ``.abi3.so`` / ``.so``). Dropping just ``-linux-ohos``
# leaves ``-aarch64`` behind, which is still not a valid suffix, so the tag has
# to be rewritten onto the interpreter's own cpython tag. The pattern is pinned
# to this interpreter's ``major.minor`` so a foreign minor version is never
# silently relabelled.
_PY_TAG = f"{sys.version_info[0]}{sys.version_info[1]}"
_FOREIGN_SO_SUFFIX = re.compile(r"\.cpython-" + _PY_TAG + r"-[^.]+\.so$")


def _read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _normalise_extension_suffixes(target):
    """Rewrite platform-tagged ``.so`` names onto this interpreter's tag.

    Returns the number of files renamed. Only names carrying a foreign platform
    tag are touched, so already-valid names are left alone.
    """
    tag = f".cpython-{_PY_TAG}.so"
    if tag not in EXTENSION_SUFFIXES:
        tag = ".so"
    renamed = 0
    for root, _dirs, files in os.walk(target):
        for fn in files:
            if not fn.endswith(".so") or not _FOREIGN_SO_SUFFIX.search(fn):
                continue
            new = _FOREIGN_SO_SUFFIX.sub(tag, fn)
            if new != fn:
                os.rename(os.path.join(root, fn), os.path.join(root, new))
                renamed += 1
    return renamed


class TootConan(ConanFile):
    name = "toot"
    version = "0.52.1"
    description = "Mastodon CLI client — command-line client for the Mastodon social network"
    license = "GPL-3.0-only"
    homepage = "https://toot.bezdomni.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)
        # Test support only — never copied into package().
        copy(self, "test_support/**", src=self.recipe_folder,
             dst=self.export_sources_folder, keep_path=True)

    def requirements(self):
        # PyPI requires_dist of 0.52.1:
        #   beautifulsoup4<5.0,>=4.5.0 | click~=8.1 | python-dateutil<3.0,>=2.8.1
        #   requests<3.0,>=2.13      | pysocks>=1.7.1 | tomlkit<1.0,>=0.10.0
        #   urwid~=3.0               | wcwidth>=0.1.7
        # ``run=True`` is mandatory for pure-Python runtime dependencies:
        # a ``python-require`` dependency defaults to ``run=False``, so its
        # ``Requirement.files`` is False and ``graph_binaries._skip_binaries``
        # marks it BINARY_SKIP (no package_folder, no runenv PYTHONPATH) as soon
        # as it is reached transitively. ``toot`` is ``application``, which also
        # forces headers/libs=False downstream, so ``run`` is the only trait
        # that can keep the dependency in the graph — without it the installed
        # client cannot import requests/beautifulsoup4 at run time.
        for name, version in CONAN_REQUIRES.items():
            self.requires(f"{name}/{version}", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # `patches` is empty: the HarmonyOS adaptation needs no upstream source
        # change (see the module docstring). The call is kept so the recipe
        # stays the standard shape and would apply patches if any were added.
        apply_conandata_patches(self)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _py_tag(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _stage(self):
        return os.path.join(self.build_folder, "stage")

    def _dep_site(self, dep):
        """PYTHONPATH entry for a conan dependency, at any depth.

        Recipes in this repo ship pure-Python payloads in two layouts: flat at
        the package root (``click``) and ``lib/pythonX.Y/site-packages``
        (``requests``, ``wcwidth``, ``beautifulsoup4``, ``python-dateutil``).
        Probe both instead of assuming one.

        Callers pass every entry of ``self.dependencies`` (not just the direct
        ``requirements()``): the suite imports ``requests``, which imports its
        own conan-resolved deps (chardet/idna/urllib3). Missing those collection
        errors out on ``tests/test_utils.py`` and ``tests/integration``.
        """
        if dep is None:
            return None
        # `self.dependencies` also lists entries without a resolved package
        # folder in some contexts (measured: package_info() raised
        # `TypeError: expected str, bytes or os.PathLike object, not NoneType`).
        folder = dep.package_folder
        if not folder:
            return None
        site = os.path.join(folder, "lib", self._py_tag(), "site-packages")
        if os.path.isdir(site):
            return site
        if os.path.isdir(folder):
            return folder
        return None

    def _pip(self, target, requirements, extra_env=None, no_deps=True,
             isolation=True, extra_args=()):
        """pip install ``requirements`` into ``target``, failing loudly."""
        if os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(target, exist_ok=True)
        env = dict(os.environ)
        env.update(extra_env or {})
        args = [sys.executable, "-m", "pip", "install", "--no-compile",
                f"--target={target}"]
        if no_deps:
            args.append("--no-deps")
        if not isolation:
            args.append("--no-build-isolation")
        args.extend(extra_args)
        args.extend(requirements)
        self.output.info(f"pip -> {os.path.basename(target)}: {' '.join(requirements)}")
        proc = subprocess.run(args, env=env, capture_output=True)
        out = proc.stdout.decode(errors="ignore") + proc.stderr.decode(errors="ignore")
        if proc.returncode != 0:
            raise ConanException(
                f"pip install failed (rc={proc.returncode}) for "
                f"{' '.join(requirements)}:\n{out[-2000:]}")
        return out

    def _can_import(self, expr, extra_paths=()):
        """True when ``expr`` succeeds under this interpreter (+extra paths)."""
        env = dict(os.environ)
        paths = [p for p in extra_paths if p]
        if paths:
            inherited = env.get("PYTHONPATH")
            env["PYTHONPATH"] = os.pathsep.join(
                paths + ([inherited] if inherited else []))
        proc = subprocess.run([sys.executable, "-c", expr],
                              env=env, capture_output=True)
        return proc.returncode == 0

    # ------------------------------------------------------------------
    # upstream test suite
    # ------------------------------------------------------------------
    def _pil_site(self):
        """Directory providing an importable PIL, or None.

        ``tests/test_utils.py`` does a module-level ``from PIL import Image``
        (pillow sits in upstream's dev dependency group), so without PIL that
        whole module fails to collect. PIL is deliberately NOT a runtime
        requirement of this recipe: toot imports it only for the optional
        ``images`` extra. Tiers, in order:

          1. the interpreter already imports PIL -> nothing to add;
          2. install pillow from the configured index;
          3. install the OHOS aarch64 wheel and rewrite its extension tag:
             that wheel ships ``_imaging.cpython-312-aarch64-linux-ohos.so``,
             which is not among this interpreter's ``EXTENSION_SUFFIXES``
             (``.cpython-312.so``/``.abi3.so``/``.so``) — measured on HarmonyOS
             PC, where ``--platform ohos_aarch64`` installs but ``import PIL``
             raises ``ImportError: cannot import name '_imaging'``. The name has
             to be rewritten onto this interpreter's own cpython tag
             (``_normalise_extension_suffixes``); merely dropping ``-linux-ohos``
             leaves ``-aarch64`` and the module still cannot be imported.

        Returning None means PIL is genuinely unavailable and the caller has to
        report that instead of pretending the module passed.
        """
        expr = "from PIL import Image; Image.new('RGB', (2, 2)).tobytes()"
        if self._can_import(expr):
            return None
        target = os.path.join(self.build_folder, "pil")
        attempts = (
            ("index", {}),
            # ``--platform`` makes pip insist on wheels only.
            ("ohos wheel", {"extra_args": ("--platform", "ohos_aarch64",
                                           "--only-binary=:all:")}),
        )
        for label, kwargs in attempts:
            extra_args = kwargs.pop("extra_args", ())
            try:
                self._pip(target, ["pillow"], no_deps=False, isolation=False,
                          extra_args=extra_args)
            except ConanException as exc:
                self.output.warning(f"pillow via {label} unavailable: {exc}")
                continue
            if not self._can_import(expr, [target]):
                # Rewrite the OHOS extension tag, then re-probe.
                renamed = _normalise_extension_suffixes(target)
                self.output.info(f"normalised {renamed} OHOS extension suffix(es)")
            if self._can_import(expr, [target]):
                self.output.info(f"PIL provided by {label}: {target}")
                return target
        return None

    def _pytest_env(self):
        """Private, deterministic pytest (CI's python has no pytest installed)."""
        target = os.path.join(self.build_folder, "testenv")
        if not self._can_import("import pytest", [target]):
            try:
                self._pip(target, ["pytest"], no_deps=False, isolation=True)
            except ConanException as exc:
                self.output.warning(f"pytest install failed: {exc}")
        return target

    def _stub_script(self):
        """Locate the exported ``test_support/mastodon_api_stub.py``.

        Where the exported sources land depends on how the recipe is being
        built (local flow vs. ``conan create`` from the cache), so probe the
        known folders instead of assuming one.
        """
        rel = os.path.join("test_support", "mastodon_api_stub.py")
        cands = []
        for attr in ("recipe_folder", "export_sources_folder",
                     "base_export_sources_folder", "base_source_folder",
                     "source_folder"):
            base = getattr(self, attr, None)
            if base:
                cands.append(os.path.join(base, rel))
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), rel))
        for path in cands:
            if os.path.isfile(path):
                return path
        return None

    def _start_stub_server(self):
        """Boot the Mastodon API stub on loopback and wait until it answers."""
        script = self._stub_script()
        if script is None:
            raise ConanException(
                "test_support/mastodon_api_stub.py not found: the 114 "
                "tests/integration cases cannot run without it")

        log_dir = os.path.join(self.build_folder, "testlogs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "mastodon_api_stub.log")
        log_file = open(log_path, "w", encoding="utf-8", errors="replace")

        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            [sys.executable, script, "--host", STUB_HOST, "--port", str(STUB_PORT),
             "--verbose"],
            stdout=log_file, stderr=subprocess.STDOUT, env=env, cwd=log_dir)

        url = f"http://{STUB_HOST}:{STUB_PORT}/api/v1/instance"
        deadline = time.time() + 20
        last_error = ""
        while time.time() < deadline:
            if proc.poll() is not None:
                log_file.close()
                raise ConanException(
                    f"stub server exited early (rc={proc.returncode})\n"
                    + "\n".join(_read_text(log_path).splitlines()[-20:]))
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        self.output.info(
                            f"stub server ready on {STUB_HOST}:{STUB_PORT} ({script})")
                        return proc, log_file, log_path
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                last_error = str(exc)[:160]
            time.sleep(0.2)

        proc.terminate()
        log_file.close()
        raise ConanException(
            f"stub server not ready on {STUB_HOST}:{STUB_PORT}: {last_error} "
            f"— see {log_path}")

    @staticmethod
    def _stop_stub_server(proc, log_file):
        try:
            log_file.close()
        except OSError:
            pass
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _run_upstream_tests(self):
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException("upstream tests/ not found in the extracted sdist")

        paths = [self.source_folder, self._stage()]
        for dep in self.dependencies.values():
            site = self._dep_site(dep)
            if site:
                paths.append(site)

        pytest_dir = self._pytest_env()
        if os.path.isdir(pytest_dir):
            paths.insert(0, pytest_dir)

        ignore = []
        pil = self._pil_site()
        if pil:
            paths.append(pil)
        elif not self._can_import("from PIL import Image"):
            ignore = ["--ignore=tests/test_utils.py"]
            self.output.warning(
                "PIL unavailable: tests/test_utils.py cannot be collected "
                "(module-level `from PIL import Image`)")

        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(p for p in paths if p)
        cmd = [sys.executable, "-m", "pytest", "tests", "-q",
               "-p", "no:cacheprovider", *ignore]

        stub, log_file, log_path = self._start_stub_server()
        # ``localhost`` (not 127.0.0.1) because test_auth.py asserts on the
        # literal ``http://localhost:3000``.
        env["TOOT_TEST_BASE_URL"] = f"http://localhost:{STUB_PORT}"
        self.output.info(f"upstream suite: {' '.join(cmd)}")
        try:
            proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                  capture_output=True, timeout=1800)
        finally:
            self._stop_stub_server(stub, log_file)
        out = (proc.stdout.decode(errors="ignore")
               + proc.stderr.decode(errors="ignore")).strip()
        # The trailing stdout line is usually a warning, not the pytest
        # tally ("150 passed, 2 skipped in 5.2s"). Pick the last line that
        # actually carries counts so the build log states the real result.
        summary = "no output"
        for line in reversed(out.splitlines()):
            if re.search(r"\d+ (passed|failed|error|skipped)", line):
                summary = line.strip()
                break
        else:
            if out:
                summary = out.splitlines()[-1]
        # Evidence that the integration cases really talked to the stub rather
        # than skipping: count the requests it served.
        served = len(re.findall(r"^stub: ", _read_text(log_path), re.M))
        self.output.info(f"stub server served {served} API request(s)")
        self.output.info(f"upstream suite result: {summary}")
        if proc.returncode != 0:
            raise ConanException(
                "upstream test suite failed — refusing to package a red build:\n"
                + "\n".join(out.splitlines()[-40:])
                + f"\n--- stub server log ({log_path}) ---\n"
                + "\n".join(_read_text(log_path).splitlines()[-40:]))

    # ------------------------------------------------------------------
    # build / package
    # ------------------------------------------------------------------
    def build(self):
        stage = self._stage()
        # toot's version is dynamic (setuptools_scm); the sdist has no git
        # metadata, so without this the artifact is toot-0.0.0 (docstring #1).
        scm_env = {"SETUPTOOLS_SCM_PRETEND_VERSION": str(self.version)}
        targets = [self.source_folder, *PIP_REQUIRES]
        try:
            self._pip(stage, targets, extra_env=scm_env)
        except ConanException as exc:
            # Restricted index: fetch the PEP 517 backend explicitly and build
            # without isolation.
            self.output.warning(
                f"pip build isolation failed ({exc}); retrying without it")
            boot = os.path.join(self.build_folder, "boot")
            self._pip(boot, ["setuptools", "setuptools_scm", "wheel"], isolation=True)
            env = dict(scm_env)
            env["PYTHONPATH"] = boot
            self._pip(stage, targets, extra_env=env, isolation=False)

        if not os.path.isdir(os.path.join(stage, "toot")):
            raise ConanException(f"toot package missing under {stage}")
        dist_info = os.path.join(stage, f"toot-{self.version}.dist-info")
        if not os.path.isdir(dist_info):
            found = sorted(d for d in os.listdir(stage)
                           if d.startswith("toot-") and d.endswith(".dist-info"))
            raise ConanException(
                f"expected toot-{self.version}.dist-info, found {found or 'none'} — "
                "setuptools_scm produced a placeholder version")

        self._run_upstream_tests()

    def package(self):
        stage = self._stage()
        if not os.path.isdir(stage):
            raise ConanException(f"staging missing: {stage}")
        # Flat payload: toot/, its pip-filled deps, dist-info and bin/toot.
        copy(self, "*", src=stage, dst=self.package_folder,
             excludes="**/__pycache__/**")
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # The flat payload lives at the package root, so PYTHONPATH points
        # there. Declared in BOTH contexts: printing it is not enough, and
        # build-time consumers need it too (aiohttp lesson).
        self.runenv_info.append_path("PYTHONPATH", self.package_folder)
        self.buildenv_info.append_path("PYTHONPATH", self.package_folder)
        # Re-declare every dependency's site directory for the consumer.
        # Necessary, not redundant: several dependency recipes in this repo
        # publish their PYTHONPATH through the Conan 1.x `env_info`, which
        # Conan 2 ignores (chardet/5.2.0, soupsieve/2.4.1), and others declare
        # nothing at all (idna, urllib3, certifi, typing-extensions). Without
        # this, `import toot.api` fails for a consumer because toot imports
        # requests, which imports chardet — measured in test_package:
        # `ModuleNotFoundError: No module named 'chardet'` against conanrun.
        for dep in self.dependencies.values():
            site = self._dep_site(dep)
            if site and site != self.package_folder:
                self.runenv_info.append_path("PYTHONPATH", site)
                self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={self.package_folder}")
