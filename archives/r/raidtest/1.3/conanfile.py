#!/usr/bin/env python3
"""Conan recipe for raidtest 1.3 — FreeBSD storage-device performance tester.

raidtest is a single-file C program maintained inside the FreeBSD ports tree
(benchmarks/raidtest). There is no upstream release tarball: MASTER_SITES is
"none" and the sources live directly in the port directory. The two needed
files (raidtest.c, README) therefore travel WITH the recipe (exports/src),
pinned to ports commit 86b2c512 and SHA256-verified in source(). Platform CI
workers have restricted network access (codeberg 429 on shared egress IPs;
some workers unreachable at all), so build-time downloads were removed
entirely.

No conandata.yml is used on purpose:
  - avoids the CI pre-download path that references an uninitialized BUILD_DIR;
  - per-file download() does not rely on archive-format inference, so the
    "BadZipFile" class of failures cannot happen.

OHOS / musl adaptation (applied in build(), see notes.md):
  1. <sys/endian.h> is a FreeBSD header; musl provides le64enc/le64dec/... in
     <endian.h>. The include is switched on __linux__/__OHOS__.
  2. Upstream fork loop writes procs[i] where the loop variable is j (i is a
     leftover from the previous loop and equals the request count), an
     out-of-bounds write that crashes with -n > 1. Fixed to procs[j].

The upstream ports Makefile is a bsd.port.mk backend fragment (USES=uidfix)
and is not reusable outside the ports framework, so build() compiles the
single translation unit directly with the Conan-provided C compiler.
"""
import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, replace_in_file
from conan.tools.layout import basic_layout

_ports_commit = "86b2c5122a18d1f73e6e4e4626889fab8fb0803a"
# Sources travel WITH the recipe (exports) instead of being downloaded at
# build time. Rationale: platform CI workers have heavily restricted network
# access (observed: codeberg 429 rate-limiting of shared egress IPs, workers
# that cannot reach ftp.gnu.org or the SSH bridge at all), and this port has
# no upstream tarball to mirror. The two small text files (14 KB total) are
# pinned to the ports commit and SHA256-verified in source(), so the
# provenance guarantee is unchanged — the recipe fails loudly on any drift.
_files = {
    "raidtest.c": "70cb131d744ea339dc7054a9a8f61c552e517bb2dc070eb04d569847b9ed2237",
    "README": "64307426f57910f3661b88bc6aed586632cd5a4ffd0df8c23de079e068e7e215",
}


class RaidtestConan(ConanFile):
    name = "raidtest"
    version = "1.3"
    description = "FreeBSD tool to test performance of storage devices."
    license = "BSD-2-Clause"
    homepage = (
        "https://cgit.freebsd.org/ports/tree/benchmarks/raidtest"
    )
    url = "https://docs.freebsd.org/en/books/porters-handbook"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # sources travel with the recipe (see _files note above)
    exports = "src/*"

    def layout(self):
        basic_layout(self)

    def source(self):
        # Place the pinned sources into the source folder, verifying each
        # file's SHA256 first (provenance check; fails loudly on drift).
        # NOTE: self.export_folder is None during source() on some Conan
        # builds (observed on the CI's conan 2.29.1), so resolve the recipe
        # directory from __file__ — Conan 2 loads this conanfile.py directly
        # from the cache export folder, where src/ lives beside it.
        recipe_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(recipe_dir, "src")
        if not os.path.isdir(src_dir):
            raise ConanException(
                f"pinned sources not found at {src_dir}; exports broken")
        for name, sha in _files.items():
            path = os.path.join(src_dir, name)
            with open(path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            if digest != sha:
                raise ConanException(
                    f"{name}: sha256 mismatch (got {digest}, want {sha}); "
                    "pinned sources drifted from ports commit "
                    + _ports_commit)
            copy(self, name, src=src_dir, dst=self.source_folder)

    def build(self):
        src = self.source_folder

        # OHOS/musl patch 1: <sys/endian.h> is FreeBSD-only, and musl
        # <endian.h> does not provide the leNNenc/leNNdec helpers either, so
        # a small byte-wise compatibility layer is added (verified against
        # the OHOS SDK aarch64 sysroot).
        replace_in_file(
            self, os.path.join(src, "raidtest.c"),
            "#include <sys/endian.h>",
            "#if defined(__linux__) || defined(__OHOS__)\n"
            "#include <endian.h>\n"
            "/* musl <endian.h> lacks the FreeBSD leNNenc/leNNdec helpers. */\n"
            "static inline void le64enc(void *pp, uint64_t u) {\n"
            "\tunsigned char *p = (unsigned char *)pp;\n"
            "\tp[0] = (unsigned char)u; p[1] = (unsigned char)(u >> 8);\n"
            "\tp[2] = (unsigned char)(u >> 16); p[3] = (unsigned char)(u >> 24);\n"
            "\tp[4] = (unsigned char)(u >> 32); p[5] = (unsigned char)(u >> 40);\n"
            "\tp[6] = (unsigned char)(u >> 48); p[7] = (unsigned char)(u >> 56);\n"
            "}\n"
            "static inline uint64_t le64dec(const void *pp) {\n"
            "\tconst unsigned char *p = (const unsigned char *)pp;\n"
            "\treturn ((uint64_t)p[0] | ((uint64_t)p[1] << 8) |\n"
            "\t    ((uint64_t)p[2] << 16) | ((uint64_t)p[3] << 24) |\n"
            "\t    ((uint64_t)p[4] << 32) | ((uint64_t)p[5] << 40) |\n"
            "\t    ((uint64_t)p[6] << 48) | ((uint64_t)p[7] << 56));\n"
            "}\n"
            "static inline void le32enc(void *pp, uint32_t u) {\n"
            "\tunsigned char *p = (unsigned char *)pp;\n"
            "\tp[0] = (unsigned char)u; p[1] = (unsigned char)(u >> 8);\n"
            "\tp[2] = (unsigned char)(u >> 16); p[3] = (unsigned char)(u >> 24);\n"
            "}\n"
            "static inline uint32_t le32dec(const void *pp) {\n"
            "\tconst unsigned char *p = (const unsigned char *)pp;\n"
            "\treturn ((uint32_t)p[0] | ((uint32_t)p[1] << 8) |\n"
            "\t    ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24));\n"
            "}\n"
            "#else\n"
            "#include <sys/endian.h>\n"
            "#endif",
        )

        # OHOS/musl patch 2: __FreeBSD_version is undefined on non-FreeBSD,
        # and #if treats it as 0, which wrongly enables the FreeBSD 4.x
        # compat block (typedef redefinition of uintmax_t/intmax_t).
        replace_in_file(
            self, os.path.join(src, "raidtest.c"),
            "#if __FreeBSD_version < 500028",
            "#if defined(__FreeBSD__) && __FreeBSD_version < 500028",
        )

        # OHOS/musl patch 3: getprogname() is not declared by the OHOS musl
        # headers; provide a static fallback on non-FreeBSD.
        replace_in_file(
            self, os.path.join(src, "raidtest.c"),
            '#define\tDEFAULT_DATA_FILE\t"raidtest.data"',
            "#if !defined(__FreeBSD__)\n"
            "static const char *\n"
            "getprogname(void)\n"
            "{\n"
            "\treturn (\"raidtest\");\n"
            "}\n"
            "#endif\n"
            "\n"
            '#define\tDEFAULT_DATA_FILE\t"raidtest.data"',
        )

        # OHOS patch 4: upstream writes procs[i] in a loop over j (i is the
        # request count left over from the previous loop) - an out-of-bounds
        # write for any nprocs > 1. Fix the two occurrences to procs[j].
        replace_in_file(
            self, os.path.join(src, "raidtest.c"),
            "\t\tprocs[i] = fork();\n\t\tswitch (procs[i]) {",
            "\t\tprocs[j] = fork();\n\t\tswitch (procs[j]) {",
        )

        # R33: take the compiler from Conan conf, never bare shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Single translation unit; upstream tests do not exist (the port has
        # no test target), functional coverage is provided by test_package.
        self.run(
            f'"{cc}" -O2 -Wall raidtest.c -o raidtest',
            cwd=src,
        )

    def package(self):
        src = self.source_folder
        copy(self, "raidtest", src=src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "README", src=src,
             dst=os.path.join(self.package_folder,
                              "share", "raidtest", "doc"), keep_path=False)
        # BSD-2-Clause grant lives in the source header; keep a copy of the
        # licensed file beside licenses so the grant travels with the package.
        copy(self, "raidtest.c", src=src,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
