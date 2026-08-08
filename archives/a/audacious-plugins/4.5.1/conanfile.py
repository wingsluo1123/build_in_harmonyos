#!/usr/bin/env python3
"""Conan recipe for audacious-plugins 4.5.1.

audacious-plugins is a collection of plugins for the Audacious audio player,
providing input/output codecs, effects, containers, and transport support.

Build system: autotools (requires autoreconf since GitHub tarball lacks configure)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration


class AudaciousPluginsConan(ConanFile):
    name = "audacious-plugins"
    version = "4.5.1"
    description = "Plugins for the Audacious audio player (codecs, effects, containers, transport)"
    license = "BSD-2-Clause"
    homepage = "https://audacious-media-player.org/"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Core dependency - the Audacious player library
        self.requires("audacious/4.5.1")
        # GLib (glib2 provides glib-2.0, gio-2.0, gobject-2.0)
        self.requires("glib2/2.88.0")
        # Audio codecs
        self.requires("libmpg123/1.32.9")        # MP3 input
        self.requires("libvorbis/1.3.7")         # Ogg Vorbis input
        self.requires("flac/1.4.3")               # FLAC input
        self.requires("opus/1.5.2")               # Opus input
        self.requires("opusfile/0.12")            # Opus file support
        self.requires("wavpack/5.9.0")            # WavPack input
        # Audio output
        self.requires("alsa-lib/1.2.12")         # ALSA output
        self.requires("pulseaudio/17.0")          # PulseAudio output
        # System integration
        self.requires("dbus/1.14.10")             # MPRIS2 plugin
        self.requires("neon/0.35.0")              # HTTP/HTTPS transport
        self.requires("libxml2/2.15.3")           # XSPF playlists
        self.requires("zlib/1.3.1")               # Console/GME (zlib)
        # Transitive deps of glib2 and others
        self.requires("libogg/1.3.5")
        self.requires("pcre/8.45")
        self.requires("pcre2/10.40")
        self.requires("libiconv/1.17")
        self.requires("expat/2.8.2")
        self.requires("libsamplerate/0.2.2")     # Resample effect

    def build_requirements(self):
        self.tool_requires("automake/1.17")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("libtool/2.4.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R32: settings.os must check both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("audacious-plugins only supports Linux/OHOS")
        # Platform: no GTK/Qt desktop on HarmonyOS
        tc.configure_args.append("--disable-gtk")
        tc.configure_args.append("--disable-qt")
        # FFmpeg static libs lack PIC — cannot link into shared .so plugins.
        # Will revisit when conan ffmpeg provides shared libs with PIC.
        tc.configure_args.append("--disable-ffaudio")
        # Generate pkg-config files from conan deps
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub tarball lacks configure script — regenerate
        autotools.autoreconf(args=["--force", "--install"])
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # audacious-plugins produces .so plugin files loaded dynamically by audacious.
        # No single library to link against — plugins are discovered at runtime.
        self.cpp_info.libs = []
        # Plugin directories under lib/audacious/{Input,Output,Effect,General,Container,Transport}/
        self.cpp_info.includedirs = ["include/audacious-plugins"]
        self.cpp_info.libdirs = ["lib/audacious"]
