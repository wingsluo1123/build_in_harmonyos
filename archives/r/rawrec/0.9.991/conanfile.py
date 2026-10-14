#!/usr/bin/env python3
"""Conan recipe — rawrec 0.9.991 (Makefile)"""

import json
import os
import shutil
import time

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class RawrecConan(ConanFile):
    name = "rawrec"
    version = "0.9.991"
    description = "CLI program to record or play raw audio data via OSS."
    license = "GPL-2.0-only"
    homepage = "http://rawrec.sourceforge.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def generate(self):
        pass

    def _resolve_cc(self):
        # Pinned conf path first, but with existence probe: the preflight
        # profile may pin /data/service/hnp/bin/clang which no longer exists
        # (make: ... No such file or directory, Error 127). Missing -> warn
        # plus sibling/PATH fallback; never blindly use a stale absolute path.
        conf_cc = None
        try:
            exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            if isinstance(exes, dict):
                conf_cc = exes.get("c")
        except Exception:
            conf_cc = None
        if conf_cc and os.path.isabs(conf_cc):
            try:
                if os.path.isfile(conf_cc) and os.access(conf_cc, os.X_OK):
                    return conf_cc
            except OSError:
                pass
            self.output.warning("pinned CC not usable: {}; falling back via PATH".format(conf_cc))
            try:
                sibling = os.path.join(os.path.dirname(conf_cc), "clang")
                if os.path.isfile(sibling) and os.access(sibling, os.X_OK):
                    self.output.info("CC fallback (sibling): {}".format(sibling))
                    return sibling
            except OSError:
                pass
        elif conf_cc:
            found = shutil.which(conf_cc)
            if found:
                return found
        for bare in ("clang", "cc", "gcc"):
            found = shutil.which(bare)
            if found:
                if found != conf_cc:
                    self.output.info("CC fallback (PATH): {}".format(found))
                return found
        return conf_cc or "clang"

    def _resolve_make(self):
        # Prefer HMBS-injected make (HMBS_MAKE / user.hmbs:make_path), with
        # existence probe; fall back to PATH make/gmake (hmbs puts tool dirs
        # on PATH). Bare "make" last so PATH still resolves it.
        candidates = []
        try:
            candidates.append(os.environ.get("HMBS_MAKE"))
        except Exception:
            pass
        try:
            candidates.append(self.conf.get("user.hmbs:make_path", default=None))
        except Exception:
            pass
        for cand in candidates:
            if not cand:
                continue
            if os.path.isabs(cand):
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
                except OSError:
                    continue
            else:
                found = shutil.which(cand)
                if found:
                    return found
        for bare in ("make", "gmake"):
            found = shutil.which(bare)
            if found:
                return found
        return "make"

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("rawrec requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        # Portability: respect external CC/CFLAGS/LDFLAGS and fix link order.
        # Done via replace_in_file (not a patch) to stay robust against
        # upstream Makefile context drift (e.g. comment lines between
        # OPTFLAGS and CFLAGS that broke the previous unified diff).
        mk = os.path.join(self.source_folder, "src", "Makefile")
        replace_in_file(self, mk, "CC = gcc\n", "CC ?= gcc\n")
        replace_in_file(
            self,
            mk,
            "CFLAGS = $(WARNFLAGS) $(OPTFLAGS) $(DEBUGFLAGS) -DUSEBUFFLOCK \\\n"
            "         $(FANCY_THREAD_DEFINES) -D_REENTRANT -D_GNU_SOURCE \\\n"
            "         -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE\n"
            "LDFLAGS = -lm -lpthread",
            "CFLAGS += $(WARNFLAGS) $(OPTFLAGS) $(DEBUGFLAGS)\n"
            "CPPFLAGS += -DUSEBUFFLOCK $(FANCY_THREAD_DEFINES) -D_REENTRANT -D_GNU_SOURCE \\\n"
            "         -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE\n"
            "LDFLAGS ?=\n"
            "LIBS = -lm -lpthread",
        )
        replace_in_file(
            self,
            mk,
            "$(CC) $(OBJS) $(LDFLAGS) -o $(PROG)",
            "$(CC) $(LDFLAGS) $(OBJS) -o $(PROG) $(LIBS)",
        )
        cc = self._resolve_cc()
        make = self._resolve_make()
        src_dir = os.path.join(self.source_folder, "src")
        # Low-memory mitigation (true-machine `tar: Cannot fork: Out of memory`):
        # keep the build strictly serial and cap in-file opt/debug defaults
        # via command-line overrides (OPTFLAGS=-O0 DEBUGFLAGS=-g1 win over the
        # Makefile's `-O2`/`-O0 -g`). Append-only: external CFLAGS/LDFLAGS
        # injected by the cross toolchain are preserved through `+=`/`?=` above.
        # Serial build with transient-fork retry: CI workers occasionally fail
        # the very first clang exec with `Resource temporarily unavailable`
        # (EAGAIN on fork, make Error 127) even though the same tree passes
        # the true-machine preflight. Retry with backoff so a momentary
        # shortage does not fail the whole package; persistent errors still
        # surface after the last attempt.
        build_cmd = "{} -j1 CC={} OPTFLAGS=-O0 DEBUGFLAGS=-g1".format(make, cc)
        for attempt in (1, 2, 3):
            try:
                self.run(build_cmd, cwd=src_dir)
                break
            except Exception as exc:
                if attempt >= 3:
                    raise
                wait = 15 * attempt
                self.output.warning(
                    "make attempt {}/3 failed ({}); retrying in {}s".format(
                        attempt, exc, wait))
                try:
                    time.sleep(wait)
                except Exception:
                    pass
        marker = {
            # No upstream test target exists, so check command is empty;
            # explanation lives in test_package/MANIFEST.yml upstream_test_audit.
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "manual audit of 0.9.991 tarball (39 files): Makefile targets all/debug/bin_install/man_install/install/clean/distclean/uninstall only, no check/test target, no tests/ dir; sole test-named file src/test_dsp_params.c is production code linked into rawrec via OBJS wildcard (*.c), not a test suite",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(marker, sort_keys=True)))

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "rawrec", src=src_dir, dst=bindir)
        for link in ("rawplay",):
            target = os.path.join(bindir, link)
            try:
                if os.path.islink(target) or os.path.exists(target):
                    os.remove(target)
            except OSError:
                pass
            try:
                os.symlink("rawrec", target)
            except OSError:
                copy(self, "rawrec", src=src_dir, dst=os.path.join(self.package_folder, "bin"))
                try:
                    os.rename(os.path.join(bindir, "rawrec"), target)
                    copy(self, "rawrec", src=src_dir, dst=bindir)
                except OSError:
                    pass
        man_src = os.path.join(self.source_folder, "docs", "user", "rawrec.1")
        if os.path.isfile(man_src):
            copy(self, "rawrec.1", src=os.path.dirname(man_src), dst=os.path.join(self.package_folder, "share", "man", "man1"))
            man_link = os.path.join(self.package_folder, "share", "man", "man1", "rawplay.1")
            try:
                if os.path.islink(man_link) or os.path.exists(man_link):
                    os.remove(man_link)
                os.symlink("rawrec.1", man_link)
            except OSError:
                pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
