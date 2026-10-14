from conan.tools.files import replace_in_file
from conan.tools.env import Environment
"""libwmf 0.2.15 with its upstream converter regression suite."""

import hashlib
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibwmfConan(ConanFile):
    name = "libwmf"
    version = "0.2.15"
    package_type = "shared-library"
    description = "Windows Metafile decoding and conversion library"
    homepage = "https://github.com/caolanm/libwmf"
    license = "LGPL-2.0-or-later"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("freetype/2.14.3", transitive_headers=True)
        self.requires("libpng/1.6.58")
        self.requires("zlib/1.3.1.1")
        self.requires("expat/2.8.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBWMF_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local libwmf source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("OHOS ELF signer/readelf missing")
        original = Path(path)
        if not original.is_file() or original.is_symlink():
            raise ConanException("missing real libwmf ELF: " + str(original))
        signed = original.with_name(original.name + ".signed")
        if signed.exists():
            raise ConanInvalidConfiguration("stale signed ELF sibling")
        try:
            subprocess.run([signer, "sign", "-inFile", str(original),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed libwmf ELF lacks .codesign")
            os.chmod(signed, original.stat().st_mode)
            os.replace(signed, original)
        finally:
            if signed.exists():
                signed.unlink()

    def _dependency_loader(self):
        libdirs = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                path = Path(libdir)
                if not path.is_absolute():
                    path = Path(dependency.package_folder, libdir)
                if path.is_dir() and str(path) not in libdirs:
                    libdirs.append(str(path))
        if not libdirs:
            raise ConanException("missing Conan dependency library directories")
        return ":".join(libdirs)

    def build(self):
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            # mktemp -d fixes mode 0700 independently of the caller's umask.
            # Use exclusive creation in task-private TMPDIR, not chmod on
            # shared filesystem paths, and preserve config.status cleanup.
            configure = os.path.join(self.source_folder, "configure")
            replacements = (
                ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 007 && mkdir "$tmp") &&'),
                ('tmp=./conf$$-$RANDOM', 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"'),
                ('(umask 077 && mkdir "$tmp")', '(umask 007 && mkdir "$tmp")'),
            )
            for original, replacement in replacements:
                replace_in_file(self, configure, original, replacement, strict=True)
            scratch = Path(self.build_folder, ".autoconf-tmp")
            previous_umask = os.umask(0o007)
            try:
                scratch.mkdir(mode=0o770, exist_ok=False)
            finally:
                os.umask(previous_umask)
            environment.define("TMPDIR", str(scratch))
        with environment.vars(self).apply():
            self._build_with_autoconf_tmpdir()

    def _build_with_autoconf_tmpdir(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._native_config_helpers()
        autotools = Autotools(self)
        loader = self._dependency_loader()
        prefix = "LD_LIBRARY_PATH=" + shlex.quote(loader) + "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
        configure = shlex.quote(str(Path(self.source_folder, "configure")))
        self.run(f"{prefix} {configure} {autotools._configure_args} "
                 "--disable-static --enable-shared --with-expat=yes "
                 "--with-libxml2=no --disable-gd --with-jpeg=no",
                 cwd=self.build_folder, env=["conanbuild", "conanrun"])
        autotools.make(args=["-j1"])
        if str(self.settings.os) == "OHOS":
            real_libs = [p for p in Path(self.build_folder, "src", ".libs").glob("libwmf*.so*")
                         if p.is_file() and not p.is_symlink()]
            if len(real_libs) != 2:
                raise ConanException("expected libwmf and libwmflite shared libraries")
            for library in real_libs:
                self._sign_elf(library)
            for name in ("wmf2svg", "wmf2eps", "wmf2fig"):
                real = Path(self.build_folder, "src", "convert", ".libs", name)
                outer = Path(self.build_folder, "src", "convert", name)
                if not real.is_file() or not outer.is_file():
                    raise ConanException("missing converter and Libtool wrapper: " + name)
                self._sign_elf(real)
                shutil.copy2(real, outer)
        test_loader = shlex.quote(str(Path(self.build_folder, "src", ".libs")) + ":" + loader)
        self.run(f"LD_LIBRARY_PATH={test_loader}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}} "
                 "make -j1 check LOG_COMPILER=/bin/sh",
                 cwd=self.build_folder, env=["conanbuild", "conanrun"])
        self.output.info("LIBWMF_UPSTREAM_1_OF_1_PASS")

    def _native_config_helpers(self):
        # The release ships generated configure and a 2024 config.sub which
        # already accepts linux-ohos. No ambient Automake is needed at build time.
        auxdir = Path(self.source_folder, "build-aux")
        expected_aux = {
            "config.guess": "84339878730349f6ae49d0e10af84d6a52f937dffb652032584376d76822a002",
            "config.sub": "d047a2613db0e587c9a9ab64f4ba0eb304421a6501ea8653a06c179eb57952be",
        }
        backup = Path(self.build_folder, ".autoconf-aux-backup")
        backup.mkdir(mode=0o770, exist_ok=False)
        for name, expected in expected_aux.items():
            source = auxdir / name
            if not source.is_file() or source.is_symlink():
                raise ConanInvalidConfiguration("invalid bundled config helper: " + name)
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise ConanInvalidConfiguration("unverified bundled config helper: " + name)
            shutil.copy2(source, backup / name)
            if hashlib.sha256((backup / name).read_bytes()).hexdigest() != expected:
                raise ConanException("config helper backup mismatch: " + name)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("c") or "clang"
        target = subprocess.run(shlex.split(compiler) + ["-dumpmachine"], check=True,
                                capture_output=True, text=True, timeout=20).stdout.strip()
        if not re.fullmatch(r"aarch64(?:-[A-Za-z0-9_.]+)?-linux-ohos", target):
            raise ConanInvalidConfiguration("unexpected native OHOS compiler tuple: " + target)
        canonical = subprocess.run(["/bin/sh", str(auxdir / "config.sub"), target], check=True,
                                   capture_output=True, text=True, timeout=20).stdout.strip()
        if not re.fullmatch(r"aarch64-[A-Za-z0-9_.]+-linux-ohos", canonical):
            raise ConanInvalidConfiguration("invalid canonical OHOS tuple: " + canonical)
        guess = auxdir / "config.guess"
        guess.write_text("#!/bin/sh\nprintf '%s\\n' " + shlex.quote(canonical) + "\n", encoding="utf-8")
        proved = subprocess.run(["/bin/sh", str(guess)], check=True,
                                capture_output=True, text=True, timeout=20).stdout.strip()
        if proved != canonical:
            raise ConanException("task-local config.guess did not reproduce compiler tuple")
        self.output.info("LIBWMF_NATIVE_CONFIG_TUPLE=" + proved)

    def package(self):
        Autotools(self).install()
        if str(self.settings.os) == "OHOS":
            real_libs = [p for p in Path(self.package_folder, "lib").glob("libwmf*.so*")
                         if p.is_file() and not p.is_symlink()]
            if len(real_libs) != 2:
                raise ConanException("expected installed libwmf and libwmflite")
            for library in real_libs:
                self._sign_elf(library)
            for name in ("wmf2svg", "wmf2eps", "wmf2fig"):
                self._sign_elf(Path(self.package_folder, "bin", name))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["wmf", "wmflite"]
        self.cpp_info.requires = ["freetype::freetype", "libpng::libpng",
                                  "zlib::zlib", "expat::expat"]
        self.cpp_info.set_property("cmake_file_name", "libwmf")
        self.cpp_info.set_property("cmake_target_name", "libwmf::libwmf")
        self.cpp_info.set_property("pkg_config_name", "libwmf")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
