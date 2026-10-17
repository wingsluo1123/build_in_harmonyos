#!/usr/bin/env python3
"""Conan recipe for tran 5 (Perl filter and data tables)."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TranConan(ConanFile):
    name = "tran"
    description = "Perl text transliteration filter with pluggable character tables"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kilobyte/tran"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def set_version(self):
        # The task directory and branch keep the upstream release number 5.
        # Conan requires at least two characters, so the artifact is 5.0.
        self.version = "5.0"

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

    def _render_script(self, destination, keep_flags=True):
        source = os.path.join(self.source_folder, "tran")
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
        if not keep_flags:
            flags = ""
        lines[0] = "#!%s%s\n" % (self._get_perl(), " " + flags if flags else "")
        content = "".join(lines)
        content = content.replace(
            "use strict;", "use strict;\nuse FindBin;", 1
        )
        content = content.replace('my $DATA="data";', 'my $DATA="";', 1)
        content = content.replace(
            "read_config($DATA);",
            'read_config($DATA eq "" ? "$FindBin::RealBin/data" : $DATA);',
            1,
        )
        with open(destination, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.chmod(destination, 0o755)

    def build(self):
        rendered = os.path.join(self.build_folder, "tran-check")
        self._render_script(rendered, keep_flags=False)
        self.run('"%s" -c "%s"' % (self._get_perl(), rendered), env="conanrun")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "tran")
        os.makedirs(bin_dir, exist_ok=True)
        self._render_script(os.path.join(bin_dir, "tran"))
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "data"),
            dst=os.path.join(bin_dir, "data"),
        )
        for name in ("README", "LICENSE", "tran.pod"):
            copy(self, name, src=self.source_folder, dst=doc_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
