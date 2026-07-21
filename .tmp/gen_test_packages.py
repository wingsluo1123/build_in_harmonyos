import os

BASE = "/storage/Users/currentUser/build_in_harmonyos/archives/p"

packages = [
    ("perl-crypt-openssl-dsa", "0.20", "DSA", "boot_Crypt__OpenSSL__DSA", "lib/auto/Crypt/OpenSSL/DSA", "Crypt::OpenSSL::DSA"),
    ("perl-dbi", "1.637", "DBI", "boot_DBI", "lib/auto/DBI", "DBI"),
    ("perl-devel-lexalias", "0.05", "LexAlias", "boot_Devel__LexAlias", "lib/auto/Devel/LexAlias", "Devel::LexAlias"),
    ("perl-digest-md5", "2.59", "MD5", "boot_Digest__MD5", "lib/auto/Digest/MD5", "Digest::MD5"),
    ("perl-digest-sha1", "2.13", "SHA1", "boot_Digest__SHA1", "lib/auto/Digest/SHA1", "Digest::SHA1"),
    ("perl-digest-sha3", "1.01", "SHA3", "boot_Digest__SHA3", "lib/auto/Digest/SHA3", "Digest::SHA3"),
    ("perl-encode-jis2k", "0.05-r2", "JIS2K", "boot_Encode__JIS2K", "lib/auto/Encode/JIS2K", "Encode::JIS2K"),
    ("perl-ev", "4.37", "EV", "boot_EV", "lib/auto/EV", "EV"),
    ("perl-html-parser", "3.83-r1", "Parser", "boot_HTML__Parser", "lib/auto/HTML/Parser", "HTML::Parser"),
    ("perl-io-tty", "1.31", "Tty", "boot_IO__Tty", "lib/auto/IO/Tty", "IO::Tty"),
    ("perl-ipc-sharelite", "0.17-r14", "ShareLite", "boot_IPC__ShareLite", "lib/auto/IPC/ShareLite", "IPC::ShareLite"),
    ("perl-json-xs", "4.04", "XS", "boot_JSON__XS", "lib/auto/JSON/XS", "JSON::XS"),
    ("perl-match-simple-xs", "0.002", "XS", "boot_match__simple__XS", "lib/auto/match/simple/XS", "match::simple::XS"),
    ("perl-math-random-mt-auto", "6.23-r10", "Auto", "boot_Math__Random__MT__Auto", "lib/auto/Math/Random/MT/Auto", "Math::Random::MT::Auto"),
    ("perl-mime-base64", "3.16", "Base64", "boot_MIME__Base64", "lib/auto/MIME/Base64", "MIME::Base64"),
    ("perl-perlio-utf8_strict", "0.010", "utf8_strict", "boot_PerlIO__utf8_strict", "lib/auto/PerlIO/utf8_strict", "PerlIO::utf8_strict"),
    ("perl-netaddr-ip", "4.079", "Util", "boot_NetAddr__IP__Util", "lib/auto/NetAddr/IP/Util", "NetAddr::IP::Util"),
]

for pkg_name, version, so_name, boot_sym, libdirs, module_desc in packages:
    pkg_dir = os.path.join(BASE, pkg_name, version)
    test_pkg_dir = os.path.join(pkg_dir, "test_package")
    os.makedirs(test_pkg_dir, exist_ok=True)
    
    test_content = f'''#!/usr/bin/env python3
"""Conan test_package — {module_desc} Perl XS module.

Verifies that the package contains a valid .so artifact:
- Shared library (valid ELF magic)
- boot symbol ({boot_sym}) present via nm -D
"""
import os
import subprocess

from conan import ConanFile


class TestPackageConan(ConanFile):
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["{pkg_name}"]
        pkg_folder = dep.package_folder

        self.output.info(f"Package folder: {{pkg_folder}}")

        # Walk package folder to find .so files
        so_files = []
        for root, dirs, files in os.walk(pkg_folder):
            for f in files:
                if f.endswith(".so"):
                    so_files.append(os.path.join(root, f))

        assert so_files, f"No .so files found in package {{pkg_folder}}"
        so_path = so_files[0]
        self.output.info(f"Found .so: {{so_path}}")

        # Verify ELF magic number
        with open(so_path, "rb") as fh:
            magic = fh.read(4)
            assert magic == b"\\x7fELF", f"Not ELF format: magic={{magic}} for {{so_path}}"

        # Verify boot symbol exists via nm -D
        result = subprocess.run(
            ["nm", "-D", so_path],
            capture_output=True, text=True
        )
        assert "{boot_sym}" in result.stdout, (
            f"Boot symbol '{boot_sym}' not found in {{so_path}}\\n"
            f"nm -D output:\\n{{result.stdout}}"
        )

        self.output.info(f"OK: {so_name}.so verified (ELF + {boot_sym})")
'''
    
    test_path = os.path.join(test_pkg_dir, "conanfile.py")
    with open(test_path, "w") as f:
        f.write(test_content)
    print(f"Created: {test_path}")

print(f"\nTotal: {len(packages)} test_package/conanfile.py files created")
