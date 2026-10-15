"""flam3 3.1.1 static fractal-flame library and utilities."""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Flam3Conan(ConanFile):
    name = "flam3"
    version = "3.1.1"
    package_type = "static-library"
    # Runtime palette XML is required even though the code archive is static.
    package_type_traits = {"run": True}
    description = "Fractal flame library and command-line tools"
    homepage = "https://github.com/scottdraves/flam3"
    license = "GPL-3.0-or-later"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def requirements(self):
        self.requires("zlib/1.3.2")
        self.requires("libpng/1.6.58.3")
        self.requires("libxml2/2.15.3.1")
        self.requires("libjpeg-turbo/3.2.0")

    def layout(self):
        basic_layout(self, build_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        archive_name = os.environ.get("FLAM3_SOURCE_ARCHIVE")
        if archive_name:
            archive = Path(archive_name).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        toolchain.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("OHOS ELF signer/readelf missing")
        original = Path(path)
        pending = original.with_name(original.name + ".flam3-signing")
        signed = original.with_name(original.name + ".flam3-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale signing sibling")
        try:
            shutil.copy2(original, pending)
            subprocess.run([signer, "sign", "-inFile", str(pending),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed ELF has no .codesign")
            os.chmod(signed, original.stat().st_mode)
            os.replace(signed, original)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._refresh_config_sub()
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            configure = os.path.join(self.build_folder, "configure")
            replace_in_file(self, configure,
                            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                            'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 007 && mkdir "$tmp") &&',
                            strict=True)
            replace_in_file(self, configure, 'tmp=./conf$$-$RANDOM',
                            'tmp="${TMPDIR:-.}/conf$$-$RANDOM"', strict=True)
            replace_in_file(self, configure, '(umask 077 && mkdir "$tmp")',
                            '(umask 007 && mkdir "$tmp")', strict=True)
            scratch = Path(self.build_folder, ".autoconf-tmp")
            previous_umask = os.umask(0o007)
            try:
                scratch.mkdir(mode=0o770, exist_ok=False)
            finally:
                os.umask(previous_umask)
            environment.define("TMPDIR", str(scratch))
        for dependency in self.dependencies.host.values():
            environment.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dependency.package_folder, "lib"))
        with environment.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        # Upstream has test.flam3 data but no registered check target.
        self.output.info("UPSTREAM_0_OF_0_NO_REGISTERED_SUITE")

    def _refresh_config_sub(self):
        tuple_name = "aarch64-unknown-linux-ohos"
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        environment = os.environ.copy()
        environment["TMPDIR"] = self.build_folder
        # A release worker need not have Automake installed. The release ships
        # a 2007 canonicalizer: extend only its kernel/OS and CPU alternatives,
        # then execute it rather than assuming that the textual edits suffice.
        bundled = Path(self.build_folder, "config.sub")
        if not bundled.is_file() or bundled.is_symlink():
            raise ConanInvalidConfiguration("bundled config.sub is not an ordinary file")
        contents = bundled.read_text(encoding="utf-8")
        substitutions = (
            ("nto-qnx* | linux-gnu*", "nto-qnx* | linux-ohos* | linux-gnu*"),
            ("| a29k \\", "| aarch64 | a29k \\"),
            ("| a29k-*", "| aarch64-* | a29k-*"),
            ("| -mingw32* | -linux-gnu*", "| -mingw32* | -linux-ohos* | -linux-gnu*"),
        )
        for old, new in substitutions:
            if contents.count(old) != 1:
                raise ConanInvalidConfiguration("unexpected bundled config.sub anchor: " + old)
            contents = contents.replace(old, new, 1)
        bundled.write_text(contents, encoding="utf-8", newline="\n")
        check = subprocess.run([shell, str(bundled), tuple_name],
                               env=environment, capture_output=True,
                               text=True, timeout=20)
        if check.returncode or check.stdout.strip() != tuple_name:
            raise ConanInvalidConfiguration("bundled config.sub rejects OHOS tuple: " + check.stderr)
        self.output.info("BUNDLED_CONFIG_SUB_FOR_OHOS")

    def package(self):
        Autotools(self).install()
        if str(self.settings.os) == "OHOS":
            for executable in ("flam3-animate", "flam3-genome", "flam3-render",
                               "flam3-convert"):
                self._sign_elf(os.path.join(self.package_folder, "bin", executable))
        copy(self, "COPYING.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["flam3"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("pkg_config_name", "flam3")
        self.runenv_info.define(
            "flam3_palettes",
            os.path.join(self.package_folder, "share", "flam3", "flam3-palettes.xml"))
