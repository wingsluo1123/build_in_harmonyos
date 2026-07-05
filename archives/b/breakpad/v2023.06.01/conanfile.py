#!/usr/bin/env python3
"""Conan recipe for breakpad v2023.06.01 — custom build (bypass autotools).

Google Breakpad is a crash reporting system. On OHOS, autotools config.status
fails because the /storage filesystem doesn't support file execution needed
by awk scripts. This recipe bypasses autotools entirely and compiles the
source files directly.

Only the Linux client library (libbreakpad_client) is built, which is the
component used for crash reporting on Linux/OHOS platforms.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


LSS_STUB = '''#ifndef LINUX_SYSCALL_SUPPORT_H
#define LINUX_SYSCALL_SUPPORT_H
#include <sys/types.h>
#include <sys/stat.h>
#include <signal.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/wait.h>
#include <sys/mman.h>
#include <sys/ptrace.h>
#include <sys/prctl.h>
#include <dirent.h>
#include <sched.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/uio.h>
struct kernel_dirent {
    unsigned long d_ino;
    unsigned long d_off;
    unsigned short d_reclen;
    char d_name[256];
};
#define kernel_stat stat
#define kernel_sigaction sigaction
#define kernel_iovec iovec
#define kernel_msghdr msghdr
#define kernel_pollfd pollfd
static inline int sys_close(int fd) { return close(fd); }
static inline int sys_open(const char* p, int f, ...) { return open(p, f); }
static inline ssize_t sys_read(int fd, void* b, size_t n) { return read(fd, b, n); }
static inline ssize_t sys_write(int fd, const void* b, size_t n) { return write(fd, b, n); }
static inline int sys_dup(int fd) { return dup(fd); }
static inline int sys_dup2(int a, int b) { return dup2(a, b); }
static inline off_t sys_lseek(int fd, off_t o, int w) { return lseek(fd, o, w); }
static inline int sys_unlink(const char* p) { return unlink(p); }
static inline pid_t sys_getpid(void) { return getpid(); }
static inline pid_t sys_getppid(void) { return getppid(); }
static inline pid_t sys_gettid(void) { return syscall(SYS_gettid); }
static inline int sys_kill(pid_t p, int s) { return kill(p, s); }
static inline pid_t sys_waitpid(pid_t p, int* s, int o) { return waitpid(p, s, o); }
static inline int sys_tgkill(pid_t t, pid_t p, int s) { return syscall(SYS_tgkill, t, p, s); }
static inline int sys_pipe(int fds[2]) { return pipe(fds); }
static inline void* sys_mmap(void* a, size_t l, int p, int f, int fd, off_t o) { return mmap(a, l, p, f, fd, o); }
static inline int sys_munmap(void* a, size_t l) { return munmap(a, l); }
static inline int sys_rt_sigaction(int s, const struct sigaction* a, struct sigaction* o, size_t) { return sigaction(s, a, o); }
static inline int sys_sigaltstack(const stack_t* s, stack_t* o) { return sigaltstack(s, o); }
static inline int sys_socket(int d, int t, int p) { return socket(d, t, p); }
static inline ssize_t sys_sendmsg(int fd, const struct msghdr* m, int f) { return sendmsg(fd, m, f); }
static inline ssize_t sys_recvmsg(int fd, struct msghdr* m, int f) { return recvmsg(fd, m, f); }
static inline int sys_getdents(int fd, void* b, size_t n) { return syscall(SYS_getdents64, fd, b, n); }
static inline int sys_connect(int fd, const struct sockaddr* a, socklen_t l) { return connect(fd, a, l); }
static inline int sys_bind(int fd, const struct sockaddr* a, socklen_t l) { return bind(fd, a, l); }
static inline int sys_listen(int fd, int b) { return listen(fd, b); }
static inline int sys_accept(int fd, struct sockaddr* a, socklen_t* l) { return accept(fd, a, l); }
static inline int sys_setsockopt(int fd, int l, int n, const void* v, socklen_t len) { return setsockopt(fd, l, n, v, len); }
static inline int sys_getsockopt(int fd, int l, int n, void* v, socklen_t* len) { return getsockopt(fd, l, n, v, len); }
static inline int sys_shutdown(int fd, int h) { return shutdown(fd, h); }
static inline int sys_ptrace(int op, ...) { return ptrace(op, 0, 0, 0); }
static inline int sys_sigemptyset(sigset_t* s) { sigemptyset(s); return 0; }
static inline int sys_stat(const char* p, struct stat* s) { return stat(p, s); }
static inline int sys_fstat(int fd, struct stat* s) { return fstat(fd, s); }
static inline ssize_t sys_readlink(const char* p, char* b, size_t s) { return readlink(p, b, s); }
static inline int sys_prctl(int op, ...) { return prctl(op, 0, 0, 0, 0); }
static inline int sys_clone(int (*fn)(void *), void *stack, int flags, void *arg,
                            pid_t *ptid, void *tls, pid_t *ctid) {
    pid_t pid = syscall(SYS_clone, flags, stack, ptid, ctid, tls);
    if (pid == 0) {
        fn(arg);
        _exit(0);
    }
    return pid;
}
#endif
'''

STAB_H_STUB = '''#ifndef STAB_H
#define STAB_H
#define N_GSYM 0x20
#define N_FUN 0x24
#define N_SLINE 0x44
#define N_SO 0x64
#define N_LSYM 0x80
#define N_BINCL 0x82
#define N_SOL 0x84
#define N_PSYM 0xa0
#define N_EINCL 0xa2
#define N_LBRAC 0xc0
#define N_RBRAC 0xe0
#define N_STSYM 0x26
#define N_LCSYM 0x28
#define N_ROSYM 0x2c
#define N_RSYM 0x40
#define N_BCOMM 0xe2
#define N_ECOMM 0xe4
#define N_SSYM 0x60
#define N_ENDM 0xfe
#endif
'''

CONFIG_H = '''#ifndef BREAKPAD_CONFIG_H
#define BREAKPAD_CONFIG_H
#define HAVE_ARC4RANDOM 1
#define HAVE_GETRANDOM 1
#define HAVE_MEMFD_CREATE 1
#define HAVE_INTTYPES_H 1
#define HAVE_STDINT_H 1
#define HAVE_STDIO_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRINGS_H 1
#define HAVE_STRING_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_UNISTD_H 1
#define HAVE_SYS_MMAN_H 1
#define HAVE_SYS_RANDOM_H 1
#define HAVE_PTHREAD 1
#define PACKAGE "breakpad"
#define PACKAGE_VERSION "v2023.06.01"
#endif
'''


class BreakpadConan(ConanFile):
    name = "breakpad"
    version = "v2023.06.01"
    description = "Google Breakpad - crash reporting library and tools"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/breakpad"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # Create linux_syscall_support.h stub (lss not available on OHOS)
        lss_dir = os.path.join(src, "src", "third_party", "lss")
        os.makedirs(lss_dir, exist_ok=True)
        lss_path = os.path.join(lss_dir, "linux_syscall_support.h")
        if not os.path.exists(lss_path):
            with open(lss_path, "w") as f:
                f.write(LSS_STUB)

        # Create stab.h stub
        stab_path = os.path.join(src, "src", "stab.h")
        if not os.path.exists(stab_path):
            with open(stab_path, "w") as f:
                f.write(STAB_H_STUB)

        # Create config.h manually (bypassing autotools config.status)
        config_h_path = os.path.join(src, "src", "config.h")
        with open(config_h_path, "w") as f:
            f.write(CONFIG_H)

        # Source files for libbreakpad_client (Linux client library)
        client_sources = [
            "src/client/minidump_file_writer.cc",
            "src/client/linux/crash_generation/crash_generation_client.cc",
            "src/client/linux/crash_generation/crash_generation_server.cc",
            "src/client/linux/dump_writer_common/thread_info.cc",
            "src/client/linux/dump_writer_common/ucontext_reader.cc",
            "src/client/linux/handler/exception_handler.cc",
            "src/client/linux/handler/minidump_descriptor.cc",
            "src/client/linux/log/log.cc",
            "src/client/linux/microdump_writer/microdump_writer.cc",
            "src/client/linux/minidump_writer/linux_core_dumper.cc",
            "src/client/linux/minidump_writer/linux_dumper.cc",
            "src/client/linux/minidump_writer/linux_ptrace_dumper.cc",
            "src/client/linux/minidump_writer/minidump_writer.cc",
            "src/client/linux/minidump_writer/pe_file.cc",
            "src/common/convert_UTF.cc",
            "src/common/linux/breakpad_getcontext.S",
            "src/common/linux/crc32.cc",
            "src/common/linux/elf_core_dump.cc",
            "src/common/linux/elf_symbols_to_module.cc",
            "src/common/linux/file_id.cc",
            "src/common/linux/elfutils.cc",
            "src/common/linux/linux_libc_support.cc",
            "src/common/linux/memory_mapped_file.cc",
            "src/common/linux/safe_readlink.cc",
            "src/common/linux/synth_elf.cc",
            "src/common/language.cc",
            "src/common/md5.cc",
            "src/common/module.cc",
            "src/common/path_helper.cc",
            "src/common/simple_string_dictionary.cc",
        ]

        # Note: dwarf sources and dump_symbols.cc are excluded because they
        # use non-standard types (uint64, int32) and are only needed for
        # symbol processing tools, not the client library.

        all_sources = list(client_sources)

        # Filter out non-source files and non-existent files
        compile_sources = []
        for s in all_sources:
            if s.endswith(('.cc', '.c', '.S')) and os.path.exists(os.path.join(src, s)):
                compile_sources.append(s)

        # Compile all source files
        obj_files = []
        for src_file in compile_sources:
            obj_file = src_file.replace('/', '_').replace('.cc', '.o').replace('.c', '.o').replace('.S', '.o')
            obj_path = os.path.join(src, obj_file)
            cmd = (f"clang++ -std=c++17 -O2 -fPIC -DHAVE_CONFIG_H "
                   f"-I{src}/src -I{src}/src/common -I{src}/src/client "
                   f"-I{src}/src/third_party/lss "
                   f"-c {src}/{src_file} -o {obj_path}")
            self.run(cmd)
            obj_files.append(obj_path)

        # Create static library
        lib_path = os.path.join(src, "libbreakpad_client.a")
        ar_cmd = f"ar rcs {lib_path} {' '.join(obj_files)}"
        self.run(ar_cmd)

    def package(self):
        src = self.source_folder
        # Install library
        copy(self, "libbreakpad_client.a",
             src=src, dst=os.path.join(self.package_folder, "lib"))
        # Install headers
        copy(self, "*.h",
             src=os.path.join(src, "src", "client"),
             dst=os.path.join(self.package_folder, "include", "client"))
        copy(self, "*.h",
             src=os.path.join(src, "src", "common"),
             dst=os.path.join(self.package_folder, "include", "common"))
        copy(self, "*.h",
             src=os.path.join(src, "src", "google_breakpad"),
             dst=os.path.join(self.package_folder, "include", "google_breakpad"))
        copy(self, "*.h",
             src=os.path.join(src, "src", "third_party", "lss"),
             dst=os.path.join(self.package_folder, "include", "third_party", "lss"))

    def package_info(self):
        self.cpp_info.libs = ["breakpad_client"]
