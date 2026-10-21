#!/usr/bin/env python3
"""Conan recipe for kodi-vfs-libarchive 21.0.2 — Kodi "archive://" VFS add-on.

Upstream: https://github.com/xbmc/vfs.libarchive (tag 21.0.2-Omega,
commit 089fb08587d534b2b709757eb389560781abd7f6). The package name follows the
repository's kodi-* family convention (add-on class "vfs" + the upstream
project id "libarchive" suffix); the upstream project id is "vfs.libarchive".

The add-on gives Kodi read-only access to archive files (7z/tar/tar.gz/
tar.bz2/tar.xz/zip/gz/bz2/xz, plus multi-volume RAR discovery) through the
libarchive library. It is a single-translation-unit C++17 binary add-on
(src/ArchiveFile.cpp, kodi::addon::CInstanceVFS + CAddonBase).

The upstream CMakeLists.txt resolves its build through modules shipped with
the kodi-addon-dev distribution (find_package(Kodi) + build_addon() from
AddonHelpers.cmake), which expects a Kodi SDK installation. The ohpcd
registry has no kodi package, so this recipe supplies its own CMake entry
point (recipe-cmake/, consumed via build_script_folder) that builds the same
unmodified upstream source against the Kodi add-on SDK headers and the
Conan-provided libarchive. Upstream additionally require_packages lz4/lzo2/
openssl/liblzma/bzip2/zlib only as the closure of the *static* libarchive it
bundles under depends/common; against the registry shared libarchive package
those are already absorbed (zlib/bzip2/xz statically, zstd dynamically), and
the add-on source itself only calls the libarchive public API (archive.h /
archive_entry.h). There is no GL/EGL render path in a VFS add-on.

The Kodi add-on SDK headers (xbmc/addons/kodi-dev-kit/include) are taken from
the xbmc 21.3-Omega release tarball — the same source the kodi-tools/21.3,
kodi-addon-screensaver/21.0.2 and kodi-addon-imagedecoder/21.0.2 recipes
consume; only that include subtree is extracted (the full xbmc tree extracts
to several hundred MB). Headers-only: AddonBase.h is fully inline, the module
never links libkodi.

Per DRAFT-KODI01, BUILD_KODI_ADDON / ADDON_*_USED are deliberately NOT
defined: build_addon()'s shallow include scan cannot detect instance-API
usage, and a hand-defined BUILD_KODI_ADDON without the matching USED macro
would silently drop the VFS case from kodi/versions.h.
"""
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, download, get


class KodiVfsLibarchiveConan(ConanFile):
    name = "kodi-vfs-libarchive"
    version = "21.0.2"
    description = "Kodi archive:// VFS add-on (multi-format read-only archive support)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/xbmc/vfs.libarchive"
    url = "https://github.com/xbmc/vfs.libarchive"

    settings = "os", "compiler", "build_type", "arch"

    # CMakeDeps so consumers (test_package here, a future Kodi port later)
    # can consume this package through find_package().
    generators = "CMakeDeps"
    exports_sources = "recipe-cmake/*"

    def requirements(self):
        # Upstream pins libarchive 3.4.3 in its depends/common directory
        # (built statically with ENABLE_TEST/ENABLE_*_TOOLS off). The ohpcd
        # registry carries libarchive 3.7.4/3.7.7/3.8.7; this recipe uses the
        # published 3.7.7 (same major API, libarchive public API is stable and
        # the add-on only uses archive_open/read/seek + entry iteration).
        # The registry libarchive package is shared-only, so the add-on module
        # keeps a DT_NEEDED entry on libarchive (like any Kodi deployment
        # against system libs). zlib/bzip2/xz are statically absorbed into
        # libarchive.so; zstd stays a dynamic dependency of libarchive.
        self.requires("libarchive/3.7.7")

    def validate(self):
        # Packaged as part of the HarmonyOS PC porting repository; the
        # recipe is only exercised against the OHOS toolchain/profile.
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "kodi-vfs-libarchive/21.0.2 is packaged for OHOS only."
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]

        # 1. Add-on sources. Conan merges exports_sources into the source
        #    folder BEFORE source() runs (config_source trap, see
        #    kodi-platform/20250416 notes), so recipe-cmake/ already exists
        #    here and the tarball (which has no recipe-cmake/ directory)
        #    cannot clobber it. Re-copy defensively like the kodi-platform
        #    precedent.
        get(self, **data["addon"], strip_root=True,
            filename="vfs.libarchive-21.0.2-Omega.tar.gz")
        copy(self, "*", src=os.path.join(self.recipe_folder, "recipe-cmake"),
             dst=os.path.join(self.source_folder, "recipe-cmake"))

        # 2. Kodi add-on SDK headers: download the xbmc 21.3-Omega tarball
        #    (URL list tried in order) and extract only the kodi-dev-kit
        #    include subtree.
        sdk_data = data["sdk"]
        urls = sdk_data["url"] if isinstance(sdk_data["url"], list) else [sdk_data["url"]]
        sdk_archive = os.path.join(self.source_folder, "kodi-sdk.tar.gz")
        last_error = None
        for url in urls:
            try:
                download(self, url, sdk_archive, sha256=sdk_data["sha256"])
                last_error = None
                break
            except ConanException as exc:
                last_error = exc
        if last_error is not None:
            raise ConanException("could not download the Kodi add-on SDK "
                                 "source: %s" % last_error)

        sdk_root = os.path.join(self.source_folder, "kodi-sdk")
        prefix = "xbmc-21.3-Omega/xbmc/addons/kodi-dev-kit/include"
        with tarfile.open(sdk_archive, "r:gz") as archive:
            members = [member for member in archive.getmembers()
                       if member.name == prefix or member.name.startswith(prefix + "/")]
            archive.extractall(sdk_root, members=members, filter="data")
        os.rename(os.path.join(sdk_root, prefix),
                  os.path.join(self.source_folder, "kodi-sdk-include"))
        # Only the empty xbmc-21.3-Omega/ directory chain is left here.
        shutil.rmtree(sdk_root)
        os.remove(sdk_archive)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["ADDON_SRC_DIR"] = self.source_folder
        toolchain.variables["KODI_SDK_INCLUDE_DIR"] = os.path.join(
            self.source_folder, "kodi-sdk-include")
        # E092: CMake has no HarmonyOS platform module, use Linux
        # (kodi-platform/20250416 precedent).
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="recipe-cmake")
        cmake.build()

    def package(self):
        copy(self, "vfs.libarchive.so", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The product is a Kodi-side loaded module (vfs.libarchive.so,
        # declared in the add-on's addon.xml.in library_filename). Nothing
        # links against it — consumers deploy the module into the Kodi add-on
        # tree. The module directory is exposed so tooling can locate it.
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "kodi-vfs-libarchive")
        self.cpp_info.set_property("cmake_target_name",
                                   "kodi-vfs-libarchive::kodi-vfs-libarchive")
