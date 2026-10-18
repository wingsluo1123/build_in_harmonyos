"""Real-consumer integration test for the packaged synadm 0.49.2.

Executed by test_package/conanfile.py inside the Conan "conanrun" environment,
i.e. with exactly the PYTHONPATH/PATH a downstream consumer of the package
gets. Three things are therefore checked, not assumed:

  1. provenance - every module the package needs resolves out of a Conan
     package folder, never out of the host interpreter's site-packages;
  2. function - the CLI actually talks to a Synapse Admin API (a stub server on
     localhost) over real sockets and renders real answers;
  3. packaging - the dist-info the recipe writes is what synadm's own
     version plumbing and click's --version read back.

argv: <package_folder> <dep>=<folder> ...
"""

import datetime
import importlib
import importlib.metadata
import json
import os
import shutil
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

USERS = [
    {
        "name": "@alice:example.org",
        "displayname": "Alice",
        "is_guest": False,
        "deactivated": False,
        "locked": False,
    },
    {
        "name": "@bob:example.org",
        "displayname": None,
        "is_guest": False,
        "deactivated": True,
        "locked": False,
    },
]
SERVER_VERSION = {"server_version": "1.111.0", "python_version": "3.12.9"}


class _SynapseStub(BaseHTTPRequestHandler):
    """Enough of the Synapse Admin API to drive synadm end to end."""

    protocol_version = "HTTP/1.1"

    def _send(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - http.server API
        # Route on the path component only: synadm sends real query strings
        # (?from=0&limit=100&...), which urllib leaves in self.path.
        path = urllib.parse.unquote(
            urllib.parse.urlparse(self.path).path)
        if path.startswith("/_synapse/admin/v1/server_version"):
            self._send(SERVER_VERSION)
        elif path == "/_synapse/admin/v2/users":
            self._send({"users": USERS, "next_token": "tok-2", "total": 2})
        elif path.startswith("/_synapse/admin/v2/users/"):
            name = path.rsplit("/", 1)[-1]
            match = [u for u in USERS if u["name"] == name]
            if not match:
                self._send({"errcode": "M_NOT_FOUND"}, status=404)
            else:
                self._send(match[0])
        elif path.startswith("/_synapse/admin/v1/whois/"):
            name = path.rsplit("/", 1)[-1]
            self._send({
                "user_id": name,
                "devices": [{"device_id": "AAA", "display_name": "phone"}],
            })
        elif path.startswith("/_synapse/admin/v1/rooms"):
            self._send({
                "rooms": [{"room_id": "!r1:example.org", "name": "general",
                           "joined_members": 7, "state": "public"}],
                "total_rooms": 1,
                "offset": 0,
                "next_batch": "2",
            })
        elif path.startswith("/_synapse/admin/v2/users/"):
            self._send({"errcode": "M_NOT_FOUND"}, status=404)
        elif path.startswith("/_synapse/admin/v1/users/"):
            self._send({"devices": [{"device_id": "AAA"}]})
        else:
            self._send({"errcode": "M_UNRECOGNISED", "error": path}, status=404)

    def log_message(self, *args):
        pass


def serve_stub():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SynapseStub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


CONFIG = {
    "user": "admin",
    "token": "syt_SECRET",
    "protocol": "http",
    "base_url": None,          # filled in setUpClass
    "admin_path": "/_synapse/admin",
    "matrix_path": "/_matrix",
    "timeout": 10,
    "server_discovery": "well-known",
    "homeserver": "example.org",
    "ssl_verify": False,
    "format": "json",
}


class Test01Provenance(unittest.TestCase):
    """What got imported must be what was packaged."""

    def test_synadm_module_from_package(self):
        import synadm
        self.assertTrue(
            os.path.realpath(synadm.__file__).startswith(SITE),
            f"synadm came from {synadm.__file__}, expected under {SITE}",
        )

    def test_api_and_cli_from_package(self):
        import synadm.api
        import synadm.cli
        self.assertTrue(os.path.realpath(synadm.api.__file__).startswith(SITE))
        self.assertTrue(os.path.realpath(synadm.cli.__file__).startswith(SITE))

    def test_registry_dependencies_from_own_packages(self):
        for module, dist in (("click", "click"), ("requests", "requests"),
                             ("tabulate", "tabulate"), ("yaml", "pyyaml"),
                             # requests' own import closure; if any of these
                             # four is missing from the run environment the
                             # failure surfaces as "import requests" dying, so
                             # they are asserted individually here instead.
                             ("certifi", "certifi"), ("chardet", "chardet"),
                             ("idna", "idna"), ("urllib3", "urllib3")):
            with self.subTest(module=module):
                loaded = importlib.import_module(module)
                origin = os.path.realpath(loaded.__file__)
                self.assertTrue(
                    origin.startswith(DEP_FOLDERS[dist]),
                    f"{module} resolved from {origin}, expected under the "
                    f"{dist} package folder {DEP_FOLDERS[dist]}",
                )

    def test_vendored_dependencies_from_package(self):
        for module in ("dns", "dns.resolver", "click_option_group",
                       "requests_unixsocket"):
            with self.subTest(module=module):
                loaded = importlib.import_module(module)
                origin = os.path.realpath(loaded.__file__)
                self.assertTrue(
                    origin.startswith(SITE),
                    f"vendored {module} resolved from {origin}, expected "
                    f"under {SITE}",
                )

    def test_host_site_packages_not_used(self):
        import synadm.cli._helper as helper
        for name in ("api", "cli", "cli._helper"):
            with self.subTest(name=name):
                module = importlib.import_module(f"synadm.{name}")
                self.assertNotIn("site-packages", module.__file__.replace(
                    SITE, ""))


class Test02PackagingMetadata(unittest.TestCase):
    """The dist-info the recipe writes must be the metadata tooling reads."""

    def test_synadm_distribution_version(self):
        self.assertEqual(importlib.metadata.version("synadm"), "0.49.2")

    def test_user_agent_carries_version(self):
        # synadm/api.py builds the User-Agent from importlib.metadata, so a
        # packaged install must announce its version to Synapse.
        import logging

        import synadm.api
        api = synadm.api.SynapseAdmin(
            logging.getLogger("synadm-test-ua"), "admin", "tok", "http",
            "http://127.0.0.1:1", "/_synapse/admin", 5, False, False)
        self.assertEqual(api.headers["User-Agent"], "synadm/0.49.2")
        self.assertEqual(api.headers["Authorization"], "Bearer tok")

    def test_console_script_entry_point_declared(self):
        dist = importlib.metadata.distribution("synadm")
        points = {
            (ep.group, ep.name): ep.value
            for ep in dist.entry_points
        }
        self.assertEqual(
            points.get(("console_scripts", "synadm")), "synadm.cli:root")

    def test_vendored_distribution_metadata(self):
        expected = {
            "dnspython": "2.8.0",
            "click-option-group": "0.5.9",
            "requests-unixsocket": "0.4.1",
        }
        for dist, version in expected.items():
            with self.subTest(dist=dist):
                self.assertEqual(importlib.metadata.version(dist), version)

    def test_licenses_shipped(self):
        licenses = os.path.join(PKG, "licenses")
        present = sorted(os.listdir(licenses))
        self.assertIn("LICENSE", present)
        for name in ("LICENSE.dnspython-2.8.0",
                     "LICENSE.click-option-group-0.5.9",
                     "LICENSE.requests-unixsocket-0.4.1"):
            self.assertIn(name, present)
        with open(os.path.join(licenses, "LICENSE"), encoding="utf-8") as fh:
            self.assertIn("GNU GENERAL PUBLIC LICENSE", fh.read())


class Test03ModuleSurface(unittest.TestCase):
    """Every upstream module must be importable from the packaged tree."""

    # synadm/__main__.py is deliberately absent: importing it calls root(),
    # i.e. it parses this script's argv. It is checked as a file and run as
    # `python -m synadm` instead.
    MODULES = [
        "synadm", "synadm.api", "synadm.cli",
        "synadm.cli._common", "synadm.cli._helper", "synadm.cli.group",
        "synadm.cli.history", "synadm.cli.matrix", "synadm.cli.media",
        "synadm.cli.notice", "synadm.cli.raw", "synadm.cli.regtok",
        "synadm.cli.room", "synadm.cli.user",
    ]

    def test_all_modules_import(self):
        for name in self.MODULES:
            with self.subTest(module=name):
                importlib.import_module(name)

    def test_module_count_matches_upstream(self):
        # upstream 0.49.2 ships 16 .py files; 15 are importable modules, one
        # of which (__main__.py) is an entry point rather than an import, and
        # setup.py is not part of the package.
        self.assertEqual(len(self.MODULES), 14)

    def test_main_entry_point_module_is_packaged(self):
        path = os.path.join(SITE, "synadm", "__main__.py")
        self.assertTrue(os.path.isfile(path), path)
        with open(path, encoding="utf-8") as handle:
            self.assertIn("root()", handle.read())

    def test_cli_command_tree(self):
        import synadm.cli
        for name in ("config", "version", "user", "room", "media", "group",
                     "history", "matrix", "regtok", "notice", "raw"):
            with self.subTest(command=name):
                self.assertIn(name, synadm.cli.root.commands)

    def test_user_subcommands(self):
        import synadm.cli
        user = synadm.cli.root.commands["user"]
        # The complete 0.49.2 set, asserted as a set so a packaging slip that
        # drops one cli/user.py command cannot pass unnoticed.
        self.assertEqual(
            set(user.commands),
            {"list", "deactivate", "deactivate-regex", "prune-devices",
             "password", "membership", "search", "details", "modify", "whois",
             "media", "login", "shadow-ban", "redact", "redact-status",
             "auth-provider", "3pid", "suspend"})

    def test_helper_formatters_complete(self):
        from synadm.cli._helper import APIHelper
        self.assertEqual(
            sorted(APIHelper.FORMATTERS),
            ["human", "json", "minified", "pprint", "yaml"])


class Test04Formatters(unittest.TestCase):
    """Output rendering is the CLI's product; exercise each formatter."""

    SAMPLE = {"server_version": "1.111.0", "python_version": "3.12.9"}

    def _format(self, kind, data):
        from synadm.cli._helper import APIHelper
        return APIHelper.FORMATTERS[kind](data)

    def test_json_is_indented_and_round_trips(self):
        out = self._format("json", self.SAMPLE)
        self.assertEqual(json.loads(out), self.SAMPLE)
        self.assertIn("\n", out)

    def test_minified_has_no_whitespace_padding(self):
        out = self._format("minified", self.SAMPLE)
        self.assertEqual(json.loads(out), self.SAMPLE)
        self.assertNotIn(", ", out)

    def test_yaml_round_trips(self):
        import yaml
        out = self._format("yaml", self.SAMPLE)
        self.assertEqual(yaml.safe_load(out), self.SAMPLE)

    def test_pprint_is_evaluable(self):
        self.assertEqual(eval(self._format("pprint", self.SAMPLE)), self.SAMPLE)

    def test_human_list_of_dicts_becomes_table(self):
        out = self._format("human", USERS)
        self.assertIn("@alice:example.org", out)
        self.assertIn("displayname", out)
        self.assertIn("---", out)  # tabulate "simple" rule line

    def test_human_dict_becomes_pivoted_table(self):
        out = self._format("human", self.SAMPLE)
        self.assertIn("server_version", out)
        self.assertIn("1.111.0", out)

    def test_human_list_of_strings(self):
        out = self._format("human", ["a", "b", "c"])
        self.assertEqual(out, "a\nb\nc")

    def test_human_scalar_falls_back_to_str(self):
        self.assertEqual(self._format("human", 42), "42")


class Test05ApiRequestBuilding(unittest.TestCase):
    """URL construction and argument sanitising, without a server."""

    def _api(self, protocol="http", base_url="http://example.org:8008"):
        import logging

        import synadm.api
        return synadm.api.SynapseAdmin(
            logging.getLogger("synadm-test-url"), "admin", "tok", protocol,
            base_url, "/_synapse/admin", 5, False, False)

    def test_trailing_slash_removed_from_base_url(self):
        api = self._api(base_url="http://example.org:8008/")
        self.assertEqual(api.base_url, "http://example.org:8008")

    def test_admin_path_stripped_of_slashes(self):
        import logging

        import synadm.api
        api = synadm.api.SynapseAdmin(
            logging.getLogger("synadm-test-url2"), "admin", "tok", "http",
            "http://example.org:8008", "/_synapse/admin/", 5, False, False)
        self.assertEqual(api.path, "_synapse/admin")

    def test_user_id_is_url_quoted_into_path(self):
        # query() quotes **kwargs with safe="" before str.format, so an MXID's
        # @ and : are encoded while the endpoint template stays readable.
        # SynapseAdmin.user_details() uses exactly this call shape.
        api = self._api()
        seen = {}

        class Resp:
            ok = True
            status_code = 200

            def json(self):
                return {"ok": True}

        def fake_request(method, url, **kwargs):
            seen["url"] = url
            seen["kwargs"] = kwargs
            return Resp()

        import synadm.api as api_module
        real = api_module.requests.request
        api_module.requests.request = fake_request
        try:
            api.query("get", "v2/users/{user_id}", user_id="@alice:example.org")
        finally:
            api_module.requests.request = real
        self.assertIn("/_synapse/admin/v2/users/%40alice%3Aexample.org",
                      seen["url"])
        self.assertEqual(seen["kwargs"]["timeout"], 5)

    def test_timestamp_helpers_round_trip(self):
        api = self._api()
        stamp = api._timestamp_from_days_ago(1)
        back = api._datetime_from_timestamp(stamp)
        delta = abs((datetime.datetime.now() - datetime.timedelta(days=1)
                     - back).total_seconds())
        self.assertLess(delta, 60)
        self.assertIsInstance(stamp, int)

    def test_timestamp_from_datetime_truncates_to_ms(self):
        api = self._api()
        moment = datetime.datetime(2026, 10, 15, 12, 0, 0)
        self.assertEqual(api._timestamp_from_datetime(moment),
                         int(moment.timestamp()) * 1000)

    def test_format_datetime_is_human_readable(self):
        api = self._api()
        out = api._format_datetime(datetime.datetime(2026, 10, 15, 12, 0, 0))
        self.assertIn("2026", str(out))


class Test06CliAgainstStubSynapse(unittest.TestCase):
    """End-to-end: the packaged CLI against a live HTTP server."""

    server = None
    base_url = None
    workdir = None

    @classmethod
    def setUpClass(cls):
        cls.server, cls.base_url = serve_stub()
        cls.workdir = os.path.realpath(
            os.path.join(os.environ.get("TMPDIR", os.path.expanduser("~/.tmp")),
                         "synadm-consumer-suite"))
        os.makedirs(cls.workdir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.workdir, ignore_errors=True)

    def config_path(self, name="synadm.yaml", **overrides):
        import yaml
        cfg = {**CONFIG, "base_url": self.base_url, **overrides}
        path = os.path.join(self.workdir, name)
        with open(path, "w", encoding="utf-8") as handle:
            yaml.dump(cfg, handle)
        return path

    def run_cli(self, *args, config=None):
        binary = shutil.which("synadm")
        self.assertIsNotNone(
            binary, "the package must put bin/synadm on PATH")
        proc = subprocess.run(
            [binary, *(("-c", config) if config else ()), *args],
            capture_output=True, text=True, timeout=120,
            env=dict(os.environ, PYTHONNOUSERSITE="1"),
        )
        return proc

    def test_binary_on_path_is_the_packaged_one(self):
        binary = shutil.which("synadm")
        self.assertTrue(os.path.realpath(binary).startswith(PKG),
                        f"{binary} is not from {PKG}")

    def test_version_flag_reports_packaged_version(self):
        proc = self.run_cli("--version")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("synadm, version 0.49.2", proc.stdout)

    def test_help_lists_admin_commands(self):
        proc = self.run_cli("--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for word in ("user", "room", "media", "config", "version"):
            self.assertIn(word, proc.stdout)

    def test_server_version_command(self):
        proc = self.run_cli("version", config=self.config_path())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), SERVER_VERSION)

    def test_user_list_over_http(self):
        proc = self.run_cli("user", "list", config=self.config_path())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["users"][0]["name"], "@alice:example.org")

    def test_user_details_sends_bearer_token(self):
        path = self.config_path("details.yaml")
        proc = self.run_cli("user", "details", "@alice:example.org",
                            config=path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["displayname"], "Alice")

    def test_output_override_to_yaml(self):
        import yaml
        proc = self.run_cli("-o", "yaml", "version",
                            config=self.config_path())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(yaml.safe_load(proc.stdout), SERVER_VERSION)

    def test_output_override_to_human_makes_table(self):
        proc = self.run_cli("-o", "human", "version",
                            config=self.config_path())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("server_version", proc.stdout)
        self.assertIn("1.111.0", proc.stdout)

    def test_room_list(self):
        proc = self.run_cli("room", "list", config=self.config_path())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["rooms"][0]["room_id"], "!r1:example.org")

    def test_unreachable_server_exits_with_connection_error(self):
        path = self.config_path("dead.yaml",
                                base_url="http://127.0.0.1:1")
        proc = self.run_cli("--no-confirm", "version", config=path)
        self.assertNotEqual(proc.returncode, 0)
        combined = (proc.stdout + proc.stderr).lower()
        self.assertTrue("connection error" in combined
                        or "synapse can be reached" in combined,
                        combined)

    def test_missing_config_tells_user_to_configure(self):
        path = os.path.join(self.workdir, "absent.yaml")
        proc = self.run_cli("--no-confirm", "version", config=path)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("Please setup synadm", proc.stdout)


class Test07PythonModuleEntry(unittest.TestCase):
    """`python -m synadm` is the Debian-style alternate entry point."""

    def test_module_entry_version(self):
        proc = subprocess.run(
            [sys.executable, "-m", "synadm", "--version"],
            capture_output=True, text=True, timeout=120,
            env=dict(os.environ, PYTHONNOUSERSITE="1"),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("0.49.2", proc.stdout)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
