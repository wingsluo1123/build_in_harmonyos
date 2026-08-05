#!/usr/bin/env python3
"""Conan recipe — audiowaveform 1.10.3 (CMake, executable).

audiowaveform generates waveform images and JSON data from audio files.
It is a command-line tool (not a library).

Dependencies:
  libmad/0.16.4, libid3tag/0.16.3, libgd/2.3.3,
  libsndfile/1.2.2, boost/1.91.0
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class AudiowaveformConan(ConanFile):
    name = "audiowaveform"
    version = "1.10.3"
    description = "Generate waveform images and JSON data from audio files"
    license = "GPL-3.0"
    homepage = "https://github.com/bbc/audiowaveform"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"audiowaveform supports Linux and OHOS, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("libmad/0.16.4")
        self.requires("libid3tag/0.16.3")
        self.requires("libgd/2.3.3")
        self.requires("libsndfile/1.2.2")
        self.requires("boost/1.91.0")
        self.requires("zlib/1.3.1.1")
        self.requires("libogg/1.3.6.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_pkg(self, name):
        return self.dependencies[name].package_folder

    def _dep_incdir(self, name):
        return os.path.join(self._dep_pkg(name), "include").replace("\\", "/")

    def _dep_lib(self, name, candidates):
        pkg = self._dep_pkg(name)
        for cand in candidates:
            matches = sorted(glob.glob(os.path.join(pkg, "lib", cand)))
            if matches:
                return matches[0].replace("\\", "/")
        return os.path.join(pkg, "lib", candidates[0]).replace("\\", "/")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["ENABLE_TESTS"] = "0"
        gd_inc = self._dep_incdir("libgd")
        gd_lib = self._dep_lib("libgd", ["libgd.so", "libgd.so.*", "libgd.a"])
        tc.cache_variables["LIBGD_INCLUDE_DIRS"] = gd_inc
        tc.cache_variables["LIBGD_LIBRARIES"] = gd_lib
        sf_inc = self._dep_incdir("libsndfile")
        sf_lib = self._dep_lib("libsndfile", ["libsndfile.so", "libsndfile.so.*", "libsndfile.a"])
        tc.cache_variables["LIBSNDFILE_INCLUDE_DIRS"] = sf_inc
        tc.cache_variables["LIBSNDFILE_LIBRARIES"] = sf_lib
        mad_inc = self._dep_incdir("libmad")
        mad_lib = self._dep_lib("libmad", ["libmad.so", "libmad.so.*", "libmad.a"])
        tc.cache_variables["LIBMAD_INCLUDE_DIRS"] = mad_inc
        tc.cache_variables["LIBMAD_LIBRARIES"] = mad_lib
        id3_inc = self._dep_incdir("libid3tag")
        id3_lib = self._dep_lib("libid3tag", ["libid3tag.so", "libid3tag.so.*", "libid3tag.a"])
        tc.cache_variables["LIBID3TAG_INCLUDE_DIRS"] = id3_inc
        tc.cache_variables["LIBID3TAG_LIBRARIES"] = id3_lib
        tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.cache_variables["CMAKE_INSTALL_RPATH_USE_ORIGIN"] = True
        ld_dirs = []
        for dep in ("libmad", "libid3tag", "libgd", "libsndfile", "boost"):
            d = os.path.join(self._dep_pkg(dep), "lib")
            if os.path.isdir(d):
                ld_dirs.append(d)
        existing = os.environ.get("LDFLAGS", "")
        os.environ["LDFLAGS"] = (
            " ".join(f"-L{d} -Wl,-rpath-link,{d}" for d in ld_dirs)
            + " " + existing
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
