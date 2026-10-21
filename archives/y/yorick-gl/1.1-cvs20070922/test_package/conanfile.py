#!/usr/bin/env python3
"""test_package for yorick-gl.

Consumer verification: the *real* yorick interpreter dynamically loads the
built ``yorgl.so`` plugin from the package (``plug_in, "yorgl"``) and drives the
compiled iso-surface engine — ``PrepIsoTet()`` plus ``MakeContourTree`` via the
upstream interpreted wrapper ``mak_isotree`` over a 12x12x12 field — asserting
the resulting octree.  This is a genuine API test: it fails if ``yorgl.so``
cannot be loaded or the compiled symbols are wrong.

The plugin's interactive-graphics routines (``win3d``/``draw3d``) need an X
display, which the OHOS target has no server for, so the test is headless.
"""
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class YorickGlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        yorick_pkg = self.dependencies["yorick"].package_folder
        yorick_bin = os.path.join(yorick_pkg, "bin", "yorick")
        ygl_pkg = self.dependencies[self.tested_reference_str].package_folder

        if not os.path.isfile(yorick_bin):
            raise ConanException(f"yorick interpreter missing: {yorick_bin}")
        if not os.path.isfile(os.path.join(ygl_pkg, "lib", "yorgl.so")):
            raise ConanException(f"packaged plugin missing: {ygl_pkg}/lib/yorgl.so")
        for rel in ("i0/cntrfunc.i", "i/contour.i", "i/tristruct.i", "i-start/yiso3d.i"):
            if not os.path.isfile(os.path.join(ygl_pkg, rel)):
                raise ConanException(f"packaged interpreted layer missing: {rel}")

        # All scratch output goes to a task-private temp dir: conan runs the
        # test with cwd == the test_package folder, which must stay pristine.
        run_dir = tempfile.mkdtemp(prefix="yorick-gl-test-")
        test_home = os.path.join(run_dir, "home")
        test_tmp = os.path.join(run_dir, "tmp")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)

        # materialise the yorick test script with the package path baked in
        with open(self._asset("test_yorick_gl.i"), encoding="utf-8") as handle:
            script = handle.read()
        script_path = os.path.join(run_dir, "test_yorick_gl_final.i")
        with open(script_path, "w", encoding="utf-8") as handle:
            handle.write(script.replace("@YORICKGL_PKG@", ygl_pkg))

        # isolated HOME + TMPDIR for the test subprocess (the porting runner
        # keeps the real HOME; only the child interpreter is isolated)
        env = Environment()
        env.define("HOME", test_home)
        env.define("TMPDIR", test_tmp)
        env.prepend_path("PATH", os.path.join(yorick_pkg, "bin"))

        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        with env.vars(self).apply():
            self.run(
                f'{bash} "{self._asset("test_yorick_gl.sh")}" '
                f'"{yorick_bin}" "{script_path}"',
                cwd=run_dir,
                env="conanrun",
            )

    def _asset(self, name):
        bases = []
        for attr in ("recipe_folder", "source_folder"):
            base = getattr(self, attr, None)
            if base:
                bases.append(base)
        bases.append(os.path.dirname(os.path.abspath(__file__)))
        tried = []
        for base in bases:
            path = os.path.join(base, name)
            tried.append(path)
            if os.path.isfile(path):
                return path
        raise ConanException(f"test_package asset not found: {name} (tried {tried})")
