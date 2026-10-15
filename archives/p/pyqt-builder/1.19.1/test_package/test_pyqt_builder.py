#!/usr/bin/env python3
"""Consumer test for the packaged PyQt-builder.

Upstream ships no test suite, so this exercises the public surface against
the *installed* package plus the dependency chain it needs at import time:

* ``pyqtbuild`` imports (which requires ``sip`` from the graph — the reason
  this package declares sip as a requirement);
* the four public classes PyQt6's build backend relies on are present
  (PyQtBindings, QmakeBuilder, PyQtProject, QmakeTargetInstallable);
* the version constant matches the pinned release;
* the data trees shipped by the sdist survive packaging (bundle/packages has
  the packaging metadata modules, qt_wheel_distinfo has the wheel metadata);
* both console scripts execute (``--help``).
"""
import os
import subprocess
import sys


def main(pkg):
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    assert os.path.isdir(site), site
    sys.path.insert(0, site)

    import pyqtbuild
    from pyqtbuild.version import PYQTBUILD_VERSION_STR

    print("pyqtbuild version:", PYQTBUILD_VERSION_STR)
    assert PYQTBUILD_VERSION_STR == "1.19.1", PYQTBUILD_VERSION_STR

    # Public API used by PyQt6's pyproject build backend (sipbuild.api ->
    # pyqtbuild.builder / project).
    from pyqtbuild import (PyQtBindings, PyQtProject, QmakeBuilder,  # noqa: F401
                           QmakeTargetInstallable)
    from pyqtbuild.bundle import qt_metadata  # noqa: F401
    print("public API importable (incl. sip dependency at load time)")

    # Data trees must survive packaging.
    pkgdir = os.path.dirname(pyqtbuild.__file__)
    pkgs = os.path.join(pkgdir, "bundle", "packages")
    assert os.path.isfile(os.path.join(pkgs, "pyqt6.py")), pkgs
    assert os.path.isfile(os.path.join(pkgdir, "bundle",
                                       "qt_wheel_distinfo", "METADATA"))
    print("bundle data trees present")

    bindir = os.path.join(pkg, "bin")
    env = dict(os.environ)
    # PREPEND our site-packages; never replace PYTHONPATH outright, because
    # the conanrun env already carries the sip dependency's path and the
    # console scripts import sipbuild at load time.
    env["PYTHONPATH"] = os.pathsep.join(
        [site] + [p for p in [env.get("PYTHONPATH", "")] if p])
    for tool in ("pyqt-bundle", "pyqt-qt-wheel"):
        exe = os.path.join(bindir, tool)
        assert os.path.isfile(exe), exe
        assert os.access(exe, os.X_OK), "%s not executable" % exe
        r = subprocess.run([exe, "--help"], capture_output=True, text=True,
                           env=env, timeout=120)
        assert r.returncode == 0, (tool, r.returncode, r.stderr[:300])
        assert "usage" in (r.stdout + r.stderr).lower(), tool
    print("all 2 console scripts execute")

    print("PYQT-BUILDER-CONSUMER-OK")


main(sys.argv[1] if len(sys.argv) > 1 else sys.argv[0])
