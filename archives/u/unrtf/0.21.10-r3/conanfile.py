#!/usr/bin/env python3
"""Conan recipe for GNU UnRTF 0.21.10-r3."""
import configparser
import hashlib
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, chdir, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnrtfConan(ConanFile):
    name = "unrtf"
    version = "0.21.10-r3"
    description = "GNU UnRTF converts Rich Text Format documents to HTML, text, LaTeX and other formats"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/unrtf/"
    url = ""
    package_type = "application"
    win_bash = True

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--datarootdir=${prefix}/share")
        tc.configure_args.append("--disable-maintainer-mode")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build_directory(self):
        build_tag = hashlib.sha1(os.path.normpath(self.build_folder).encode("utf-8")).hexdigest()[:12]
        base_dir = os.environ.get("TMPDIR") or self.build_folder
        return os.path.join(base_dir, f"{self.name}-{self.version}-{build_tag}")

    def configure_arguments(self):
        config = configparser.ConfigParser()
        config.read(os.path.join(self.generators_folder, "conanbuild.conf"))
        return config.get("toolchain", "configure_args")

    def write_mktemp_wrapper(self, build_dir):
        tools_dir = os.path.join(build_dir, "conan-tools")
        os.makedirs(tools_dir, exist_ok=True)
        wrapper = os.path.join(tools_dir, "mktemp")
        save(
            self,
            wrapper,
            """#!/usr/bin/env bash
set -e
for candidate in /storage/Users/currentUser/usr/local/bin/mktemp /system/bin/mktemp /bin/mktemp; do
  if [[ -x "$candidate" && "$candidate" != "$0" ]]; then
    umask 022
    exec "$candidate" "$@"
  fi
done
echo "mktemp: no real mktemp found" >&2
exit 127
""",
        )
        os.chmod(wrapper, 0o755)
        return tools_dir

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        build_dir = self.build_directory()
        os.makedirs(build_dir, exist_ok=True)
        with chdir(self, build_dir):
            if self.settings_build.get_safe("os") == "Windows":
                autotools.configure(build_script_folder=self.source_folder)
            else:
                configure_shell = os.environ.get("CONFIG_SHELL") or "bash"
                if os.path.isabs(configure_shell) and not os.path.exists(configure_shell):
                    configure_shell = "bash"
                os.environ["CONFIG_SHELL"] = configure_shell
                os.environ["SHELL"] = configure_shell
                os.environ["PATH"] = f"{self.write_mktemp_wrapper(build_dir)}:{os.environ.get('PATH', '')}"
                configure_script = os.path.join(self.source_folder, "configure")
                self.run(
                    f'CONFIG_SHELL="{configure_shell}" SHELL="{configure_shell}" '
                    f'"{configure_shell}" "{configure_script}" {self.configure_arguments()}'
                )
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        with chdir(self, self.build_directory()):
            autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
