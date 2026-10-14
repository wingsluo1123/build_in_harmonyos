#!/usr/bin/env python3
"""Conan recipe for Open Cubic Player (ocp) — HarmonyOS PC (aarch64) adaptation.

Platform notes
--------------
* The GNU config.guess / config.sub shipped in the tarball predate HarmonyOS and
  reject the ``aarch64-unknown-linux-ohos`` triplet, so
  ``patches/0001-autotools-ohos-triplet.patch`` teaches both scripts the triplet.
  Without it configure aborts with "cannot guess build type" on a HarmonyOS host
  (see knowledge entry E007).
* ``--host=aarch64-unknown-linux-ohos`` is passed explicitly so that the recipe
  also works when the build machine is not a HarmonyOS host (the CI worker runs
  on x86_64 Linux): there configure detects an x86_64 build triplet and
  cross-compiles, which is the documented upstream workflow.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class OcpConan(ConanFile):
    name = "ocp"
    version = "3.3.1"
    description = "Open Cubic Player - music player with module/tracker/adlib/SID support"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/mywave82/opencubicplayer"
    url = "https://github.com/mywave82/opencubicplayer"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory: the player UI is curses based (configure aborts without it).
        self.requires("ncurses/6.6")
        # Optional decoders, enabled automatically by configure when present.
        self.requires("zlib/1.3.2")
        self.requires("bzip2/1.0.8.2")
        self.requires("mad/0.16.4")
        # libvorbis/1.3.7 pins libogg/1.3.6 while flac/1.5.0 pins libogg/1.3.5:
        # override keeps a single ogg runtime in the graph (flac is rebuilt then).
        self.requires("libogg/1.3.6", override=True)
        self.requires("libvorbis/1.3.7")
        self.requires("flac/1.5.0")
        self.requires("libpng/1.6.58.3")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("game-music-emu/0.6.5")
        self.requires("alsa-lib/1.2.16.1")
        self.requires("libdiscid/0.6.5")
        self.requires("cjson/1.7.19")
        self.requires("ancient/2.3.0")

    def build_requirements(self):
        # required by libsidplayfp (playsid) to assemble its 6502 code.
        self.tool_requires("xa/2.4.1")

    def configure(self):
        # ocp's bundled makefiles build plain C sources with the configure time
        # CXXFLAGS (playopl/Makefile: "adplug_adlibemu.o: ...
        # $(CC) $(LIBADPLUG_CXXFLAGS) $^ -o $@ -c"), and the compiler rejects
        # "-std=c++17 ... not allowed with 'C'".  Dropping the C++ standard and
        # stdlib settings keeps those flags out of the environment: the makefiles
        # request the standard they need themselves (adplug is built as C++14)
        # and the HarmonyOS toolchain defaults to gnu++17 with libc++.
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ocp is supported on Linux/OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        # ocp's configure script validates the vendored decoder submodules with
        # paths relative to the current directory, so it cannot be configured
        # out-of-tree: the build happens in-source.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # No X11 / desktop integration on HarmonyOS PC.
            "--with-x11=no",
            "--without-info",
            "--without-desktop_file_install",
            "--without-update-mime-database",
            "--without-update-desktop-database",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        PkgConfigDeps(self).generate()
        # ocp discovers ncursesw (mandatory) and its optional decoders through
        # pkg-config; Conan does not put the dependency .pc directories on
        # PKG_CONFIG_PATH by itself, so inject them explicitly.
        env = tc.environment()
        for dep in self.dependencies.values():
            cpp_info = dep.cpp_info.aggregated_components()
            package_folder = dep.package_folder
            # ocp probes several libraries with plain AC_CHECK_LIB (bzip2, mad,
            # ...) instead of pkg-config, hence the -I/-L flags are required.
            for incdir in cpp_info.includedirs:
                path = incdir if os.path.isabs(incdir) else os.path.join(package_folder, incdir)
                if os.path.isdir(path):
                    env.append("CPPFLAGS", "-I{}".format(path))
                    # Several rules in the bundled makefiles compile without any
                    # -I at all (filesel/Makefile: "filesystem-bzip2.o: ...
                    # $(CC) $< -o $@ -c"), relying on the headers sitting in the
                    # compiler's default search path, which is true on a desktop
                    # Linux but not on HarmonyOS.  CPATH adds the directory to
                    # every compile of the build.
                    env.append_path("CPATH", path)
            for libdir in cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(package_folder, libdir)
                if os.path.isdir(path):
                    env.append("LDFLAGS", "-L{}".format(path))
                    # Same for the link steps, some of which pass no -L flag.
                    env.append_path("LIBRARY_PATH", path)
            for sub in ("lib/pkgconfig", "share/pkgconfig"):
                pcdir = os.path.join(package_folder or "", sub)
                if os.path.isdir(pcdir):
                    # The dependency copy is intentionally left out of
                    # PKG_CONFIG_PATH: the staged copy below is used instead, so
                    # a stale "prefix=" cannot take precedence.
                    self._stage_pkg_config(pcdir, package_folder or "")
        for generated in (os.path.join(self.generators_folder, "pkgconfig"),
                          self.generators_folder):
            if os.path.isdir(generated):
                env.append_path("PKG_CONFIG_PATH", generated)
        # Staged copies are appended last, hence searched first: a few packages
        # ship a .pc whose prefix is still the install prefix they were built
        # with (ancient/2.3.0 declares "prefix=/", which made pkg-config hand
        # out "-I//include" and <ancient/ancient.hpp> could not be found).
        staged = os.path.join(self.generators_folder, "ohos-pkgconfig")
        if os.path.isdir(staged):
            env.append_path("PKG_CONFIG_PATH", staged)
        tc.generate(env)

    def _stage_pkg_config(self, pcdir, package_folder):
        """Stage dependency .pc files, resolving paths against the package.

        The copies land in <generators>/ohos-pkgconfig, which is put in front of
        PKG_CONFIG_PATH, so a stale path cannot leak unusable -I/-L flags into
        the build.  Two real cases: ancient/2.3.0 ships 'prefix=/', and the
        cjson package ships an absolute 'includedir=' pointing at the temporary
        build directory, which is gone once the package has been created.
        """
        staged = os.path.join(self.generators_folder, "ohos-pkgconfig")
        os.makedirs(staged, exist_ok=True)
        overrides = {"includedir": os.path.join(package_folder, "include"),
                     "libdir": os.path.join(package_folder, "lib")}
        for entry in sorted(os.listdir(pcdir)):
            if not entry.endswith(".pc"):
                continue
            with open(os.path.join(pcdir, entry),
                      encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            lines = []
            for line in content.splitlines(True):
                name, separator, value = line.partition("=")
                if separator:
                    value = value.strip()
                    if name == "prefix":
                        line = "prefix={}\n".format(package_folder)
                    elif name in overrides and value.startswith("/") \
                            and not os.path.isdir(value):
                        line = "{}={}\n".format(name, overrides[name])
                lines.append(line)
            with open(os.path.join(staged, entry), "w", encoding="utf-8") as handle:
                handle.write("".join(lines))

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/ocp"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
