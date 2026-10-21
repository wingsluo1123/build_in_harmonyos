#!/usr/bin/env python3
"""Consumer test for the packaged imaptool executable (Conan L1).

imaptool is a monolithic X11 application (single main() in imaptool.c) — it
exposes no library API and ships no headers, so the consumer test executes the
packaged binary itself and asserts real process behaviour (R34), not a stub.

There is no X server on the device or on the CI worker (no Xorg/Xvfb in the
image and no OHOS xorg-server published on the remote), so the window-driven
image-map editing cannot run here.  test_imaptool.py still asserts real
properties of the packaged artifact:

  * the binary is present, executable and an aarch64 OHOS ELF;
  * its DT_NEEDED records the Conan X11 stack (libXaw7/libXt/libX11) — i.e.
    it was linked against the packaged dependencies, not against a system X11;
  * it carries exactly one OHOS ``.codesign`` section (the package() signature);
  * every headless run (no DISPLAY, and a bogus DISPLAY) loads the whole
    dynamic dependency chain and exits non-zero with Xt's "Can't open display"
    diagnostic instead of hanging or silently succeeding;
  * the man page is installed.

Note on Xt initialisation order: imaptool.c calls XtVaAppInitialize() before
parseparams() (imaptool.c:171 then :178), so even -h/-v require a display;
unlike xfontsel there is no argument path that completes headlessly.  The
no-display path is therefore the only runnable code path and is asserted as
such.

Runtime closure: the OHOS loader may ignore LD_LIBRARY_PATH for Conan cache
paths and the cache libs are symlink chains that HMFS materialises
unreliably, so every concrete (non-symlink) shared object of the dependency
graph is passed to the test script as LD_PRELOAD (same technique as
archives/x/xfontsel/1.1.2/test_package/conanfile.py).
"""
import os
import shlex
import sys

from conan import ConanFile


class ImaptoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _concrete_shared_objects(dependency):
        """Real (non-symlink) *.so* files inside a dependency package."""
        hits = []
        for root, _dirs, files in os.walk(dependency.package_folder):
            for name in sorted(files):
                if ".so" not in name:
                    continue
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue
                hits.append(path)
        return hits

    def _runtime_preload(self):
        """Lower-level libraries first so LD_PRELOAD mirrors link order."""
        order = {
            "libxau": 0,
            "libxdmcp": 1,
            "libxcb": 2,
            "libx11": 3,
            "libxext": 4,
            "libice": 5,
            "libsm": 6,
            "libxt": 7,
            "libxmu": 8,
            "libxpm": 9,
            "libxaw": 10,
        }
        preload = []
        for name, dependency in self.dependencies.items():
            if str(name).split("/")[0] not in order:
                continue
            preload.extend(self._concrete_shared_objects(dependency))
        preload.sort(key=lambda p: os.path.basename(p))
        return ":".join(dict.fromkeys(preload))

    def test(self):
        package = self.dependencies["imaptool"]
        binary = os.path.join(package.package_folder, "bin", "imaptool")
        script = os.path.join(self.source_folder, "test_imaptool.py")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        command = " ".join(
            shlex.quote(item)
            for item in (
                sys.executable,
                script,
                binary,
                package.package_folder,
                preload,
            )
        )
        self.run(command, env="conanrun")
