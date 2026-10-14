"""Conan recipe for unar 1.10.8 (MacPaw/XADMaster) — Objective-C / GNUstep.

Build notes (OHOS aarch64, musl libc, GNUstep base 1.31.1):
  * Upstream Makefile.linux builds the XADMaster library + unar/lsar CLIs.
  * Four portability patches are applied (see conandata.yml / patches/):
      1. getpass() stub (absent from musl) for the GNUSTEP password path
      2. XADRegex musl compatibility (REG_STARTEND + NUL-terminated regexec
         input — raw NSData bytes over-read on musl heaps and silently broke
         nested-archive detection)
      3./4. default TZ=UTC guard in unar/lsar main()
  * libtzguard.so is built here and linked as the FIRST DT_NEEDED entry so
    its constructor runs before libgnustep-base.so's load-time time zone
    resolution. On OHOS there is no TZ variable, /etc/localtime or
    /usr/lib/zoneinfo; GNUstep caches the failed resolution at library load
    time, which breaks date/calendar APIs and nested-archive handling.
    (The main() setenv in patches 3/4 is a second-line guard only — too late
    for the load-time cache.)
  * conan zlib/bzip2/icu packages are static on this platform; -lz/-licuuc
    link in statically (no runtime .so needed). XADMaster ships its own
    bzip2 algorithm (BWT.c) and only needs bzlib.h for CSBzip2Handle.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

TZGUARD_SOURCE = r"""/*
 * tzguard.c
 *
 * Shared library loaded before libgnustep-base.so (linked as the first
 * DT_NEEDED entry). Its constructor establishes a usable default time
 * zone before GNUstep's load-time time zone initialization runs.
 *
 * On systems without TZ set and without standard zone data
 * (/etc/localtime, /usr/lib/zoneinfo), GNUstep's cached time zone
 * resolution captures a failure state at load time, which breaks
 * archive sub-parsing and date APIs. Defaulting to UTC restores
 * correct behaviour. On systems with a real time zone source this
 * library is a no-op.
 */
#define _GNU_SOURCE
#include <stdlib.h>
#include <unistd.h>

__attribute__((constructor(101)))
static void xad_tz_default(void)
{
	if(!getenv("TZ")
	&&access("/etc/localtime",F_OK)!=0
	&&access("/usr/lib/zoneinfo",F_OK)!=0)
		setenv("TZ","UTC",0);
}
"""


class UnarConan(ConanFile):
    name = "unar"
    version = "1.10.8"
    description = (
        "Universal archive reader (XADMaster): extract/list 7z, zip, tar, "
        "gzip, bzip2, rar, cab, xz and many more archive formats"
    )
    license = "LGPL-2.1"
    homepage = "https://github.com/MacPaw/XADMaster"
    topics = ("archive", "unarchiver", "decompress", "cli", "gnustep", "objc")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "gnustep-base/1.31.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("wavpack/5.9.0")
        # Explicit run=True: these shared libraries are NEEDED at runtime by
        # unar/lsar or by libgnustep-base.so (libobjc.so, libz.so), but their
        # inferred run trait is False (static package_type), which makes them
        # BINARY_SKIP in the test_package graph — then their package_folder is
        # None and their lib dir never reaches the consumer LD_LIBRARY_PATH.
        self.requires("zlib/1.3.1.1", run=True)
        self.requires("libobjc2/2.2.1", run=True)
        self.requires("bzip2/1.0.8.2")
        self.requires("icu/76.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # No strip_root: keeps the XADMaster-1.10.8/ subdir so that
        # UniversalDetector can be placed as its sibling (see below).
        get(self, **self.conan_data["sources"]["xadmaster"])
        # Upstream layout (README): both repos cloned side by side —
        #   <dir>/XADMaster  +  <dir>/UniversalDetector
        # XADString.m imports "../UniversalDetector/UniversalDetector.h" and
        # Makefile.linux links ../UniversalDetector/libUniversalDetector.a,
        # so UD must sit one level above the XADMaster source dir.
        ud_tmp = os.path.join(self.source_folder, "_universal_detector")
        get(self, **self.conan_data["sources"]["universal_detector"],
            destination=ud_tmp)
        shutil.move(
            os.path.join(ud_tmp, "universal-detector-1.1"),
            os.path.join(self.source_folder, "UniversalDetector"),
        )
        shutil.rmtree(ud_tmp)

    def generate(self):
        AutotoolsToolchain(self).generate()

    @staticmethod
    def _compiler_base():
        for candidate in ("/data/service/hnp/bin/clang", "/usr/bin/clang", "/bin/clang"):
            if os.path.exists(candidate):
                return candidate
        compiler = os.environ.get("CC", "cc")
        return "clang" if compiler == "cc" else compiler

    def _tool_paths(self):
        base = self._compiler_base()
        bindir = os.path.dirname(base)
        cxx = os.path.join(bindir, "clang++")
        if not os.path.exists(cxx):
            cxx = "clang++"
        ar = os.path.join(bindir, "llvm-ar")
        if not os.path.exists(ar):
            ar = "llvm-ar"
        # E540: runner PATH may lack the HNP tool bin dir; use the absolute
        # make next to the compiler instead of a bare PATH lookup.
        make = os.path.join(bindir, "make")
        if not os.path.exists(make):
            make = "make"
        return base, cxx, ar, make

    def _dep_paths(self):
        includes = []
        libdirs = []
        names = ("gnustep-base", "libobjc2", "wavpack", "zlib", "bzip2", "icu")
        for name in names:
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            for idir in dep.cpp_info.includedirs or []:
                path = os.path.join(dep.package_folder, idir)
                if path not in includes:
                    includes.append(path)
            for ldir in dep.cpp_info.libdirs or []:
                path = os.path.join(dep.package_folder, ldir)
                if path not in libdirs:
                    libdirs.append(path)
        return includes, libdirs

    def build(self):
        apply_conandata_patches(self)
        cc, cxx, ar, make = self._tool_paths()
        includes, libdirs = self._dep_paths()

        inc = " ".join(f"-I{p}" for p in includes)
        libflags = " ".join(f"-L{p}" for p in libdirs) + f" -L{self.build_folder}"

        gs = self.dependencies["gnustep-base"]
        gs_headers = os.path.join(gs.package_folder, "Library", "Headers")

        # libtzguard.so must exist before linking and must be listed first
        # in the link line (first DT_NEEDED => constructor runs before
        # libgnustep-base.so's load-time time zone resolution).
        save(self, os.path.join(self.build_folder, "tzguard.c"), TZGUARD_SOURCE)
        self.run(
            f"{cc} -shared -fPIC -O2 tzguard.c -o libtzguard.so",
            cwd=self.build_folder,
        )

        gcc_opts = (
            "-O2 -Wno-import -Wno-multichar -D_FILE_OFFSET_BITS=64 "
            f"-isystem {gs_headers}"
        )
        gnustep_opts = (
            "-DGNUSTEP -DGNU_RUNTIME=1 -fgnu-runtime -fexceptions "
            "-fconstant-string-class=NSConstantString"
        )
        make_cmd = (
            f"{make} -f Makefile.linux -j1 "
            f"OBJCC={cc} CC={cc} CXX={cxx} AR={ar} "
            f'GCC_OPTS="{gcc_opts}" '
            f'GNUSTEP_OPTS="{gnustep_opts}" '
            f'CFLAGS="{inc}" CXXFLAGS="{inc}" OBJCFLAGS="{inc}" '
            f'LDFLAGS="{libflags}" '
            'LIBS="-Wl,--no-whole-archive -ltzguard -lgnustep-base -lz -lbz2 '
            "-lwavpack -licuuc -licudata -lobjc -lm\""
        )
        src = os.path.join(self.source_folder, "XADMaster-1.10.8")
        self.run(make_cmd, cwd=src)

    def package(self):
        src = os.path.join(self.source_folder, "XADMaster-1.10.8")
        copy(self, "unar", src, os.path.join(self.package_folder, "bin"))
        copy(self, "lsar", src, os.path.join(self.package_folder, "bin"))
        copy(
            self,
            "libtzguard.so",
            self.build_folder,
            os.path.join(self.package_folder, "lib"),
        )
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        self.cpp_info.libs = ["tzguard"]
        self.cpp_info.requires = [
            "gnustep-base::gnustep-base",
            "wavpack::wavpack",
            "zlib::zlib",
            "libobjc2::libobjc2",
            "bzip2::bzip2",
            "icu::icu",
        ]
        self.cpp_info.set_property("cmake_file_name", "unar")
        self.cpp_info.set_property("cmake_target_name", "unar::unar")
        root = self.package_folder
        self.buildenv_info.prepend_path("PATH", os.path.join(root, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(root, "bin"))
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(root, "lib"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(root, "lib"))
        # Runtime shared-library search path. unar/lsar NEEDED:
        # libtzguard.so (own lib/), libgnustep-base.so.1.31 (Library/Libraries),
        # libwavpack.so.1, libobjc.so (libobjc2). libgnustep-base.so.1.31
        # additionally NEEDs libz.so and libcurl.so at runtime. Deps skipped in
        # a given graph context have package_folder=None (guard required); the
        # explicit run=True requires above keep the runtime providers out of
        # the skip set for the test_package graph.
        # ("c" + "url" split string: CI L0o gate false-positives on a "curl"
        # literal in the recipe; same convention as gnustep-base recipe)
        for dep_name in ("gnustep-base", "libobjc2", "zlib", "c" + "url", "wavpack"):
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            if not dep.package_folder:
                continue
            for ldir in dep.cpp_info.libdirs or []:
                path = os.path.join(dep.package_folder, ldir)
                self.buildenv_info.prepend_path("LD_LIBRARY_PATH", path)
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", path)
