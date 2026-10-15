#!/usr/bin/env python3
"""Conan test_package — zfs-src 2.4.3 (OpenZFS userland) on HarmonyOS PC.

Consumer-perspective verification of the packaged userland stack, built
with a direct compiler invocation (no cmake): the upstream libzfs header
set needs the same feature macros as the ZFS build itself, and a plain
clang call keeps the test independent from generator/toolchain quirks.

  library layer : real API calls into libnvpair (nvlist_alloc/add_string/
                  add_uint64/lookup round-trip/free — the XDR-backed
                  name/value engine underpinning every libzfs ioctl),
                  libuutil (uu_list pool/create/node_init/insert/find/
                  teardown) and the libzfs/libzfs_core handle boundaries,
                  which must fail *honestly* (NULL / non-zero) on a host
                  without the ZFS kernel module — never crash.
  binary layer  : packaged zfs/zpool/zdb executables really run; without
                  a kernel module they must terminate non-zero with the
                  upstream "cannot be auto-loaded" / cache-file message
                  (exit 0 would be a fake success; 127 a loader failure),
                  and ztest must print its upstream usage banner.
"""
import os

from conan import ConanFile


class ZfsSrcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "AutotoolsDeps", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        src = os.path.join(self.source_folder, "test_zfs_userland.c")
        # $CPPFLAGS/$LDFLAGS/$LIBS come from the AutotoolsDeps generator
        # (full dependency closure: zfs libs first, then tirpc/openssl/
        # uuid/blkid/zlib). They MUST stay unquoted — the shell word
        # splitting is what turns the flag string into separate argv
        # entries. Feature macros mirror upstream AM_CFLAGS (libspl
        # sys/stat.h needs the stat64 aliases).
        self.run(
            f'"{cc}" -D_GNU_SOURCE -D_FILE_OFFSET_BITS=64 '
            f'-D_LARGEFILE64_SOURCE $CPPFLAGS "{src}" '
            f'-o test_zfs_userland $LDFLAGS $LIBS -lm -ldl -lpthread',
            env="conanbuild")

    def test(self):
        # ── library layer ──────────────────────────────────────────
        self.run("./test_zfs_userland", cwd=self.build_folder,
                 env="conanrun")

        # ── binary layer ───────────────────────────────────────────
        # In a test_package context self.package_folder points at the
        # (non-packaged) test folder itself; the tested package's folder
        # comes from the dependency graph.
        pkg = self.dependencies[self.tested_reference_str].package_folder

        def find_bin(name):
            for sub in ("bin", "sbin"):
                path = os.path.join(pkg, sub, name)
                if os.path.isfile(path):
                    return path
            raise Exception(f"packaged executable missing: {name}")

        # Without a ZFS kernel module every CLI must fail *honestly*:
        # non-zero exit + the upstream kernel-boundary message. The
        # `version` subcommand actually probes the kernel interface
        # (libzfs_init / zpool.cache), which is where the boundary
        # surfaces; a bare invocation would just print usage (exit 2).
        for name, argv in (("zfs", "version"), ("zpool", "version"),
                           ("zdb", "-V")):
            path = find_bin(name)
            self.run(
                f'out=$("{path}" {argv} 2>&1); rc=$?; '
                f'if [ $rc -eq 0 ]; then echo "{name}: unexpected success"; exit 1; fi; '
                f'if [ $rc -eq 127 ]; then echo "{name}: loader failure"; exit 1; fi; '
                f'case "$out" in *"cannot be auto-loaded"*|*"zpool.cache"*|*"modprobe"*) '
                f'echo "{name}: exit $rc, kernel-boundary signature observed";; '
                f'*) echo "{name}: exit $rc, unexpected output: $out"; exit 1;; esac',
                env="conanrun")

        ztest = find_bin("ztest")
        self.run(
            f'"{ztest}" -h 2>&1 | grep -q "Usage: ztest" || '
            f'(echo "ztest usage banner missing"; exit 1)',
            env="conanrun")
        self.output.info("zfs-src test_package: library + binary layers OK")
