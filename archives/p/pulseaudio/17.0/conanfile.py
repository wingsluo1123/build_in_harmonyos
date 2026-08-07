#!/usr/bin/env python3
"""Conan recipe for pulseaudio 17.0 — PulseAudio client libraries for OHOS.

Builds only the client libraries (libpulse, libpulse-simple, libpulsecommon)
without the daemon, glib mainloop, or libsndfile dependency. This is sufficient
for client applications that use the PulseAudio async C API.
"""
from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PulseaudioConan(ConanFile):
    name = "pulseaudio"
    version = "17.0"
    description = "PulseAudio sound server client libraries"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/PulseAudio/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        import os
        # Set archiver path for meson (llvm-ar not in default PATH in Conan env)
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        tc = MesonToolchain(self)
        # Build only client libraries, not the daemon
        tc.project_options["daemon"] = "false"
        tc.project_options["client"] = "true"
        # Disable all optional features not needed for client library
        tc.project_options["alsa"] = "disabled"
        tc.project_options["bluez5"] = "disabled"
        tc.project_options["jack"] = "disabled"
        tc.project_options["dbus"] = "disabled"
        tc.project_options["udev"] = "disabled"
        tc.project_options["systemd"] = "disabled"
        tc.project_options["webrtc-aec"] = "disabled"
        tc.project_options["samplerate"] = "disabled"
        tc.project_options["soxr"] = "disabled"
        tc.project_options["speex"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["asyncns"] = "disabled"
        tc.project_options["glib"] = "disabled"
        tc.project_options["tests"] = "false"
        tc.project_options["man"] = "false"
        tc.project_options["doxygen"] = "false"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Create .tarball-version file required by git-version-gen
        import os
        with open(os.path.join(self.source_folder, ".tarball-version"), "w") as f:
            f.write("17.0")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["pulse", "pulse-simple"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        # Also provide libpulsecommon as a private lib
        self.cpp_info.set_property("cmake_file_name", "PulseAudio")
        self.cpp_info.set_property("cmake_target_name", "PulseAudio::PulseAudio")
        self.cpp_info.set_property("pkg_config_name", "libpulse")
