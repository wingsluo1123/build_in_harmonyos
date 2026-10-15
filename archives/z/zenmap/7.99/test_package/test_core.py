#!/usr/bin/env python3
"""Consumer integration tests for the *installed* zenmap Conan package.

These are not the upstream unit tests (the recipe's ``build()`` runs those
against the source tree).  Here zenmap is imported from the installed Conan
package (``PYTHONPATH`` comes from ``zenmap``'s ``package_info()``) and the
public ``zenmapCore`` API is exercised the way a real consumer would.

The suite also asserts the HarmonyOS binding this package depends on: the
``nmap`` scanner zenmap drives must be the OHOS ``aarch64`` build shipped by the
``nmap/7.99`` run dependency, and the packaged launcher must be installed for
the OHOS runtime.
"""

import os
import platform
import struct
import sys
import tempfile
import unittest

import zenmapCore.Version
from zenmapCore.NmapOptions import NmapOptions, split_quoted
from zenmapCore.NmapParser import NmapParser
from zenmapCore.SearchResult import HostSearch, SearchResult
from zenmapCore.StringPool import unique

# A small but realistic `nmap -oX` document: one up host, an open SSH port with
# service detection, a closed HTTP port and one OS match.  Same schema the OHOS
# nmap build emits.
SCAN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -oX - -p 22,80 127.0.0.1" start="1700000000"
         startstr="Tue Nov 14 00:00:00 2023" version="7.99" xmloutputversion="1.05">
<scaninfo type="syn" protocol="tcp" numservices="2" services="22,80"/>
<host starttime="1700000000" endtime="1700000001">
<status state="up" reason="localhost-response" reason_ttl="0"/>
<address addr="127.0.0.1" addrtype="ipv4"/>
<hostnames><hostname name="localhost" type="PTR"/></hostnames>
<ports>
<port protocol="tcp" portid="22">
<state state="open" reason="syn-ack" reason_ttl="64"/>
<service name="ssh" product="OpenSSH" version="9.6" extrainfo="Ubuntu Linux"
         method="probed" conf="10"/>
</port>
<port protocol="tcp" portid="80">
<state state="closed" reason="reset" reason_ttl="64"/>
<service name="http" method="table" conf="3"/>
</port>
</ports>
<os>
<osmatch name="Linux 5.15 - 6.1" accuracy="95" line="12345">
<osclass type="general purpose" vendor="Linux" osfamily="Linux" osgen="5.X"
         accuracy="95"/>
</osmatch>
</os>
</host>
<runstats><finished time="1700000002" elapsed="1.23"/>
<hosts up="1" down="0" total="1"/></runstats>
</nmaprun>
"""

ELF_MAGIC = b"\x7fELF"
EM_AARCH64 = 0xB7  # e_machine for 64-bit ARM
PT_INTERP = 3
OHOS_INTERP = b"ld-musl-aarch64.so.1"


def _write_scan():
    fd, path = tempfile.mkstemp(suffix=".xml", prefix="zenmap-consumer-")
    with os.fdopen(fd, "w") as fh:
        fh.write(SCAN_XML)
    return path


def _parse_scan():
    path = _write_scan()
    try:
        scan = NmapParser()
        scan.parse_file(path)
    finally:
        os.remove(path)
    return scan


def _elf_interpreter(path):
    """Return (e_machine, interpreter) of an ELF file; raise on a non-ELF."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != ELF_MAGIC:
        raise AssertionError("{} is not an ELF file".format(path))
    if data[4] != 2:  # EI_CLASS == ELFCLASS64
        raise AssertionError("{} is not a 64-bit ELF file".format(path))
    e_machine = struct.unpack_from("<H", data, 18)[0]
    e_phoff = struct.unpack_from("<Q", data, 32)[0]
    e_phentsize = struct.unpack_from("<H", data, 54)[0]
    e_phnum = struct.unpack_from("<H", data, 56)[0]
    interp = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if struct.unpack_from("<I", data, off)[0] != PT_INTERP:
            continue
        p_offset = struct.unpack_from("<Q", data, off + 8)[0]
        p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
        interp = data[p_offset:p_offset + p_filesz].split(b"\x00", 1)[0]
    return e_machine, interp


class InstalledPackageTest(unittest.TestCase):
    """The installed package exposes the expected version, modules and metadata."""

    def test_version(self):
        self.assertEqual(zenmapCore.Version.VERSION, "7.99")

    def test_distribution_metadata(self):
        # The wheel metadata is installed next to the packages; a missing
        # dist-info means the payload was staged without its bookkeeping.
        root = os.path.dirname(os.path.dirname(zenmapCore.__file__))
        dist = [n for n in os.listdir(root)
                if n.lower().startswith("zenmap-7.99") and n.endswith(".dist-info")]
        self.assertTrue(dist, "zenmap-7.99.dist-info not found under {}".format(root))

    def test_public_modules_import(self):
        # GTK-free zenmapCore modules a headless consumer can use.
        import zenmapCore.Diff  # noqa: F401
        import zenmapCore.NmapCommand  # noqa: F401
        import zenmapCore.TargetList  # noqa: F401
        import zenmapCore.UmitConf  # noqa: F401


class NmapOptionsConsumerTest(unittest.TestCase):
    """Public option-parsing API of the installed package."""

    def test_split_quoted(self):
        self.assertEqual(split_quoted('a "b c" d'), ["a", "b c", "d"])

    def test_parse_and_render_roundtrip(self):
        opts = NmapOptions()
        for cmd in ("nmap", "nmap -v", "nmap -oX - 127.0.0.1 -PS10"):
            opts.parse_string(cmd)
            first = opts.render_string()
            opts.parse_string(first)
            self.assertEqual(first, opts.render_string())
        opts.parse_string("nmap -p 22,80 -sS 127.0.0.1")
        self.assertEqual(opts.target_specs, ["127.0.0.1"])
        self.assertEqual(opts["-p"], "22,80")
        self.assertEqual(opts.render()[0], "nmap")

    def test_quoted_option_value(self):
        opts = NmapOptions()
        opts.parse_string('nmap --script "http-title" 10.0.0.1')
        self.assertEqual(opts["--script"], "http-title")
        self.assertEqual(opts.target_specs, ["10.0.0.1"])

    def test_string_pool_unique(self):
        # `unique` is the memoising __getitem__ of a string pool: equal strings
        # must collapse to one shared object.
        a = "".join(["zenmap", "-", "core"])
        b = "".join(["zenmap", "-", "core"])
        self.assertEqual(a, b)
        self.assertIs(unique(a), unique(b))


class NmapParserConsumerTest(unittest.TestCase):
    """Parse a real `nmap -oX` document through the installed parser."""

    def test_parse_scan_document(self):
        scan = _parse_scan()
        hosts = scan.get_hosts()
        self.assertEqual(len(hosts), 1)
        host = hosts[0]
        self.assertEqual(host.get_hostnames()[0]["hostname"], "localhost")

        ports = {p["portid"]: p for p in host.get_ports()}
        self.assertEqual(ports["22"]["port_state"], "open")
        self.assertEqual(ports["22"]["service_name"], "ssh")
        self.assertEqual(ports["22"]["service_version"], "9.6")
        self.assertEqual(ports["80"]["port_state"], "closed")

        self.assertEqual(host.get_osmatches()[0]["accuracy"], "95")

        # HostSearch is the predicate layer zenmapGUI drives; consuming it here
        # proves the parser + search glue works headless.
        self.assertTrue(HostSearch.match_target(host, "localhost"))
        self.assertTrue(HostSearch.match_service(host, "ssh"))
        self.assertTrue(HostSearch.match_port(host.get_ports(), "22", "open"))

    def test_search_result_query_layer(self):
        scan = _parse_scan()

        class _OneScan(SearchResult):
            def get_scan_results(self):
                return [scan]

        # Values are lists: SearchResult.search() applies every argument of an
        # operator, so a bare string would be iterated character by character.
        self.assertEqual(len(list(_OneScan().search(open=["22"]))), 1)
        self.assertEqual(len(list(_OneScan().search(closed=["80"]))), 1)
        self.assertEqual(len(list(_OneScan().search(service=["ssh"]))), 1)
        self.assertEqual(len(list(_OneScan().search(open=["9999"]))), 0)


class OhosRuntimeTest(unittest.TestCase):
    """HarmonyOS-specific checks for the packaged artifact and its nmap binding."""

    def test_nmap_dependency_is_ohos_aarch64_build(self):
        """The scanner zenmap drives is the OHOS aarch64 nmap from nmap/7.99."""
        nmap = os.environ.get("ZENMAP_TEST_NMAP", "")
        self.assertTrue(
            nmap and os.path.isfile(nmap),
            "ZENMAP_TEST_NMAP not provided by the test harness (got {!r})".format(nmap))
        e_machine, interp = _elf_interpreter(nmap)
        self.assertEqual(
            e_machine, EM_AARCH64,
            "nmap is not an aarch64 ELF (e_machine=0x{:x})".format(e_machine))
        self.assertIsNotNone(interp, "nmap has no PT_INTERP program header")
        self.assertIn(
            OHOS_INTERP, interp,
            "nmap is not linked against the OHOS musl loader (interp={!r})".format(interp))

    def test_launcher_installed_for_ohos_runtime(self):
        """bin/zenmap is installed and starts through the device python3."""
        root = os.path.dirname(os.path.dirname(zenmapCore.__file__))
        launcher = os.path.join(root, "bin", "zenmap")
        self.assertTrue(os.path.isfile(launcher), "bin/zenmap not installed")
        self.assertTrue(os.access(launcher, os.X_OK), "bin/zenmap is not executable")
        with open(launcher) as fh:
            first = fh.readline().rstrip("\n")
        self.assertEqual(first, "#!/usr/bin/env python3")

    def test_core_works_on_harmonyos_runtime(self):
        """zenmapCore data resolution works under the HarmonyOS CPython runtime."""
        self.assertTrue(sys.version_info >= (3, 8),
                        "zenmap requires Python >= 3.8 (pyproject requires-python)")
        # The OHOS CPython reports sys.platform as 'ohos' (some builds say
        # 'linux'), so it cannot be asserted to one literal.  What matters is
        # that the runtime is the aarch64 OHOS one and does not fall into
        # zenmap's 'darwin'/'win32' branches.
        self.assertNotIn(sys.platform, ("win32", "darwin"),
                         "unexpected platform for the OHOS runtime: %r" % sys.platform)
        self.assertEqual(platform.machine(), "aarch64")
        from zenmapCore.Paths import Path
        self.assertTrue(os.path.isdir(Path.config_dir),
                        "zenmap config data dir missing: {}".format(Path.config_dir))


if __name__ == "__main__":
    unittest.main(verbosity=2)
