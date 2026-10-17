#!/usr/bin/env python3
"""Conan recipe for uruk 20260218 (POSIX shell scripts)."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UrukConan(ConanFile):
    name = "uruk"
    version = "20260218"
    description = "Shell-based iptables firewall configuration front end"
    license = "GPL-3.0-or-later"
    homepage = "https://mdcc.cx/uruk/"
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

    def _get_bash(self):
        candidates = [
            os.environ.get("BASH"),
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            "/usr/bin/bash",
            "/bin/bash",
            shutil.which("bash"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return "/data/service/hnp/bin/bash"

    @staticmethod
    def _rewrite_shebang(source, destination, interpreter):
        with open(source, encoding="utf-8") as handle:
            lines = handle.read().splitlines(True)
        if lines and lines[0].startswith("#!"):
            first = lines[0].rstrip("\r\n")
            flags = first[2:].strip()
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
        bash = self._get_bash()
        for script in ("uruk", "urukctl", "uruk-save"):
            self.run(
                '"%s" -n "%s"'
                % (bash, os.path.join(self.source_folder, "script", script)),
                env="conanrun",
            )

    def package(self):
        source = os.path.join(self.source_folder, "script")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        bash = self._get_bash()
        for script in ("uruk", "urukctl", "uruk-save"):
            destination = os.path.join(bin_dir, script)
            self._rewrite_shebang(
                os.path.join(source, script), destination, bash
            )
            os.chmod(destination, 0o755)

        doc_dir = os.path.join(self.package_folder, "share", "doc", "uruk")
        for name in ("README", "COPYING", "AUTHORS", "ChangeLog"):
            copy(self, name, src=self.source_folder, dst=doc_dir)
        copy(self, "uruk.8", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "urukctl.8", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "uruk-save.8", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
