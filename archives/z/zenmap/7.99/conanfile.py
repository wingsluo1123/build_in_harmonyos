#!/usr/bin/env python3
"""Conan recipe — zenmap 7.99 (pure Python, setuptools) for HarmonyOS aarch64.

Zenmap is the graphical Nmap frontend and results viewer.  It is not published
as a standalone tarball; it lives in the Nmap source tree, so the ``zenmap/``
subtree of the official Nmap repository archive is the payload packaged here.
The archive is pinned to the upstream commit that produced the 7.99 release
(``deb076224e9f…``); its ``zenmap/`` tree is byte-for-byte identical to the
official nmap-7.99 release tarball — see conandata.yml.  Upstream builds it the
same way (nmap's ``Makefile``: ``$(PYTHON) -m build $(ZENMAPDIR)/``) and
installs it with ``pip``.  conandata.yml also explains why the repository
archive is used instead of the nmap.org release tarball (nmap.org is
unreachable from the CI workers) and why one packaging-only patch is needed
(no gettext ``msgfmt`` on OHOS).

Adaptation notes
----------------
* **Pure Python, no cross-compilation.**  The payload is 112 ``.py`` files plus
  data (config/pixmaps/docs/locale).  There is no C/C++ compilation step, so the
  recipe does not force a compiler dependency; it is built with the interpreter
  Conan itself runs under (``sys.executable``), which keeps ``build()`` free of
  undeclared shell variables (R33).

* **Runtime dependency on the scanner.**  Zenmap launches ``nmap``; the recipe
  ``requires`` the published OHOS ``nmap/7.99`` package.  That reference is a
  *run* dependency (Conan promotes ``application`` references to ``run=True``),
  so a consumer that installs zenmap also gets the OHOS ``nmap`` binary on
  ``PATH`` — exercised by ``test_package/``.

* **PyGObject / GTK 3 is deliberately NOT a Conan requirement.**  ``zenmapGUI``
  and ``radialnet`` do ``import gi`` at module load.  The registry publishes
  ``pygobject/3.58.0`` and ``gtk/3.24.38``, but on OHOS neither is consumable
  today: pygobject's extension ships as
  ``_gi.cpython-312-aarch64-linux-ohos.so``, which matches none of the
  interpreter's ``EXT_SUFFIX`` values (``.cpython-312.so`` / ``.abi3.so`` /
  ``.so``), and the gtk/gobject-introspection packages ship no ``.typelib``
  files at all.  Declaring them would add a large dependency chain that still
  cannot import ``gi`` — a useless C/C++ dependency chain, which is exactly what
  this task forbids.  GTK is therefore documented as a *platform* prerequisite
  (see notes.md); the pure-Python core (``zenmapCore``) is fully functional and
  is what this package installs and tests.

Upstream test suite (see reports/test-report.md for raw logs)
-------------------------------------------------------------
Upstream ships its cases inside the modules and drives them with
``zenmap/test/run_tests.py`` (``unittest`` discovery over ``*.py``).  Measured
against the 7.99 tarball the suite holds **31** unittest methods in 5 classes:

  * ``zenmapCore.NmapOptions``      : ``NmapOptionsTest`` 17 + ``SplitQuotedTest`` 3
  * ``zenmapCore.SearchResult``     : ``SearchResultTest`` 6
  * ``zenmapCore.StringPool``       : ``StringPoolTest`` 1
  * ``zenmapCore.NetworkInventory`` : ``NetworkInventoryTest`` 2 +
                                      ``FilteredNetworkInventoryTest`` 1 +
                                      ``PortChangeTest`` 1

``build()`` runs 27 of them (the GTK-free modules) and must see them pass.
The 4 ``NetworkInventory`` cases import ``zenmapGUI.SearchGUI`` → ``gi`` and are
executed only where PyGObject is importable; the runner reports them as
GTK-gated skips instead of silently dropping them.
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.layout import basic_layout

# Only the `zenmap/` subtree of the nmap tarball is packaged.
_ZENMAP_SUBDIR = "zenmap"

# Executables produced by the upstream wheel: `zenmap = zenmapGUI.App:run`.
# `ndiff` is declared in zenmap's own pyproject.toml but ndiff is a *separate*
# upstream package (nmap-7.99/ndiff/pyproject.toml, built by `make build-ndiff`),
# so the zenmap wheel carries no `ndiff` module and the generated `bin/ndiff`
# launcher is dangling.  It is removed from the package (see package()).
_DANGLING_SCRIPTS = ("ndiff",)

# Upstream unittest methods per module, measured from the 7.99 tarball.  The
# runner in build() is derived from these two groups.
GTK_FREE_MODULES = (
    "zenmapCore.NmapOptions",
    "zenmapCore.StringPool",
    "zenmapCore.SearchResult",
)
GTK_GATED_MODULES = ("zenmapCore.NetworkInventory",)

# Small embedded runner: run the GTK-free upstream cases, and run the gated ones
# only when `gi` imports.  Printing the gate reason keeps the skip auditable.
_UPSTREAM_RUNNER = '''\
import importlib
import sys
import unittest

GTK_FREE = {gtk_free}
GTK_GATED = {gtk_gated}

try:
    importlib.import_module("gi")
    gi_available = True
except Exception:
    gi_available = False

runner = unittest.TextTestRunner(verbosity=2)
suite = unittest.TestSuite()
for name in GTK_FREE:
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
if gi_available:
    for name in GTK_GATED:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))

cases = suite.countTestCases()
result = runner.run(suite)

if not gi_available:
    for name in GTK_GATED:
        print("SKIP(gtk) {{}}: PyGObject 'gi' is not importable here".format(name))

print("upstream: cases={{}} failures={{}} errors={{}} gtk_gated={{}}".format(
    cases, len(result.failures), len(result.errors),
    0 if gi_available else len(GTK_GATED)))
sys.exit(0 if result.wasSuccessful() else 1)
'''.format(gtk_free=GTK_FREE_MODULES, gtk_gated=GTK_GATED_MODULES)


class ZenmapConan(ConanFile):
    name = "zenmap"
    version = "7.99"
    description = "Zenmap — the graphical Nmap frontend and results viewer"
    license = "NPSL-1.0"
    homepage = "https://nmap.org/zenmap/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Application: the wheel installs the `zenmap` launcher (zenmapGUI.App:run).
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Zenmap drives the nmap scanner at run time.  `application` references
        # are promoted to run=True by Conan, so no explicit run= is needed.
        self.requires("nmap/7.99")

    def layout(self):
        basic_layout(self)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _zenmap_src(self):
        return os.path.join(self.source_folder, _ZENMAP_SUBDIR)

    def _tmp_dir(self):
        # E002: /tmp is read-only on HarmonyOS; keep scratch space inside the
        # build folder so nothing is written to a shared location (R49).
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        return tmp

    def _wheel_dir(self):
        return os.path.join(self.build_folder, "wheels")

    def _wheel_path(self):
        wheels = self._wheel_dir()
        found = sorted(f for f in os.listdir(wheels) if f.endswith(".whl"))
        if len(found) != 1:
            raise ConanException(
                "expected exactly one wheel in {}, got {}".format(wheels, found))
        return os.path.join(wheels, found[0])

    def _run_in_src(self, command, src):
        return self.run(command, cwd=src, env="conanbuild")

    # ------------------------------------------------------------------
    # steps
    # ------------------------------------------------------------------
    def source(self):
        # Official nmap repository archive pinned to the 7.99 release commit;
        # strip the top-level nmap-<sha>/ directory.  See conandata.yml for the
        # source-host rationale (nmap.org is unreachable from the CI workers).
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        src = self._zenmap_src()
        if not os.path.isdir(src):
            raise ConanException("zenmap/ not found in the nmap source tree: " + src)

        python = sys.executable

        # Applies the packaging-only portability patch declared in conandata.yml
        # (drop the setuptools-gettext build step: no msgfmt on OHOS/CI).
        apply_conandata_patches(self)

        # E002: keep every scratch file off the read-only /tmp.
        os.environ["TMPDIR"] = self._tmp_dir()

        # (1) wheel — upstream builds zenmap with `python -m build`; `pip wheel`
        #     is the same PEP 517 flow without pulling the `build` frontend.
        #     The isolated build resolves setuptools + setuptools-gettext (the
        #     declared backend) and so compiles the gettext catalogues.  When the
        #     worker cannot reach an index, fall back to an in-place build with
        #     the interpreter's own setuptools (catalogues stay as .po).
        wheels = self._wheel_dir()
        os.makedirs(wheels, exist_ok=True)
        rc = self.run(
            '{} -m pip wheel "{}" --no-deps --wheel-dir "{}"'.format(python, src, wheels),
            cwd=src, env="conanbuild", ignore_errors=True)
        if rc != 0 or not any(f.endswith(".whl") for f in os.listdir(wheels)):
            self.output.warning(
                "isolated wheel build failed (exit {}); retrying with "
                "--no-build-isolation".format(rc))
            self._run_in_src(
                '{} -m pip wheel "{}" --no-deps --no-build-isolation '
                '--wheel-dir "{}"'.format(python, src, wheels), src)

        # (2) upstream suite against the unmodified source tree.  PYTHONPATH
        #     points at the tarball so the cases exercise the shipped sources.
        runner = os.path.join(self.build_folder, "_ohc_upstream_runner.py")
        save(self, runner, _UPSTREAM_RUNNER)
        self.run('PYTHONPATH="{}" {} "{}"'.format(src, python, runner),
                 cwd=src, env="conanbuild")

    def package(self):
        python = sys.executable
        # Stage the wheel with pip so wheel `.data` directories land where pip
        # says they belong (share/locale for the compiled catalogues, bin for the
        # console scripts) instead of being unzipped into site-packages.
        stage = os.path.join(self.build_folder, "stage")
        shutil.rmtree(stage, ignore_errors=True)
        self.run(
            '{} -m pip install "{}" --target "{}" --no-deps --no-compile'.format(
                python, self._wheel_path(), stage),
            env="conanbuild")

        copy(self, "*", src=stage, dst=self.package_folder)

        # Rewrite the console-script shebang: pip bakes the build interpreter's
        # absolute path in, which need not exist on the target device.
        bin_dir = os.path.join(self.package_folder, "bin")
        for name in os.listdir(bin_dir) if os.path.isdir(bin_dir) else []:
            script = os.path.join(bin_dir, name)
            if not os.path.isfile(script):
                continue
            first, _, rest = load(self, script).partition("\n")
            if first.startswith("#!"):
                save(self, script, "#!/usr/bin/env python3\n" + rest)
            os.chmod(script, 0o755)

        # Drop upstream's dangling `ndiff` launcher (ndiff is a separate
        # upstream package; the zenmap wheel ships no `ndiff` module).
        for name in _DANGLING_SCRIPTS:
            stale = os.path.join(self.package_folder, "bin", name)
            if os.path.exists(stale):
                os.remove(stale)
                self.output.info("removed dangling launcher bin/{}".format(name))

        copy(self, "LICENSE", src=self._zenmap_src(), dst=os.path.join(
            self.package_folder, "licenses"))
        copy(self, "COPYING_HIGWIDGETS", src=self._zenmap_src(), dst=os.path.join(
            self.package_folder, "licenses"))

    def package_info(self):
        # Pure-Python payload installed at the package root (module packages
        # zenmapCore / zenmapGUI / radialnet), plus bin/ for the launcher.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.append_path("PYTHONPATH", self.package_folder)
        self.buildenv_info.append_path("PYTHONPATH", self.package_folder)
