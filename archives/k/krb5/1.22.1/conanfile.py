#!/usr/bin/env python3
"""Conan recipe for MIT Kerberos 5 (krb5).

Build system: autotools (configure in src/ subdirectory)
Patches: config.guess/sub update, configure TMPDIR/umask fix, dnsglue.c musl fix
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Krb5Conan(ConanFile):
    name = "krb5"
    version = "1.22.1"
    description = "MIT Kerberos 5 - network authentication protocol"
    license = "MIT"
    homepage = "https://web.mit.edu/kerberos/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("krb5 is only supported on Linux/OHOS")

    def source(self):
        # Download using curl (Conan's get() has issues with MIT server)
        import tarfile
        from conan.tools.files import check_sha256
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        filename = "krb5-1.22.1.tar.gz"
        tarball = os.path.join(self.source_folder, filename)
        self.run(f'curl -L -k -o "{tarball}" "{url}"', cwd=self.source_folder)
        check_sha256(self, tarball, sha256)
        # Extract
        with tarfile.open(tarball, "r:gz") as tar:
            tar.extractall(path=self.source_folder)
        os.remove(tarball)
        # Move krb5-1.22.1/ contents to source_folder root
        import glob
        extracted = os.path.join(self.source_folder, "krb5-1.22.1")
        if os.path.isdir(extracted):
            for item in os.listdir(extracted):
                src_path = os.path.join(extracted, item)
                dst_path = os.path.join(self.source_folder, item)
                if os.path.exists(dst_path):
                    if os.path.isdir(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                shutil.move(src_path, dst_path)
            os.rmdir(extracted)
        # krb5 source is in src/ subdirectory, promote to root
        src_dir = os.path.join(self.source_folder, "src")
        if os.path.isdir(src_dir):
            for item in os.listdir(src_dir):
                src_path = os.path.join(src_dir, item)
                dst_path = os.path.join(self.source_folder, item)
                if os.path.exists(dst_path):
                    if os.path.isdir(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                shutil.move(src_path, dst_path)
            os.rmdir(src_dir)

    def build(self):
        apply_conandata_patches(self)

        # Ensure TMPDIR exists for HarmonyOS (E082: umask 077 + SGID issue)
        tmpdir = os.environ.get("TMPDIR", "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        prefix = self.package_folder
        configure_cmd = f"./configure --prefix={prefix}"
        if not self.options.shared:
            configure_cmd += " --enable-static --disable-shared"

        self.run(configure_cmd, cwd=self.source_folder)
        self.run("make -e -j1", cwd=self.source_folder)

    def package(self):
        self.run("make install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = [
            "krb5",
            "gssapi_krb5",
            "k5crypto",
            "com_err",
            "gssrpc",
            "kadm5clnt_mit",
            "kadm5srv_mit",
            "kdb5",
            "krad",
            "krb5support",
            "verto",
        ]
        self.cpp_info.set_property("cmake_file_name", "krb5")
        self.cpp_info.set_property("cmake_target_name", "krb5::krb5")
