#!/usr/bin/env python3
"""Consumer test for terminado/0.18.1 (R34 substantial verification).

terminado is a pure-Python wheel library; the assertions themselves live in
test_terminado.py so the package ships a real test source file (CI L0c
requires one; conanfile.py alone does not count).

The run environment provides PYTHONPATH for terminado and its dependencies,
but the aggregation is order-dependent (a dependency that uses
``runenv_info.define_path("PYTHONPATH", ...)`` can clobber a sibling's
``prepend_path``).  The payload roots are exported as
``*_PACKAGE_ROOT`` variables exactly so this test can rebuild the path
robustly instead of trusting the merged PYTHONPATH.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TerminadoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ptyprocess / tornado are only transitive via terminado; declare them
        # explicitly so their runenv (PYTHONPATH) is part of this test's
        # environment — otherwise terminado's own `import tornado` fails
        # inside the consumer test (same root cause fixed in snakeviz/2.2.2).
        self.requires("ptyprocess/0.7.0")
        self.requires("tornado/6.5.2")

    def _pick_python(self):
        """Return an interpreter that can actually *use* a pseudo terminal.

        The consumer test drives a real pty (openpty + select), so a probe
        that merely imports the modules is not enough: the extension modules
        must be native-built too.  On this device the hnp interpreter ships
        non-native ``lib-dynload`` binaries, so ``import select``/``pty``
        fail there (G2 stdlib damage), while the interpreter in
        ``~/usr/local/bin`` is complete.  Probe functionally, then pick.
        """
        probe = (
            "import pty, select, os\n"
            "m, s = pty.openpty()\n"
            "os.write(m, b'x')\n"
            "assert select.select([m], [], [], 0.5)[0]\n"
            "os.close(m); os.close(s)\n"
            "print('PTY_PROBE_OK')\n"
        )
        from shutil import which
        seen = []
        for cand in ("python3", "python3.12", "python"):
            path = which(cand)
            if not path or path in seen:
                continue
            seen.append(path)
            if self.run('"%s" -c "%s"' % (path, probe),
                        ignore_errors=True) == 0:
                return path
        return sys.executable

    def test(self):
        if not can_run(self):
            return
        test_script = os.path.join(self.source_folder, "test_terminado.py")
        python = self._pick_python()
        self.output.info(f"consumer test interpreter: {python}")
        self.run('"%s" "%s"' % (python, test_script), env="conanrun")
