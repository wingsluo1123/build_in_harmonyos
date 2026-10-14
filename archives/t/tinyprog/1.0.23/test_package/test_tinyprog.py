#!/usr/bin/env python3
"""Consumer test suite for the **installed** tinyprog 1.0.23 conan package.

Invoked as ``python3 test_tinyprog.py <package_folder> <version>`` by
``test_package/conanfile.py`` and, identically, by the CI L1 step.  It is a
consumer test (R34): everything is imported from the produced package, never
from the source tree, and the assertions below exercise the real protocol code
rather than printing a banner.

Why this suite carries the test burden
-------------------------------------
Upstream ships **no Python test suite** — ``programmer/README.md`` states
"Tests have been removed for now pending refactoring of test methodology", and
the repository's ``tests/`` directory holds only Verilog RTL testbenches for the
bootloader *firmware* (they need an icarus-verilog simulator that the OHOS CI
image does not provide).  So the adapted package is verified from the consumer
side instead, and the census of what was and was not run is recorded explicitly
(``test_package/MANIFEST.yml``) rather than reported as a bare
"0 passed".

Coverage map (12 tests, each an independent consumer step)
----------------------------------------------------------
 1. package layout          — tinyprog/, dist-info, bin/, licenses present
 2. import from package     — the imported module really lives in the package
 3. distribution metadata   — version identity via importlib.metadata
 4. console-script entry    — the declared entry point resolves to __main__:main
 5. dependency wiring       — pyserial/six come from conan deps (not vendored),
                              intelhex/jsonmerge/tqdm/pyusb/packaging from the
                              package; all seven upstream requirements import
 6. CLI --help              — installed console script runs
 7. CLI -l                  — real serial enumeration path
 8. SPI framing + flash-id  — byte-exact command framing; ISSI vs Adesto branch
 9. metadata integration    — security-page addressing, jsonmerge merge,
                              @addr+len pointer resolution, addr ranges, uuid
10. bit-reverse + helpers   — table involution over all 256 values
11. HarmonyOS fingerprint   — the OHOS/aarch64 runtime upstream's platform
                              branch actually sees (sys.platform accepted in
                              all its linux/ohos/harmonyos spellings)
12. HarmonyOS enumeration   — the shipped pyserial shim engages, then
                              comports()/get_ports() run on OHOS

Nothing here needs a physical TinyFPGA board: the tests either assert platform
and packaging facts, or drive the real protocol implementation through a scripted
in-memory transport.
"""

import importlib.metadata
import json
import os
import struct
import subprocess
import sys
import unittest

PKG = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else None
VERSION = sys.argv[2] if len(sys.argv) > 2 else None
BIN = os.path.join(PKG, "bin", "tinyprog") if PKG else None

# The seven runtime requirements declared by upstream setup.py, split by how
# this recipe provides them (see conanfile.py's W0 census).
CONAN_PROVIDED = ("serial", "six")
PACKAGE_PROVIDED = ("intelhex", "tqdm", "jsonmerge", "usb", "packaging")


def run_cli(*args):
    """Run the installed console script; return (rc, combined output)."""
    proc = subprocess.run([sys.executable, BIN, *args],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.decode(errors="ignore")


class FakeSerial(object):
    """Scripted in-memory transport that speaks tinyprog's real wire format.

    ``TinyProg.cmd()`` frames every request as::

        0x01 | <H payload_len | <H read_len | opcode | addr(3, BE, optional) | data

    and then reads exactly ``read_len`` bytes back.  Parsing that frame here
    means the tests exercise the genuine addressing (including the ISSI
    security-page bit offset) and not a stub.
    """

    # Opcodes that carry a 3-byte big-endian address after the opcode.
    ADDR_OPCODES = {0x0B, 0x20, 0x52, 0xD8, 0x03, 0x02,
                    0x68, 0x62, 0x64, 0x48, 0x42, 0x44}

    def __init__(self, flash_id=b"\x9d\x60\x15", pages=None, payloads=None):
        self.flash_id = flash_id
        self.pages = pages or {}      # security-register page -> bytes
        self.payloads = payloads or {}  # (addr, read_len) -> bytes
        self.frames = []              # every raw frame written, for assertions
        self.commands = []            # decoded (opcode, addr, read_len)
        self._pending = b""

    # -- serial.Serial surface used by tinyprog ------------------------
    def write(self, data):
        data = bytes(data)
        self.frames.append(data)
        body_len, read_len = struct.unpack("<HH", data[1:5])
        body = data[5:5 + body_len]
        opcode = body[0]
        if opcode in self.ADDR_OPCODES:
            addr = int.from_bytes(body[1:4], "big")
            rest = body[4:]
        else:
            addr, rest = None, body[1:]
        self.commands.append((opcode, addr, read_len))
        self._pending = self._respond(opcode, addr, read_len, rest)

    def flush(self):
        pass

    def read(self, length):
        data = self._pending[:length]
        self._pending = self._pending[length:]
        if len(data) < length:
            data += b"\x00" * (length - len(data))
        return data

    # -- scripted responses -------------------------------------------
    def _respond(self, opcode, addr, read_len, rest):
        if opcode == 0x9F:
            return self.flash_id[:read_len].ljust(read_len, b"\x00")
        if opcode == 0x05:
            return b"\x00"  # status: not busy
        if opcode in (0x68, 0x48):  # security-register page read
            # ISSI shifts the page number by 8 + bit_offset (= 12).
            for shift in (12, 8):
                page = addr >> shift
                if page in self.pages and (addr & ((1 << shift) - 1)) == 0:
                    return self.pages[page].ljust(read_len, b"\x00")[:read_len]
            return b"\x00" * read_len
        if opcode == 0x0B and (addr, read_len) in self.payloads:
            return self.payloads[(addr, read_len)][:read_len]
        return b"\x00" * read_len


class TinyprogConsumerTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.assertTrue(PKG, "package folder argument missing")
        self.assertTrue(VERSION, "version argument missing")

    # ---------------------------------------------------------------- 1
    def test_01_package_layout(self):
        """The produced package has the pip --target flat payload shape."""
        self.assertTrue(os.path.isdir(os.path.join(PKG, "tinyprog")),
                        f"tinyprog/ missing from package: {PKG}")
        dist = os.path.join(PKG, f"tinyprog-{VERSION}.dist-info")
        self.assertTrue(os.path.isdir(dist),
                        f"tinyprog-{VERSION}.dist-info missing: "
                        f"{sorted(d for d in os.listdir(PKG) if d.endswith('.dist-info'))}")
        self.assertTrue(os.path.isfile(BIN), f"bin/tinyprog missing: {BIN}")
        self.assertTrue(os.path.isdir(os.path.join(PKG, "licenses")),
                        "licenses/ missing (MIT license must ship)")

    # ---------------------------------------------------------------- 2
    def test_02_import_from_package(self):
        """The module we import is the one inside the produced package."""
        import tinyprog
        self.assertTrue(tinyprog.__file__.startswith(PKG + os.sep),
                        f"imported tinyprog outside the package: {tinyprog.__file__}")
        for name in ("pretty_hex", "to_int", "get_ports", "TinyProg",
                     "TinyMeta", "SerialPort", "UsbPort"):
            self.assertTrue(hasattr(tinyprog, name),
                            f"public API missing from package: {name}")

    # ---------------------------------------------------------------- 3
    def test_03_distribution_metadata(self):
        """Distribution metadata reports the adapted version (upstream 1.0.23)."""
        self.assertEqual(importlib.metadata.version("tinyprog"), VERSION)

    # ---------------------------------------------------------------- 4
    def test_04_console_script_entry_point(self):
        """The declared entry point resolves to tinyprog.__main__:main."""
        entries = [e for e in importlib.metadata.entry_points(
            group="console_scripts") if e.name == "tinyprog"]
        self.assertEqual(len(entries), 1, f"expected one tinyprog entry point: {entries}")
        self.assertEqual(entries[0].value, "tinyprog.__main__:main")
        import tinyprog.__main__ as m
        self.assertTrue(callable(m.main), "tinyprog.__main__:main is not callable")

    # ---------------------------------------------------------------- 5
    def test_05_dependency_wiring(self):
        """All seven upstream requirements are importable from the package.

        And they arrive by the route the recipe intends: ``pyserial``/``six``
        from their *conan* packages (proving the ``run=True`` requirement
        traits keep them in the graph), the rest pip-filled into the package.
        """
        for name in CONAN_PROVIDED + PACKAGE_PROVIDED:
            with self.subTest(module=name):
                __import__(name)
        import six
        import serial
        for mod in (serial, six):
            path = os.path.abspath(mod.__file__)
            self.assertFalse(
                path.startswith(PKG + os.sep),
                f"{mod.__name__} was vendored into the package instead of "
                f"being resolved from its conan dependency: {path}")
        for name in PACKAGE_PROVIDED:
            mod = __import__(name)
            self.assertTrue(
                os.path.abspath(mod.__file__).startswith(PKG + os.sep),
                f"{name} should be shipped inside the package: {mod.__file__}")
        # pyserial's sub-modules are what tinyprog actually imports.
        from serial.serialutil import SerialTimeoutException  # noqa: F401
        from serial.tools.list_ports import comports  # noqa: F401

    # ---------------------------------------------------------------- 6
    def test_06_cli_help(self):
        """The installed console script runs and advertises its board options."""
        rc, out = run_cli("--help")
        self.assertEqual(rc, 0, f"`tinyprog --help` failed:\n{out}")
        for flag in ("--lib", "--update", "--boot", "--device", "--list"):
            self.assertIn(flag, out, f"`--help` lost the {flag} option:\n{out}")

    # ---------------------------------------------------------------- 7
    def test_07_cli_list_ports(self):
        """`-l` walks the real enumeration path (rc=1 when no board attached)."""
        rc, out = run_cli("-l")
        self.assertIn(rc, (0, 1), f"`tinyprog -l` errored (rc={rc}):\n{out}")
        self.assertIn("TinyProg", out, f"unexpected `-l` output:\n{out}")

    # ---------------------------------------------------------------- 8
    def test_08_spi_framing_and_flash_id_branch(self):
        """Byte-exact command framing + the ISSI/Adesto security-page branch."""
        import tinyprog as tp

        # A board whose flash answers security pages with a minimal metadata
        # root, so TinyProg.__init__ can complete.
        root = json.dumps({"boardmeta": {"uuid": "deadbeef"}}).encode()
        serial_port = FakeSerial(pages={1: root})

        prog = tp.TinyProg(serial_port)

        # Frame layout: 0x01 | <H payload_len | <H read_len | body
        self.assertEqual(
            serial_port.frames[0],
            b"\x01" + struct.pack("<HH", 1, 0) + b"\xab",
            "wake command was not framed as the TinyFPGA protocol specifies")

        # ISSI (0x9D,0x60) selects bit offset 4 and the 0x6x command set.
        self.assertEqual(prog.security_page_bit_offset, 4)
        self.assertEqual(prog.security_page_write_cmd, 0x62)
        self.assertEqual(prog.security_page_read_cmd, 0x68)
        self.assertEqual(prog.security_page_erase_cmd, 0x64)

        # The security page was addressed as page << (8 + 4).
        sec_reads = [c for c in serial_port.commands if c[0] == 0x68]
        self.assertTrue(sec_reads, "no security-register read was issued")
        self.assertIn((0x68, 1 << 12, 255), sec_reads,
                      f"ISSI security page 1 must be read at 0x1000: {sec_reads}")

        self.assertEqual(prog.read_id(), b"\x9d\x60\x15")
        self.assertTrue(prog.is_bootloader_active())

        # Adesto parts take the other branch (offset 0, 0x4x command set).
        adesto = FakeSerial(flash_id=b"\x1f\x45\x01", pages={1: root})
        other = tp.TinyProg(adesto)
        self.assertEqual(other.security_page_bit_offset, 0)
        self.assertEqual(other.security_page_write_cmd, 0x42)
        self.assertEqual(other.security_page_read_cmd, 0x48)
        adesto_reads = [c for c in adesto.commands if c[0] == 0x48]
        self.assertIn((0x48, 1 << 8, 255), adesto_reads,
                      f"Adesto security page 1 must be read at 0x100: {adesto_reads}")

    # ---------------------------------------------------------------- 9
    def test_09_metadata_integration(self):
        """Metadata assembly: page addressing, jsonmerge, pointers, ranges.

        Three metadata roots are returned from three security pages so that
        ``jsonmerge.merge`` has to combine them, and one value is an
        ``@ 0xADDR + LEN`` pointer that forces the implementation to issue a
        further read and parse the result.  Bootloader/userimage ranges and the
        board uuid then come out of the merged structure.
        """
        import tinyprog as tp

        page1 = json.dumps({"bootmeta": {"addrmap": {
            "bootloader": "0x00000 - 0x0FFFF",
            "userimage": "0x10000 - 0x1FFFF",
            "userdata": "0x20000 - 0x2FFFF"}}}).encode()
        page2 = json.dumps({"boardmeta": {"uuid": "0123abcd"}}).encode()
        # The pointer length must equal the JSON length exactly: the transport
        # hands back precisely `len` bytes, so a mismatch truncates the payload
        # (measured: an 18-byte object over a 16-byte pointer fails to parse).
        resolved = b'{"resolved": true}'
        page3 = json.dumps({"extra": f"@ 0x2000 + {len(resolved)}"}).encode()

        serial_port = FakeSerial(
            pages={1: page1, 2: page2, 3: page3},
            payloads={(0x2000, len(resolved)): resolved},
        )
        prog = tp.TinyProg(serial_port)

        self.assertEqual(prog.meta.bootloader_addr_range(), (0x00000, 0x0FFFF))
        self.assertEqual(prog.meta.userimage_addr_range(), (0x10000, 0x1FFFF))
        self.assertEqual(prog.meta.userdata_addr_range(), (0x20000, 0x2FFFF))
        self.assertEqual(prog.meta.uuid(), "0123abcd")

        # jsonmerge combined all three roots...
        self.assertIn("bootmeta", prog.meta.root)
        self.assertIn("boardmeta", prog.meta.root)
        # ...and the @addr+len pointer was followed and parsed.
        self.assertEqual(prog.meta.root["extra"], {"resolved": True})
        self.assertIn((0x0B, 0x2000, len(resolved)), serial_port.commands,
                      "the @addr+len pointer read was never issued")

    # ---------------------------------------------------------------- 10
    def test_10_bit_reverse_and_helpers(self):
        """The flash bit-reversal table is a true involution over all 256."""
        import tinyprog as tp

        table = tp.bit_reverse_table
        self.assertEqual(len(table), 256)
        for value in range(256):
            reversed_value = table[value]
            self.assertEqual(
                table[reversed_value], value,
                f"reversal is not involutive at {value:#04x} -> "
                f"{reversed_value:#04x} -> {table[reversed_value]:#04x}")
            # Bit-reversal: LSB<->MSB ordering.
            self.assertEqual(reversed_value,
                             int(format(value, "08b")[::-1], 2))
        self.assertEqual(tp._mirror_byte(0x01), 0x80)
        self.assertEqual(bytes(tp._mirror_each_byte(b"\x01\x02\x04")),
                         bytes([0x80, 0x40, 0x20]))
        self.assertEqual(tp.to_int("A"), 65)
        self.assertEqual(tp.to_int(65), 65)

    # ---------------------------------------------------------------- 11
    def test_11_harmonyos_runtime_fingerprint(self):
        """The runtime this package was adapted for: HarmonyOS PC / aarch64.

        This is the platform fingerprint upstream's own branch depends on —
        ``get_ports()`` special-cases ``platform.system() == "Darwin"`` — so on
        HarmonyOS PC the package must observe HarmonyOS and must *not* observe
        Darwin, otherwise port discovery silently diverges from the intended
        pyserial path.
        """
        import platform as _platform

        uname = os.uname()
        self.assertEqual(uname.sysname, "HarmonyOS",
                         f"not running on the HarmonyOS kernel: {uname}")
        self.assertEqual(_platform.system(), "HarmonyOS")
        self.assertNotEqual(_platform.system(), "Darwin")
        self.assertEqual(uname.machine, "aarch64",
                         f"expected the aarch64 OHOS PC target: {uname.machine}")
        # The interpreter is the OHOS runtime's own, not a host toolchain one.
        # ``sys.platform`` is not stable across OHOS interpreter builds — the
        # HNP python reports "linux" while the worker's own python reports
        # "ohos" (build #89823) — so accept every fingerprint OHOS is known to
        # report instead of pinning one that only one build happens to emit.
        self.assertTrue(
            sys.platform.startswith(("linux", "ohos", "harmonyos")),
            f"unexpected platform fingerprint: sys.platform={sys.platform!r}")
        self.assertGreaterEqual(sys.version_info, (3, 8),
                                f"unexpected interpreter: {sys.version}")

    # ---------------------------------------------------------------- 12
    def test_12_harmonyos_serial_enumeration(self):
        """pyserial enumeration works on OHOS and drives get_ports()."""
        import tinyprog as tp

        # On OHOS the shipped sitecustomize shim must have registered pyserial's
        # Linux backend under the posix name, otherwise this very import raises
        # (that is how CI build #89823 failed).  Assert the shim engaged rather
        # than only noticing its absence through a traceback.
        if sys.platform.startswith(("ohos", "harmonyos")):
            from serial.tools import list_ports_linux
            self.assertIs(
                sys.modules.get("serial.tools.list_ports_posix"),
                list_ports_linux,
                "the OHOS pyserial shim did not register the Linux "
                "port-enumeration backend")

        from serial.tools.list_ports import comports

        ports = comports()
        self.assertIsInstance(ports, list,
                              f"comports() must return a list on OHOS: {ports!r}")

        # get_ports() must take the pyserial branch on HarmonyOS and never
        # raise, whether or not a TinyFPGA board is attached.
        found = tp.get_ports("1d50:6130")
        self.assertIsInstance(found, list)
        for port in found:
            self.assertIsInstance(port, tp.SerialPort)

        # SerialPort must report its name through __str__ (used by the CLI).
        probe = tp.SerialPort("/dev/ttyNULL-not-present")
        self.assertEqual(str(probe), "/dev/ttyNULL-not-present")


if __name__ == "__main__":
    if not PKG or not VERSION:
        sys.exit("usage: test_tinyprog.py <package_folder> <version>")
    print(f"consumer tests: tinyprog {VERSION} at {PKG} "
          f"(python {sys.version.split()[0]}, {os.uname().sysname}/"
          f"{os.uname().machine})")
    unittest.main(verbosity=2, argv=[sys.argv[0]])

