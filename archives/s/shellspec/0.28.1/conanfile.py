#!/usr/bin/env python3
"""Conan recipe for shellspec 0.28.1 — pure Shell script BDD testing framework.

shellspec is a BDD testing framework for POSIX shell scripts.
It is a pure Shell script project with no compilation step; "installation"
consists of running `make install` to copy scripts to bin/ and lib/.

Patches:
  0001-Makefile.patch: Add DESTDIR variable support + make `all` target a no-op

The configure wrapper is created in build() rather than via a patch file,
because refresh-patch only tracks modified files, not new files.

R32: /bin/sh exists on OHOS, no shebang fix needed.
R28: test_package/ exists.
R38: CLI tool — commands.json declared at software level.
R39: Source URL is official GitHub archive/tag URL.
"""
import os
import hashlib

from conan import ConanFile
from conan.tools.files import unzip, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ShellspecConan(ConanFile):
    name = "shellspec"
    version = "0.28.1"
    description = "BDD testing framework for POSIX shell scripts"
    license = "MIT"
    homepage = "https://github.com/shellspec/shellspec"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        urls = sources["url"]
        if isinstance(urls, str):
            urls = [urls]
        sha256 = sources["sha256"]
        sha256_alt = sources.get("sha256_alt")
        accepted_sha256 = {sha256}
        if sha256_alt:
            accepted_sha256.add(sha256_alt)
        filename = "source.tar.gz"

        archive_path = os.path.join(self.source_folder, filename)

        # Use curl — CI workers may lack Python ssl module for HTTPS
        for url in urls:
            try:
                self.run(f'curl -L -sS --fail -o "{archive_path}" "{url}"',
                         cwd=self.source_folder)
                if os.path.exists(archive_path) and os.path.getsize(archive_path) > 0:
                    break
            except Exception:
                continue
        else:
            raise RuntimeError(f"Failed to download from any URL: {urls}")

        # Verify sha256
        h = hashlib.sha256()
        with open(archive_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        if h.hexdigest() not in accepted_sha256:
            raise RuntimeError(f"SHA256 mismatch: expected one of {accepted_sha256}, got {h.hexdigest()}")

        unzip(self, archive_path, self.source_folder, strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # Create configure wrapper (shellspec has no configure script)
        configure_path = os.path.join(src, "configure")
        if not os.path.exists(configure_path):
            with open(configure_path, "w") as f:
                f.write("#!/bin/sh\n")
                f.write("# shellspec configure wrapper\n")
                f.write("echo \"shellspec is a pure Shell project\"\n")
                f.write("exit 0\n")
            os.chmod(configure_path, 0o755)

        # shellspec is a pure shell project, no build step needed
        self.run("make all", cwd=src)

    def package(self):
        src = self.source_folder
        self.run(f"make install PREFIX={self.package_folder}", cwd=src)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
