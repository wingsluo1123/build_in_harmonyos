#!/usr/bin/env python3
"""Conan recipe for rmcast 2.0.0 — Reliable Multicast Library (RML).

Upstream: LAND/UFRJ Reliable Multicast Library (QPL-1.0).
Build system: autotools upstream, built here with a deterministic direct
compile. Rationale: the archive's config.guess/config.sub are from 2007 and
predate aarch64 entirely (the shipped configure cannot accept an OHOS host
triplet), so regeneration with autoreconf --force --install (Homebrew's
approach) is required — but the OHOS device toolchain ships autoconf only
(no automake, no libtool/libtoolize/libtool.m4), so the regeneration stack
cannot be satisfied there. The source has zero HAVE_* feature macros
(config.h is only included behind HAVE_CONFIG_H), which makes the upstream
CFLAGS reproducible outside autotools; this was cross-validated against a
real OHOS clang build (8/8 sources compile, consumers link).

Products: librmcast (.a, and .so for shared=True) plus the upstream demo
tools rmchat/mcastproxy.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

LIB_SOURCES = [
    "rmcache.c", "rmcast.c", "rmevent.c", "rminternals.c",
    "rmmsg.c", "rmmsgpckt.c", "rmtcp.c", "rmwinmask.c",
]

# The source archive is the Debian tgif 1:4.2.5 orig tarball, which bundles
# the whole rmcast 2.0.0 project tree under <root>/rmcast/ (upstream site is
# dead; provenance in conandata.yml). All build paths live inside it.
BUNDLE_SUBDIR = "rmcast"

# Upstream src/Makefile.am librmcast_la_CFLAGS (verbatim defines).
# STR_VERSION is wrapped in shell single quotes so the escaped quotes reach
# the compiler (the shell would otherwise strip them and rmcast.c's
# "RMCAST "STR_VERSION string concatenation fails to compile).
UPSTREAM_DEFS = (
    "-fno-strict-aliasing "
    "'-DSTR_VERSION=\"2.0.0\"' "
    "-DRANDOM_TIMERS -DREFRESH -DSINGLE_NACK "
    "-DSUPPORT_FOR_NEW_MEMBERS -D_REENTRANT "
)


class RmcastConan(ConanFile):
    name = "rmcast"
    version = "2.0.0"
    description = "Reliable Multicast Library (RML) — reliable transmission over IP multicast"
    license = "QPL-1.0"
    homepage = "https://www.land.ufrj.br/tools/rmcast/rmcast.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rmcast is supported only on Linux/OHOS")
        if self.settings.arch != "armv8" and self.settings.os == "OHOS":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # rmcast depends only on the C library and POSIX sockets; no third-party deps.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, BUNDLE_SUBDIR)
        bld = self.build_folder
        os.makedirs(bld, exist_ok=True)

        # Toolchain variables from the Autotools toolchain (CC/CFLAGS/AR),
        # R33: never hardcode a compiler.
        tc = AutotoolsToolchain(self)
        env_vars = tc.vars()
        cc = env_vars.get("CC", "clang")
        cflags = env_vars.get("CFLAGS", "")
        ar = env_vars.get("AR", "ar")

        objs = []
        for c in LIB_SOURCES:
            out = os.path.join(bld, c + ".o")
            objs.append(out)
            self.run(
                '"{}" {} {} -I"{}/src" -c "{}/src/{}" -o "{}"'.format(
                    cc, cflags, UPSTREAM_DEFS, src, src, c, out
                ),
                cwd=bld,
            )

        # Static archive (upstream builds libtool .a/.so; same symbols).
        self.run('"{}" rcs librmcast.a {}'.format(ar, " ".join('"%s"' % o for o in objs)), cwd=bld)

        if self.options.shared:
            pic_objs = []
            picflags = "-fPIC " + cflags
            for c in LIB_SOURCES:
                out = os.path.join(bld, "pic_" + c + ".o")
                pic_objs.append(out)
                self.run(
                    '"{}" {} {} -I"{}/src" -c "{}/src/{}" -o "{}"'.format(
                        cc, picflags, UPSTREAM_DEFS, src, src, c, out
                    ),
                    cwd=bld,
                )
            soname = "librmcast.so.0"
            self.run(
                '"{}" -shared -Wl,-soname,{} -o librmcast.so.0.0.0 {} -lm -lpthread'.format(
                    cc, soname, " ".join('"%s"' % o for o in pic_objs)
                ),
                cwd=bld,
            )
            # Materialize the SONAME/linker names as real files (no symlinks:
            # HMDFS on OHOS cannot preserve them).
            for name in ("librmcast.so.0", "librmcast.so"):
                self.run('cp librmcast.so.0.0.0 "{}"'.format(name), cwd=bld)

        # Demo tools (link the objects directly; upstream links -lrmcast).
        for tool, tool_src in (("rmchat", "rmchat/rmchat.c"), ("mcastproxy", "mcastproxy/mcastproxy.c")):
            self.run(
                '"{}" {} -I"{}/src" "{}/{}" librmcast.a -lm -lpthread -o "{}"'.format(
                    cc, cflags, src, src, tool_src, tool
                ),
                cwd=bld,
            )

    def package(self):
        src = os.path.join(self.source_folder, BUNDLE_SUBDIR)
        bld = self.build_folder
        copy(self, "rmcast.h", src=os.path.join(src, "src"), dst=os.path.join(self.package_folder, "include"))
        copy(self, "librmcast.a", src=bld, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "librmcast.so.0.0.0", src=bld, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "librmcast.so.0", src=bld, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "librmcast.so", src=bld, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "rmchat", src=bld, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "mcastproxy", src=bld, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        for exe in ("rmchat", "mcastproxy"):
            path = os.path.join(self.package_folder, "bin", exe)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        copy(self, "LICENSE.QPL", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=src, dst=os.path.join(self.package_folder, "share", "rmcast", "doc"))

    def package_info(self):
        self.cpp_info.libs = ["rmcast"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
