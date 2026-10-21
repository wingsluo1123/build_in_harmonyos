#!/usr/bin/env python3
"""Conan recipe for rfdump 1.6 — RFID tag reader/writer (C + GTK3, autotools).

RFDump decodes RFID tags through the ACG multi-tag reader (or a compatible
reader) attached to a serial line and presents them in a GtkBuilder GUI.
Upstream 1.6 (2008) is the last release; it still targets GTK2 + libglade.

OHOS PC adaptation notes (see notes.md for the measured evidence):

* GTK2 and libglade are not published in the ohpcd repository, but
  gtk/3.24.43 is, and that build enables only the **Broadway** HTML5 backend
  (meson -Dx11_backend=false -Dwayland_backend=false -Dbroadway_backend=true),
  i.e. exactly the display-less situation of HarmonyOS PC.  The recipe
  therefore carries the drop-libglade / GTK3 port (patches/0001, adapted from
  the Arch Linux and Debian packages) instead of depending on GTK2.
* The 2008 tarball ships autoconf-2.61 generated files.  Regenerating them is
  not an option (automake 1.18 removed AM_CONFIG_HEADER, and the CI worker has
  no automake at all), so patches/0004 brings the shipped `configure` and
  `src/Makefile.in` in line with the ported `configure.in`/`src/Makefile.am`.
* HarmonyOS has no `/var/lock`; the reader bring-up used to fail on the
  lockfile before it ever touched the serial node (patches/0005).
* The Conan package is relocatable, so the GUI/tag-type data files are looked
  up next to the executable (patches/0005), and the serial device node is
  absent on PCIe-less machines (documented degradation path, see notes.md).
* gtk_init() runs before argv parsing upstream, so the packaged binary is
  given a headless --version/--help contract (patches/0006).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class RfdumpConan(ConanFile):
    name = "rfdump"
    version = "1.6"
    description = ("RFDump — tool to decode RFID tag data (ACG/compatible "
                   "reader over a serial line, GTK3 GtkBuilder GUI)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.rfdump.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rfdump builds on Linux/OHOS only, got {self.settings.os}")

    def requirements(self):
        # gtk/3.24.43's published OHOS binary pins glib/2.84.0.1; declaring the
        # same gtk revision keeps the whole GTK closure on prebuilt binaries
        # (R36).  expat is used directly by src/xml.c and is not reachable
        # through gtk+-3.0.pc, so it is declared explicitly.
        self.requires("gtk/3.24.43", transitive_headers=True,
                      transitive_libs=True)
        self.requires("expat/2.8.2.1", transitive_headers=True,
                      transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

        env = Environment()
        # R33: compiler and flags come from the Conan toolchain configuration,
        # never from bare ${CC}/${CFLAGS} shell variables.
        compilers = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp")
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables['c'] is not configured")
        env.define("CC", cc)
        env.define("CXX", cxx or cc)
        # src/Makefile.am keeps `CFLAGS = -Wall @CFLAGS@ -DVERSION=\"1.6\"`,
        # so the configure-time CFLAGS value is what the compile lines use.
        env.define("CFLAGS", "-fPIC -O2")
        env.define("CXXFLAGS", "-fPIC -O2")

        # expat is consumed directly (XML_ParserCreate) and gtk+-3.0.pc does
        # not carry it; inject its flags explicitly ($CPPFLAGS at compile
        # time, $LIBS at link time through @LIBS@ in the generated Makefile).
        expat = self.dependencies["expat"]
        incdirs = self._abs_dirs(expat, expat.cpp_info.includedirs)
        libdirs = self._abs_dirs(expat, expat.cpp_info.libdirs)
        env.define("CPPFLAGS", " ".join(f"-I{d}" for d in incdirs))
        link = [f"-L{d}" for d in libdirs]
        link += [f"-l{lib}" for lib in expat.cpp_info.libs]
        env.define("LIBS", " ".join(link))

        # HarmonyOS links with lld, which (unlike the GNU ld default on
        # Debian) does not pass --as-needed: every probe binary autoconf
        # builds keeps a DT_NEEDED entry for -lexpat even when it never calls
        # into it, so the shared libraries of the host dependencies must be
        # resolvable while configure runs - otherwise a plain
        # `int main(){}` conftest is reported as "cannot run C compiled
        # programs" (measured: 0001 build attempt).
        for dependency in self.dependencies.host.values():
            for libdir in self._abs_dirs(dependency,
                                         dependency.cpp_info.libdirs):
                env.prepend_path("LD_LIBRARY_PATH", libdir)

        # HarmonyOS refuses to execute scripts through their shebang
        # (avahi-ui-tools / pioneers precedent): drive configure with an
        # explicit shell.
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)

        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("rfdump_env")

    @staticmethod
    def _abs_dirs(dependency, dirs):
        out = []
        for directory in dirs:
            if not os.path.isabs(directory):
                directory = os.path.join(dependency.package_folder, directory)
            if os.path.isdir(directory):
                out.append(directory)
        return out

    # The tarball ships the *generated* autotools files (configure,
    # Makefile.in, config.h.in, aclocal.m4) and this recipe patches them
    # directly (patches/0004) instead of regenerating them: automake 1.18
    # dropped AM_CONFIG_HEADER so a 2008 autoconf-2.61 tree cannot be
    # regenerated, and the CI worker has no autoconf/automake at all.  The
    # shipped Makefiles nevertheless carry the 2008 maintainer-mode rules,
    # which fire as soon as configure.in/Makefile.am are newer than the
    # generated files - and the device *does* have autoconf 2.73, which then
    # rewrites `configure` back to a version whose AS_TMPDIR uses
    # `umask 077`; HMDFS turns that into a directory config.status cannot
    # write into ("confXXXXXX/subs1.awk: Permission denied", measured).
    # Touch the generated files so make treats them as authoritative.
    _GENERATED_AUTOTOOLS = ("aclocal.m4", "configure", "config.h.in",
                            "Makefile.in", "src/Makefile.in")

    def _stamp_generated_autotools(self):
        for name in self._GENERATED_AUTOTOOLS:
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                raise ConanException(f"generated autotools file missing: {path}")
            os.utime(path, None)
        self.output.info("stamped generated autotools files: "
                         + ", ".join(self._GENERATED_AUTOTOOLS))

    def build(self):
        apply_conandata_patches(self)
        self._stamp_generated_autotools()
        # --prefix=/ keeps every installed artefact inside the package once
        # DESTDIR is applied in package(); Autotools(configure) is deliberately
        # not used because the 2008 configure has no AC_CANONICAL_SYSTEM and
        # rejects the --build/--host flags the Conan toolchain would add.
        self.run('sh configure --prefix=/', cwd=self.source_folder,
                 env=["conanbuild", "rfdump_env"])
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
        self.run(f"make -j{jobs}", cwd=self.source_folder,
                 env=["conanbuild", "rfdump_env"])
        binary = os.path.join(self.source_folder, "src", "rfdump")
        if not os.path.isfile(binary):
            raise ConanException(f"rfdump binary was not built: {binary}")

    def package(self):
        with_env = ["conanbuild", "rfdump_env"]
        destination = shlex.quote(self.package_folder)
        self.run(f"make -j1 install DESTDIR={destination}",
                 cwd=self.source_folder, env=with_env)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "AUTHORS", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        self._verify_installed_tree()
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(
                os.path.join(self.package_folder, "bin", "rfdump"))

    def _verify_installed_tree(self):
        """Fail loudly if automake silently fell back to the 2000-vintage
        install-sh: the packaged layout is part of the delivery contract."""
        expected = [
            "bin/rfdump",
            "share/rfdump/rfdump.ui",
            "share/rfdump/rfd_types.xml",
            "share/rfdump/rfd.dtd",
            "share/rfdump/mifare.txt",
        ]
        missing = [p for p in expected
                   if not os.path.exists(os.path.join(self.package_folder, p))]
        if missing:
            raise ConanException(
                "installed tree is incomplete: " + ", ".join(missing))
        self.output.info("installed tree verified: " + ", ".join(expected))

    @staticmethod
    def _sign_ohos_elf(path):
        import shutil
        import subprocess
        signer = shutil.which("binary-sign-tool") \
            or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") \
            or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"missing executable to sign: {path}")
        if not os.path.isfile(signer):
            raise ConanException(f"HarmonyOS signer missing: {signer}")
        output = path + ".signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", output,
                        "-selfSign", "1"], check=True, timeout=120)
        if os.path.isfile(readelf):
            sections = subprocess.run([readelf, "-SW", output], check=True,
                                      capture_output=True, text=True,
                                      timeout=30).stdout
            if sections.count(".codesign") != 1:
                raise ConanException(
                    "signed executable does not carry exactly one .codesign "
                    "section")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
