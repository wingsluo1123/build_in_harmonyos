#!/usr/bin/env python3
"""Conan recipe for pseudo 1.9.2-git20250711-d1db9c219abf on OHOS.

pseudo is a fakeroot replacement used by embedded build systems.  Its
upstream configure script is a small custom shell script, not Autoconf, and
requires SQLite.  The recipe builds in-source because the upstream test
runner assumes ``PSEUDO_PREFIX=$(pwd)`` and the freshly built executables and
libpseudo.so are found below that tree.

The upstream test scripts are executed one by one.  A small number depend on
host utilities or capabilities that are not part of the OHOS device image
(getfacl/setfacl, xattr tools, tclsh); those are recorded as platform skips
instead of being misreported as passes.
"""

import os
import shutil
import subprocess
import re
import signal
import time
import shlex

_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNTOOL = "/data/service/hnp/bin/binary-sign-tool"

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, save
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

from ohos_adapt import adapt_ohos_source


_FTS_COMPAT_HEADER = """#ifndef PSEUDO_OHOS_FTS_COMPAT_H
#define PSEUDO_OHOS_FTS_COMPAT_H

/* OHOS does not ship <fts.h>, but libc may still export the ABI. */
typedef struct _fts FTS;
typedef struct _ftsent FTSENT;

FTS *fts_open(char *const *path_argv, int options,
              int (*compar)(const FTSENT **, const FTSENT **));

#endif
"""

_TOUCH_SHIM = r"""#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

/* Keep the upstream touch(1) call inside libc so pseudo can observe it. */
int main(int argc, char **argv) {
    int status = 0;
    int i;

    if (argc < 2) {
        return 0;
    }

    for (i = 1; i < argc; ++i) {
        int fd = open(argv[i], O_WRONLY | O_CREAT, 0666);
        if (fd < 0) {
            fprintf(stderr, "touch: %s: %s\n", argv[i], strerror(errno));
            status = 1;
            continue;
        }
        close(fd);
        if (utimensat(AT_FDCWD, argv[i], NULL, 0) < 0) {
            fprintf(stderr, "touch: %s: %s\n", argv[i], strerror(errno));
            status = 1;
        }
    }
    return status;
}
"""


class PseudoConan(ConanFile):
    name = "pseudo"
    version = "1.9.2-git20250711-d1db9c219abf"
    description = "Advanced fakeroot replacement with a central database"
    license = "LGPL-2.1-only"
    homepage = "https://git.yoctoproject.org/pseudo"
    url = "https://git.yoctoproject.org/pseudo"
    package_type = "application"
    exports = "ohos_adapt.py"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pseudo supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("sqlite3/3.53.4")

    def layout(self):
        basic_layout(self, src_folder="src")
        self.folders.build = "src"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf(self, path):
        if not os.path.isfile(path) or os.path.islink(path) or not self._is_elf(path):
            return
        if os.path.isfile(_SIGNTOOL):
            self.run(f'{_OBJCOPY} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{_SIGNTOOL} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        os.chmod(path, 0o755)

    def _sign_runtime_tree(self):
        for folder in (
            os.path.join(self.source_folder, "bin"),
            os.path.join(self.source_folder, "lib"),
        ):
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                self._sign_elf(os.path.join(folder, name))


    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        sqlite = self.dependencies["sqlite3"].package_folder.replace("\\", "/")
        sqlite_header = os.path.join(sqlite, "include", "sqlite3.h")
        sqlite_archive = os.path.join(sqlite, "lib", "libsqlite3.a")
        if not os.path.isfile(sqlite_header) or not os.path.isfile(sqlite_archive):
            raise ConanInvalidConfiguration(
                "sqlite3/3.53.4 must provide include/sqlite3.h and lib/libsqlite3.a"
            )

        self._adapt_test_shebang()
        self._adapt_ohos_subports()
        self._adapt_ohos_portdefs()
        self._adapt_ohos_fts()
        self._adapt_ohos_varargs_wrappers()
        adapt_ohos_source(self)
        self._adapt_exec_env_allocation()
        prefix = self.package_folder.replace("\\", "/")
        self.run(
            " ".join(
                [
                    "/bin/sh ./configure",
                    f'--prefix="{prefix}"',
                    f'--libdir="{prefix}/lib"',
                    f'--with-sqlite="{sqlite}"',
                    f'--with-static-sqlite="{sqlite_archive}"',
                    "--without-rpath",
                    "--enable-xattr=no",
                    "--enable-xattrdb=no",
                    "--bits=64",
                    "--cflags=-fPIC",
                ]
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        self._sign_runtime_tree()
        self._run_upstream_tests()

    def _replace_idempotent(self, path, old, new):
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        if old in content:
            save(self, path, content.replace(old, new))
        elif new not in content:
            raise ConanException(f"adaptation pattern not found in {path}")

    def _adapt_exec_env_allocation(self):
        # Backport upstream 44e53fd. The exec wrappers call
        # pseudo_setupenvp() with a cleaned environment from commands such as
        # `env -i`; allocate the LD_* slots even when the input omitted them.
        path = os.path.join(self.source_folder, "pseudo_util.c")
        old = """\t\t++env_count;\n\t}\n\n\tfor (i = 0; pseudo_env[i].key; i++) {"""
        new = """\t\t++env_count;\n\t}\n\n\t/* If LD_PRELOAD or LD_LIBRARY_PATH were not included in the existing\n\t * environment, we need to make space for them.\n\t */\n\tif (!ld_preload)\n\t\tenv_count++;\n\tif (!ld_library_path)\n\t\tenv_count++;\n\n\tfor (i = 0; pseudo_env[i].key; i++) {"""
        self._replace_idempotent(path, old, new)

    def _adapt_test_shebang(self):

        # The device image exposes the supported bash at this absolute path;
        # /bin/bash is not present.  The scripts use bash arrays and locals,
        # so switching to /bin/sh would change their semantics.
        bash = "/data/service/hnp/bin/bash"
        tests = os.path.join(self.source_folder, "test")
        if not os.path.isdir(tests):
            raise ConanInvalidConfiguration(f"upstream test directory missing: {tests}")
        for name in os.listdir(tests):
            if not name.endswith(".sh"):
                continue
            path = os.path.join(tests, name)
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            updated = re.sub(r"(?m)^#!\s*/bin/bash\s*$", f"#!{bash}", content)
            if updated == content:
                continue
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(updated)

    def _adapt_ohos_subports(self):
        # The common port script predates OHOS and only maps Linux or Darwin
        # to an upstream port. OHOS uses the Linux port implementation.
        path = os.path.join(self.source_folder, "ports", "common", "subports")
        self._replace_idempotent(
            path,
            "case $(uname -s) in\nLinux)",
            "case $(uname -s) in\nLinux|OHOS|HarmonyOS)",
        )

    def _adapt_ohos_portdefs(self):
        # The fallback statx layout uses glibc's internal __intN_t names.
        # OHOS exposes the standard fixed-width types instead.
        path = os.path.join(
            self.source_folder, "ports", "linux", "nostatx", "portdefs.h"
        )
        old = "struct statx_timestamp"
        new = "#include <stdint.h>\n\nstruct statx_timestamp"
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        if new not in content:
            if old not in content:
                raise ConanException(f"adaptation pattern not found in {path}")
            save(self, path, content.replace(old, new, 1))
        for old, new in (
            ("__int64_t", "int64_t"),
            ("__uint64_t", "uint64_t"),
            ("__uint32_t", "uint32_t"),
            ("__int32_t", "int32_t"),
            ("__uint16_t", "uint16_t"),
        ):
            self._replace_idempotent(path, old, new)

    def _adapt_ohos_fts(self):
        # pseudo only needs the fts_open prototype to build its optional
        # passthrough wrapper; the OHOS sysroot omits glibc's <fts.h>.
        save(
            self,
            os.path.join(self.source_folder, "fts_compat.h"),
            _FTS_COMPAT_HEADER,
        )
        self._replace_idempotent(
            os.path.join(self.source_folder, "pseudo_wrappers.c"),
            "#include <fts.h>",
            '#include "fts_compat.h"',
        )

    def _adapt_ohos_varargs_wrappers(self):
        # OHOS clang does not implement GCC's __builtin_apply family.
        # syscall() and prctl() are variadic, so forward the largest
        # documented argument lists through va_list instead. Extra arguments
        # are harmless because both interfaces ignore unused parameters.
        path = os.path.join(self.source_folder, "ports", "linux", "pseudo_wrappers.c")
        replacements = (
            (
                """\t/* gcc magic to attempt to just pass these args to syscall. we have to
\t * guess about the number of args; the docs discuss calling conventions
\t * up to 7, so let's try that?
\t */
\tvoid *res = __builtin_apply((void (*)(void)) real_syscall, __builtin_apply_args(), sizeof(long) * 7);
\t__builtin_return(res);
""",
                """\tva_start(ap, number);
\tlong a1 = va_arg(ap, long);
\tlong a2 = va_arg(ap, long);
\tlong a3 = va_arg(ap, long);
\tlong a4 = va_arg(ap, long);
\tlong a5 = va_arg(ap, long);
\tlong a6 = va_arg(ap, long);
\tva_end(ap);
\treturn real_syscall(number, a1, a2, a3, a4, a5, a6);
""",
            ),
            (
                """\t/* gcc magic to attempt to just pass these args to prctl. we have to
\t * guess about the number of args; the docs discuss calling conventions
\t * up to 5, so let's try that?
\t */
\tvoid *res = __builtin_apply((void (*)(void)) real_prctl, __builtin_apply_args(), sizeof(long) * 5);
\t__builtin_return(res);
""",
                """\tva_start(ap, option);
\tlong a1 = va_arg(ap, long);
\tlong a2 = va_arg(ap, long);
\tlong a3 = va_arg(ap, long);
\tlong a4 = va_arg(ap, long);
\tva_end(ap);
\treturn real_prctl(option, a1, a2, a3, a4);
""",
            ),
        )
        for old, new in replacements:
            self._replace_idempotent(path, old, new)

    def _adapt_ohos_large_file_aliases(self):
        # OHOS maps LFS symbols such as fopen64 directly to fopen. Keeping
        # both generated wrappers would define the same C function twice.
        # The non-LFS wrappers cover both names because they share one ABI.
        aliases = {
            "creat64",
            "fcntl64",
            "fopen64",
            "freopen64",
            "fstat64",
            "fstatat64",
            "ftw64",
            "glob64",
            "lstat64",
            "mkostemp64",
            "mkstemp64",
            "nftw64",
            "open64",
            "openat64",
            "scandir64",
            "stat64",
            "truncate64",
        }
        path = os.path.join(self.source_folder, "ports", "linux", "wrapfuncs.in")
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
        filtered = []
        for line in lines:
            match = re.match(r"\s*[^#\n][^()]*?\b([A-Za-z_]\w*)\s*\(", line)
            if match and match.group(1) in aliases:
                continue
            filtered.append(line)
        save(self, path, "".join(filtered))

    def _adapt_ohos_nftw_alias(self):
        # The unix port already defines the nftw wrapper. OHOS aliases
        # nftw64 to that same symbol, so the Linux duplicate must be omitted.
        path = os.path.join(self.source_folder, "ports", "linux", "pseudo_wrappers.c")
        old = """#undef NFTW_NAME
#undef NFTW_STAT_NAME
#undef NFTW_STAT_STRUCT
#undef NFTW_LSTAT_NAME
#define NFTW_NAME nftw64
#define NFTW_STAT_NAME stat64
#define NFTW_STAT_STRUCT stat64
#define NFTW_LSTAT_NAME lstat64
#include \"../unix/guts/nftw_wrapper_base.c\"
"""
        self._replace_idempotent(path, old, "/* nftw64 aliases nftw on OHOS. */")

    def _run_upstream_tests(self):
        tests_dir = os.path.join(self.source_folder, "test")
        scripts = sorted(
            name for name in os.listdir(tests_dir)
            if name.startswith("test") and name.endswith(".sh")
        )
        if len(scripts) != 25:
            raise ConanException(
                f"upstream pseudo test inventory changed: {len(scripts)}/25 scripts"
            )

        optional_tools = {
            "test-acl.sh": ("setfacl", "getfacl"),
            "test-xattr.sh": ("getfattr", "setfattr"),
            "test-tclsh-fork.sh": ("tclsh",),
        }
        chroot_skip = (
            "OHOS terminates chroot(2) from the unprivileged device account " 
            "with SIGSYS (signal 31, core dumped), so no chroot can be created"
        )
        platform_skips = {
            "test-nftw.sh": (
                "OHOS libc omits the GNU nftw extensions " 
                "(FTW_ACTIONRETVAL/FTW_SKIP_SUBTREE/FTW_SKIP_SIBLINGS)"
            ),
            "test-statx.sh": (
                "OHOS libc does not export the Linux statx syscall wrapper"
            ),
            # OHOS ships no user namespaces or capability model for this sandbox:
            # chroot(2) from the unprivileged device account is terminated by the
            # service sandbox with SIGSYS (signal 31, core dumped), so a chroot
            # can never be established for these three scripts.
            "test-chroot.sh": chroot_skip,
            "test-chroot-symlink.sh": chroot_skip,
            "test-reexec-chroot.sh": chroot_skip,
            # Every file on OHOS is created with security.selinux/security.isolate
            # attributes and security.* xattrs cannot be written by the device
            # account (setxattr -> EPERM), so the upstream test's precondition of
            # an attribute-free file cannot hold on any mounted filesystem.
            "test-xattr.sh": (
                "OHOS pre-labels every file with security.selinux/security.isolate " 
                "and rejects security.* setxattr with EPERM (user.* is accepted); " 
                "the upstream test requires an attribute-free file"
            ),
            # OHOS mounts / and every /data/system level directory as 0711, so
            # openat(fd, "../", O_DIRECTORY) - which is O_RDONLY - fails with
            # EACCES before the walk can reach /.  Measured with the pseudo
            # preload removed entirely, so the loop is not reachable on this
            # device no matter how pseudo behaves.
            "test-openat.sh": (
                "OHOS system directories are mode 0711, so the upstream walk " 
                "fails with EACCES on openat(fd, '../', O_DIRECTORY) even " 
                "without the pseudo preload"
            ),
        }
        skipped = []
        passed = []
        failed = []

        mirror_dir = os.path.join(
            "/data/storage/el2/base/cache",
            f"pseudo-source-{os.getpid()}-{time.time_ns()}",
        )
        shutil.copytree(self.source_folder, mirror_dir, symlinks=True)
        state_dir = os.path.join(mirror_dir, "var", "pseudo")
        shutil.rmtree(state_dir, ignore_errors=True)
        os.makedirs(state_dir, exist_ok=True)

        helper_sources = sorted(
            name for name in os.listdir(os.path.join(mirror_dir, "test"))
            if name.startswith("test-") and name.endswith(".c")
        )
        unsupported_helpers = {"test-nftw", "test-nftw64", "test-statx"}
        helper_targets = [
            os.path.join("test", name[:-2])
            for name in helper_sources
            if name[:-2] not in unsupported_helpers
        ]
        self.run(
            "make -j1 " + " ".join(helper_targets),
            cwd=mirror_dir,
            env="conanbuild",
        )
        for target in helper_targets:
            self._sign_elf(os.path.join(mirror_dir, target))

        tool_dir = os.path.join(mirror_dir, ".ohos-test-tools")
        os.makedirs(tool_dir, exist_ok=True)
        cc = (self.conf.get("tools.build:compiler_executables", default={}) or {}).get("c")
        cc = cc or "/data/service/hnp/bin/clang"
        gcc_wrapper = os.path.join(tool_dir, "gcc")
        with open(gcc_wrapper, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                "#!/bin/sh\n"
                "set -e\n"
                "out=\n"
                "prev=\n"
                "for arg in \"$@\"; do\n"
                "  if [ \"$prev\" = \"-o\" ]; then out=$arg; fi\n"
                "  prev=$arg\n"
                "done\n"
                f"{shlex.quote(cc)} \"$@\"\n"
                "if [ -n \"$out\" ] && [ -f \"$out\" ]; then\n"
                f"  {shlex.quote(_OBJCOPY)} --remove-section .codesign \"$out\" 2>/dev/null || true\n"
                f"  {shlex.quote(_SIGNTOOL)} sign -inFile \"$out\" -outFile \"$out\" -selfSign 1 >/dev/null\n"
                "fi\n"
            )
        os.chmod(gcc_wrapper, 0o755)

        touch_source = os.path.join(tool_dir, "touch.c")
        save(self, touch_source, _TOUCH_SHIM)
        touch_shim = os.path.join(tool_dir, "touch")
        self.run(
            f"{shlex.quote(cc)} -O2 -o {shlex.quote(touch_shim)} {shlex.quote(touch_source)}",
            cwd=mirror_dir,
            env="conanbuild",
        )
        self._sign_elf(touch_shim)

        env = dict(os.environ)
        env["PATH"] = tool_dir + os.pathsep + env.get("PATH", "")
        # The upstream tests are driven by the HNP bash build, whose getcwd()
        # walks up through the parents and re-reads them.  OHOS mounts /,
        # /data, /data/storage and /data/storage/el2 as 0711 directories owned
        # by root, so that walk always stops with EACCES and bash cannot tell
        # where it is (measured on the device: "shell-init: error retrieving
        # current directory: getcwd: cannot access parent directories:
        # Permission denied", while a statically resolved getcwd() in the same
        # directory works).  Bash then keeps the stale $PWD inherited from the
        # Conan process, which breaks test-relative-from-root.sh: that test
        # splits $PWD apart and re-resolves it from /.  Hand the shell the
        # working directory it was started in so the test exercises the
        # relative-path lookup it is actually about.
        env["PWD"] = mirror_dir
        env["PSEUDO_PREFIX"] = mirror_dir
        env["PSEUDO_LOCALSTATEDIR"] = state_dir
        # Let bin/pseudo install its own preload path; an inherited value can
        # make the launcher itself start with libpseudo already loaded.
        env.pop("LD_PRELOAD", None)
        launcher = os.path.join(mirror_dir, "bin", "pseudo")
        previous_script = None

        try:
            for script in scripts:
                if script in platform_skips:
                    skipped.append((script, platform_skips[script]))
                    continue
                missing = [tool for tool in optional_tools.get(script, ()) if shutil.which(tool) is None]
                if missing:
                    skipped.append((script, "missing host tool(s): " + ", ".join(missing)))
                    continue

                # Upstream run_tests.sh starts every script from a fresh
                # var/pseudo (mkdir -p var/pseudo; ...; rm -rf var/pseudo/*).
                # Reusing one database across scripts leaks inode state and
                # makes later scripts fail for reasons unrelated to the test.
                shutil.rmtree(state_dir, ignore_errors=True)
                os.makedirs(state_dir, exist_ok=True)

                # rm -rf var/pseudo/* also retires the pseudo server for that
                # prefix upstream; a surviving daemon keeps the previous
                # script's cached umask/disable state and poisons later scripts.
                pkill_bin = shutil.which("pkill")
                if pkill_bin and previous_script:
                    # The pseudo server inherits the client's argv, so the
                    # script name still identifies a daemon left behind by the
                    # previous script.
                    subprocess.run(
                        [pkill_bin, "-f", f"test/{previous_script}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                    time.sleep(0.5)

                self.output.info(f"RUN {script}")
                previous_script = script
                started = time.monotonic()
                process = subprocess.Popen(
                    # Upstream run_tests.sh invokes bin/pseudo, which installs
                    # LD_PRELOAD and initializes the test environment through
                    # pseudo_setupenv().  Invoking bash directly skips that
                    # initialization and makes fork/unload/env_i tests fail.
                    [launcher, os.path.join("test", script), "-v"],
                    cwd=mirror_dir,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=env,
                    start_new_session=True,
                )
                try:
                    output, _ = process.communicate(timeout=180)
                    returncode = process.returncode
                except subprocess.TimeoutExpired:
                    # Some upstream tests spawn background children.  Killing only
                    # the shell can leave those children holding the captured pipe
                    # open forever, so kill the whole test process group here.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except OSError:
                        process.kill()
                    try:
                        output, _ = process.communicate(timeout=10)
                    except subprocess.TimeoutExpired:
                        output = ""
                    failed.append(script)
                    elapsed = time.monotonic() - started
                    self.output.warning(
                        f"FAIL {script} timeout after {elapsed:.1f}s\n"
                        f"{(output or '')[-1200:]}"
                    )
                    continue
                elapsed = time.monotonic() - started
                if returncode == 0:
                    passed.append(script)
                    self.output.info(f"PASS {script} ({elapsed:.1f}s)")
                else:
                    failed.append(script)
                    tail = (output or "")[-1200:]
                    self.output.warning(
                        f"FAIL {script} rc={returncode} ({elapsed:.1f}s)\n{tail}"
                    )
        finally:
            shutil.rmtree(mirror_dir, ignore_errors=True)

        self.output.info(
            "pseudo upstream tests: "
            f"{len(passed)} passed, {len(failed)} failed, "
            f"{len(skipped)} platform-skipped"
        )
        for script, reason in skipped:
            self.output.warning(f"SKIP {script}: {reason}")
        shutil.rmtree(state_dir, ignore_errors=True)
        if failed:
            raise ConanException(
                "upstream pseudo tests failed: " + ", ".join(failed)
            )

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")
        for folder in (
            os.path.join(self.package_folder, "bin"),
            os.path.join(self.package_folder, "lib"),
        ):
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                self._sign_elf(os.path.join(folder, name))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["pseudo"]
        self.cpp_info.includedirs = []
        self.cpp_info.system_libs = ["dl", "pthread"]
