#!/usr/bin/env python3
"""Verify HarmonyOS signed-ELF write protection and atomic module replacement."""

import errno
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import pglast
import pglast.parser


class HarmonyOSCodeSigningTests(unittest.TestCase):
    def test_signed_extension_atomic_replacement(self):
        self.assertEqual(os.uname().sysname, "HarmonyOS")
        installed = Path(os.environ["PGLAST_PACKAGE_ROOT"]).resolve()
        original = Path(pglast.parser.__file__).resolve()
        self.assertTrue(original.is_relative_to(installed))
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf")
        self.assertIsNotNone(objcopy)
        self.assertIsNotNone(signer)
        self.assertIsNotNone(readelf)

        with tempfile.TemporaryDirectory(prefix="pglast-harmonyos-signing-") as temporary:
            site = Path(temporary) / "site"
            package = site / "pglast"
            shutil.copytree(original.parent, package)
            extension = package / original.name
            replacement = package / (original.name + ".replacement")

            def unsigned_copy(destination):
                subprocess.run([objcopy, "--remove-section", ".codesign",
                                str(original), str(destination)], check=True)
                os.chmod(destination, 0o755)
                sections = subprocess.run([readelf, "-S", str(destination)],
                                          check=True, capture_output=True, text=True)
                self.assertNotIn(".codesign", sections.stdout)

            def sign(destination):
                subprocess.run([signer, "sign", "-inFile", str(destination),
                                "-outFile", str(destination), "-selfSign", "1"],
                               check=True)
                sections = subprocess.run([readelf, "-S", str(destination)],
                                          check=True, capture_output=True, text=True)
                self.assertIn(".codesign", sections.stdout)

            def parse_in_fresh_process(value):
                environment = os.environ.copy()
                environment["PYTHONPATH"] = str(site)
                environment["PYTHONDONTWRITEBYTECODE"] = "1"
                script = (
                    "import pathlib,sys,pglast,pglast.parser; "
                    "from pglast import parse_sql; "
                    "assert pathlib.Path(pglast.parser.__file__).resolve() == "
                    "pathlib.Path(sys.argv[1]).resolve(); "
                    "value=int(sys.argv[2]); "
                    "assert parse_sql('SELECT '+str(value))[0].stmt."
                    "targetList[0].val.val.ival == value"
                )
                subprocess.run([sys.executable, "-c", script, str(extension), str(value)],
                               env=environment, check=True, capture_output=True, text=True)

            unsigned_copy(replacement)
            os.replace(replacement, extension)
            before = hashlib.sha256(extension.read_bytes()).hexdigest()
            # Positive control: the private unsigned file is writable using
            # exactly the operation that must be rejected after signing/loading.
            with extension.open("r+b") as stream:
                first = stream.read(1)
                stream.seek(0)
                stream.write(first)
                stream.flush()
                os.fsync(stream.fileno())
            self.assertEqual(hashlib.sha256(extension.read_bytes()).hexdigest(), before)

            sign(extension)
            parse_in_fresh_process(17)
            signed_hash = hashlib.sha256(extension.read_bytes()).hexdigest()
            with self.assertRaises(OSError) as rejected:
                with extension.open("r+b") as stream:
                    first = stream.read(1)
                    stream.seek(0)
                    stream.write(first)
                    stream.flush()
                    os.fsync(stream.fileno())
            self.assertEqual(rejected.exception.errno, errno.EPERM)
            self.assertEqual(hashlib.sha256(extension.read_bytes()).hexdigest(), signed_hash)

            # Update a fresh inode and sign it before replacing the protected
            # path. Never mutate the installed package or a shared cache entry.
            old_inode = extension.stat().st_ino
            unsigned_copy(replacement)
            sign(replacement)
            os.replace(replacement, extension)
            self.assertNotEqual(extension.stat().st_ino, old_inode)
            parse_in_fresh_process(29)
            print("HARMONYOS_CODESIGN_MECHANISM: unsigned write allowed; "
                  "signed loaded write EPERM; signed inode replacement and SQL passed",
                  flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
