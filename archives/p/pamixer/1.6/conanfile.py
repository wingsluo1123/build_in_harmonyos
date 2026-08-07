#!/usr/bin/env python3
"""Conan recipe for pamixer 1.6 — PulseAudio command-line mixer.

pamixer is a command-line tool for controlling the volume of a PulseAudio
sound server. It uses the PulseAudio async C API (libpulse) and cxxopts
for command-line option parsing.

This recipe builds pamixer by directly compiling the source files (bypassing
meson) and linking against pulseaudio and cxxopts from Conan dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class PamixerConan(ConanFile):
    name = "pamixer"
    version = "1.6"
    description = "PulseAudio command-line mixer"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/cdemoulins/pamixer"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("pulseaudio/17.0@ohpcd/stable")
        self.requires("cxxopts/3.2.1@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cxx(self):
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("cpp") or "clang++"

    def build(self):
        src = self.source_folder
        cxx = self._get_cxx()

        # Get include and lib paths from Conan dependencies
        pulse_dep = self.dependencies["pulseaudio"]
        cxxopts_dep = self.dependencies["cxxopts"]

        # Build include flags
        includes = []
        for dep in [pulse_dep, cxxopts_dep]:
            for incdir in dep.cpp_info.includedirs:
                includes.append(f"-I{incdir}")
        # Also add pulse subdirectory for pulseaudio headers
        for incdir in pulse_dep.cpp_info.includedirs:
            includes.append(f"-I{incdir}/pulse")

        # Build library flags
        libdirs = []
        libs = []
        for dep in [pulse_dep]:
            for libdir in dep.cpp_info.libdirs:
                libdirs.append(f"-L{libdir}")
            libs.extend([f"-l{l}" for l in dep.cpp_info.libs])

        # Generate config.hh (meson would normally generate this)
        config_content = '#define VERSION "1.6"\n'
        with open(os.path.join(src, "config.hh"), "w") as f:
            f.write(config_content)

        # Compile the 4 source files into a single executable
        sources = [
            "src/callbacks.cc",
            "src/device.cc",
            "src/pamixer.cc",
            "src/pulseaudio.cc",
        ]
        src_files = " ".join(os.path.join(src, s) for s in sources)

        cxx_std = "-std=c++11"
        if self.settings.compiler.cppstd:
            std_value = str(self.settings.compiler.cppstd)
            cxx_std = f"-std=c++{std_value}"

        self.run(
            f"{cxx} {cxx_std} -O2 -I{src} -I{src}/src {' '.join(includes)} "
            f"{src_files} {' '.join(libdirs)} {' '.join(libs)} "
            f"-lpthread -o pamixer",
            cwd=src
        )

    def package(self):
        src = self.source_folder
        copy(self, "pamixer", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "pamixer.1", src=src, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
