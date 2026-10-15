#!/usr/bin/env python3
"""Conan recipe — mscompress 0.4

Microsoft "compress.exe/expand.exe" compatible LZ77 (de)compressor.
Autotools project building two CLI programs: mscompress + msexpand.
No external dependencies (libc only); configure.ac declares none.
License: GPL-2.0
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH (same approach as
    abiword-plugin-clarisworks)."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    fixed = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    fixed = fixed.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    if fixed != data:
        with open(path, "w", encoding="utf-8") as f:
            f.write(fixed)
        conanfile.output.info("E114: dropped umask 077 from generated configure")


class MscompressConan(ConanFile):
    name = "mscompress"
    version = "0.4"
    description = "Microsoft compress.exe/expand.exe compatible LZ77 (de)compressor"
    license = "GPL-2.0"
    homepage = "https://github.com/stapelberg/mscompress"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The upstream tag tarball ships no generated `configure`, only
        # configure.ac + Makefile.am, so build() must run `autoreconf -fi` to
        # bootstrap.  The build host (CI sandbox / minimal OHOS image) lacks
        # automake/aclocal/libtoolize (only the autoconf suite is present
        # under /data/service/hnp/bin), so pull them in as tool_requires
        # (same approach as abiword-plugin-clarisworks / argp-standalone).
        # tool_requires are resolved with the *build* profile, so both
        # -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: only Linux/OHOS are supported targets
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mscompress is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS");
        # pass the triplet explicitly (config.sub supports *-linux-ohos) so
        # configure never runs the config.guess probe (same approach as
        # abiword-plugin-clarisworks).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        apply_conandata_patches(self)
        # Upstream tag tarball does not ship a generated `configure` script,
        # only configure.ac + Makefile.am, so regenerate the build system first.
        self.run("autoreconf -fiv", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM → -j1
        autotools.make(args=["-j1"])
        # L1: run the upstream round-trip test as part of the build
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI tool: no libraries, nothing to export for consumers.
        pass