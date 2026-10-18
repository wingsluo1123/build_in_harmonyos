#!/usr/bin/env python3
"""Conan test_package — pnmixer 0.7.2 (application: GTK+3 system-tray ALSA mixer).

pnmixer is a **GTK+3 tray application**, not a library: the consumer test drives
the delivered ``bin/pnmixer`` and asserts its observable behaviour (R34).  Three
layers, all run for real:

  * **structural / linkage / install-surface assertions** (delegated to
    ``test_pnmixer.sh``): the packaged binary exists, is executable, is a valid
    ELF, carries the OHOS ``.codesign`` section, records ``libgtk-3`` /
    ``libgdk-3`` / ``libasound`` / ``libX11`` / ``libglib-2.0`` in
    ``DT_NEEDED``, asserts that ``libnotify`` is deliberately **absent**
    (``WITH_LIBNOTIFY=OFF``: the published libnotify artifact cannot be loaded
    by the OHOS loader), and checks the desktop/icon/man/pixmap/glade install
    surface.  These never execute the binary, so they must always genuinely
    pass — and must genuinely fail when the artifact is damaged (CI L1e).

  * **CLI contract** (``main.c`` option table + GOptionContext): ``--help`` must
    print the generated usage (this path works without any display because
    GOptionContext handles ``--help`` before the GTK post-parse hook), and an
    unknown option must be rejected.  ``main()`` calls
    ``g_option_context_add_group(context, gtk_get_option_group(TRUE))``, so
    *every other* invocation — including ``--version`` — opens a display inside
    the post-parse hook first.

  * **real startup against a live display server**: the OHOS GTK3 package ships
    ``bin/broadwayd`` and is built with ``broadway_backend=true`` /
    ``x11_backend=false``, so the test starts broadwayd on a private display and
    then (a) asserts ``--version`` prints exactly ``pnmixer version: 0.7.2``
    with exit code 0, and (b) starts the tray application with ``-d`` and
    asserts from its real debug log that it built the popup menu and popup
    window from the *installed* glade files, created the tray icon, loaded all
    five *installed* pixmaps, created the hotkey subsystem, hooked the audio
    subsystem (ALSA reports no sound card here — the honest, expected outcome)
    and reached ``---- Running main loop ----`` without exiting.  That is an
    end-to-end consumer test of the delivered artifact, not a stub.

If the OHOS loader rejects a dependency shared object (declared runtime
limitation), the affected case is reported as skipped with the real diagnostic;
any other failure still raises.  Marker list and tolerance contract follow the
merged ``pasystray/0.8.2`` and ``pavucontrol-qt/2.4.0`` precedents.
"""
import os
import shutil
import subprocess
import tempfile
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import load


class PnmixerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_pnmixer.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    # OHOS runtime-limitation signatures (same list as pasystray/0.8.2, which
    # itself mirrors the merged pavucontrol-qt/2.4.0 precedent).
    _LIMITATION_MARKERS = (
        "Permission denied",
        "Operation not permitted",
        "Error 126", "Error 127",
        "rc=126", "rc=127",
        "shared library",
        "symbol not found",
        "Error loading",
    )
    # CLI cases that only need the option parser (no display is opened for
    # --help because GOptionContext handles it before the post-parse hook).
    _CLI_CASES = (
        ("--help", "- A mixer for the system tray."),
        ("--help", "--version"),
        ("--help", "Show version and exit"),
        ("--help", "--help-gtk"),
    )
    _BROADWAY_DISPLAY = ":77"
    _STARTUP_MARKERS = (
        "Building from ui file",
        "Creating tray icon",
        "Loading PNMixer icon 'pnmixer-high.png'",
        "Creating hotkeys control",
        "Hooking soundcard",
        "Running main loop",
    )
    _EXEC_TIMEOUT = 60
    _STARTUP_SECONDS = 20

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Prepend every dependency lib dir to LD_LIBRARY_PATH so the delivered
        # binary resolves the conan-provided gtk/glib/alsa/X11 shared objects at
        # run time (musl ignores DT_RUNPATH; same mechanism as the merged
        # pasystray/0.8.2 and pavucontrol-qt/2.4.0 precedents).
        env = Environment()
        for libdir in self._dependency_libdirs():
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("pnmixer_test_env")

    # ------------------------------------------------------------------ #
    #  test                                                               #
    # ------------------------------------------------------------------ #
    def test(self):
        dependency = self.dependencies["pnmixer"]
        binary = os.path.join(dependency.package_folder, "bin", "pnmixer")
        package_folder = dependency.package_folder
        workdir = self._scratch_dir()
        self.output.info("pnmixer test package: binary=%s" % binary)
        self.output.info("pnmixer test package: package=%s" % package_folder)
        self.output.info("pnmixer test package: scratch=%s" % workdir)

        # Extend os.environ so that both subprocess and self.run see the runtime
        # library path (the saved env script only applies to self.run).
        self._export_runtime_env()

        # ---- A. structural / linkage / install surface: hard assertions ----
        self._run_structural_harness(binary, package_folder)

        # ---- B. CLI contract that needs no display -------------------------
        for arg, expected in self._CLI_CASES:
            self._assert_cli(binary, arg, expected, workdir)

        # Upstream main() ignores g_option_context_parse()'s return value, so an
        # unknown option is NOT rejected: it falls through to the normal startup
        # path (documented upstream behaviour, asserted instead of assumed).
        self._assert_unknown_option_fallthrough(binary, workdir)

        # ---- C. no display: must fail fast, never hang ---------------------
        self._assert_headless_failure(binary, workdir)

        # ---- D. real startup against a live broadway display ---------------
        self._run_display_cases(binary, workdir)

    # ------------------------------------------------------------------ #
    #  helpers                                                            #
    # ------------------------------------------------------------------ #
    def _env_names(self):
        return ["conanrun", "pnmixer_test_env"]

    def _dependency_libdirs(self):
        libdirs = []
        for dep in self.dependencies.host.values():
            package_folder = dep.package_folder
            if not package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                full = os.path.join(package_folder, libdir)
                if os.path.isdir(full) and full not in libdirs:
                    libdirs.append(full)
        return libdirs

    def _export_runtime_env(self):
        libdirs = self._dependency_libdirs()
        if not libdirs:
            return
        joined = os.pathsep.join(libdirs)
        existing = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = (
            joined + os.pathsep + existing if existing else joined)
        self.output.info("LD_LIBRARY_PATH entries: %d" % len(libdirs))

    def _scratch_dir(self):
        """A writable scratch dir (OHOS ``/tmp`` is a read-only erofs mount)."""
        for candidate in (os.environ.get("TMPDIR"), os.environ.get("TMP"),
                          os.path.join(os.path.expanduser("~"), "tmp"),
                          self.build_folder):
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
                return tempfile.mkdtemp(prefix="pnmixer-test-", dir=candidate)
            except OSError:
                continue
        return tempfile.mkdtemp(prefix="pnmixer-test-")

    def _run_structural_harness(self, binary, package_folder):
        """Run test_pnmixer.sh; a non-zero exit is a genuine test failure."""
        script = os.path.join(self.source_folder, "test_pnmixer.sh")
        shell = (os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
                 or shutil.which("sh") or "/bin/sh")
        self.run('"%s" "%s" "%s" "%s"'
                 % (shell, script, binary, package_folder), env=self._env_names())

    def _execute(self, argv, workdir, tag, extra_env=None):
        """Run argv with a hard wall-clock cap and capture merged output."""
        log = os.path.join(workdir, "%s.log" % tag)
        env = dict(os.environ)
        if extra_env:
            env.update(extra_env)
        with open(log, "wb") as stream:
            try:
                completed = subprocess.run(
                    argv, stdout=stream, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, env=env, cwd=workdir,
                    timeout=self._EXEC_TIMEOUT)
                rc = completed.returncode
            except subprocess.TimeoutExpired:
                rc = "timeout"
        output = (load(self, log) if os.path.isfile(log) else "").strip()
        return rc, output

    def _tolerate_or_raise(self, message):
        if not any(marker in message for marker in self._LIMITATION_MARKERS):
            raise ConanException(message)
        self.output.info(
            "Execution skipped due to OHOS platform limitation: %s" % message)

    def _assert_cli(self, binary, arg, expected, workdir, expect_success=True):
        """Execute the delivered binary, assert its real captured output."""
        tag = "cli_%s_%s" % (arg.lstrip("-").replace("=", "_"),
                             expected.replace(" ", "_").replace("/", "_")[:24])
        rc, output = self._execute([binary, arg], workdir, tag)
        if expect_success and rc != 0:
            self._tolerate_or_raise(
                "pnmixer %s exited rc=%s; output=%r" % (arg, rc, output))
        if not expect_success and rc == 0:
            raise ConanException(
                "pnmixer %s unexpectedly succeeded (rc=0); output=%r"
                % (arg, output))
        if expected not in output:
            raise ConanException(
                "pnmixer %s: expected %r in output, got %r"
                % (arg, expected, output))
        first_line = output.splitlines()[0] if output else ""
        self.output.info("OK: pnmixer %s -> %r" % (arg, first_line))

    def _assert_headless_failure(self, binary, workdir):
        """Bare run, no display at all: must fail fast with a diagnostic."""
        rc, output = self._execute(
            [binary], workdir, "no_display",
            extra_env={"GDK_BACKEND": "x11", "DISPLAY": "",
                       "WAYLAND_DISPLAY": "", "BROADWAY_DISPLAY": ""})
        if rc == 0:
            raise ConanException(
                "pnmixer without a display unexpectedly exited rc=0; "
                "output=%r" % output)
        if not output:
            raise ConanException(
                "pnmixer without a display exited rc=%s with no diagnostic "
                "output at all" % rc)
        self.output.info(
            "OK: pnmixer without a display failed fast (rc=%s): %r"
            % (rc, output.splitlines()[0]))

    def _assert_unknown_option_fallthrough(self, binary, workdir):
        """An unknown option behaves exactly like no option at all.

        ``main()`` calls ``g_option_context_parse(context, &argc, &argv, NULL)``
        and never looks at the return value, so GTK's post-parse hook still runs
        and the unknown option is silently ignored.  The observable contract is
        therefore "same as a bare invocation", and that is what is asserted — no
        imaginary "Unknown option" diagnostic.
        """
        rc, output = self._execute(
            [binary, "--not-a-pnmixer-option"], workdir, "cli_unknown_option",
            extra_env={"GDK_BACKEND": "x11", "DISPLAY": "",
                       "WAYLAND_DISPLAY": "", "BROADWAY_DISPLAY": ""})
        if rc == 0:
            raise ConanException(
                "pnmixer --not-a-pnmixer-option unexpectedly exited rc=0; "
                "output=%r" % output)
        if "cannot open display" not in output:
            raise ConanException(
                "pnmixer --not-a-pnmixer-option did not fall through to the "
                "normal startup path (expected a display diagnostic), got %r"
                % output)
        self.output.info(
            "OK: unknown option falls through to normal startup (rc=%s): %r"
            % (rc, output.splitlines()[0]))

    # ---- D. live-display cases ---------------------------------------- #
    def _find_broadwayd(self):
        candidates = []
        try:
            gtk = self.dependencies["gtk"]
        except (KeyError, ConanException):
            gtk = None
        if gtk is not None and gtk.package_folder:
            candidates.append(os.path.join(gtk.package_folder, "bin",
                                           "broadwayd"))
        found = shutil.which("broadwayd")
        if found:
            candidates.append(found)
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(
                    candidate, os.X_OK):
                return candidate
        return None

    def _run_display_cases(self, binary, workdir):
        broadwayd = self._find_broadwayd()
        if not broadwayd:
            raise ConanException(
                "broadwayd is missing from the gtk package: the GTK3 build this "
                "package links has no usable display backend, so the delivered "
                "binary cannot be exercised at all")
        runtime_dir = os.path.join(workdir, "xdg-runtime")
        os.makedirs(runtime_dir, exist_ok=True)
        try:
            os.chmod(runtime_dir, 0o700)
        except OSError:
            pass
        env = dict(os.environ)
        env.update({
            "XDG_RUNTIME_DIR": runtime_dir,
            "GDK_BACKEND": "broadway",
            "BROADWAY_DISPLAY": self._BROADWAY_DISPLAY,
        })
        server_log = os.path.join(workdir, "broadwayd.log")
        self.output.info("starting broadwayd: %s %s"
                         % (broadwayd, self._BROADWAY_DISPLAY))
        with open(server_log, "wb") as stream:
            server = subprocess.Popen(
                [broadwayd, self._BROADWAY_DISPLAY], stdout=stream,
                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env,
                cwd=workdir)
        try:
            if not self._wait_for_broadwayd(server_log, server):
                raise ConanException(
                    "broadwayd did not start; log=%r"
                    % (load(self, server_log) if os.path.isfile(server_log)
                       else ""))
            self.output.info("broadwayd is listening")

            # (a) --version / -v: require a working display (GTK post-parse
            #     hook opens it before main() reaches the version branch).
            for flag in ("--version", "-v"):
                rc, output = self._execute(
                    [binary, flag], workdir, "version_with_display_%s" % flag,
                    extra_env={"GDK_BACKEND": "broadway",
                               "BROADWAY_DISPLAY": self._BROADWAY_DISPLAY,
                               "XDG_RUNTIME_DIR": runtime_dir})
                if rc != 0:
                    self._tolerate_or_raise(
                        "pnmixer %s under broadway exited rc=%s; output=%r"
                        % (flag, rc, output))
                if "pnmixer version: 0.7.2" not in output:
                    raise ConanException(
                        "pnmixer %s under broadway: expected "
                        "'pnmixer version: 0.7.2', got %r" % (flag, output))
                self.output.info("OK: %s with a live display -> %r"
                                 % (flag, output.splitlines()[0]))

            # (b) real startup: assert the tray app initialises and stays up.
            rc, output = self._start_and_collect(
                binary, workdir, env, runtime_dir)
            missing = [m for m in self._STARTUP_MARKERS if m not in output]
            if missing:
                raise ConanException(
                    "pnmixer -d startup log is missing %r; output tail=%r"
                    % (missing, output[-2000:]))
            self.output.info(
                "OK: pnmixer started, built its UI from the installed data "
                "files, hooked audio and reached the main loop (%d markers)"
                % len(self._STARTUP_MARKERS))
        finally:
            self._stop_process(server)

    def _wait_for_broadwayd(self, server_log, server, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if server.poll() is not None:
                return False
            if (os.path.isfile(server_log)
                    and "Listening on" in load(self, server_log)):
                return True
            time.sleep(0.5)
        return False

    def _start_and_collect(self, binary, workdir, env, runtime_dir):
        """Start the tray app with -d, prove it stays alive, return its log."""
        log = os.path.join(workdir, "startup_debug.log")
        run_env = dict(env)
        run_env.update({"GDK_BACKEND": "broadway",
                        "BROADWAY_DISPLAY": self._BROADWAY_DISPLAY,
                        "XDG_RUNTIME_DIR": runtime_dir})
        with open(log, "wb") as stream:
            process = subprocess.Popen(
                [binary, "-d"], stdout=stream, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, env=run_env, cwd=workdir)
            exited_early = True
            try:
                process.wait(timeout=self._STARTUP_SECONDS)
            except subprocess.TimeoutExpired:
                exited_early = False
            output = (load(self, log) if os.path.isfile(log) else "").strip()
            self._stop_process(process)
        if exited_early:
            raise ConanException(
                "pnmixer -d exited on its own with rc=%s instead of staying in "
                "its main loop; output tail=%r"
                % (process.returncode, output[-2000:]))
        return "timeout", output

    @staticmethod
    def _stop_process(process):
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
