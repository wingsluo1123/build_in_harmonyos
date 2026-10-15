#!/usr/bin/env python3
"""Conan recipe for X.Org libXrender 0.9.12."""

import os
import re
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibxrenderConan(ConanFile):
    name = "libxrender"
    version = "0.9.12.1"
    description = "X.Org X Render extension client library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxrender"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/6.4.0", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxrender supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"])
        local_archive = self.conf.get("user.libxrender:source_archive", default=None)
        if local_archive:
            archive_path = Path(local_archive).resolve()
            if not archive_path.is_file():
                raise ConanException(
                    f"LIBXRENDER_SOURCE_ARCHIVE is not a regular file: {archive_path}"
                )
            source["url"] = archive_path.as_uri()
            source["filename"] = archive_path.name
        get(self, **source, strip_root=True)

    def generate(self):
        self._prepare_linker_view()
        PkgConfigDeps(self).generate()
        toolchain = self._autotools_toolchain()
        environment = toolchain.environment()
        if str(self.settings.os) == "OHOS" and os.uname().sysname == "HarmonyOS":
            self._native_compiler_environment(environment)
        toolchain.generate(environment)

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._generate_ohos_configure()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._configure_ohos()
                self._run_ohos("make -j1")
                self._sign_elfs(self.build_folder)
                self._run_ohos("make -j1 check")
                self._record_upstream_inventory()
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        self._relocate_metadata()
        if str(self.settings.os) == "OHOS":
            self._sign_elfs(self.package_folder)
            self._materialize_aliases()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["Xrender"]
        self.cpp_info.requires = ["libx11::libx11", "xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "libxrender")
        self.cpp_info.set_property("cmake_target_name", "libxrender::libxrender")
        self.cpp_info.set_property("pkg_config_name", "xrender")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        if hasattr(self, "_linker_view"):
            environment.define("LD_LIBRARY_PATH", str(self._linker_view))
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _prepare_linker_view(self):
        """Use actual libraries without installed libtool archives or their RPATH."""
        linker_view = Path(self.build_folder, "linker-view")
        linker_view.mkdir(parents=True, exist_ok=True)
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for source in source_dir.iterdir():
                    if source.suffix not in (".a", ".so") or not source.is_file():
                        continue
                    destination = linker_view / source.name
                    shutil.copyfile(source, destination)
        self._linker_view = linker_view

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        library_args = (
            ("--enable-shared", "--disable-static")
            if self.options.shared
            else ("--disable-shared", "--enable-static")
        )
        toolchain.configure_args.extend(
            argument
            for argument in library_args
            if argument not in toolchain.configure_args
        )
        toolchain.extra_ldflags.append("-L" + self._linker_view.as_posix())
        return toolchain

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = self._ohos_configure_path()
        configure_args = [
            f"--srcdir={self.source_folder}",
            *self._autotools_toolchain().configure_args,
        ]
        arguments = " ".join(
            shlex.quote(argument)
            for argument in configure_args
        )
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        generated = self._ohos_configure_path()
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "xrender.pc")
        if not pc_path.is_file():
            raise ConanException("installed xrender.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("xrender.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        la_path = Path(self.package_folder, "lib", "libXrender.la")
        if la_path.is_file():
            la_path.unlink()

    def _native_compiler_environment(self, environment):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        for language, variable in [("c", "CC"), ("cpp", "CXX")]:
            configured = compilers.get(language)
            if not configured:
                continue
            header = Path(configured).read_bytes()
            mode = "--driver-mode=g++ " if language == "cpp" else ""
            expected = ('#!/bin/sh\nDIR="$(cd "$(dirname "$0")" && pwd)"\n'
                'exec "$DIR/clang-15" ' + mode + '--sysroot="$DIR/../sysroot" -fuse-ld=lld '
                '-Wl,--code-sign -L"$DIR/../sysroot/usr/lib/aarch64-linux-ohos" '
                '-D__MUSL__ "$@"\n').encode()
            if header != expected:
                continue
            directory = Path(configured).resolve().parent
            driver = directory / "clang-15"
            if driver.read_bytes()[:4] != b"\x7fELF":
                raise ConanException("Native raw Clang is not ELF")
            sysroot = directory.parent / "sysroot"
            arguments = [str(driver)] + (["--driver-mode=g++"] if language == "cpp" else [])
            arguments += ["--sysroot=" + str(sysroot), "-D__MUSL__"]
            environment.define(variable, shlex.join(arguments))
            environment.append("LDFLAGS", ["-fuse-ld=lld", "-Wl,--code-sign",
                "-L" + str(sysroot / "usr/lib/aarch64-linux-ohos")])

    def _sign_elfs(self, directory):
        signer = self.conf.get("user.libxrender:signer", default=None) or shutil.which("binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy")
        readelf = shutil.which("llvm-readelf")
        if not all(p and os.path.isfile(p) for p in [signer, objcopy, readelf]):
            raise ConanException("OHOS final-byte signing tools missing")
        import subprocess
        for path in sorted(Path(directory).rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            with path.open("rb") as stream:
                header = stream.read(20)
            if header[:4] != b"\x7fELF" or int.from_bytes(header[16:18], "little") not in (2, 3):
                continue
            if header[4:6] != b"\x02\x01" or int.from_bytes(header[18:20], "little") != 183:
                raise ConanException("Unexpected target ELF")
            subprocess.run([objcopy, "--remove-section", ".codesign", str(path)], check=True)
            temporary = str(path) + ".signed"
            subprocess.run([signer, "sign", "-inFile", str(path), "-outFile", temporary, "-selfSign", "1"], check=True)
            sections = subprocess.check_output([readelf, "-SW", temporary], text=True)
            if sections.count(".codesign") != 1:
                raise ConanException("Signed ELF section is not unique")
            os.chmod(temporary, (path.stat().st_mode & 0o777) | 0o055)
            os.replace(temporary, path)

    def _materialize_aliases(self):
        if not self.options.shared:
            return
        library = Path(self.package_folder, "lib", "libXrender.so.1.3.0")
        if not library.is_file() or library.is_symlink():
            raise ConanException("Versioned libXrender ELF missing")
        for name in ["libXrender.so.1", "libXrender.so"]:
            alias = library.parent / name
            if os.path.lexists(alias):
                alias.unlink()
            shutil.copyfile(library, alias)
            os.chmod(alias, library.stat().st_mode & 0o777)

    def _record_upstream_inventory(self):
        import hashlib
        import json
        inventory = []
        for path in sorted(Path(self.source_folder).rglob("Makefile.am")):
            content = path.read_text(encoding="utf-8")
            if re.search(r"(?m)^\s*(?:TESTS|check_PROGRAMS|check_LTLIBRARIES|check-local)\s*(?:[:+?]?=|:)", content):
                raise ConanException("Upstream test inventory changed")
            inventory.append({"path": str(path.relative_to(self.source_folder)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        if len(inventory) != 2:
            raise ConanException("Release Automake inventory changed")
        evidence = Path(self.build_folder, "libxrender-test-evidence")
        evidence.mkdir()
        (evidence / "upstream-inventory.json").write_text(json.dumps({
            "registered": 0, "executed": 0, "failed": 0, "skipped": 0,
            "source_root": self.source_folder, "registration_files": inventory,
            "check_command": "make -j1 check", "check_rc": 0}), encoding="utf-8")
        self.output.info("UPSTREAM_TEST_COUNT=0 (no suite); make check RC=0")
