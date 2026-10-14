#!/usr/bin/env python3
"""Conan recipe for tinyprog 1.0.23 — TinyFPGA USB bootloader programmer.

HarmonyOS PC (aarch64) adaptation notes
---------------------------------------
tinyprog is a **pure-Python** application (setuptools, no C extension), so there
is no cross-compilation step at all: the entire adaptation is a packaging
problem.  This recipe therefore declares **no C/C++ toolchain dependency** —
adding one would be cargo-cult, not adaptation.

1. **Source layout.**  Upstream tags the release ``tinyprog-1.0.23`` inside the
   ``TinyFPGA-Bootloader`` repository; the distributable Python package lives in
   the ``programmer/`` subdirectory of that tag.  ``source()`` fetches the tag
   archive (R39: official GitHub source) and ``build()`` installs
   ``programmer/`` into a private staging prefix (R49).

2. **Dependency pre-flight (W0), measured against the ``ohpcd`` registry.**
   tinyprog's ``setup.py`` declares seven runtime requirements.  Probing the
   registry with ``conan download`` / ``conan install`` (R35 — ``conan list`` is
   not trustworthy for binaries) gives::

     requirement   ohpcd census                        how this recipe gets it
     pyserial      pyserial/3.5, binary present   ->   requires() (conan)
     six           six/1.17.0, binary present     ->   requires() (conan)
     intelhex      not published                  ->   pip-filled
     jsonmerge     not published                  ->   pip-filled
     tqdm          not published                  ->   pip-filled
     pyusb         not published                  ->   pip-filled
     packaging     recipe only, and UNUSABLE      ->   pip-filled

   ``packaging/26.3`` deserves its own note: a recipe *does* exist, but it
   cannot be consumed — ``conan install --requires=packaging/26.3`` fails with
   ``Invalid: 'settings.os.version' value not defined``.  Declaring it as a
   ``requires()`` would turn every CI run red, so it is pip-filled instead
   (measured, not assumed).

   The five without a usable published recipe are installed with pip into the
   package itself at build time — the same approach used by ``acstore``,
   ``adb-enhanced`` and ``alot``.  A recipe PR must not bundle
   unrelated packages (W2/PF1), so they cannot be adapted here.

3. **pip index.**  The HarmonyOS community mirror
   (``https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple``) is
   the only index reachable from this environment; public PyPI and the
   Tsinghua mirror both fail here (measured).  ``_pip()`` therefore pins the
   community index, overridable via ``OHC_PIP_INDEX``.

4. **Runtime fingerprint and the OHOS pyserial shim (R32).**  The HarmonyOS PC
   runtime reports ``os.uname().sysname == "HarmonyOS"`` and
   ``platform.system() == "HarmonyOS"``, but ``sys.platform`` is *not* stable
   across interpreter builds: the HNP interpreter reports ``"linux"`` while the
   worker's own interpreter reports ``"ohos"`` (and other builds use
   ``"harmonyos"`` / ``"ohos-*"``).  pyserial 3.5's
   ``serial.tools.list_ports_posix`` only knows the prefixes it was written for
   and raises ``ImportError`` for anything else, so on the worker
   ``tinyprog --help`` died at ``from serial.tools.list_ports import comports``
   (CI build #89823) even though it passed locally.  This recipe therefore
   ships ``sitecustomize.py`` next to the payload: CPython auto-imports it, and
   on OHOS *only* it registers the Linux port-enumeration backend under the name
   pyserial's dispatcher looks for.  The payload is otherwise identical on every
   platform; ``test_package/`` asserts both the runtime fingerprint and the
   shim.

5. **No shared-prefix writes (R49).**  Everything is staged under
   ``<self.build_folder>/stage`` and copied from there by ``package()``;
   nothing is written to ``/usr/local`` or any other shared location.

6. **Console script.**  ``pip --target`` materialises the ``entry_points``
   console script as ``bin/tinyprog``; a CLI-bearing *application* must also
   ship the software-level ``commands.json`` (R38).

7. **The pip closure must stay pure Python, so it is pinned and asserted.**
   ``jsonmerge`` only asks for ``jsonschema (>2.4.0)``, leaving the transitive
   set to whatever the mirror's resolver finds — and that is *not* stable:
   ``jsonschema >=4.18`` pulls ``referencing`` -> ``rpds-py``, a Rust
   extension.  Whether the mirror lists that wheel varies between runs
   (``pip download rpds-py`` answers "from versions: none" on 2026-10-12), so
   the same recipe staged a pure-Python payload locally and a native one on
   the worker.  There the HNP python (``/data/service/hnp/bin/python3``, which
   the CI profile prepends to ``PATH``) cannot dlopen a user-storage ``.so``
   at all (E212), and ``tinyprog --help`` died with ``ImportError: Error
   loading shared library .../rpds.cpython-312-aarch64-linux-ohos.so:
   Permission denied`` (CI build #84759).  ``jsonschema`` is therefore pinned
   to ``2.6.0`` — the newest release whose closure is pure Python, and one
   that satisfies jsonmerge's constraint — and ``build()`` refuses to stage
   any native extension at all, so the drift surfaces locally instead of on
   the worker.

Upstream test suite — measured, not assumed
-------------------------------------------
tinyprog ships **no Python test suite**.  ``programmer/README.md`` states
verbatim: "Tests have been removed for now pending refactoring of test
methodology", and ``setup.py`` declares no ``test_suite``/``tests_require``.
The repository's ``tests/`` directory contains only Verilog RTL testbenches
that simulate the FPGA bootloader *firmware*: they do not exercise this Python
package and require an icarus-verilog simulator that the OHOS CI image does not
provide.

Nothing is silently dropped.  ``_run_upstream_tests()`` records the exact
census it finds (Python test files found: 0; RTL benches; simulator
availability) so the report is auditable rather than a bare "0 passed", and
``build()`` independently compiles every shipped ``.py`` with the OHOS
interpreter and drives the installed console script end to end.

Because upstream has no runnable suite for this package, this adaptation
supplies the test evidence itself: ``test_package/`` runs a real consumer
suite (R34) with HarmonyOS-specific assertions — see
``test_package/MANIFEST.yml`` for the full census.
"""

import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Runtime requirements that have **no usable published recipe** on the ohpcd
# registry (see the module docstring for the measured census).  They are pip
# installed into the package itself at build time.
PIP_REQUIRES = (
    "intelhex==2.3.0",
    "jsonmerge==1.9.2",
    "tqdm==4.70.1",
    "pyusb==1.3.1",
    "packaging==26.3",
    # jsonmerge only constrains this to ``jsonschema (>2.4.0)``; left to the
    # resolver the closure floats, and jsonschema >=4.18 drags in
    # ``referencing`` -> ``rpds-py``, a Rust extension.  That native payload
    # cannot be imported on the worker — the HNP python cannot dlopen a
    # user-storage .so (E212) — which is how CI build #84759 failed.  2.6.0 is
    # the newest jsonschema with a pure-Python closure; build() asserts the
    # payload stays native-free (module note 7).
    "jsonschema==2.6.0",
)

# Only the community mirror is reachable from the HarmonyOS PC worker
# (measured); public PyPI and the Tsinghua mirror both fail here.
PIP_INDEX = os.environ.get(
    "OHC_PIP_INDEX",
    "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple",
)
PIP_TRUSTED_HOST = "pypi.cnb.cool"


class TinyprogConan(ConanFile):
    name = "tinyprog"
    version = "1.0.23"
    description = ("tinyprog — TinyFPGA USB bootloader programmer "
                   "(pure Python CLI, HarmonyOS PC aarch64)")
    license = "MIT"
    homepage = "https://github.com/tinyfpga/TinyFPGA-Bootloader"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("fpga", "bootloader", "usb", "spi-flash", "cli", "python")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        # The OHOS pyserial shim (module note 4) ships as an extra payload file,
        # not as an upstream patch, so it is exported alongside patches/.
        copy(self, "sitecustomize.py", src=self.recipe_folder,
             dst=self.export_sources_folder)
        export_conandata_patches(self)

    def requirements(self):
        # ``run=True`` is mandatory for pure-Python runtime dependencies: a
        # ``python-require`` dependency defaults to ``run=False``, so its
        # ``Requirement.files`` is False and the binary is skipped (no
        # package_folder, no runenv PYTHONPATH) as soon as it is reached
        # transitively.  ``tinyprog`` is ``application``, which additionally
        # forces headers/libs=False downstream, so ``run`` is the only trait
        # that keeps the dependency in the graph — without it the installed
        # client cannot ``import serial`` / ``import six`` at run time.
        self.requires("pyserial/3.5", run=True)
        self.requires("six/1.17.0", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # ``patches`` is empty: the HarmonyOS adaptation needs no upstream
        # source change (see the module docstring).  The call is kept so the
        # recipe stays the standard shape and would apply patches if any were
        # ever added.
        apply_conandata_patches(self)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _py_tag(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _upstream(self):
        return os.path.join(self.source_folder, "programmer")

    def _stage(self):
        """Private staging prefix (R49: never a shared/system prefix)."""
        return os.path.join(self.build_folder, "stage")

    def _dep_site(self, dep):
        """PYTHONPATH entry for a conan dependency, at any depth.

        Recipes in this repo ship pure-Python payloads in several layouts:
        ``lib/pythonX.Y/site-packages`` (packaging-style), ``lib/python/
        site-packages`` (``pyserial``, ``six`` — measured) and flat at the
        package root.  Probe all of them instead of assuming one.
        """
        if dep is None:
            return None
        # ``self.dependencies`` also lists entries without a resolved package
        # folder in some contexts (measured upstream: package_info() raised
        # ``TypeError: expected str, bytes or os.PathLike object, not NoneType``).
        folder = dep.package_folder
        if not folder:
            return None
        for candidate in (
            os.path.join(folder, "lib", self._py_tag(), "site-packages"),
            os.path.join(folder, "lib", "python", "site-packages"),
        ):
            if os.path.isdir(candidate):
                return candidate
        if os.path.isdir(folder):
            return folder
        return None

    def _dep_sites(self, extra=()):
        """Every dependency site dir, plus ``extra``, de-duplicated in order."""
        seen = []
        for path in list(extra) + [
            self._dep_site(dep) for dep in self.dependencies.values()
        ]:
            if path and path not in seen:
                seen.append(path)
        return seen

    def _pip(self, target, requirements, clean=True, no_deps=True,
             isolation=True, extra_env=None):
        """pip install ``requirements`` into ``target``, failing loudly."""
        if clean and os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(target, exist_ok=True)
        env = dict(os.environ)
        env.update(extra_env or {})
        args = [sys.executable, "-m", "pip", "install", "--no-compile",
                "--index-url", PIP_INDEX,
                "--trusted-host", PIP_TRUSTED_HOST,
                f"--target={target}"]
        if no_deps:
            args.append("--no-deps")
        if not isolation:
            args.append("--no-build-isolation")
        args.extend(requirements)
        self.output.info(f"pip -> {os.path.basename(target)}: {' '.join(requirements)}")
        proc = subprocess.run(args, env=env, capture_output=True)
        out = proc.stdout.decode(errors="ignore") + proc.stderr.decode(errors="ignore")
        if proc.returncode != 0:
            raise ConanException(
                f"pip install failed (rc={proc.returncode}) for "
                f"{' '.join(requirements)}:\n{out[-2000:]}")
        return out

    def _run(self, args, extra_paths=(), cwd=None):
        """Run a command with the staged payload + dependencies importable."""
        env = dict(os.environ)
        paths = [p for p in self._dep_sites(extra_paths) if p]
        if paths:
            inherited = env.get("PYTHONPATH")
            env["PYTHONPATH"] = os.pathsep.join(
                paths + ([inherited] if inherited else []))
        env["PATH"] = os.pathsep.join(
            [os.path.join(self._stage(), "bin"), env.get("PATH", "")])
        return subprocess.run(args, env=env, cwd=cwd or self.build_folder,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def _compile_all(self, stage):
        """Byte-compile every shipped ``.py`` with the target interpreter.

        This is a real gate, not decoration: it catches syntax/encoding that a
        Python-2-era code path might still carry (the tag also ships a
        ``py2-no...`` wheel upstream) without ever importing anything.
        """
        files = []
        for dirpath, dirnames, filenames in os.walk(stage):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            files.extend(os.path.join(dirpath, n)
                         for n in filenames if n.endswith(".py"))
        if not files:
            raise ConanException(f"no .py files staged under {stage}")
        cmd = [sys.executable, "-c",
               "import sys, py_compile\n"
               "for p in sys.argv[1:]:\n"
               "    py_compile.compile(p, doraise=True)\n"]
        cmd.extend(files)
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode != 0:
            raise ConanException(
                "staged payload failed to byte-compile on the target "
                f"interpreter:\n{proc.stderr.decode(errors='ignore')[-2000:]}")
        self.output.info(f"byte-compiled {len(files)} staged Python files")

    # ------------------------------------------------------------------
    # upstream test suite
    # ------------------------------------------------------------------
    def _upstream_census(self):
        """Measured census of the *upstream* tree: (py_tests, rtl_benches).

        Only upstream's own locations are inspected — ``programmer/`` (the
        package) and the repository-level ``tests/``.  Restricting the walk is
        necessary rather than tidy: ``basic_layout()`` makes
        ``self.source_folder`` coincide with the build folder, which also holds
        the staging tree, so an unrestricted walk finds pip-installed
        third-party test files (measured: ``stage/jsonschema/tests/test_cli.py``
        was mistaken for an upstream test and aborted the build).
        """
        py_tests, rtl = [], []
        stage = os.path.abspath(self._stage())
        for rel_root in ("programmer", "tests"):
            root = os.path.join(self.source_folder, rel_root)
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames
                               if d not in ("__pycache__", ".git", "boards")
                               and not os.path.abspath(
                                   os.path.join(dirpath, d)).startswith(stage)]
                in_test_dir = any(part in ("tests", "test")
                                  for part in os.path.relpath(
                                      dirpath, root).split(os.sep))
                for name in filenames:
                    rel = os.path.relpath(os.path.join(dirpath, name),
                                          self.source_folder)
                    if name.endswith(".v"):
                        rtl.append(rel)
                    elif (name.endswith(".py")
                          and (name.startswith("test_")
                               or name.endswith("_test.py")
                               or in_test_dir)):
                        py_tests.append(rel)
        return sorted(py_tests), sorted(rtl)

    def _run_upstream_tests(self):
        """Run the upstream suite when one exists; otherwise record the census.

        A bare "0 passed" would be indistinguishable from a silently skipped
        suite, so the census is printed explicitly and names the evidence.
        """
        py_tests, rtl = self._upstream_census()
        self.output.info(
            f"upstream census: python test files={len(py_tests)} "
            f"{py_tests or '(none)'}; RTL testbenches={len(rtl)}")

        if py_tests:
            proc = self._run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                 *[os.path.join(self.source_folder, t) for t in py_tests]],
                extra_paths=[self._stage()])
            out = proc.stdout.decode(errors="ignore")
            self.output.info(f"upstream pytest rc={proc.returncode}\n{out[-1500:]}")
            if proc.returncode != 0:
                raise ConanException(
                    f"upstream test suite failed (rc={proc.returncode}):\n"
                    f"{out[-2000:]}")
        else:
            # Not a masked failure — upstream removed the suite.  Programmer
            # README says so verbatim and setup.py declares no test target.
            self.output.info(
                "upstream ships NO Python test suite for this package: "
                "programmer/README.md states 'Tests have been removed for now "
                "pending refactoring of test methodology', and setup.py has no "
                "test_suite/tests_require. There is nothing to run for this "
                "package; the adaptation supplies its own consumer suite in "
                "test_package/ (census in test_package/MANIFEST.yml).")

        if rtl:
            sim = shutil.which("iverilog")
            self.output.info(
                f"upstream tests/ holds {len(rtl)} Verilog RTL testbenches that "
                f"simulate the bootloader FIRMWARE — they do not exercise this "
                f"Python package and need an icarus-verilog simulator "
                f"(iverilog: {'found' if sim else 'NOT present in this CI '
                'image'}) -> not executed, recorded as an environment "
                f"capability gap (W0b), not a package failure")

    def _smoke(self, stage):
        """Drive the installed console script end to end (real execution)."""
        script = os.path.join(stage, "bin", "tinyprog")

        proc = self._run([sys.executable, script, "--help"], extra_paths=[stage])
        out = proc.stdout.decode(errors="ignore")
        if proc.returncode != 0:
            raise ConanException(
                f"`tinyprog --help` failed (rc={proc.returncode}):\n{out[-1500:]}")
        self.output.info("smoke: `tinyprog --help` ok")

        # `-l` enumerates serial ports through the conan-provided pyserial.
        # Upstream exits 1 when no bootloader is attached, so rc=1 is the
        # expected outcome on a board-less worker — the *message* is asserted
        # instead, and any other rc is a real failure.
        proc = self._run([sys.executable, script, "-l"], extra_paths=[stage])
        out = proc.stdout.decode(errors="ignore")
        if proc.returncode not in (0, 1):
            raise ConanException(
                f"`tinyprog -l` failed (rc={proc.returncode}):\n{out[-1500:]}")
        if "TinyProg" not in out:
            raise ConanException(
                f"`tinyprog -l` produced unexpected output (rc={proc.returncode})"
                f":\n{out[-1500:]}")
        self.output.info(
            "smoke: `tinyprog -l` ok (pyserial enumeration on HarmonyOS, "
            "rc=1 = no bootloader attached, as upstream specifies)")

    # ------------------------------------------------------------------
    # build / package
    # ------------------------------------------------------------------
    def build(self):
        upstream = self._upstream()
        if not os.path.isdir(upstream):
            raise ConanException(
                f"upstream package directory missing: {upstream} — the tag "
                f"archive layout is not what this recipe expects")

        stage = self._stage()

        # 1. The application itself.  Its requirements are resolved by conan
        #    (pyserial/six) or pip-filled below, hence --no-deps.
        try:
            self._pip(stage, [upstream], no_deps=True, isolation=True)
        except ConanException as exc:
            # Build isolation needs an index for setuptools/wheel; fall back to
            # the interpreter's own toolchain (same fallback as acstore).
            self.output.warning(f"pip build isolation failed ({exc}); "
                                f"retrying without it")
            boot = os.path.join(self.build_folder, "boot")
            self._pip(boot, ["setuptools", "wheel"], isolation=True)
            self._pip(stage, [upstream], no_deps=True, isolation=False,
                      extra_env={"PYTHONPATH": boot})

        # 2. Dependencies with no usable published recipe.  Installed WITH
        #    their transitive requirements so the payload is self-contained
        #    (jsonmerge -> jsonschema).
        self._pip(stage, list(PIP_REQUIRES), clean=False, no_deps=False)

        # 3. OHOS pyserial shim (module note 4).  Shipped as a sibling of the
        #    payload so CPython auto-imports it from PYTHONPATH: without it the
        #    worker's `sys.platform == 'ohos'` makes pyserial's dispatcher raise
        #    ImportError and every `tinyprog` import fails.
        copy(self, "sitecustomize.py", src=self.export_sources_folder,
             dst=stage)

        # 4. Native-free closure gate.  This adaptation is pure Python by
        #    construction (module note 7): a staged extension means the pip
        #    resolution drifted back to a native requirement, which the worker
        #    cannot import at all (E212).  Fail here, naming the culprit,
        #    rather than letting CI discover it as a permission error.
        native = []
        for dirpath, dirnames, filenames in os.walk(stage):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            native.extend(os.path.relpath(os.path.join(dirpath, name), stage)
                          for name in filenames
                          if name.endswith((".so", ".pyd", ".dylib"))
                          or ".so." in name)
        if native:
            raise ConanException(
                "pip closure is no longer pure Python — native extension(s) "
                f"staged: {sorted(native)[:5]}.  An HNP python cannot dlopen a "
                "user-storage .so (E212); pin the drifting requirement instead "
                "(see PIP_REQUIRES / module note 7).")

        # 5. Layout gate.
        if not os.path.isdir(os.path.join(stage, "tinyprog")):
            raise ConanException(f"tinyprog package missing under {stage}")
        dist_info = os.path.join(stage, f"tinyprog-{self.version}.dist-info")
        if not os.path.isdir(dist_info):
            found = sorted(d for d in os.listdir(stage)
                           if d.startswith("tinyprog-")
                           and d.endswith(".dist-info"))
            raise ConanException(
                f"expected tinyprog-{self.version}.dist-info, found "
                f"{found or 'none'}")
        if not os.path.isfile(os.path.join(stage, "bin", "tinyprog")):
            raise ConanException(
                f"console script bin/tinyprog missing under {stage} — the "
                f"entry_points were not materialised")

        # 6. Syntax gate on the target interpreter.
        self._compile_all(stage)

        # 7. Upstream suite (census; nothing runnable for this package).
        self._run_upstream_tests()

        # 8. End-to-end smoke of the *installed* console script.
        self._smoke(stage)

    def package(self):
        stage = self._stage()
        if not os.path.isdir(stage):
            raise ConanException(f"staging missing: {stage}")
        # Flat payload: tinyprog/, its pip-filled deps, dist-info and
        # bin/tinyprog — the same flat shape produced by `pip --target`.
        # ``**/__pycache__/**`` does not match a *top-level* bytecode cache
        # (``**`` is plain fnmatch here, so it needs a leading directory), and
        # the OHOS shim sits at the payload root — exclude both spellings so
        # no build byproduct is packaged.
        copy(self, "*", src=stage, dst=self.package_folder,
             excludes=("**/__pycache__/**", "__pycache__/**"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # The flat payload lives at the package root, so PYTHONPATH points
        # there.  Declared in BOTH contexts: printing it is not enough, and
        # build-time consumers need it too.
        self.runenv_info.append_path("PYTHONPATH", self.package_folder)
        self.buildenv_info.append_path("PYTHONPATH", self.package_folder)
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        # Re-declare every dependency's site directory for the consumer.
        # Necessary, not redundant: ``six/1.17.0`` publishes PYTHONPATH through
        # ``runenv_info`` only (no buildenv), so a build-time consumer would not
        # see it otherwise; ``pyserial/3.5`` uses the un-versioned
        # ``lib/python/site-packages`` layout that a naive probe misses.
        for dep in self.dependencies.values():
            site = self._dep_site(dep)
            if site and site != self.package_folder:
                self.runenv_info.append_path("PYTHONPATH", site)
                self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={self.package_folder}")
