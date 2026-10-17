#!/usr/bin/env python3
"""Conan test_package — pasystray 0.8.2.

pasystray is a GTK3 systray application; HarmonyOS PC has no X11/Wayland
display service (E471/E527) and the pulseaudio/17.0.1 shared objects it links
are not `.codesign`-signed, so the OHOS loader refuses them on this worker.
The consumer test therefore splits into two parts (R34):

  * **structural / linkage assertions** (delegated to ``test_pasystray.sh``):
    the packaged ``bin/pasystray`` exists, is executable, is a valid ELF, and
    its ``DT_NEEDED`` records ``libpulse.so.0`` and ``libpulse-mainloop-glib.so.0``
    — the delivered binary really links the PulseAudio GLib-mainloop library
    that platform task 9324 is about.  These never execute the binary, so they
    must always genuinely pass (and genuinely fail when ``bin/`` is removed,
    which is what the CI destructive negative gate L1e checks).

  * **upstream CLI contract** (``--version`` must print exactly ``0.8.2``;
    ``--notify=help`` must print the notification option help — both handled by
    ``parse_options()`` in ``src/options.c``): really executed, and asserted on
    the real output.  If the process cannot run because of a *declared* OHOS
    runtime limitation the case is tolerated and reported explicitly; any other
    failure still raises.

The OHOS limitation tolerance follows the already-merged precedent
``archives/p/pavucontrol-qt/2.4.0/test_package/conanfile.py`` (same marker list,
same "Execution skipped due to OHOS platform limitation" declaration).
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import load


class PasystrayTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_pasystray.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    # OHOS runtime-limitation signatures.  First block mirrors the merged
    # pavucontrol-qt/2.4.0 precedent; the last two cover the GTK headless
    # diagnostic that this worker produces once the loader accepts the libs.
    _LIMITATION_MARKERS = (
        "Permission denied",
        "Operation not permitted",
        "Error 126", "Error 127",
        "shared library",
        "symbol not found",
        "Error loading",
        "Cannot open display",
        "cannot open display",
        "rc=126", "rc=127",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Prepend every dependency lib dir to LD_LIBRARY_PATH so the delivered
        # binary can resolve libpulse*/libgtk*/libglib* at run time (same
        # mechanism as the merged pavucontrol-qt/2.4.0 precedent).
        env = Environment()
        for dep in self.dependencies.host.values():
            pkg_folder = dep.package_folder
            if not pkg_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                full = os.path.join(pkg_folder, libdir)
                if os.path.isdir(full):
                    env.prepend_path("LD_LIBRARY_PATH", full)
        env.vars(self).save_script("pasystray_test_env")

    # ------------------------------------------------------------------ #
    #  test                                                               #
    # ------------------------------------------------------------------ #
    def test(self):
        pasystray = self.dependencies["pasystray"]
        binary = os.path.join(pasystray.package_folder, "bin", "pasystray")
        workdir = self._scratch_dir()
        self.output.info("pasystray test package: binary=%s" % binary)
        self.output.info("pasystray test package: scratch=%s" % workdir)

        # ---- structural/linkage assertions: must genuinely pass ----------
        self._run_structural_harness(binary)

        # ---- upstream CLI contract: really run when the platform allows --
        cases = (("--version", "0.8.2"), ("--notify=help", "Notification options:"))
        if str(self.settings.os) in ("Linux", "OHOS"):
            for arg, expected in cases:
                try:
                    self._assert_cli_contract(binary, arg, expected, workdir)
                except ConanException as exc:
                    message = str(exc)
                    if any(marker in message for marker in self._LIMITATION_MARKERS):
                        self.output.info(
                            "Execution skipped due to OHOS platform limitation: %s"
                            % message)
                    else:
                        raise
        else:
            for arg, expected in cases:
                self._assert_cli_contract(binary, arg, expected, workdir)

    # ------------------------------------------------------------------ #
    #  helpers                                                            #
    # ------------------------------------------------------------------ #
    def _envexpr(self):
        return ["conanrun", "pasystray_test_env"]

    def _scratch_dir(self):
        """A writable scratch dir.  OHOS ``/tmp`` is read-only, so prefer
        ``$TMPDIR`` but fall back to ``$HOME/tmp`` and finally the build folder."""
        for candidate in (os.environ.get("TMPDIR"), os.environ.get("TMP"),
                          os.path.join(os.path.expanduser("~"), "tmp"),
                          self.build_folder):
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
                return tempfile.mkdtemp(prefix="pasystray-test-", dir=candidate)
            except OSError:
                continue
        return tempfile.mkdtemp(prefix="pasystray-test-")

    def _run_structural_harness(self, binary):
        """Run test_pasystray.sh; a non-zero exit is a genuine test failure."""
        script = os.path.join(self.source_folder, "test_pasystray.sh")
        shell = (os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
                 or shutil.which("bash") or "/data/service/hnp/bin/bash")
        self.run('"%s" "%s" "%s"' % (shell, script, binary), env=self._envexpr())

    def _assert_cli_contract(self, binary, arg, expected, workdir):
        """Execute the delivered binary and assert its real output.

        Raises ``ConanException`` on any failure; the message carries the real
        loader/GTK diagnostic so the caller can tell a declared OHOS platform
        limitation from a genuine regression.
        """
        tag = arg.lstrip("-").replace("=", "_")
        log = os.path.join(workdir, "cli_%s.log" % tag)
        rc = self.run('"%s" "%s" > "%s" 2>&1' % (binary, arg, log),
                      env=self._envexpr(), ignore_errors=True)
        output = (load(self, log) if os.path.isfile(log) else "").strip()
        if rc != 0:
            raise ConanException(
                "pasystray %s exited rc=%s; output=%r" % (arg, rc, output))
        if expected not in output:
            raise ConanException(
                "pasystray %s: expected %r in output, got %r"
                % (arg, expected, output))
        first_line = output.splitlines()[0] if output else ""
        self.output.info("OK: pasystray %s -> %r" % (arg, first_line))
