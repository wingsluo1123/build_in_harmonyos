#!/usr/bin/env python3
"""Conan recipe for mar 0.5 - meta archive library, C++ stream wrappers and the mar utility.

Upstream (Mark Aylett, 2004, MIT) ships a two-level plain Makefile that builds libmar.a and the
`mar` command-line utility; `make check` additionally builds and runs the C++ test program mar_test.

OHOS notes
----------
* Plain `char` is unsigned on OHOS aarch64 (as on every AAPCS64 Linux target).  The utility keeps
  mar_getopt()'s int result in a `char`; the EOF (-1) that ends option parsing becomes 255, the
  `-1 != ch` loop condition is always true, the switch falls into `default` and every real
  invocation ends with "Unknown option" and exit status 1 (only -h, which returns early, works).
  The option list is scanned twice (main() and mar_run()), so there are two such variables; patch
  0003 declares both as int.  clang does warn (-Wtautological-constant-out-of-range-compare, on by
  default) but the build still succeeds, so the recipe promotes exactly that warning to an error
  as a regression guard.
* The C++ stream wrappers call members of their dependent base classes unqualified (rdbuf, setg,
  sputc).  clang/libc++ rejects that (two-phase name lookup), so neither a C++ consumer of the
  installed headers nor upstream's own `make check` compiles.  Patches 0001 and 0002 add base_type::.
* Upstream `make install` is not used: its header list lacks mar_string_c.h (included by
  mar_key_cpp.h, so eight of the twelve C++ headers cannot be included after an upstream install),
  it never creates $(MANDIR)/man1 and it has no DESTDIR.  package() installs the files itself.
* mar_storage_c.h stops with #error unless MAR_STATIC or MAR_SHARED is defined, so package_info()
  exports MAR_STATIC for consumers.
* bin/mar is linked -static-pie (PIE, RELRO, BIND_NOW) like tal and cutmp3: the delivered binary
  is self-contained, so build() and test_package execute that very file natively on AArch64 and
  through qemu-aarch64 on x86 runners (a dynamic OHOS executable cannot start there: no
  /lib/ld-musl-aarch64.so.1).
"""
import os
import platform
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# The public headers of upstream's Makefile (HEADERS) plus mar_string_c.h, which mar_key_cpp.h needs.
HEADERS = (
    "mar_c.h", "mar_defs_c.h", "mar_storage_c.h", "mar_string_c.h", "mar_types_c.h",
    "mar_archive_cpp.h", "mar_compat_cpp.h", "mar_defs_cpp.h", "mar_exception_cpp.h",
    "mar_index_cpp.h", "mar_iterator_cpp.h", "mar_key_cpp.h", "mar_stream_cpp.h",
    "mar_streambuf_cpp.h", "mar_transaction_cpp.h", "mar_types_cpp.h", "mar_util_cpp.h",
)


class MarConan(ConanFile):
    name = "mar"
    version = "0.5"
    description = "MAR meta archive: simple binary file format for meta data and user data, C library, C++ wrappers and mar utility"
    license = "MIT"
    homepage = "https://cgit.freebsd.org/ports/tree/archivers/mar"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("archive", "metadata", "mmap", "file-format")

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mar is validated on Linux/OHOS only, not {self.settings.os}")

    def configure(self):
        # libmar.a and the utility are plain C: the C++ runtime does not enter the package id.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @staticmethod
    def _llvm_tool(cc, name):
        # The profile names only clang; llvm-ar/llvm-ranlib sit next to the real compiler
        # (the profile path is a symlink into the SDK).
        candidate = os.path.join(os.path.dirname(os.path.realpath(cc)), name)
        return candidate if os.path.exists(candidate) else name

    def _make(self, *targets):
        execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = execs.get("c", "clang")
        cxx = execs.get("cpp", "clang++")
        ar = execs.get("ar") or self._llvm_tool(cc, "llvm-ar")
        ranlib = execs.get("ranlib") or self._llvm_tool(cc, "llvm-ranlib")
        opt = "-O0 -g" if self.settings.build_type == "Debug" else "-O2"
        # Command-line variables override the Makefile's own CC/CXX/AR/RANLIB/CFLAGS/LDFLAGS.
        # The same LDFLAGS link both `mar` and the upstream test program.
        guard = "-Werror=tautological-constant-out-of-range-compare"
        args = ["make", "-j1", "-C", "src", *targets,
                f"CC={cc}", f"CXX={cxx}", f"AR={ar}", f"RANLIB={ranlib}",
                f"CFLAGS={opt} -fPIC {guard}", "CXXFLAGS=-std=gnu++17",
                "LDFLAGS=-static-pie -Wl,-z,relro,-z,now"]
        self.run(shlex.join(args), cwd=self.source_folder, env="conanbuild")

    def _target_cmd(self, *args):
        """Command line that runs an AArch64 binary: natively on AArch64, else via qemu-aarch64."""
        if platform.machine().lower() in ("aarch64", "arm64"):
            return shlex.join(args)
        qemu = shutil.which("qemu-aarch64")
        if qemu is None:
            return None
        return shlex.join((qemu,) + args)

    def _run_upstream_tests(self):
        # Upstream's `make check` target builds src/mar_test (C++ wrappers on top of libmar.a) and runs
        # ./mar_test; it is built through the same make rules and run here through the launcher.
        self.output.info("upstream check target: make check -> build src/mar_test, run ./mar_test")
        self._make("mar_test")
        workdir = os.path.join(self.build_folder, "mar_test_run")
        os.makedirs(workdir, exist_ok=True)
        cmd = self._target_cmd(os.path.join(self.source_folder, "src", "mar_test"))
        if cmd is None:
            self.output.warning("SKIPPED upstream mar_test: not an AArch64 host and no qemu-aarch64")
            return
        self.run(cmd, cwd=workdir)

    def build(self):
        apply_conandata_patches(self)
        self._make("all")
        if not self.conf.get("tools.build:skip_test", default=False):
            self._run_upstream_tests()

    def package(self):
        src, pkg = self.source_folder, self.package_folder
        copy(self, "mar", os.path.join(src, "src"), os.path.join(pkg, "bin"), keep_path=False)
        copy(self, "libmar.a", os.path.join(src, "src"), os.path.join(pkg, "lib"), keep_path=False)
        for header in HEADERS:
            copy(self, header, os.path.join(src, "include"), os.path.join(pkg, "include"))
        copy(self, "mar.1", os.path.join(src, "man", "man1"),
             os.path.join(pkg, "share", "man", "man1"), keep_path=False)
        copy(self, "copying.txt", src, os.path.join(pkg, "licenses"), keep_path=False)
        copy(self, "changelog.txt", src, os.path.join(pkg, "share", "doc", "mar"), keep_path=False)
        copy(self, "mar_format.txt", os.path.join(src, "src"),
             os.path.join(pkg, "share", "doc", "mar"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["mar"]
        self.cpp_info.defines = ["MAR_STATIC"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
