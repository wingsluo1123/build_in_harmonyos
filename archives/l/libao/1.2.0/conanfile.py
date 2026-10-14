#!/usr/bin/env python3
"""Conan recipe — libao 1.2.0 (Autotools: configure + make).

libao is the Xiph.Org cross-platform audio output library.  Its back ends
are split between always-built file writers (wav / raw / au) and the null
sink, plus optional live back ends (ALSA, PulseAudio, ESD, NAS, OSS, Sun,
sndio, aRts, Roar, WMM, ...) that `configure` probes individually.  On OHOS
none of the external audio stacks exist, so configure automatically disables
them and keeps the wav / raw / au / null writers — enough for a fully
headless functional test (no audio hardware required).  No extra configure
flags are added (R1); the OSS plugin is left to configure's own probe.

Platform adaptation (three patches, applied to a clean extraction):
  0001-config.guess.patch  HarmonyOS system recognition (E007): the 2012
                           config.guess cannot guess HarmonyOS and aborts the
                           build; the patch adds the `*:HarmonyOS:*:*` case
                           emitting the canonical aarch64-unknown-linux-ohos
                           triplet (no __OHOS__ macro, PF5-clean).
  0002-config.sub.patch    Accept linux-ohos kernel/OS triplets (E007).
  0003-configure.patch     Replace `umask 077` around the config.status temp
                           directory.  On HMDFS the UID mapping makes a
                           0700 temp dir unwritable for the calling process,
                           so configure dies with "Permission denied" (E011).

No Conan dependencies: the library links only against the system C library.

Build-run pinning (recipe level, not a source patch): the ohos-aarch64
profile buildenv exports CONFIG_SHELL/SHELL as the HNP bash, and autoconf
2.69's configure unconditionally re-execs itself with $CONFIG_SHELL; that
bash fails getcwd() on HMDFS and aborts with "configure: error: working
directory cannot be determined" (classads/1.0.10, cdck/0.7.0 precedents).
The configure invocation therefore runs under /bin/sh with both variables
pinned, unset first (an empty-but-set CONFIG_SHELL leaks an empty SHELL into
the Makefiles and breaks GNU make).
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibaoConan(ConanFile):
    name = "libao"
    version = "1.2.0"
    description = "Cross-platform audio output library (Xiph.Org)"
    license = "GPL-2.0-or-later"
    homepage = "https://xiph.org/ao/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E-note (DRAFT-autoconf269 / DRAFT-6487): runtime pin for the
        # configure step.  See the module docstring; prefix assignments win
        # over the sourced conanbuild buildenv.
        toolchain_args = load_toolchain_args(self.generators_folder)
        configure_args = toolchain_args.get("configure_args", "")
        configure_script = os.path.join(self.source_folder, "configure")
        self.run(
            f'unset CONFIG_SHELL; CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            f'/bin/sh "{configure_script}" {configure_args}',
            env="conanbuild",
        )
        autotools = Autotools(self)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # libtool .la files bake an absolute libdir into the package; headers,
        # ao.pc and cpp_info already carry the link information (libidn2
        # pattern).  Keeping them would break downstream libtool consumers.
        for la in glob.glob(os.path.join(self.package_folder, "lib", "**", "*.la"),
                            recursive=True):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["ao"]
        self.cpp_info.set_property("pkg_config_name", "ao")
