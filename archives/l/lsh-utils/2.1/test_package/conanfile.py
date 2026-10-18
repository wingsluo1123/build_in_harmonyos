#!/usr/bin/env python3
"""Conan test_package for lsh-utils 2.1 — consumer test (L1).

lsh-utils is a CLI package (package_type = "application"): it installs no
public header or library that a consumer could link against, so the consumer
test drives the installed tools and asserts their observable behaviour.  The
sequence is the one upstream's own testsuite uses
(src/testsuite/lsh-decrypt-key-test):

    lsh-keygen                > key.origkey
    lsh-writekey -c aes256-cbc -p bar -o key        < key.origkey
    lsh-writekey -c none              -o never      < key.origkey
    lsh-decrypt-key --in=key --out=decrypted --askpass=<helper>

and the decrypted private key must be byte-identical to the unencrypted copy.
That single round trip executes the real code paths of the package: RSA key
generation (libhogweed + gmp bignums), PKCS#5 / AES-256-CBC private-key
encryption (libnettle), the s-expression key reader/writer and the CLI
plumbing.  A failure anywhere in the Conan dependency wiring (missing or
mis-versioned gmp/nettle/liboop/zlib) shows up as a non-zero exit or a
mismatch, so the test is a genuine consumer check rather than a smoke test.

test_lsh_utils.sh next to this file is the same sequence as a standalone
script, used for the recorded on-device run (see reports/).
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class LshUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _tool(self, name):
        package_folder = self.dependencies["lsh-utils"].package_folder
        for subdir in ("bin", "sbin"):
            candidate = os.path.join(package_folder, subdir, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def test(self):
        if not can_run(self):
            return

        makeseed = self._tool("lsh-make-seed")
        keygen = self._tool("lsh-keygen")
        writekey = self._tool("lsh-writekey")
        decryptkey = self._tool("lsh-decrypt-key")
        for name, path in (("lsh-make-seed", makeseed),
                           ("lsh-keygen", keygen),
                           ("lsh-writekey", writekey),
                           ("lsh-decrypt-key", decryptkey)):
            if path is None:
                raise AssertionError("%s is missing from the package" % name)

        workdir = tempfile.mkdtemp(prefix="lsh-utils-consumer-")
        # lsh keeps its yarrow seed file under $HOME/.lsh, so give the tools a
        # private HOME inside the scratch directory.
        home = 'HOME="%s" ' % workdir
        askpass = os.path.join(workdir, "askpass")
        with open(askpass, "w") as handle:
            handle.write("#!/bin/sh\nprintf bar\n")
        os.chmod(askpass, 0o755)

        plain = os.path.join(workdir, "key.origkey")
        encrypted = os.path.join(workdir, "key")
        nevercrypted = os.path.join(workdir, "key.nevercrypted")
        decrypted = os.path.join(workdir, "key.decrypted")

        # 0. Seed the randomness generator (the tools refuse to run without it).
        self.run('%s"%s" -q --sloppy' % (home, makeseed), env="conanrun")

        # 1. RSA private key generation (libhogweed / gmp).
        self.run('%s"%s" > "%s"' % (home, keygen, plain), env="conanrun")
        if os.path.getsize(plain) == 0:
            raise AssertionError("lsh-keygen produced an empty key")

        # 2. Encrypt it with a passphrase, and keep an unencrypted copy.
        self.run('%s"%s" -c aes256-cbc -p bar -o "%s" < "%s"'
                 % (home, writekey, encrypted, plain), env="conanrun")
        self.run('%s"%s" -c none -o "%s" < "%s"'
                 % (home, writekey, nevercrypted, plain), env="conanrun")
        if not os.path.getsize(encrypted) or not os.path.getsize(nevercrypted):
            raise AssertionError("lsh-writekey produced no key material")

        # 3. Decrypt with the askpass helper; the result must match the
        #    unencrypted copy byte for byte.
        self.run('%s"%s" --in="%s" --out="%s" --askpass="%s"'
                 % (home, decryptkey, encrypted, decrypted, askpass),
                 env="conanrun")
        with open(decrypted, "rb") as left, open(nevercrypted, "rb") as right:
            if left.read() != right.read():
                raise AssertionError(
                    "decrypted private key differs from the unencrypted copy")

        self.output.info(
            "lsh-utils consumer test passed: lsh-keygen -> lsh-writekey "
            "(aes256-cbc) -> lsh-decrypt-key round trip is byte-identical")
