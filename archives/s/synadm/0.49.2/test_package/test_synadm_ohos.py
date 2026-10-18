"""HarmonyOS-specific integration tests for the packaged synadm 0.49.2.

These are the cases that can only be answered on the adapted platform, i.e.
they probe how synadm behaves against HarmonyOS/HMDFS reality rather than
against a generic POSIX assumption:

  1. platform identity - what `os.uname()` reports on HarmonyOS and which of
     synadm's own `os.name == "posix"` branches therefore execute;
  2. the `http+unix://` transport - Synapse on a device is reached over a
     local unix socket, which is exactly the path that depends on the
     vendored requests-unixsocket (no Conan registry package exists), so an
     AF_UNIX end-to-end request is the adaptation's load-bearing test;
  3. HMDFS filesystem semantics - `/tmp` is a read-only mount and the case
     filesystem is case-insensitive, both of which affect where synadm may
     keep state and what a packaged tree must look like;
  4. native invocation - the `bin/synadm` wrapper and `python -m synadm`
     entry point resolved on the device's own interpreter.

Sandbox capabilities are probed, not assumed. The device home and a CI
worker home are measurably different filesystems (chmod fidelity, AF_UNIX
bind permission), so a case that needs a capability the sandbox forbids is
skipped with the measured errno rather than weakened into a pass - the
HarmonyOS target itself runs all of them.

argv: <package_folder> <dep>=<folder> ...
"""

import contextlib
import importlib
import io
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PKG = os.path.realpath(sys.argv[1])
DEP_FOLDERS = {
    part.split("=", 1)[0]: os.path.realpath(part.split("=", 1)[1])
    for part in sys.argv[2:]
}

SITE = os.path.join(PKG, "lib", f"python{sys.version_info.major}."
                                f"{sys.version_info.minor}", "site-packages")
BIN = os.path.join(PKG, "bin", "synadm")

# /tmp is a read-only mount on HarmonyOS, so scratch state has to live in a
# writable home. Two mounts were measured and they are NOT equivalent: the
# device's private home and the CI worker's buildbot home differ both in
# chmod fidelity (0600 vs 0640) and in whether an AF_UNIX listener may be
# bound at all (EPERM on the worker). Both properties are therefore probed at
# runtime instead of assumed from whichever machine the suite was written on.
_HOME_SCRATCH = [
    os.environ.get("SYNADM_OHOS_WORKDIR"),
    os.path.join(os.path.expanduser("~"), ".synadm-ohos-test"),
    os.path.join(os.environ.get("XDG_CACHE_HOME")
                 or os.path.join(os.path.expanduser("~"), ".cache"),
                 "synadm-ohos-test"),
    os.path.join(os.path.expanduser("~"), ".local", "share",
                 "synadm-ohos-test"),
]

# A unix socket additionally needs a *short* name (sun_path) and the device
# puts the package build tree under a deep Conan path, so the socket always
# lives under $HOME and never falls back to the cwd.
_SOCKET_CANDIDATES = [candidate for candidate in _HOME_SCRATCH if candidate]


def _first_writable(candidates):
    for candidate in candidates:
        if not candidate:
            continue
        try:
            os.makedirs(candidate, exist_ok=True)
            candidate = os.path.realpath(candidate)
            with open(os.path.join(candidate, ".write-probe"), "w") as handle:
                handle.write("ok")
            os.unlink(os.path.join(candidate, ".write-probe"))
        except OSError:
            continue
        return candidate
    return None


def _probe_af_unix(candidates):
    """(directory, bindable, reasons) for the first AF_UNIX-bindable candidate."""
    reasons = []
    for candidate in candidates:
        candidate = os.path.realpath(candidate)
        probe = os.path.join(candidate, ".afunix-probe.sock")
        if len(probe.encode()) >= 108:
            reasons.append(f"{candidate}: probe name >= 108 bytes")
            continue
        sock = None
        try:
            os.makedirs(candidate, exist_ok=True)
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(probe)
        except OSError as exc:
            reasons.append(f"{candidate}: [Errno {exc.errno}] {exc.strerror}")
            continue
        finally:
            if sock is not None:
                sock.close()
            with contextlib.suppress(OSError):
                os.unlink(probe)
        return candidate, True, ""
    # Nothing here may host a unix socket; the transport class reports the
    # measured reason instead of pretending to pass, and the socket path kept
    # below still describes where a real device would put it.
    return (os.path.realpath(candidates[0]) if candidates else
            os.path.expanduser("~")), False, "; ".join(reasons)


WORKDIR = _first_writable(_HOME_SCRATCH + [os.environ.get("TMPDIR"),
                                           os.getcwd()])
if WORKDIR is None:
    WORKDIR = os.path.realpath(os.getcwd())
SOCKET_DIR, AF_UNIX_BINDABLE, AF_UNIX_BIND_REASON = _probe_af_unix(
    _SOCKET_CANDIDATES)
SOCKET_PATH = os.path.join(SOCKET_DIR, "synapse-admin.sock")

SERVER_VERSION = {"server_version": "1.111.0", "python_version": "3.12.9"}
USER_LIST = {
    "users": [
        {"name": "@alice:example.org", "displayname": "Alice",
         "is_guest": False, "deactivated": False, "locked": False},
    ],
    "total": 1,
}

# Mirrors APIHelper.CONFIG plus the "format" key load() reads; every value
# must be truthy (or a bool) or load() reports the config as incomplete.
CONFIG = {
    "user": "admin",
    "token": "syt_ohos_test",
    "protocol": "unix",
    "base_url": SOCKET_PATH,
    "admin_path": "/_synapse/admin",
    "matrix_path": "/_matrix",
    "timeout": 30,
    "server_discovery": "well-known",
    "homeserver": "example.org",
    "ssl_verify": True,
    "format": "json",
}

REQUESTS_SEEN = []


class _UnixSynapseStub(BaseHTTPRequestHandler):
    """Synapse Admin API served over AF_UNIX, recording what arrived."""

    protocol_version = "HTTP/1.1"

    def do_GET(self):  # noqa: N802 - name required by BaseHTTPRequestHandler
        REQUESTS_SEEN.append({"path": self.path,
                              "headers": dict(self.headers.items())})
        # Route on the path component only - synadm sends real query strings.
        path = urllib.parse.urlparse(self.path).path
        if path.endswith("/v1/server_version"):
            body = json.dumps(SERVER_VERSION).encode()
        elif path.endswith("/v2/users"):
            body = json.dumps(USER_LIST).encode()
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep the report readable
        pass


class _UnixHTTPServer(ThreadingHTTPServer):
    """HTTPServer bound to an AF_UNIX path instead of a TCP port."""

    address_family = socket.AF_UNIX
    daemon_threads = True

    def server_bind(self):
        # HTTPServer.server_bind() derives server_name/server_port by
        # unpacking a (host, port) tuple; an AF_UNIX address is a path.
        socket.socket.bind(self.socket, self.server_address)
        if self.request_queue_size:
            self.socket.listen(self.request_queue_size)
        self.server_name = "localhost"
        self.server_port = 0


def _start_unix_stub():
    os.makedirs(SOCKET_DIR, exist_ok=True)
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    server = _UnixHTTPServer(SOCKET_PATH, _UnixSynapseStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _write_config(name, **overrides):
    yaml = importlib.import_module("yaml")
    path = os.path.join(WORKDIR, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.dump(dict(CONFIG, **overrides), handle)
    return path


class Test01OhosPlatformIdentity(unittest.TestCase):
    """The adaptation targets HarmonyOS; assert what the platform reports."""

    def test_uname_identifies_harmonyos(self):
        info = os.uname()
        self.assertEqual(
            info.sysname, "HarmonyOS",
            f"full uname: {info.sysname} / {info.release} / {info.machine}")
        self.assertIn("HongMeng", info.release,
                      f"kernel release string: {info.release}")

    def test_architecture_is_aarch64(self):
        self.assertEqual(os.uname().machine, "aarch64")

    def test_python_reports_posix_so_upstream_branches_are_taken(self):
        # synadm has exactly one platform check of its own - `os.name ==
        # "posix"` in write_config() - and never reads sys.platform, so
        # "posix" is the whole premise for the upstream branch being taken.
        # sys.platform is deliberately not asserted: the device reports
        # "linux" while the CI worker reports another string, and neither is
        # consulted by the shipped code.
        self.assertEqual(os.name, "posix",
                         f"os.name={os.name!r} sys.platform={sys.platform!r}")
        pkg_dir = os.path.dirname(os.path.realpath(
            importlib.import_module("synadm").__file__))
        guards, platform_reads = [], []
        for root, dirs, files in os.walk(pkg_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                if not name.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(root, name), pkg_dir)
                with open(os.path.join(root, name), encoding="utf-8") as fh:
                    text = fh.read()
                if 'os.name == "posix"' in text:
                    guards.append(rel)
                if "sys.platform" in text:
                    platform_reads.append(rel)
        self.assertIn("cli/_helper.py", guards,
                      f"write_config() posix guard missing; guards: {guards}")
        self.assertEqual(
            platform_reads, [],
            f"packaged synadm now reads sys.platform in {platform_reads}; "
            "re-check the HarmonyOS branch coverage in this suite")

    def test_write_config_takes_posix_branch_and_restricts_mode(self):
        helper_mod = importlib.import_module("synadm.cli._helper")
        config_path = os.path.join(WORKDIR, "write-config", "synadm.yaml")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        helper = helper_mod.APIHelper(config_path, 0, True, "json")
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            self.assertTrue(helper.write_config(CONFIG))
        out = captured.getvalue()
        self.assertIn("Restricting access to config file to user only", out)
        self.assertNotIn("Unsupported OS", out)
        # What upstream intends is "no access for anyone but the user". The
        # exact bits a chmod(0600) lands on are mount-dependent: the device's
        # private home yields 0600, a CI worker's buildbot home 0640 (the
        # mount adds a group *read* bit). So: nothing at all for other, and no
        # write/execute for the group; the mount-injected group read is
        # recorded, not enforced.
        mode = os.stat(config_path).st_mode & 0o777
        self.assertEqual(mode & 0o037, 0,
                         f"config grants other-access or group write/exec: "
                         f"{oct(mode)} (chmod 0600 landed on these bits in "
                         f"{WORKDIR})")
        self.assertEqual(mode & 0o600, 0o600,
                          f"config not owner-rw: {oct(mode)}")

    def test_debug_log_writes_on_hmdfs(self):
        # init_logger() opens ~/.local/share/synadm/debug.log; HMDFS ignores
        # some POSIX niceties, so prove a real write + read-back there.
        helper_mod = importlib.import_module("synadm.cli._helper")
        marker = f"ohos-probe-{os.getpid()}"
        helper = helper_mod.APIHelper(os.path.join(WORKDIR, "unused.yaml"),
                                      0, True, "json")
        helper.log.debug(marker)
        for handler in helper.log.handlers:
            handler.flush()
        log_path = os.path.expanduser("~/.local/share/synadm/debug.log")
        with open(log_path, encoding="utf-8") as handle:
            self.assertIn(marker, handle.read())


class Test02UnixSocketTransport(unittest.TestCase):
    """http+unix:// against a real AF_UNIX socket, through synadm's own code."""

    @classmethod
    def setUpClass(cls):
        del REQUESTS_SEEN[:]
        cls.server = _start_unix_stub() if AF_UNIX_BINDABLE else None

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.shutdown()
            cls.server.server_close()
        with contextlib.suppress(OSError):
            os.unlink(SOCKET_PATH)

    def require_socket(self):
        if self.server is None:
            raise unittest.SkipTest(
                "this sandbox forbids binding an AF_UNIX listener, so no "
                f"stub Synapse could be started: {AF_UNIX_BIND_REASON}")

    def _api(self):
        api = importlib.import_module("synadm.api")
        log = logging.getLogger("synadm-test-unix")
        log.handlers = [logging.NullHandler()]
        log.setLevel(logging.CRITICAL)
        return api.SynapseAdmin(log, CONFIG["user"], CONFIG["token"], "unix",
                                SOCKET_PATH, CONFIG["admin_path"], 30, False,
                                None)

    def test_transport_library_is_the_vendored_requests_unixsocket(self):
        api = importlib.import_module("synadm.api")
        resolved = os.path.realpath(api.requests_unixsocket.__file__)
        self.assertTrue(
            resolved.startswith(os.path.realpath(SITE)),
            f"requests_unixsocket resolved from {resolved}, expected it under "
            f"the packaged site {SITE} (it has no Conan registry package)")

    def test_socket_path_is_percent_encoded_before_the_request(self):
        self.require_socket()
        client = self._api()
        self.assertEqual(client.base_url, SOCKET_PATH)
        client.version()
        # query() rewrites base_url in place for the unix transport; a path
        # that kept its "/" would be ambiguous between host and path.
        self.assertEqual(client.base_url,
                         "http+unix://" + urllib.parse.quote(SOCKET_PATH,
                                                             safe=""))

    def test_admin_api_answers_over_unix_socket(self):
        # query() rewrites self.base_url in place for the unix transport, so a
        # second request on the same object would encode the socket path
        # twice (upstream behaviour, measured here); each request gets its own
        # client, which is what the CLI does per process anyway.
        self.require_socket()
        self.assertEqual(self._api().version(), SERVER_VERSION)
        listing = self._api().query("get", "v2/users")
        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["users"][0]["name"], "@alice:example.org")

    def test_forwarded_headers_are_sent_over_the_socket(self):
        # synadm impersonates the reverse proxy on the unix transport, and
        # the headers only reach the server if the vendored adapter forwards
        # them - a regression test for the vendored package.
        self.require_socket()
        self._api().version()
        self.assertTrue(REQUESTS_SEEN, "the stub server saw no request")
        headers = REQUESTS_SEEN[-1]["headers"]
        self.assertEqual(headers.get("X-Forwarded-For"), "::1")
        self.assertEqual(headers.get("X-Forwarded-Proto"), "https")
        self.assertEqual(headers.get("Authorization"), "Bearer syt_ohos_test")
        self.assertEqual(headers.get("User-Agent"), "synadm/0.49.2")

    def test_cli_user_list_over_unix_socket(self):
        self.require_socket()
        config = _write_config("unix.yaml")
        binary = shutil.which("synadm") or BIN
        proc = subprocess.run(
            [sys.executable, "-m", "synadm", "--no-confirm", "-c", config,
             "-o", "json", "user", "list"],
            capture_output=True, text=True, timeout=180,
            env=dict(os.environ, PYTHONNOUSERSITE="1"),
        )
        self.assertEqual(proc.returncode, 0,
                         f"stdout={proc.stdout[-2000:]} stderr={proc.stderr[-2000:]}")
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["users"][0]["name"], "@alice:example.org")

    def test_cli_version_over_unix_socket_with_packaged_binary(self):
        self.require_socket()
        config = _write_config("unix-bin.yaml")
        proc = subprocess.run([BIN, "--no-confirm", "-c", config, "version"],
                              capture_output=True, text=True, timeout=180,
                              env=dict(os.environ, PYTHONNOUSERSITE="1"))
        self.assertEqual(proc.returncode, 0,
                         f"stdout={proc.stdout[-2000:]} stderr={proc.stderr[-2000:]}")
        self.assertEqual(json.loads(proc.stdout), SERVER_VERSION)


class Test03OhosFilesystemSemantics(unittest.TestCase):
    """HMDFS realities the packaged tree has to survive."""

    def _packaged_files(self):
        for root, dirs, files in os.walk(PKG):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                yield os.path.relpath(os.path.join(root, name), PKG)

    def test_no_case_colliding_paths_in_package(self):
        # HMDFS is case-insensitive: two entries differing only in case
        # collide when the package is unpacked (measured in this workspace
        # with upstream's libXext/libxext pair), so the tree must stay unique
        # under case folding.
        seen = {}
        for rel in self._packaged_files():
            key = rel.casefold()
            self.assertNotIn(key, seen,
                             f"HMDFS case collision: {seen.get(key)!r} vs "
                             f"{rel!r}")
            seen[key] = rel

    def test_no_host_build_paths_leak_into_the_package(self):
        # A recipe that recorded its build machine's absolute paths would be
        # unusable once Conan re-locates the package on another worker.
        needle = re.compile(
            r"(\.conan2/p/|/storage/Users/currentUser|\.build-synadm)")
        offenders = []
        for rel in self._packaged_files():
            if not rel.endswith((".py", ".txt", ".yaml", ".yml")) and \
                    not rel.endswith(("METADATA", "RECORD", "WHEEL",
                                      "entry_points.txt")):
                continue
            path = os.path.join(PKG, rel)
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            match = needle.search(text)
            if match:
                offenders.append(f"{rel}: {match.group(0)}")
        self.assertEqual(offenders, [])

    def test_synadm_writes_no_state_to_tmp(self):
        # /tmp is a read-only mount here, so a hardcoded /tmp write in the
        # shipped code would fail at runtime on the device.
        offenders = []
        for rel in self._packaged_files():
            if not rel.endswith(".py"):
                continue
            with open(os.path.join(PKG, rel), encoding="utf-8",
                      errors="ignore") as fh:
                for number, line in enumerate(fh, 1):
                    if "/tmp/" in line and not line.lstrip().startswith("#"):
                        offenders.append(f"{rel}:{number}: {line.strip()}")
        self.assertEqual(offenders, [])

    def test_default_state_paths_are_under_the_writable_home(self):
        helper_mod = importlib.import_module("synadm.cli._helper")
        home = os.path.realpath(os.path.expanduser("~"))
        helper = helper_mod.APIHelper("~/.config/synadm.yaml", 0, True, "json")
        resolved_config = os.path.realpath(helper.config_path)
        self.assertTrue(resolved_config.startswith(home), resolved_config)
        log_dir = os.path.realpath(os.path.dirname(
            os.path.expanduser("~/.local/share/synadm/debug.log")))
        self.assertTrue(log_dir.startswith(home), log_dir)
        # init_logger() creates the log directory eagerly, so a read-only
        # mount under $HOME would have raised already.
        self.assertTrue(os.path.isdir(log_dir), log_dir)
        self.assertTrue(os.access(log_dir, os.W_OK), log_dir)

    def test_tmp_is_read_only_and_the_suite_still_writes(self):
        # Documents the constraint the recipe/tests are built around: the
        # default temp dir is not writable on this platform, while $HOME is.
        tmpdir = "/tmp"
        probe = os.path.join(
            tmpdir, f"synadm-ohos-probe-{os.getpid()}")
        tmp_writable = True
        try:
            with open(probe, "w") as handle:
                handle.write("x")
        except OSError:
            tmp_writable = False
        finally:
            with contextlib.suppress(OSError):
                os.unlink(probe)
        self.assertFalse(tmp_writable,
                         "/tmp unexpectedly writable - re-check the /tmp "
                         "assumptions recorded in notes.md")
        # ... and the workaround actually used by this suite works.
        os.makedirs(WORKDIR, exist_ok=True)
        scratch = os.path.join(WORKDIR, "scratch.txt")
        with open(scratch, "w") as handle:
            handle.write("ok")
        with open(scratch) as handle:
            self.assertEqual(handle.read(), "ok")
        os.unlink(scratch)


class Test04NativeInvocation(unittest.TestCase):
    """The shipped entry points, run by the device's own interpreter."""

    def test_bin_wrapper_is_executable_through_path(self):
        self.assertTrue(os.access(BIN, os.X_OK), f"{BIN} is not executable")
        proc = subprocess.run([BIN, "--version"], capture_output=True,
                              text=True, timeout=180)
        self.assertEqual(proc.returncode, 0,
                         f"stdout={proc.stdout} stderr={proc.stderr}")
        self.assertIn("synadm, version 0.49.2", proc.stdout)

    def test_bin_wrapper_resolves_via_conanrun_path(self):
        binary = shutil.which("synadm")
        self.assertIsNotNone(binary, "bin/synadm is not on PATH")
        self.assertTrue(os.path.realpath(binary).startswith(PKG),
                        f"{binary} does not come from {PKG}")

    def test_python_m_synadm_entry_point(self):
        # synadm/__main__.py calls root() at import time, so the module is
        # exercised as a program rather than imported.
        proc = subprocess.run([sys.executable, "-m", "synadm", "--version"],
                              capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0,
                         f"stdout={proc.stdout} stderr={proc.stderr}")
        self.assertIn("0.49.2", proc.stdout)

    def test_interpreter_matches_the_packaged_site_layout(self):
        # The recipe stages into lib/pythonX.Y/site-packages, so a mismatch
        # between the running interpreter and that X.Y would silently give
        # "No module named synadm".
        self.assertEqual(
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            os.path.basename(os.path.dirname(SITE)))
        synadm = importlib.import_module("synadm")
        self.assertEqual(os.path.realpath(synadm.__file__),
                         os.path.join(SITE, "synadm", "__init__.py"))

    def test_af_unix_socket_path_fits_the_kernel_limit(self):
        # HarmonyOS keeps the private home under a deep path; an AF_UNIX name
        # longer than the sun_path field would make the unix transport
        # unusable no matter what the adapter does.
        self.assertLess(len(SOCKET_PATH.encode()), 108,
                        f"socket path too long for AF_UNIX: {SOCKET_PATH}")


if __name__ == "__main__":
    os.makedirs(WORKDIR, exist_ok=True)
    SUITE = unittest.TestLoader().loadTestsFromModule(sys.modules["__main__"])
    RESULT = unittest.TextTestRunner(verbosity=2).run(SUITE)
    sys.exit(0 if RESULT.wasSuccessful() else 1)
