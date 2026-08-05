#!/usr/bin/env python3
"""Conan recipe — BiSheng JDK 17.0.13 pre-built binary for HarmonyOS.

This is a pre-built binary package (not source-compiled). The adaptation
consists of three steps:
  1. Patch ELF interpreter and NEEDED entries from glibc to musl
  2. Compile a glibc compatibility shim library (libgcompat.so)
  3. Self-sign all ELF files with binary-sign-tool

See knowledge graph E083 for the ELF signing rationale.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BishengjdkConan(ConanFile):
    name = "bishengjdk"
    version = "17.0.13"
    description = "BiSheng JDK 17.0.13 for HarmonyOS (glibc-to-musl adapted + self-signed)"
    license = "GPL-2.0-with-classpath-exception"
    homepage = "https://gitee.com/openeuler/bishengjdk-17"
    url = ""  # CI fills this

    # R38: JDK provides executables (java, javac, jar, etc.)
    package_type = "application"

    # Pre-built binary: only os and arch matter
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R28: Apply conandata patches (no-op if no patches declared)
        apply_conandata_patches(self)

        # R32: Platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("bishengjdk only supports Linux/OHOS")

        # Find the JDK root directory (source() extracted files here)
        # With basic_layout, source_folder may point to a "src" subdirectory
        src_dir = self.source_folder
        if not os.path.isfile(os.path.join(src_dir, "bin", "java")):
            # Try build_folder
            src_dir = self.build_folder
        if not os.path.isfile(os.path.join(src_dir, "bin", "java")):
            # Search for the java binary
            for candidate in (self.source_folder, self.build_folder,
                               os.path.join(self.build_folder, "src"),
                               os.path.join(self.source_folder, "src")):
                if os.path.isfile(os.path.join(candidate, "bin", "java")):
                    src_dir = candidate
                    break

        self.output.info(f"JDK source directory: {src_dir}")
        lib_dir = os.path.join(src_dir, "lib")
        if not os.path.isdir(lib_dir):
            raise ConanInvalidConfiguration(f"JDK lib directory not found: {lib_dir}")

        musl_ld = "/lib/ld-musl-aarch64.so.1"
        for name in ("libc.so", "libdl.so", "libpthread.so",
                      "libm.so", "librt.so"):
            link_path = os.path.join(lib_dir, name)
            if os.path.lexists(link_path):
                os.remove(link_path)
            os.symlink(musl_ld, link_path)

        # Create libz.so symlink if system has libz.so.1
        libz_so = os.path.join(lib_dir, "libz.so")
        if not os.path.exists(libz_so):
            sys_libz = "/system/lib/libz.so.1"
            if os.path.exists(sys_libz):
                os.symlink(sys_libz, libz_so)

        # Step 2: Patch all ELF files — interpreter + NEEDED entries
        self._patch_elf_files(src_dir)

        # Step 3: Compile glibc compatibility shim library
        self._build_gcompat(lib_dir)

        # Step 4: Sign all ELF files with binary-sign-tool
        self._sign_elf_files(src_dir)

    def _patch_elf_files(self, root_dir):
        """Patch ELF interpreter and NEEDED entries from glibc to musl."""
        musl_interp = "/lib/ld-musl-aarch64.so.1"
        glibc_map = {
            "libc.so.6": "libc.so",
            "libdl.so.2": "libc.so",
            "libpthread.so.0": "libc.so",
            "libm.so.6": "libc.so",
            "librt.so.1": "libc.so",
            "ld-linux-aarch64.so.1": "libc.so",
            "libz.so.1": "libz.so",
        }
        # Find readelf and patchelf binaries
        readelf = shutil.which("readelf") or "/data/service/hnp/bin/readelf"
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        if not os.path.isfile(readelf):
            raise ConanInvalidConfiguration("readelf not found — required for ELF patching")
        if not os.path.isfile(patchelf):
            raise ConanInvalidConfiguration("patchelf not found — required for ELF patching")

        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                if not self._is_elf(fpath):
                    continue
                # Patch interpreter
                result = subprocess.run(
                    [readelf, "-l", fpath],
                    capture_output=True, text=True
                )
                if "ld-linux-aarch64" in result.stdout:
                    pe_result = subprocess.run(
                        [patchelf, "--set-interpreter", musl_interp, fpath],
                        capture_output=True, text=True
                    )
                    if pe_result.returncode != 0:
                        self.output.warning(f"patchelf interpreter failed for {fname}: {pe_result.stderr}")
                # Replace glibc NEEDED entries
                for old, new in glibc_map.items():
                    pe_result = subprocess.run(
                        [patchelf, "--replace-needed", old, new, fpath],
                        capture_output=True, text=True
                    )
                    if pe_result.returncode != 0 and pe_result.stderr:
                        self.output.info(f"patchelf NEEDED {old}->{new} for {fname}: {pe_result.stderr.strip()}")

    # glibc-to-musl compatibility shim source code
    # Provides missing glibc symbols (__getpagesize, malloc_trim, __xstat*, etc.)
    _GLIBC_COMPAT_C = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <pthread.h>
#include <setjmp.h>
#include <signal.h>
#include <ctype.h>
#include <sched.h>

int __getpagesize(void) { return getpagesize(); }

extern char **environ;
char **__environ;
__attribute__((constructor))
static void init_environ(void) { if (!__environ) __environ = environ; }

ssize_t __getdelim(char **l, size_t *n, int d, FILE *s) { return getdelim(l, n, d, s); }

int __pthread_key_create(pthread_key_t *k, void (*f)(void *)) { return pthread_key_create(k, f); }

int __sigsetjmp(sigjmp_buf e, int s) { return sigsetjmp(e, s); }

int __xstat(int v, const char *p, struct stat *b) { (void)v; return stat(p, b); }
int __fxstat(int v, int fd, struct stat *b) { (void)v; return fstat(fd, b); }
int __lxstat(int v, const char *p, struct stat *b) { (void)v; return lstat(p, b); }
int __xstat64(int v, const char *p, struct stat *b) { (void)v; return stat(p, b); }
int __fxstat64(int v, int fd, struct stat *b) { (void)v; return fstat(fd, b); }
int __lxstat64(int v, const char *p, struct stat *b) { (void)v; return lstat(p, b); }

int __xmknod(int v, const char *p, mode_t m, dev_t d) { (void)v; return mknod(p, m, d); }

int __xpg_strerror_r(int e, char *b, size_t s) { return strerror_r(e, b, s); }

static unsigned short glibc_ctype_table[384];
static unsigned short *glibc_ctype_ptr = glibc_ctype_table + 128;
const unsigned short **__ctype_b_loc(void) { return (const unsigned short **)&glibc_ctype_ptr; }

static int glibc_toupper_table[384];
static int *glibc_toupper_ptr = glibc_toupper_table + 128;
int **__ctype_toupper_loc(void) { return &glibc_toupper_ptr; }

static int glibc_tolower_table[384];
static int *glibc_tolower_ptr = glibc_tolower_table + 128;
int **__ctype_tolower_loc(void) { return &glibc_tolower_ptr; }

size_t __ctype_get_mb_cur_max(void) { return 1; }

__attribute__((constructor))
static void init_ctype_tables(void) {
    int i;
    for (i = 0; i < 384; i++) {
        int c = i - 128;
        unsigned char uc = (unsigned char)c;
        unsigned short v = 0;
        if (isupper(uc)) v |= (1 << 8);
        if (islower(uc)) v |= (1 << 9);
        if (isalpha(uc)) v |= (1 << 10);
        if (isdigit(uc)) v |= (1 << 11);
        if (isxdigit(uc)) v |= (1 << 12);
        if (isspace(uc)) v |= (1 << 13);
        if (isprint(uc)) v |= (1 << 14);
        if (isgraph(uc)) v |= (1 << 15);
        if (iscntrl(uc)) v |= (1 << 1);
        if (ispunct(uc)) v |= (1 << 2);
        if (isalnum(uc)) v |= (1 << 3);
        if (isblank(uc)) v |= (1 << 0);
        glibc_ctype_table[i] = v;
        glibc_toupper_table[i] = toupper(uc);
        glibc_tolower_table[i] = tolower(uc);
    }
}

int __libc_current_sigtimedwait(const sigset_t *s, siginfo_t *i, const struct timespec *t) { return sigtimedwait(s, i, t); }

cpu_set_t *__sched_cpualloc(size_t c) { if (c <= 0) c = 1; return (cpu_set_t *)calloc(1, CPU_ALLOC_SIZE(c)); }
int __sched_cpucount(size_t s, const cpu_set_t *set) { int i, n = 0; for (i = 0; i < (int)(s * 8); i++) if (CPU_ISSET(i, set)) n++; return n; }
void __sched_cpufree(cpu_set_t *s) { free(s); }

int malloc_trim(size_t p) { (void)p; return 0; }
void __gmon_start__(void) {}
'''

    def _build_gcompat(self, lib_dir):
        """Compile the glibc compatibility shim library."""
        # Write the embedded C source to the build folder
        compat_src = os.path.join(self.build_folder, "glibc_compat.c")
        with open(compat_src, "w") as f:
            f.write(self._GLIBC_COMPAT_C)

        cc = shutil.which("clang") or "clang"
        out_so = os.path.join(lib_dir, "libgcompat.so")
        self.output.info(f"Building glibc compat shim: {cc} -> {out_so}")
        result = subprocess.run(
            [cc, "-shared", "-fPIC", "-o", out_so, compat_src,
             "-Wall", "-Wno-unused-function"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"glibc compat shim build failed: {result.stderr}"
            )
        self.output.info("glibc compat shim built successfully")

    def _sign_elf_files(self, root_dir):
        """Self-sign all ELF files using binary-sign-tool."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.exists(sign_tool):
            raise ConanInvalidConfiguration("binary-sign-tool not found — required for ELF signing")
        count = 0
        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                if not self._is_elf(fpath):
                    continue
                signed = fpath + ".signed"
                result = subprocess.run(
                    [sign_tool, "sign", "-selfSign", "1",
                     "-inFile", fpath, "-outFile", signed,
                     "-keyAlias", "ohos", "-signAlg", "SHA256withECDSA"],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and os.path.exists(signed):
                    shutil.move(signed, fpath)
                    os.chmod(fpath, 0o755)
                    count += 1
        self.output.info(f"Signed {count} ELF files")

    @staticmethod
    def _is_elf(fpath):
        """Check if a file is an ELF binary."""
        try:
            with open(fpath, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except (IOError, OSError):
            return False

    def package(self):
        # Copy the entire JDK to the package directory
        # Source files were patched and signed in build() method
        src_dir = self.source_folder
        if not os.path.isfile(os.path.join(src_dir, "bin", "java")):
            src_dir = self.build_folder
        if not os.path.isfile(os.path.join(src_dir, "bin", "java")):
            for candidate in (self.source_folder, self.build_folder,
                               os.path.join(self.build_folder, "src"),
                               os.path.join(self.source_folder, "src")):
                if os.path.isfile(os.path.join(candidate, "bin", "java")):
                    src_dir = candidate
                    break
        copy(self, "*", src=src_dir, dst=self.package_folder)

    def package_info(self):
        # JDK executables are in bin/
        self.cpp_info.bindirs = ["bin"]
        # JDK libraries are in lib/ and lib/server/
        self.cpp_info.libdirs = ["lib", "lib/server"]
        # JDK headers for JNI
        self.cpp_info.includedirs = ["include"]
        # Conan 2.x: set JAVA_HOME and PATH for consumers
        self.runenv_info.define("JAVA_HOME", self.package_folder)
        self.runenv_info.append("PATH", os.path.join(self.package_folder, "bin"))
