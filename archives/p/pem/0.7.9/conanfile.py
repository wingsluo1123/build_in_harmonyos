#!/usr/bin/env python3
"""Conan recipe for GNU Pem 0.7.9 (Perl script)."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PemConan(ConanFile):
    name = "pem"
    version = "0.7.9"
    description = "Personal income and expense tracker with CSV storage and reports"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/pem/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _get_perl(self):
        candidates = [
            os.environ.get("PERL"),
            "/data/service/hnp/bin/perl",
            "/usr/bin/perl",
            "/usr/local/bin/perl",
            shutil.which("perl"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return "/data/service/hnp/bin/perl"

    @staticmethod
    def _rewrite_shebang(source, destination, interpreter):
        with open(source, encoding="utf-8") as handle:
            lines = handle.read().splitlines(True)
        first = lines[0].rstrip("\r\n")
        flags = first[2:].strip() if first.startswith("#!") else ""
        parts = flags.split()
        if parts and os.path.basename(parts[0]) == "env":
            parts = parts[1:]
        if parts:
            parts = parts[1:]
        flags = " ".join(parts)
        lines[0] = "#!%s%s\n" % (interpreter, " " + flags if flags else "")
        with open(destination, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(lines))

    def build(self):
        self.run(
            '"%s" -c "%s"'
            % (self._get_perl(), os.path.join(self.source_folder, "pem.pl")),
            env="conanrun",
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "pem")
        os.makedirs(bin_dir, exist_ok=True)
        destination = os.path.join(bin_dir, "pem")
        self._rewrite_shebang(
            os.path.join(self.source_folder, "pem.pl"), destination, self._get_perl()
        )
        os.chmod(destination, 0o755)
        copy(self, "pem.1", src=self.source_folder, dst=man_dir)
        for name in ("README", "COPYING", "pem.txt", "pem.info"):
            copy(self, name, src=self.source_folder, dst=doc_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
