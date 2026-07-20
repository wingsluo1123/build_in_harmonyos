#!/usr/bin/env python3
"""Conan recipe for Decker — a multimedia sketchpad (Makefile project).

Decker builds two targets:
  - lilt:  standalone Lil interpreter (no SDL dependency, always built)
  - decker: GUI app (requires SDL2 + SDL2_image, optional)

Build uses PkgConfigDeps to provide SDL2/SDL2_image flags via pkg-config
when SDL2 dependencies are available.
"""
import os
from conan import ConanFile, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class DeckerConan(ConanFile):
    name = "decker"
    version = "1.69"
    description = "Decker is a multimedia platform for creating and sharing interactive documents, with sound, images, hypertext, and scripted behavior."
    license = "MIT"
    homepage = "https://github.com/JohnEarnest/Decker"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "with_sdl": [True, False]}
    default_options = {"shared": False, "with_sdl": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_sdl:
            self.requires("sdl2/2.30.10")
            self.requires("sdl2_image/2.8.0")

    def layout(self):
        basic_layout(self)

    def generate(self):
        if self.options.with_sdl:
            pkg_deps = PkgConfigDeps(self)
            pkg_deps.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler - use settings.compiler to determine compiler name
        # The profile provides tools.build:compiler_executables as a JSON dict,
        # but Conan 2.x doesn't support nested key access on that conf.
        # Fall back to the standard compiler name from settings.
        cc = "clang" if str(self.settings.compiler) == "clang" else "gcc"

        version = self.version

        # Generate resources.h
        self.run("chmod +x scripts/resources.sh")
        self.run("./scripts/resources.sh examples/decks/tour.deck")

        # Ensure c/build/ exists before writing lilt/decker binaries into it.
        # git does not track empty dirs, so the source tarball has no c/build/.
        os.makedirs(os.path.join(self.source_folder, "c", "build"), exist_ok=True)

        # Common flags. -O2 is fixed upstream; build_type is a Makefile project
        # so we don't remap Debug/Release here.
        flags = "-std=c99 -Wall -Wextra -O2 -Wno-misleading-indentation"
        flags += " -Wno-unknown-warning-option -Wno-overlength-strings -lm"

        # Build lilt (standalone interpreter, no SDL needed)
        self.run(
            f"{cc} ./c/lilt.c -o ./c/build/lilt "
            f"{flags} -DVERSION='\"{version}\"'"
        )

        # Build decker (GUI app, needs SDL2 + SDL2_image)
        if self.options.with_sdl:
            # Use with-statements so popen() pipes are always closed, even
            # when pkg-config fails. Surface stderr instead of swallowing it.
            with os.popen("pkg-config --cflags sdl2 SDL2_image") as cf:
                sdl2_cflags = cf.read().strip()
            with os.popen("pkg-config --libs sdl2 SDL2_image") as lf:
                sdl2_libs = lf.read().strip()
            if not sdl2_cflags or not sdl2_libs:
                raise ConanException(
                    "with_sdl=True but pkg-config could not resolve "
                    "sdl2/SDL2_image flags (PKG_CONFIG_PATH / deps missing?)"
                )
            self.run(
                f"{cc} ./c/decker.c -o ./c/build/decker "
                f"{sdl2_cflags} {sdl2_libs} "
                f"{flags} -DVERSION='\"{version}\"'"
            )

    def package(self):
        # Install lilt binary
        copy(self, "c/build/lilt", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Install decker binary if built
        decker_bin = os.path.join(self.source_folder, "c", "build", "decker")
        if os.path.exists(decker_bin):
            copy(self, "c/build/decker", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Install resources
        copy(self, "*.deck", os.path.join(self.source_folder, "examples", "decks"),
             os.path.join(self.package_folder, "share", "decker", "examples"))
        copy(self, "*.lil", os.path.join(self.source_folder, "tests"),
             os.path.join(self.package_folder, "share", "decker", "tests"), keep_path=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []