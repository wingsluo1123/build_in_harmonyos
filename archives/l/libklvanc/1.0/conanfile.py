#!/usr/bin/env python3
"""Conan recipe — libklvanc 1.0 (Autotools).

The upstream git archive ships no pre-generated `configure` (only
configure.ac + autogen.sh), so build() must run `autoreconf -fi` to
bootstrap (same approach as abiword-plugin-* / argp-standalone recipes).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Point autoconf-suite env vars at whatever is actually on PATH."""
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
    """E114: HMDFS rejects umask 077 temp dirs; relax to 022."""
    if not os.path.exists(path):
        return
    content = open(path, encoding="utf-8", errors="replace").read()
    if "umask 077" in content:
        content = content.replace("umask 077", "umask 022")
        open(path, "w", encoding="utf-8").write(content)
        conanfile.output.info("E114: dropped umask 077 -> 022 in %s" % path)


class LibklvancConan(ConanFile):
    name = "libklvanc"
    version = "1.0"
    description = "libklvanc 1.0"
    license = "LGPL-2.1"
    homepage = "https://github.com/stoth68000/libklvanc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The git archive ships no `configure`: build() runs `autoreconf -fi`
        # to bootstrap, so the autotools suite must be available on the build
        # host (tool_requires resolved with the build profile).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libklvanc is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess cannot identify HarmonyOS; pass the triplet explicitly
        # (config.sub supports *-linux-ohos) so configure never runs the
        # config.guess probe.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # Bootstrap: the git archive ships no pre-generated configure.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["klvanc"]
