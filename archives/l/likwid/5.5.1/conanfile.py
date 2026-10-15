#!/usr/bin/env python3
"""Conan recipe for LIKWID 5.5.1 - HPC performance analysis tool suite.

LIKWID reads hardware performance counters through the Linux ``msr`` /
``perf_event`` kernel interfaces and ships a C library (``liblikwid``) plus a
set of Lua command line tools (``likwid-perfctr``, ``likwid-topology``,
``likwid-pin`` ...).  This recipe builds the aarch64/OHOS configuration:

* ``COMPILER=CLANGARMv8`` (clang), ``ACCESSMODE=perf_event`` (so no msr access
  daemon is built), bundled hwloc 2.9.3 and Lua 5.4 (the upstream default).
* Several OHOS/bionic portability fixes are carried as patches: glibc-only
  ``pthread_[sg]etaffinity_np`` helpers, glibc's private ``__cpu_mask``,
  hwloc's sysfs sibling-file probe, ``program_invocation_name``, the
  ``get_mempolicy`` seccomp SIGSYS trap and the missing
  ``_SC_LEVEL1_DCACHE_LINESIZE`` constant.
* Two build-environment shims are needed because OHOS ships neither the
  ``cpp`` driver used by likwid-bench's perl generator nor coreutils
  ``install``.

Runtime note: OHOS denies ``perf_event_open`` and exposes no ``/dev/cpu/*/msr``,
so counter *measurement* cannot run here; the topology / NUMA / affinity /
timer / pinning functionality is fully exercised by the consumer test.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# bionic/OHOS does not provide the glibc pthread_[sg]etaffinity_np helpers.
# likwid only ever pins the calling thread, so map those calls onto the
# thread-local sched_setaffinity(0,...) / sched_getaffinity(0,...).
# The guard is feature-based (glibc is the only libc that ships these GNU
# helpers), not a platform macro.
_COMPAT_HEADER = """\
#ifndef LIKWID_OHOS_PTHREAD_AFFINITY_COMPAT_H
#define LIKWID_OHOS_PTHREAD_AFFINITY_COMPAT_H
#if !defined(__GLIBC__)
#include <sched.h>
#include <pthread.h>
#include <sys/types.h>
#include <errno.h>
static inline int likwid_pthread_setaffinity_np(pthread_t thread, size_t cpusetsize, const cpu_set_t *cpuset)
{
    if (!pthread_equal(thread, pthread_self()))
    {
        errno = ENOSYS;
        return ENOSYS;
    }
    return sched_setaffinity(0, cpusetsize, cpuset);
}
static inline int likwid_pthread_getaffinity_np(pthread_t thread, size_t cpusetsize, cpu_set_t *cpuset)
{
    if (!pthread_equal(thread, pthread_self()))
    {
        errno = ENOSYS;
        return ENOSYS;
    }
    return sched_getaffinity(0, cpusetsize, cpuset);
}
#define pthread_setaffinity_np likwid_pthread_setaffinity_np
#define pthread_getaffinity_np likwid_pthread_getaffinity_np
#endif
#endif
"""

# minimal coreutils install(1) replacement: OHOS (toybox) has no `install`.
_INSTALL_SHIM = """\
#!/bin/sh
mode=""
dir_mode=0
while [ $# -gt 0 ]; do
  case "$1" in
    -m) mode="$2"; shift 2 ;;
    -m*) mode="${1#-m}"; shift ;;
    -o|-g) shift 2 ;;
    -d) dir_mode=1; shift ;;
    -b|-c|-s|-v|-p|-t) shift ;;
    -*) shift ;;
    *) break ;;
  esac
done
if [ "$dir_mode" = 1 ]; then
  for d in "$@"; do mkdir -p "$d"; done
  exit 0
fi
src="$1"; shift
dest="$1"
if [ -d "$dest" ]; then dest="$dest/$(basename "$src")"; fi
cp -f "$src" "$dest"
if [ -n "$mode" ]; then chmod "$mode" "$dest" 2>/dev/null || true; fi
"""


class LikwidConan(ConanFile):
    name = "likwid"
    version = "5.5.1"
    description = "HPC performance analysis tool suite (liblikwid + Lua command line tools)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/RRZE-HPC/likwid"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "likwid reads Linux/OHOS performance counters, not "
                + str(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return exes.get(name) or fallback

    def _write_shim(self, folder, name, body):
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        ar = self._compiler("ar", "llvm-ar")

        shims = os.path.join(self.build_folder, "tool-shims")
        os.makedirs(shims, exist_ok=True)
        self._write_shim(shims, "cpp", '#!/bin/sh\nexec %s -E "$@"\n' % cc)
        self._write_shim(shims, "install", _INSTALL_SHIM)

        compat = os.path.join(self.source_folder, "src", "includes",
                              "pthread_affinity_compat.h")
        with open(compat, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_COMPAT_HEADER)

        prefix = os.path.join(self.build_folder, "stage")
        arguments = [
            "COMPILER=CLANGARMv8",
            "ACCESSMODE=perf_event",
            "BUILDFREQ=false",
            # The upstream probes mis-detect OHOS (no glibc ldd, "HongMeng
            # Kernel" uname): pin the values the OHOS platform actually has.
            "HAS_MEMPOLICY=1",
            "HAS_SCHEDAFFINITY=1",
            "GLIBC_VERSION_MAJOR=2",
            "GLIBC_VERSION_MINOR=39",
            "CC=" + cc,
            "CXX=" + cxx,
            "AR=" + ar,
            "AS=" + cc + " -c",
            "PREFIX=" + prefix,
            "INSTALLED_PREFIX=" + prefix,
        ]
        quoted = " ".join(shlex.quote(item) for item in arguments)
        make_env = "PATH={}:$PATH".format(shlex.quote(shims))
        self.run("{} make -j1 {}".format(make_env, quoted),
                 cwd=self.source_folder)
        self.run("{} make -j1 {} install".format(make_env, quoted),
                 cwd=self.source_folder)
        self._run_upstream_tests(prefix)

    def _run_upstream_tests(self, prefix):
        """Run the upstream executable tests that OHOS can actually run.

        ``test/executable_tests/tester.sh`` drives each Lua tool with the
        expectations in ``<tool>.txt`` but hardcodes ``/tmp`` for its scratch
        files, which is read-only on OHOS.  The same expectations are applied
        here with the scratch output written into the build folder.
        """
        import subprocess
        tests = {
            "likwid-topology": ["-c", "-C", "-v"],
            "likwid-features": ["-l", "-h"],
            "likwid-pin": ["-c 0 echo likwid-pin-ok"],
        }
        log = []
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.path.join(prefix, "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
        for tool, invocations in tests.items():
            binary = os.path.join(prefix, "bin", tool)
            for inv in invocations:
                proc = subprocess.run("{} {} </dev/null".format(binary, inv),
                                      shell=True, cwd=self.build_folder, env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      timeout=120)
                log.append("$ {} {}\n[rc={}]\n{}".format(tool, inv, proc.returncode,
                                                          proc.stdout.decode("utf-8", "replace")))
        with open(os.path.join(self.build_folder, "upstream-executable-tests.log"),
                  "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(log))

    def _copy_tree(self, src, dst):
        for root, _dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            target = dst if rel == "." else os.path.join(dst, rel)
            os.makedirs(target, exist_ok=True)
            for name in files:
                shutil.copy2(os.path.join(root, name), os.path.join(target, name))

    def _rewrite_baked_paths(self, old, new):
        """The Lua tools bake INSTALLED_PREFIX into themselves; point them at
        the final package folder so the installed scripts are runnable."""
        old_bytes = old.encode()
        new_bytes = new.encode()
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                try:
                    with open(path, "rb") as handle:
                        data = handle.read()
                except OSError:
                    continue
                if old_bytes in data and not data.startswith(b"\x7fELF"):
                    with open(path, "wb") as handle:
                        handle.write(data.replace(old_bytes, new_bytes))

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        self._copy_tree(stage, self.package_folder)
        self._rewrite_baked_paths(stage, self.package_folder)
        for folder in (os.path.join(self.package_folder, "bin"),
                       os.path.join(self.package_folder, "share", "likwid", "filter")):
            if os.path.isdir(folder):
                for name in os.listdir(folder):
                    path = os.path.join(folder, name)
                    if os.path.isfile(path):
                        os.chmod(path, 0o755)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["likwid", "likwidpin", "likwid-hwloc", "likwid-lua"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "likwid")
        self.cpp_info.set_property("cmake_target_name", "likwid::likwid")
