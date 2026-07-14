#!/usr/bin/env python3
"""Conan recipe — dante 1.4.4 (Autotools)

SOCKS server and client, implementing RFC 1928 and related standards.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class DanteConan(ConanFile):
    name = "dante"
    version = "1.4.4"
    description = "SOCKS server and client implementing RFC 1928 and related standards"
    license = "BSD-Inferno-Nettverk"
    homepage = "https://www.inet.no/dante/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # dante's configure uses relative paths (libscompat/), so build in-source
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Dante requires help2man/makeinfo which may not be available on OHOS
        tc.configure_args.append("HELP2MAN=/bin/true")
        tc.configure_args.append("MAKEINFO=/bin/true")
        tc.generate()
        # OHOS: use bash as CONFIG_SHELL (system /bin/sh is mksh, lacks some features)
        if self.settings.os in ("Linux", "OHOS"):
            env = Environment()
            env.define("CONFIG_SHELL", "bash")
            envvars = env.vars(self)
            envvars.save_script("env_overrides")

    def build(self):
        apply_conandata_patches(self)

        # E011: Fix HMDFS permission issues in configure (umask 077 + mktemp)
        if self.settings.os in ("Linux", "OHOS"):
            self._fix_hmdfs_issues()

        autotools = Autotools(self)
        autotools.configure()

        # After configure: apply platform-specific fixes
        if self.settings.os in ("Linux", "OHOS"):
            self._apply_ohos_macros()
            self._fix_missing_symbols()
            self._fix_shebangs()
            self._disable_recheck()

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = ["socks"]
        self.cpp_info.bindirs = ["sbin", "bin"]

    def _fix_hmdfs_issues(self):
        """Fix HMDFS permission issues in configure and config.status (E011)."""
        for script in ["configure", "config.status"]:
            path = os.path.join(self.source_folder, script)
            if not os.path.exists(path):
                continue
            with open(path, "r") as f:
                content = f.read()
            # Remove umask 077 (causes permission issues on HMDFS)
            content = content.replace("umask 077", "umask 022")
            # Fix mktemp to use TMPDIR instead of relative paths
            content = re.sub(
                r'mktemp\s+"?\./confXXXXXX"?',
                'mktemp "${TMPDIR:-/tmp}/confXXXXXX"',
                content,
            )
            with open(path, "w") as f:
                f.write(content)

    def _apply_ohos_macros(self):
        """Add OHOS platform macros to autoconf.h after configure."""
        autoconf_path = os.path.join(self.source_folder, "include", "autoconf.h")
        if not os.path.exists(autoconf_path):
            return
        with open(autoconf_path, "r") as f:
            lines = f.readlines()
        macros = {
            "HAVE_NO_RESOLVESTUFF": ("1", "musl libc does not support _res global variable"),
            "HAVE_SCHED_SETAFFINITY": ("0", "cpu_set_t not available on OHOS"),
            "HAVE_CPU_EQUAL": ("0", "cpu_set_t not available on OHOS"),
        }
        for name, (value, comment) in macros.items():
            replacement = f"#define {name} {value}  /* {comment} */\n"
            found = False
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Match active #define (not inside comment)
                if re.match(rf"^#define\s+{name}\s+\S+", stripped):
                    lines[i] = replacement
                    found = True
                    break
                # Match #undef
                elif stripped == f"#undef {name}":
                    lines[i] = replacement
                    found = True
                    break
                # Match commented-out #define: /* #define NAME ... */
                elif re.match(rf"^/\*\s*#define\s+{name}\s", stripped):
                    lines[i] = replacement
                    found = True
                    break
            if not found:
                lines.append(replacement)
        with open(autoconf_path, "w") as f:
            f.writelines(lines)

    def _fix_missing_symbols(self):
        """Remove symbols for functions not available on OHOS from socks.sym files."""
        missing = {"bindresvport", "rresvport", "Rbindresvport", "Rrresvport"}
        for sym_file in ["dlib/socks.sym", "lib/socks.sym"]:
            path = os.path.join(self.source_folder, sym_file)
            if not os.path.exists(path):
                continue
            with open(path, "r") as f:
                lines = f.readlines()
            lines = [l for l in lines if l.strip() not in missing]
            with open(path, "w") as f:
                f.writelines(lines)

    def _fix_shebangs(self):
        """Fix shebangs in scripts: /bin/bash -> /data/service/hnp/bin/bash (E165)."""
        bash_path = "/data/service/hnp/bin/bash"
        sh_path = "/system/bin/sh"
        for dirpath, _, filenames in os.walk(self.source_folder):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                if not os.path.isfile(fpath):
                    continue
                try:
                    with open(fpath, "r") as f:
                        first_line = f.readline()
                    if first_line.startswith("#!/bin/bash"):
                        self._replace_first_line(fpath, f"#!{bash_path}\n")
                    elif first_line.startswith("#!/bin/sh"):
                        self._replace_first_line(fpath, f"#!{sh_path}\n")
                except (UnicodeDecodeError, PermissionError):
                    continue

    @staticmethod
    def _replace_first_line(fpath, new_first_line):
        with open(fpath, "r") as f:
            lines = f.readlines()
        if lines:
            lines[0] = new_first_line
            with open(fpath, "w") as f:
                f.writelines(lines)

    @staticmethod
    def _disable_recheck():
        """Disable config.status --recheck in Makefile to avoid reconfiguration."""
        makefile_path = "Makefile"
        if not os.path.exists(makefile_path):
            return
        with open(makefile_path, "r") as f:
            content = f.read()
        content = re.sub(r"config\.status\s*--recheck", "config.status", content)
        with open(makefile_path, "w") as f:
            f.write(content)
