#!/usr/bin/env python3
"""Conan test_package for ca-certificates.

Verifies that:
1. Certificate files are installed in share/ca-certificates/mozilla/
2. A certificate can be parsed by openssl
3. The update-ca-certificates script exists
"""
import glob
import os

from conan import ConanFile


class CaCertificatesTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_root = str(self.dependencies["ca-certificates"].package_folder)

        # 1. Check certificate directory exists
        cert_dir = os.path.join(pkg_root, "share", "ca-certificates", "mozilla")
        assert os.path.isdir(cert_dir), f"Certificate dir not found: {cert_dir}"

        # 2. Count certificate files (expect 100+)
        crt_files = glob.glob(os.path.join(cert_dir, "*.crt"))
        assert len(crt_files) >= 100, \
            f"Expected 100+ certificates, found {len(crt_files)}"

        # 3. Verify a certificate is valid PEM using openssl
        test_crt = crt_files[0]
        ret = self.run(f'openssl x509 -in "{test_crt}" -noout -subject')
        assert ret == 0, f"openssl x509 verification failed with exit code {ret}"

        # 4. Check update-ca-certificates script exists
        sbin_path = os.path.join(pkg_root, "sbin", "update-ca-certificates")
        assert os.path.isfile(sbin_path), \
            "update-ca-certificates not found in sbin/"

        self.output.info(f"Verified {len(crt_files)} certificates")
