#!/usr/bin/env python3
"""Conan test_package — xlbiff 4.6.11.

xlbiff is a GUI executable (R34: the test must exercise the packaged
artifact).  Neither the device nor the CI worker has an X server — there is
no Xorg/Xvfb binary in the image and no OHOS xorg-server implementation is
published on the remote (same environment as the coolmail/1.3 precedent) —
and xlbiff handles "-version"/"-help" only AFTER XtVaAppInitialize has
already opened the display, so no argument path completes headlessly.
test_xlbiff.sh still asserts real behaviour of the packaged binary:

  * the packaged binary exists, is an executable ELF and has the 4.6.11
    version string compiled in (grep on the binary);
  * a run without DISPLAY exits non-zero with Xt's "Can't open display"
    diagnostic — that loads the whole dynamic dependency chain
    (libXt -> libSM/libICE, libXaw -> libXmu/libXpm, libX11 ->
    libxcb/libXau/libXdmcp, libXrandr -> libXrender) and executes the
    app-resource parsing at the top of main() before display init fails;
  * the installed man pages, app-defaults resource file (XLbiff) and the
    mailbox-preview helper script are present.

Runtime library resolution follows the xeyes/1.3.1 precedent: the OHOS
loader may ignore LD_LIBRARY_PATH, so dependency .so files are preloaded
by absolute path (dependency order) and the conanrun LD_LIBRARY_PATH is
exported on top.
"""
import os
import shutil

from conan import ConanFile


class XlbiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dep, soname_prefix):
        """Find a SONAME-prefixed .so inside a dependency package.

        Conan cache libraries are usually .so -> .so.N -> .so.N.x.y
        symlink chains; HMFS materializes symlinks unreliably (E050), so
        prefer the concrete (non-symlink) file - the loader registers it
        under its embedded SONAME, which is equivalent.
        """
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for name in sorted(files):
                if name.startswith(soname_prefix):
                    hits.append(os.path.join(root, name))
        if not hits:
            return None
        for path in hits:
            if not os.path.islink(path):
                return path
        return hits[0]

    def _runtime_preload(self):
        """xlbiff runtime shared libraries (conan deps + transitive)."""
        found = []
        wanted = (
            ("libxau", "libXau.so.6"),
            ("libxdmcp", "libXdmcp.so.6"),
            ("libxcb", "libxcb.so.1"),
            ("libxrender", "libXrender.so.1"),
            ("libx11", "libX11.so.6"),
            ("libxext", "libXext.so.6"),
            ("libsm", "libSM.so.6"),
            ("libice", "libICE.so.6"),
            ("libxt", "libXt.so.6"),
            ("libxmu", "libXmu.so.6"),
            ("libxmuu", "libXmuu.so.1"),
            ("libxpm", "libXpm.so.4"),
            ("libxaw", "libXaw.so.7"),
            ("libxrandr", "libXrandr.so.2"),
        )
        for name, prefix in wanted:
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        dep = self.dependencies["xlbiff"]
        xlbiff_bin = os.path.join(dep.package_folder, "bin", "xlbiff")

        # HMBS [shell_getcwd]: run with the injected SHELL (/bin/sh), do
        # not hardcode /data/service/hnp/bin/bash. POSIX sh only.
        shell = (
            os.environ.get("SHELL")
            or os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/bin/sh"
        )
        script = os.path.join(self.source_folder, "test_xlbiff.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        command = (
            f'"{shell}" "{script}" "{dep.package_folder}" '
            f'"{xlbiff_bin}" "{preload}"'
        )
        self.run(command, env="conanrun")
        # Upstream suite audit (R51, see test_package/MANIFEST.yml
        # upstream_test_audit): xlbiff 4.6.11 ships 23 upstream test
        # cases (9 unittest in mailbox-preview-test.py executed above
        # against the packaged helper; 1 nmh/Xvfb integration case in
        # tests/test-scan-interface.sh; 5 man-formatter cases in
        # tests/test-doc-format.sh; 8 windowing sequences in
        # tests/test-windowing.sh). Makefile.am defines no
        # TESTS/check_PROGRAMS, so `make check` is a no-op. See the
        # audit block printed by test_xlbiff.sh.
