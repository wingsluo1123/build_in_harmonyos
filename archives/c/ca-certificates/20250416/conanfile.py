#!/usr/bin/env python3
"""Conan recipe for ca-certificates — Mozilla CA root certificate bundle.

This is a data-only package: no compilation, only certificate generation
from Mozilla's certdata.txt using certdata2pem.py.

The certdata2pem.py script depends on Python's `cryptography` module.
On HarmonyOS, the cryptography module's Rust bindings (.so) have
permission issues. A lightweight shim using OpenSSL CLI is generated
at build time, providing the same x509 API without modifying
certdata2pem.py.
"""
import os
import textwrap

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CaCertificatesConan(ConanFile):
    name = "ca-certificates"
    version = "20250416"
    description = "Mozilla CA root certificate bundle for TLS trust"
    license = "MPL-2.0"
    homepage = "https://salsa.debian.org/debian/ca-certificates"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Generate the cryptography shim that uses OpenSSL CLI.
        # The real cryptography module's Rust .so has permission issues on OHOS.
        self._generate_cryptography_shim()

        # Run certdata2pem.py unmodified — no trimming.
        # PYTHONPATH points to the shim so the cryptography module is resolved.
        moz_dir = os.path.join(self.build_folder, "mozilla")
        shim_dir = os.path.join(self.build_folder, "cryptography_shim")
        self.run(f'PYTHONPATH={shim_dir}${{PYTHONPATH:+:$PYTHONPATH}} '
                 f'python3 certdata2pem.py', cwd=moz_dir)

    def _generate_cryptography_shim(self):
        """Create a minimal cryptography.x509 shim backed by OpenSSL CLI."""
        base = os.path.join(self.build_folder, "cryptography_shim")
        # Package directories
        for d in ["cryptography", "cryptography/x509",
                   "cryptography/hazmat",
                   "cryptography/hazmat/bindings",
                   "cryptography/hazmat/bindings/_rust"]:
            os.makedirs(os.path.join(base, d), exist_ok=True)
        # __init__.py stubs
        for rel in ["cryptography/__init__.py",
                     "cryptography/hazmat/__init__.py",
                     "cryptography/hazmat/bindings/__init__.py",
                     "cryptography/hazmat/bindings/_rust/__init__.py"]:
            path = os.path.join(base, rel)
            if not os.path.exists(path):
                with open(path, "w") as f:
                    f.write("# Shim package\n")
        # The actual x509 shim
        x509_init = os.path.join(base, "cryptography", "x509", "__init__.py")
        with open(x509_init, "w") as f:
            f.write(textwrap.dedent("""\
                import datetime
                import os
                import shutil
                import subprocess
                import tempfile

                _OPENSSL = shutil.which("openssl") or "/bin/openssl"


                class Certificate:
                    def __init__(self, der_data):
                        self._der_data = der_data
                        self._not_valid_after = None
                        self._parse()

                    def _parse(self):
                        fd, tmpfile = tempfile.mkstemp(suffix=".der")
                        os.write(fd, self._der_data)
                        os.close(fd)
                        try:
                            result = subprocess.run(
                                [_OPENSSL, "x509", "-inform", "der",
                                 "-in", tmpfile, "-noout", "-enddate"],
                                capture_output=True, text=True, timeout=10
                            )
                            if result.returncode == 0:
                                line = result.stdout.strip()
                                if line.startswith("notAfter="):
                                    date_str = line.split("=", 1)[1].strip()
                                    self._not_valid_after = datetime.datetime.strptime(
                                        date_str, "%b %d %H:%M:%S %Y %Z"
                                    )
                        except Exception:
                            pass
                        finally:
                            if os.path.exists(tmpfile):
                                os.unlink(tmpfile)

                    @property
                    def not_valid_after(self):
                        return self._not_valid_after


                def load_der_x509_certificate(data):
                    return Certificate(data)
            """))

    def package(self):
        # Copy generated certificate files
        copy(self, "*.crt",
             src=os.path.join(self.build_folder, "mozilla"),
             dst=os.path.join(self.package_folder, "share/ca-certificates/mozilla"))

        # Copy update-ca-certificates script
        copy(self, "update-ca-certificates",
             src=os.path.join(self.build_folder, "sbin"),
             dst=os.path.join(self.package_folder, "sbin"))

    def package_info(self):
        self.cpp_info.resdirs = ["share/ca-certificates"]
        self.cpp_info.bindirs = ["sbin"]
