import os
import time as _time
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class AconnectguiConan(ConanFile):
    name = "aconnectgui"
    version = "0.9.0rc2-1"
    description = "FLTK-based GUI frontend for aconnect (ALSA sequencer)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/radiganm/aconnectgui"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "preconf/*", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("fltk/1.4.5")
        self.requires("alsa-lib/1.2.12")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aconnectgui supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        save(self, os.path.join(self.source_folder, "COPYING"),
             "This program is free software; you can redistribute it and/or modify\n"
             "it under the terms of the GNU General Public License version 2 as\n"
             "published by the Free Software Foundation.\n")
        import shutil as _sh
        preconf_dir = os.path.join(self.export_sources_folder, "preconf")
        for root, _, files in os.walk(preconf_dir):
            rel_root = os.path.relpath(root, preconf_dir)
            for f in files:
                src = os.path.join(root, f)
                dst_dir = self.source_folder if rel_root == "." else os.path.join(self.source_folder, rel_root)
                os.makedirs(dst_dir, exist_ok=True)
                dst = os.path.join(dst_dir, f)
                _sh.copyfile(src, dst)
                st = os.stat(src)
                if st.st_mode & 0o111:
                    os.chmod(dst, st.st_mode)
        for f_name in ["configure", "Makefile.in", "aclocal.m4", os.path.join("src", "Makefile.in"), os.path.join("src", "config.h.in")]:
            p = os.path.join(self.source_folder, f_name)
            if os.path.exists(p):
                os.utime(p, None)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # FL/Fl.H and alsa/asoundlib.h must be reachable when the
        # pre-generated configure probes them (AC_HAVE_HEADERS uses
        # CPPFLAGS) and when src/Makefile.am compiles (the upstream
        # Makefile carries no AM_CPPFLAGS): pass CPPFLAGS on the
        # configure command line (uget's curl -I precedent; the
        # toolchain env CPPFLAGS would be written over by the toolchain
        # script, so the configure argument form is used instead).
        _inc_flags = []
        for _dep_name in ("fltk", "alsa-lib"):
            _dep = self.dependencies[_dep_name]
            for _inc in (_dep.cpp_info.includedirs or ["include"]):
                _inc_abs = _inc if os.path.isabs(_inc) else os.path.join(_dep.package_folder, _inc)
                _inc_flags.append("-I" + _inc_abs)
        tc.configure_args.append("CPPFLAGS=" + " ".join(_inc_flags))
        tc.generate()
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS" and sys.platform != "linux":
            configure_path = os.path.join(self.source_folder, "configure")
            if os.path.isfile(configure_path):
                with open(configure_path, "r", encoding="utf-8") as f:
                    cfg = f.read()
                cfg = cfg.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
                cfg = cfg.replace("#! /bin/bash", "#! /data/service/hnp/bin/bash")
                cfg = cfg.replace("#!/bin/sh", "#!/system/bin/sh")
                cfg = cfg.replace("#! /bin/sh", "#! /system/bin/sh")
                cfg = cfg.replace("${CONFIG_SHELL-/bin/sh}", "${CONFIG_SHELL-/system/bin/sh}")
                cfg = cfg.replace("${SHELL-/bin/sh}", "${SHELL-/system/bin/sh}")
                cfg = cfg.replace("${SHELL-${CONFIG_SHELL-/bin/sh}}", "${SHELL-${CONFIG_SHELL-/system/bin/sh}}")
                cfg = cfg.replace("SHELL = /bin/sh", "SHELL = /system/bin/sh")
                orig = (
                    '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
                    '  test -d "$tmp"'
                )
                repl = (
                    '  tmp=./conf$$-$RANDOM\n'
                    '  (umask 022 && mkdir "$tmp" && chmod 755 "$tmp")'
                )
                cfg = cfg.replace(orig, repl)
                cfg = cfg.replace(
                    '(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null',
                    '(umask 022 && mkdir ./conf$$-$RANDOM && chmod 755 ./conf$$-$RANDOM)',
                )
                with open(configure_path, "w", encoding="utf-8") as f:
                    f.write(cfg)
        autotools = Autotools(self)
        autotools.configure()
        # The OHOS worker ships no automake/autoconf; the preconf output
        # was generated by automake 1.16.5. Re-stamp every file involved
        # in make's remake rules (Makefile.in <- Makefile.am/configure.in/
        # aclocal.m4/configure) to one mtime so none of the
        # configure/Makefile.in/aclocal.m4 regeneration rules can fire.
        _t = _time.time()
        for _base in (self.source_folder, self.build_folder):
            for _name in (
                "configure", "configure.in", "Makefile.am", "Makefile.in",
                "aclocal.m4", "config.status", "Makefile",
                os.path.join("src", "Makefile.am"),
                os.path.join("src", "Makefile.in"),
                os.path.join("src", "config.h.in"),
                os.path.join("src", "Makefile"),
                os.path.join("src", "config.h"),
            ):
                _p = os.path.join(_base, _name)
                if os.path.exists(_p):
                    os.utime(_p, (_t, _t))
        # -j1 + SHELL=/bin/sh (R9/E074: HMDFS blocks the jobserver FIFO).
        self.run("make -j1 SHELL=/bin/sh", cwd=self.build_folder, env="conanbuild")

    def package(self):
        # conan's AutotoolsToolchain configured this build with --prefix=/
        # (see build(): `configure --prefix=/ '--bindir=${prefix}/bin' ...`),
        # NOT the package_folder as the old comment assumed. A bare
        # `make install` therefore writes to //<dir> on the OHOS worker's
        # READ-ONLY root filesystem:
        #   install-sh -c -d '//bin'
        #   /system/bin/install -c aconnectgui '//bin'
        #   install: //bin/aconnectgui: Read-only file system
        #   make[2]: *** [Makefile:348: install-binPROGRAMS] Error 1  (build #97543)
        # Redirect with DESTDIR (the automake-1.16.5-generated Makefile honours
        # it): prefix=/ + DESTDIR=package_folder lands the files under
        # package_folder/{bin,...} instead of /. -j1 keeps the HMDFS fifo
        # restriction happy (R9/E074).
        destdir = self.package_folder
        self.run(f"make -j1 SHELL=/bin/sh install DESTDIR='{destdir}'",
                 cwd=self.build_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
