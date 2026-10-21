#!/usr/bin/env python3
"""Conan recipe for slurm-wlm 25.11.4 -- the Slurm HPC workload manager.

Path C (high-difficulty) adaptation: ~750 C translation units and a dependency
chain of munge/hwloc/json-c/http-parser/readline/ncurses/libcap/libaio.

The SchedMD *release* tarball is used on purpose: it ships a pre-generated
``configure`` (plus ``Makefile.in``/``aclocal.m4``), which is the only way to
build here -- the HarmonyOS hosts provide autoconf/m4 but no automake,
aclocal or libtoolize, so a GitHub tag archive (configure.ac + Makefile.am
only) cannot be bootstrapped at all.  Optional backends that have no OHOS
counterpart (freeipmi, NVML/CUDA, RSMI/ROCm, MySQL) are switched off.

The upstream unit suite (testsuite/slurm_unit, 41 libcheck programs) is built
and executed by build() and its result is printed as SLURM-UPSTREAM-* lines.
"""
import io
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, save)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


_MUSL_SHIM_C = r"""/* OHOS/musl shims for glibc-only reentrant account enumeration.
 * The non-reentrant getpwent()/getgrent() are wrapped and their string fields
 * are copied into the caller supplied buffer.
 */
#include <errno.h>
#include <grp.h>
#include <pwd.h>
#include <stddef.h>
#include <string.h>

static char *dup_field(char **cursor, char **end, const char *s)
{
    size_t n;
    char *out;

    if (!s)
        return NULL;
    n = strlen(s) + 1;
    if ((size_t)(*end - *cursor) < n)
        return NULL;
    out = *cursor;
    memcpy(out, s, n);
    *cursor += n;
    return out;
}

int getpwent_r(struct passwd *pwd, char *buf, size_t buflen, struct passwd **result)
{
    struct passwd *p = getpwent();
    char *cur = buf, *end = buf + buflen;
    struct passwd tmp;

    if (!p) { *result = NULL; return 0; }
    tmp = *p;
    tmp.pw_name = dup_field(&cur, &end, p->pw_name);
    tmp.pw_passwd = dup_field(&cur, &end, p->pw_passwd);
    tmp.pw_gecos = dup_field(&cur, &end, p->pw_gecos);
    tmp.pw_dir = dup_field(&cur, &end, p->pw_dir);
    tmp.pw_shell = dup_field(&cur, &end, p->pw_shell);
    if (!tmp.pw_name || !tmp.pw_passwd || !tmp.pw_dir || !tmp.pw_shell ||
        (p->pw_gecos && !tmp.pw_gecos)) {
        *result = NULL;
        return ERANGE;
    }
    *pwd = tmp;
    *result = pwd;
    return 0;
}

int getgrent_r(struct group *grp, char *buf, size_t buflen, struct group **result)
{
    struct group *g = getgrent();
    char *cur = buf, *end = buf + buflen;
    struct group tmp;
    int i;

    if (!g) { *result = NULL; return 0; }
    tmp = *g;
    tmp.gr_name = dup_field(&cur, &end, g->gr_name);
    tmp.gr_passwd = dup_field(&cur, &end, g->gr_passwd);
    if (!tmp.gr_name || !tmp.gr_passwd) { *result = NULL; return ERANGE; }
    if (g->gr_mem) {
        char **mem = (char **)cur;
        for (i = 0; g->gr_mem[i]; i++) {
            char *n = dup_field(&cur, &end, g->gr_mem[i]);
            if (!n) { *result = NULL; return ERANGE; }
            mem[i] = n;
        }
        mem[i] = NULL;
        tmp.gr_mem = mem;
    } else {
        tmp.gr_mem = NULL;
    }
    *grp = tmp;
    *result = grp;
    return 0;
}


/* glibc-only; musl exposes faccessat() with AT_EACCESS instead */
#include <fcntl.h>
#include <unistd.h>

int euidaccess(const char *path, int mode)
{
    return faccessat(AT_EACCESS, path, mode, 0);
}

/* musl has no working pthread cancellation (known gap, knowledge
 * musl-pthread-cancel-gap); provide the entry points as no-op stubs so the
 * daemons link. */
#include <pthread.h>

int pthread_cancel(pthread_t thread)
{
    (void)thread;
    return 0;
}

int pthread_setcanceltype(int type, int *oldtype)
{
    if (oldtype)
        *oldtype = PTHREAD_CANCEL_DEFERRED;
    (void)type;
    return 0;
}

int pthread_setcancelstate(int state, int *oldstate)
{
    if (oldstate)
        *oldstate = PTHREAD_CANCEL_ENABLE;
    (void)state;
    return 0;
}

void pthread_testcancel(void)
{
}
"""
_MUSL_COMPAT_H = r"""/* OHOS (musl) compatibility shims for glibc-only interfaces.
 *
 * musl does not implement the NSAP address helpers (inet_nsap_addr /
 * inet_nsap_ntoa) or the reentrant resolver entry points; slurm uses them in
 * its "run a command" / host-id paths.  They are provided here as static
 * inline functions and force-included into every translation unit, so no
 * link-time symbol is left undefined and no upstream file has to change.
 */
#ifndef SLURM_MUSL_COMPAT_H
#define SLURM_MUSL_COMPAT_H

static inline unsigned char *inet_nsap_addr(const char *ascii,
                                            unsigned char *binary, int maxlen)
{
    const char *p = ascii;
    int len = 0, nib = 0;
    unsigned char b = 0;

    if (p == 0 || binary == 0)
        return 0;
    if (p[0] == '0' && (p[1] == 'x' || p[1] == 'X'))
        p += 2;
    for (; *p != '\0' && len < maxlen; p++) {
        int v;
        if (*p == '.')
            continue;
        if (*p >= '0' && *p <= '9') v = *p - '0';
        else if (*p >= 'a' && *p <= 'f') v = *p - 'a' + 10;
        else if (*p >= 'A' && *p <= 'F') v = *p - 'A' + 10;
        else return 0;
        if (nib == 0) { b = (unsigned char)(v << 4); nib = 1; }
        else { binary[len++] = (unsigned char)(b | v); nib = 0; }
    }
    if (nib != 0 && len < maxlen)
        binary[len++] = b;
    return binary;
}

static inline char *inet_nsap_ntoa(int binlen, const unsigned char *binary,
                                   char *ascii)
{
    static const char hexd[] = "0123456789abcdef";
    char *p = ascii;
    int i;

    if (binary == 0 || ascii == 0)
        return 0;
    *p++ = '0';
    *p++ = 'x';
    for (i = 0; i < binlen; i++) {
        *p++ = hexd[(binary[i] >> 4) & 0x0f];
        *p++ = hexd[binary[i] & 0x0f];
    }
    *p = '\0';
    return ascii;
}

/* glibc-only <sys/wait.h> helpers */
#ifndef W_EXITCODE
#  define W_EXITCODE(ret, sig) ((ret) << 8 | (sig))
#endif
#ifndef W_STOPCODE
#  define W_STOPCODE(sig) ((sig) << 8 | 0x7f)
#endif

/* glibc-only libc helpers */
#include <stdlib.h>
#include <unistd.h>

static inline char *canonicalize_file_name(const char *path)
{
    return realpath(path, NULL);
}

static inline char *get_current_dir_name(void)
{
    return getcwd(NULL, 0);
}

#endif /* SLURM_MUSL_COMPAT_H */
"""


class SlurmWlmConan(ConanFile):
    name = "slurm-wlm"
    version = "25.11.4"
    # "application" on purpose, although the package also delivers libslurm:
    # package_type="library" makes Conan's AutotoolsToolchain inject
    # `--disable-shared --enable-static` (it maps the type/`shared` option to
    # the autotools flags), and a static-only build of slurm breaks twice --
    # the loadable modules (src/plugins/**/*.so) are not produced at all and
    # src/*/lib_ref.la (the binary-blob "fake .lo" idiom) loses its members,
    # so linking sacct fails with `_binary_help_txt_start` undefined.
    # The cost is that CMakeDeps then leaves `<pkg>_INCLUDE_DIRS_RELEASE` /
    # `<pkg>_LIBS_RELEASE` empty (knowledge DRAFT-12592-...-application-
    # pkgtype-strips-cppinfo), which test_package/ works around explicitly.
    package_type = "application"
    description = ("Slurm workload manager: cluster resource management, job "
                   "scheduling and accounting tools plus libslurm")
    license = "GPL-2.0-or-later"
    homepage = "https://www.schedmd.com/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        # Every dependency below is already published in the ohpcd remote.
        self.requires("munge/0.5.16")
        self.requires("hwloc/2.14.0")
        self.requires("json-c/0.18")
        self.requires("http-parser/2.9.4")
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")
        # numactl is deliberately NOT used: the prebuilt static libnuma.a in the
        # registry carries glibc-style symbol versions (numa_get_membind@libnuma_1.1)
        # that lld cannot resolve ("has undefined version libnuma_1.1").  Slurm
        # probes libnuma optionally, so it simply builds without NUMA affinity.
        self.requires("libcap/2.78")
        self.requires("libaio/0.3.112.1")
        # transitive deps disagree (libpng/1.6.58 pulls zlib/1.3.1.1 while
        # another branch pins zlib/1.3.1) -- pin one version for the whole graph
        self.requires("zlib/1.3.1.1", override=True)

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # libcheck drives testsuite/slurm_unit.  Its 41 check(3) programs are
        # only wired into the build when configure finds "check >= 0.9.8"
        # (HAVE_CHECK), and without it `make check` silently runs a single
        # test.  test_requires keeps libcheck out of the delivered package:
        # it is needed to build/run the upstream tests, nothing else links
        # against it, and it is not propagated to consumers.
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # glibc-only interfaces that musl lacks are provided as inline shims and
        # force-included in every TU (see _MUSL_COMPAT_H)
        compat_h = os.path.join(self.generators_folder, "slurm_musl_compat.h")
        save(self, compat_h, _MUSL_COMPAT_H)
        tc.extra_cflags.append("-include%s" % compat_h)
        # musl only exposes cpu_set_t/CPU_SET and friends with _GNU_SOURCE
        # (src/common/xsched.h needs them); glibc exposes them by default
        tc.extra_cflags.append("-D_GNU_SOURCE")
        # these four backends only have --with-<x>=PATH probes (no pkg-config),
        # so point them at the Conan package folders explicitly
        # (--with-yaml is deliberately not passed: libyaml is optional upstream
        # and the two upstream cases that need the serializer/yaml plugin stay
        # broken on this platform anyway - see reports/test-report.md §4.3)
        for dep, flag in (("munge", "--with-munge"),
                          ("hwloc", "--with-hwloc"),
                          ("json-c", "--with-json"),
                          ("http-parser", "--with-http-parser")):
            try:
                folder = self.dependencies[dep].package_folder
            except Exception:
                continue
            if folder:
                tc.configure_args.append("%s=%s" % (flag, folder))
        tc.configure_args.extend([
            # config.guess cannot guess on OHOS and the bundled 2022 config.sub
            # rejects the ohos OS (E007), so the triplet is degraded to
            # aarch64-linux-gnu: the actual target is still OHOS because CC/CXX
            # and the sysroot come from the Conan OHOS toolchain
            "--build=aarch64-linux-gnu",
            "--host=aarch64-linux-gnu",
            "--without-rpath",
            "--disable-dependency-tracking",
            # no OHOS counterpart for these optional backends
            "--without-freeipmi",
            "--without-nvml",
            "--without-rsmi",
            "--without-mysql",
        ])
        # slurm's configure probes munge/hwloc/json-c/http-parser/readline via
        # headers and pkg-config; AutotoolsDeps puts every dependency prefix into
        # CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH, so they are detected without
        # hardcoding --with-<dep>=<path> (which would bake absolute build paths).
        env = tc.environment()
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: getcwd() is unreliable here (E114/E386) -- autoconf aborts with
        # "working directory cannot be determined" because its `pwd` probe
        # returns nothing.  Shells fall back to $PWD when getcwd fails, so pin
        # it (same handling as the juman / kmer recipes in this repository).
        os.environ["PWD"] = self.build_folder
        os.environ.setdefault("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # configure compiles and RUNS small probes; those probes link against the
        # dependency shared libraries, so the loader has to be able to find them
        # (same handling as the smpeg recipe in this repository).
        libdirs = []
        for dep in self.dependencies.values():
            for d in (dep.cpp_info.libdirs or []):
                if d not in libdirs:
                    libdirs.append(d)
        if libdirs:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(
                libdirs + ([old] if old else []))
            self.output.info("slurm: LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"])
        # testsuite/slurm_unit is gated on PKG_CHECK_MODULES([CHECK], [check >=
        # 0.9.8]).  pkg.m4 short-circuits that probe when CHECK_CFLAGS and
        # CHECK_LIBS are already in the environment, which is both simpler and
        # more reliable here: the check.pc shipped in the registry has the
        # prefix of whoever built the package baked into it.
        self._prepare_libcheck()
        autotools = Autotools(self)
        # R9: single job
        autotools.configure()
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        shim_c = os.path.join(self.build_folder, "musl_account_shim.c")
        shim_o = os.path.join(self.build_folder, "musl_account_shim.o")
        shim_a = os.path.join(self.build_folder, "libmusl_account_shim.a")
        save(self, shim_c, _MUSL_SHIM_C)
        self.run('"%s" -c -O2 -fPIC "%s" -o "%s"' % (cc, shim_c, shim_o),
                 env="conanbuild")
        self.run('"%s" rcs "%s" "%s"' % (ar, shim_a, shim_o), env="conanbuild")
        # append the shim to the LIBS that configure computed for the whole tree
        libs = ""
        with open(os.path.join(self.build_folder, "Makefile"), encoding="utf-8",
                  errors="replace") as fh:
            for line in fh:
                if line.startswith("LIBS = "):
                    libs = line[len("LIBS = "):].strip()
                    break
        self._patch_makefile_libs()
        autotools.make(args=["-j1"])
        # upstream unit suite: report the numbers (see the method docstring)
        self._run_upstream_tests()

    def _prepare_libcheck(self):
        """Expose libcheck to configure through CHECK_CFLAGS/CHECK_LIBS."""
        try:
            check = self.dependencies["check"]
            include = check.cpp_info.includedirs[0]
            libdir = check.cpp_info.libdirs[0]
        except Exception as exc:
            self.output.info("slurm: libcheck is not available (%s); the "
                             "upstream unit suite stays disabled" % exc)
            return
        os.environ["CHECK_CFLAGS"] = "-I%s -pthread" % include
        os.environ["CHECK_LIBS"] = "-L%s -lcheck" % libdir
        self.output.info("slurm: CHECK_CFLAGS=%s / CHECK_LIBS=%s"
                         % (os.environ["CHECK_CFLAGS"],
                            os.environ["CHECK_LIBS"]))

    def _run_upstream_tests(self):
        """Build and run the upstream unit suite, then report the outcome.

        testsuite/slurm_unit holds 41 check(3) programs (one per *-test.c).
        They are driven through the tree's own `make check` harness, so the
        working directory, the libtool wrappers and the slurm.conf fixtures are
        the ones upstream intended.

        The outcome is *reported*, not enforced: the acceptance gate for this
        package is test_package/ (the consumer checks).  A failure here means
        an upstream test needs a facility this platform does not have, which is
        documented per test in
        archives/s/slurm-wlm/25.11.4/reports/test-report.md.
        """
        if not os.environ.get("CHECK_LIBS"):
            self.output.info("SLURM-UPSTREAM-TESTS skipped (HAVE_CHECK off)")
            return
        # libcheck picks its fork-mode IPC directory from TEMP, then P_tmpdir
        # (which musl defines as the root-owned /tmp) and finally TMPDIR, so
        # TEMP has to point at a directory the build user can write to.
        tmp = os.path.join(self.build_folder, "check-tmp")
        os.makedirs(tmp, exist_ok=True)
        os.environ["TEMP"] = tmp
        # libcheck kills a test after 4 seconds by default; dns-test performs a
        # real name-service lookup that needs longer than that on a host whose
        # DNS server is not reachable (a timing artefact, not a slurm defect)
        os.environ["CK_DEFAULT_TIMEOUT"] = "120"
        # -k: the whole suite has to run even when one test fails
        self.run("make -j1 -k check", env="conanbuild", cwd=self.build_folder,
                 ignore_errors=True)
        self._report_upstream_tests()

    def _report_upstream_tests(self):
        """Summarise testsuite/**/test-suite.log as SLURM-UPSTREAM-* lines."""
        counters = {"TOTAL": 0, "PASS": 0, "FAIL": 0, "ERROR": 0, "SKIP": 0}
        failed = []
        for base, _dirs, files in os.walk(os.path.join(self.build_folder,
                                                       "testsuite")):
            if "test-suite.log" not in files:
                continue
            log = io.open(os.path.join(base, "test-suite.log"), encoding="utf-8",
                          errors="replace").read()
            for line in log.splitlines():
                for key in counters:
                    if line.startswith("# %s:" % key):
                        counters[key] += int(line.split(":")[1].strip())
                if line.startswith("FAIL: ") or line.startswith("ERROR: "):
                    failed.append("%s [%s]" % (line.split(" ", 1)[1].strip(),
                                               os.path.basename(base)))
        total = counters["TOTAL"]
        passed = counters["PASS"]
        rate = (100.0 * passed / total) if total else 0.0
        for name in sorted(set(failed)):
            self.output.info("SLURM-UPSTREAM-FAILED %s" % name)
        self.output.info("SLURM-UPSTREAM-TESTS total=%d pass=%d fail=%d error=%d "
                         "skip=%d rate=%.1f%%"
                         % (total, passed, counters["FAIL"], counters["ERROR"],
                            counters["SKIP"], rate))

    def _patch_makefile_libs(self):
        """Append the compat tail to LIBS in every generated Makefile.

        `make LIBS=...` cannot be used: the value contains several words and it
        would be split into separate make arguments.  Rewriting the generated
        Makefiles is order-safe (the tail lands at the end of the link line) and
        covers both `make` and `make install`.
        """
        tail = self._shim_tail()
        patched = 0
        for base, _dirs, files in os.walk(self.build_folder):
            if "Makefile" not in files:
                continue
            path = os.path.join(base, "Makefile")
            try:
                text = io.open(path, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            out = []
            for line in text.split("\n"):
                if line.startswith("LIBS = ") and tail not in line:
                    line = line + " " + tail
                    patched += 1
                out.append(line)
            with io.open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write("\n".join(out))
        self.output.info("slurm: patched LIBS in %d generated Makefile(s)" % patched)

    def _shim_tail(self):
        """Extra libraries appended to make's LIBS.

        * libmusl_account_shim.a -- getpwent_r/getgrent_r (musl has neither)
        * -lncursesw              -- termcap entries (tgetflag/UP) that live in
          libncursesw.a inside the Conan ncurses package; configure's own LIBS
          order leaves them unresolved for sacctmgr
        """
        parts = [os.path.join(self.build_folder, "libmusl_account_shim.a")]
        try:
            nc = self.dependencies["ncurses"].cpp_info
            # no quotes: the value is passed as a single make argument and
            # inner quotes would break the shell's word splitting
            parts += ["-L%s" % d for d in (nc.libdirs or [])]
            parts.append("-lncursesw")
        except Exception:
            pass
        return " ".join(parts)

    def package_info(self):
        # slurm installs the public headers under include/slurm/ (consumers do
        # #include <slurm/slurm.h>) and the library as libslurm.
        self.cpp_info.libs = ["slurm"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.set_property("cmake_file_name", "Slurm")
        self.cpp_info.set_property("cmake_target_name", "Slurm::Slurm")

    def package(self):
        autotools = Autotools(self)
        # the Makefiles were already patched in build(); `make install` re-links
        # the programs (install depends on all) and therefore needs the same LIBS
        autotools.install(args=["-j1"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
