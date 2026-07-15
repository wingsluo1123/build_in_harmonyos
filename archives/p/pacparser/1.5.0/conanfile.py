#!/usr/bin/env python3
"""Conan recipe — pacparser 1.5.0

Library to parse proxy auto-config (PAC) files.
Homepage: https://github.com/manugarg/pacparser
License: LGPL-3.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# The configure wrapper script is created in build() since Conan patches
# cannot create new files. Uses /system/bin/sh shebang (E165).
_CONFIGURE_SCRIPT = """#!/system/bin/sh
# Minimal configure script for pacparser (custom Makefile project)
PREFIX="/usr"
VERSION="v1.5.0"

for arg in "$@"; do
    case "$arg" in
        --prefix=*)
            PREFIX="${arg#--prefix=}"
            ;;
        --version)
            echo "$VERSION"
            exit 0
            ;;
        --help|-h)
            echo "Usage: ./configure [options]"
            echo "Options:"
            echo "  --prefix=DIR    Installation prefix [$PREFIX]"
            echo "  --help          Display this help"
            echo "  --version       Display version"
            exit 0
            ;;
        *)
            echo "configure: warning: unrecognized option: $arg"
            ;;
    esac
done

echo "VERSION=$VERSION" > src/version.mk

echo "Configuration for pacparser $VERSION:"
echo "  Prefix: $PREFIX"
echo ""
echo "Now run: make -C src PREFIX=$PREFIX"
"""


class PacparserConan(ConanFile):
    name = "pacparser"
    version = "1.5.0"
    description = "Library to parse proxy auto-config (PAC) files"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/manugarg/pacparser"
    url = "https://github.com/manugarg/pacparser"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Create the configure wrapper script (E165: use /system/bin/sh shebang)
        save(self, os.path.join(self.source_folder, "configure"), _CONFIGURE_SCRIPT)

        # Commands must run from source_folder since Makefile is there
        src = self.source_folder

        # Generate version.mk via configure
        self.run(f"cd {src} && /system/bin/sh ./configure --prefix=")

        # R9: Use -j1
        self.run(f"cd {src} && make -j1")

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        copy(self, "pacparser.h", src_dir, os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libpacparser.so.1", src_dir, os.path.join(self.package_folder, "lib"))
            # Create symlink libpacparser.so -> libpacparser.so.1
            so_link = os.path.join(self.package_folder, "lib", "libpacparser.so")
            if os.path.lexists(so_link):
                os.remove(so_link)
            os.symlink("libpacparser.so.1", so_link)
        else:
            copy(self, "libpacparser.a", src_dir, os.path.join(self.package_folder, "lib"))
        # pactester CLI tool
        copy(self, "pactester", src_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["pacparser"]
        self.cpp_info.bindirs = ["bin"]
