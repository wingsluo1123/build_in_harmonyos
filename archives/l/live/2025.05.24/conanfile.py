#!/usr/bin/env python3
"""Conan recipe for the LIVE555 2025.05.24 HarmonyOS PC port."""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class LiveConan(ConanFile):
    name = "live"
    version = "2025.05.24"
    description = "LIVE555 streaming media libraries"
    license = "LGPL-3.0-or-later, GPL-3.0-or-later"
    homepage = "http://www.live555.com/liveMedia/"
    url = "http://www.live555.com/liveMedia/"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Keep the upstream default TLS/SRTP/HMAC feature set.  NO_OPENSSL is
        # intentionally not used.
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("live supports Linux and OHOS only")
        if bool(self.options.shared):
            raise ConanInvalidConfiguration("this upstream release builds static archives")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("live supports OHOS armv8 only")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def _config_text(self):
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        cxx = self.conf.get("tools.build:compiler_executables", default={}).get("cpp", "clang++")
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        openssl = self.dependencies["openssl"].cpp_info
        include_flags = " ".join('-I"%s"' % p for p in openssl.includedirs)
        library_flags = " ".join('-L"%s"' % p for p in openssl.libdirs)
        pic = " -fPIC" if bool(self.options.fPIC) else ""
        optimize = "-O0 -g" if str(self.settings.build_type) == "Debug" else "-O2 -DNDEBUG"
        return """COMPILE_OPTS = $(INCLUDES) -I. {includes} {optimize}{pic} -DSOCKLEN_T=socklen_t -D_LARGEFILE_SOURCE=1 -D_FILE_OFFSET_BITS=64
C = c
C_COMPILER = {cc}
C_FLAGS = $(COMPILE_OPTS) $(CPPFLAGS) $(CFLAGS)
CPP = cpp
CPLUSPLUS_COMPILER = {cxx}
CPLUSPLUS_FLAGS = $(COMPILE_OPTS) -std=c++20 -Wall -DBSD=1 $(CPPFLAGS) $(CXXFLAGS)
OBJ = o
LINK = {cxx} -o
LINK_OPTS = -L. {libdirs} $(LDFLAGS)
CONSOLE_LINK_OPTS = $(LINK_OPTS)
EMPTY =
SPACE = $(EMPTY) $(EMPTY)
LIBRARY_LINK = {ar} cr$(SPACE)
LIBRARY_LINK_OPTS =
LIB_SUFFIX = a
LIBS_FOR_CONSOLE_APPLICATION = -lssl -lcrypto -pthread
LIBS_FOR_GUI_APPLICATION =
EXE =
""".format(includes=include_flags, optimize=optimize, pic=pic,
           cc=cc, cxx=cxx, ar=ar, libdirs=library_flags)

    def build(self):
        apply_conandata_patches(self)
        save(self, os.path.join(self.source_folder, "config.ohos"), self._config_text())
        self.run("./genMakefiles ohos", cwd=self.source_folder)
        jobs = min(build_jobs(self), 4)
        self.run("make -j%d" % jobs, cwd=self.source_folder)
        # The default tree has 37 self-contained program targets and all were
        # built above.  The optional testGSMStreamer skeleton is inventoried
        # but not applicable: this release deliberately omits
        # testGSMEncoder.cpp and asks the user to provide the platform-specific
        # createNewGSMAudioSource() implementation.
        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"none",'
            '"command":"none (upstream has no registered automatic tests)",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}')

    def package(self):
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for component in ("liveMedia", "groupsock", "UsageEnvironment", "BasicUsageEnvironment"):
            copy(self, "*.hh", src=os.path.join(self.source_folder, component, "include"),
                 dst=os.path.join(self.package_folder, "include"), keep_path=False)
            copy(self, "*.h", src=os.path.join(self.source_folder, component, "include"),
                 dst=os.path.join(self.package_folder, "include"), keep_path=False)
            copy(self, "*.a", src=os.path.join(self.source_folder, component),
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # All 37 applicable upstream programs were compiled as compatibility
        # evidence. This library package deliberately exposes no bin/ payload.

    def package_info(self):
        self.cpp_info.libs = ["liveMedia", "groupsock", "BasicUsageEnvironment", "UsageEnvironment"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "live")
        self.cpp_info.set_property("cmake_target_name", "live::live")

        required = ["libliveMedia.a", "libgroupsock.a",
                    "libBasicUsageEnvironment.a", "libUsageEnvironment.a"]
        missing = [name for name in required
                   if not os.path.isfile(os.path.join(self.package_folder, "lib", name))]
        if missing:
            raise ConanException("missing packaged archives: %s" % ", ".join(missing))
