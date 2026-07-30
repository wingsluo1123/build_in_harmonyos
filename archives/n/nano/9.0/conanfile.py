#!/usr/bin/env python3
"""Conan recipe for GNU nano 9.0."""

import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NanoConan(ConanFile):
    name = "nano"
    version = "9.0"
    description = "Small and friendly command-line text editor"
    license = "GPL-3.0-or-later"
    homepage = "https://www.nano-editor.org/"
    url = "https://git.savannah.gnu.org/cgit/nano.git"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        get(self, **sources["nano"], strip_root=True)
        get(
            self,
            **sources["ncurses"],
            destination=self._ncurses_source_folder(),
            strip_root=True,
        )

    def _ncurses_source_folder(self):
        return os.path.join(self.source_folder, "_ncurses")

    def _ncurses_prefix(self):
        return os.path.join(self.build_folder, "ncurses-prefix")

    @staticmethod
    def _settings_triplet(settings):
        arch = str(settings.arch)
        machine = {
            "x86": "i686",
            "x86_64": "x86_64",
            "armv8": "aarch64",
            "armv8_32": "aarch64",
            "armv8.3": "aarch64",
        }.get(arch)
        if machine is None and arch.startswith("arm"):
            machine = "arm"
        if machine is None:
            raise ConanInvalidConfiguration(
                f"Cannot derive a GNU triplet for architecture {arch}"
            )

        os_name = str(settings.os)
        system = {
            "Linux": "linux-gnu",
            "OHOS": "linux-ohos",
        }.get(os_name)
        if system is None:
            raise ConanInvalidConfiguration(
                f"Cannot derive a GNU triplet for operating system {os_name}"
            )
        if machine == "arm":
            system += "eabi"
            if arch in ("armv5hf", "armv7hf"):
                system += "hf"
        elif arch == "armv8_32":
            system += "_ilp32"
        return f"{machine}-{system}"

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        include_dir = os.path.join(self._ncurses_prefix(), "include")
        library_dir = os.path.join(self._ncurses_prefix(), "lib")
        toolchain.extra_cflags.extend(
            [f"-I{include_dir}", f"-I{os.path.join(include_dir, 'ncursesw')}"]
        )
        toolchain.extra_ldflags.append(f"-L{library_dir}")
        toolchain.configure_args.extend(
            ["--disable-nls", "--disable-libmagic", "--disable-speller"]
        )
        toolchain.generate()

    def _build_ncurses(self):
        build_folder = self._ncurses_source_folder()

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c")
        cxx = compiler_executables.get("cpp")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define c and cpp"
            )

        host_triplet = self.conf.get(
            "tools.gnu:host_triplet"
        ) or self._settings_triplet(self.settings)
        build_triplet = self.conf.get(
            "tools.gnu:build_triplet"
        ) or self._settings_triplet(self.settings_build)

        configure_args = [
            "./configure",
            f"--prefix={self._ncurses_prefix()}",
            f"--build={build_triplet}",
            f"--host={host_triplet}",
            "--without-shared",
            "--with-normal",
            "--enable-widec",
            "--with-termlib",
            "--without-cxx",
            "--without-cxx-binding",
            "--without-progs",
            "--without-tests",
            "--without-manpages",
        ]
        build_env = Environment()
        build_env.define("CC", cc)
        build_env.define("CXX", cxx)
        build_env.define("CFLAGS", "-fPIC")
        build_env.define("CPPFLAGS", "-D_GNU_SOURCE")
        with build_env.vars(self).apply():
            self.run(shlex.join(configure_args), cwd=build_folder)
            self.run("make -j1", cwd=build_folder)
            self.run("make install.libs install.includes", cwd=build_folder)

    def build(self):
        apply_conandata_patches(self)
        bash_path = shutil.which("bash")
        shell_env = Environment()
        if bash_path:
            shell_env.define("CONFIG_SHELL", bash_path)
            shell_env.define("SHELL", bash_path)
        tmpdir = os.environ.get("TMPDIR") or tempfile.gettempdir()
        if not os.path.isdir(tmpdir) or not os.access(tmpdir, os.W_OK):
            raise ConanInvalidConfiguration(
                "TMPDIR must identify a writable temporary directory"
            )
        shell_env.define("TMPDIR", tmpdir)

        with shell_env.vars(self).apply():
            self._build_ncurses()

            ncurses_include = os.path.join(
                self._ncurses_prefix(), "include", "ncursesw"
            )
            ncurses_lib = os.path.join(self._ncurses_prefix(), "lib")
            nano_env = Environment()
            nano_env.define("NCURSESW_CFLAGS", f"-I{ncurses_include}")
            nano_env.define(
                "NCURSESW_LIBS", f"-L{ncurses_lib} -lncursesw -ltinfow"
            )

            autotools = Autotools(self)
            with nano_env.vars(self).apply():
                autotools.configure()
                autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "COPYING",
            src=self._ncurses_source_folder(),
            dst=os.path.join(self.package_folder, "licenses", "ncurses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
