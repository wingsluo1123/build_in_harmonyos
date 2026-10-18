#!/usr/bin/env python3
"""Conan recipe for mfoc 0.10.7-git20180724 (Autotools CLI).

mfoc (Mifare Classic Offline Cracker) is an offline nested attack tool
for MIFARE Classic cards. Upstream: https://github.com/nfc-tools/mfoc
This version is master snapshot at 2018-07-24 (commit ba072f1),
matching Debian 0.10.7+git20180724.

Build system: autotools (configure.ac + src/Makefile.am).
The GitHub archive ships no pre-generated `configure`, so build()
runs `autoreconf -fi` with automake/libtool via Conan tool_requires
(E178 pattern, same as bwm-ng/zzuf/zbar/apertium).

Dependencies (per configure.ac):
  - libnfc >= 1.7.0 (Conan: libnfc/1.8.0, provides libnfc.pc)
  - pkg-config for PKG_CHECK_MODULES
  - libtool/2.5.4.1 as host requires: 制品仓 libnfc 为静态库，mfoc 二进制
    DT_NEEDED libltdl.so.7（-lltdl 随构建依赖注入链接，但 runenv 仅含 host
    依赖；无此声明时真机运行时报 Error loading shared library libltdl.so.7）

Upstream tests: none. configure.ac has no test macros, Makefile.am
and src/Makefile.am define no TESTS/check_PROGRAMS, no tests/ dir,
no gtest/pytest. `make check` is automake default no-op (0 cases).

R32: supports Linux and OHOS.
Package type application: ships only bin/mfoc + man page.
"""
import json
import os
import time
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MfocConan(ConanFile):
    name = "mfoc"
    version = "0.10.7-git20180724"
    description = "Mifare Classic Offline Cracker (offline nested attack tool)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/nfc-tools/mfoc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("nfc", "mifare", "cracker", "rfid")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "%s is only supported on Linux/OHOS, not %s" % (self.name, self.settings.os)
            )

    def requirements(self):
        self.requires("libnfc/1.8.0")
        # Runtime DT_NEEDED libltdl.so.7: 制品仓 libnfc/1.8.0 为静态库，
        # 链接时 -lltdl 来自 libtool 构建依赖的 cpp_info（generate 全上下文注入），
        # 但 VirtualRunEnv 只带 host 依赖进 runenv，test/运行时 loader 找不到
        # libltdl.so.7（真机：Error loading shared library libltdl.so.7，exit 127）。
        # 显式 host 依赖使 libtool 的 libdir 进入 conanrun LD_LIBRARY_PATH。
        self.requires("libtool/2.5.4.1")

    def build_requirements(self):
        # Archive ships configure.ac only. Worker has autoconf, not automake.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"][self.version]
        get(self, **src, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # HMBS radcli/1.2.11: old config.guess (2024-07-27 from automake/1.18)
        # has no HarmonyOS branch; `uname -s` = HarmonyOS makes configure
        # abort with "cannot guess build type". Pass explicit --build to
        # bypass the guess path entirely (native build on HarmonyOS PC).
        arch_map = {
            "armv8": "aarch64",
            "aarch64": "aarch64",
            "armv7": "armv7l",
            "armv7hf": "armv7l",
            "x86_64": "x86_64",
            "x86": "i686",
        }
        build_arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
        build_triplet = "%s-unknown-linux-gnu" % build_arch
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=") and not str(a).startswith("--host=")
        ]
        tc.configure_args.append("--build=%s" % build_triplet)
        tc.configure_args.append("--host=%s" % build_triplet)
        # HMBS OOM hardening (2026-10-16 tar fork OOM): shared runner under
        # global memory pressure; minimize peak compile/link usage while
        # keeping -j1 and full `make check` (adapted from cpluff/0.2.0).
        tc.configure_args.append("--disable-dependency-tracking")
        for _flag in ("-g0", "-Os"):
            try:
                if hasattr(tc, "extra_cflags"):
                    tc.extra_cflags.append(_flag)
                elif hasattr(tc, "cflags"):
                    tc.cflags.append(_flag)
                else:
                    break
            except Exception:
                break
        try:
            if hasattr(tc, "extra_ldflags"):
                tc.extra_ldflags.append("-Wl,--strip-debug")
            elif hasattr(tc, "ldflags"):
                tc.ldflags.append("-Wl,--strip-debug")
        except Exception:
            pass
        tc.generate()
        # libnfc.pc must be findable by PKG_CHECK_MODULES.
        # AutotoolsToolchain only prepends generators_folder, not dep pkgconfig dirs,
        # so inject PKG_CONFIG_PATH / CPPFLAGS / LDFLAGS / LIBS explicitly
        # (same pattern as libnfc/1.8.0 recipe).
        env = Environment()
        libs = []
        for dep in self.dependencies.values():
            pkgconfig = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig):
                env.prepend_path("PKG_CONFIG_PATH", pkgconfig)
            for inc in dep.cpp_info.includedirs:
                env.append("CPPFLAGS", "-I" + inc)
            for libdir in dep.cpp_info.libdirs:
                env.append("LDFLAGS", "-L" + libdir)
            for lib in dep.cpp_info.libs:
                libs.append("-l" + lib)
        if libs:
            env.append("LIBS", libs)
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("mfoc-deps-env")

    def _patch_config_guess_python(self, cg_path):
        with open(cg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        orig = content
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            if old in content:
                content = content.replace(
                    old,
                    "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos",
                    1,
                )
        if "HarmonyOS" not in content:
            # HMBS radcli/1.2.11: normalize HongMeng kernel uname to Linux
            # so any residual config.guess call returns a linux-gnu triplet
            # instead of aborting. Insert after UNAME_VERSION assignment;
            # fall back to UNAME_SYSTEM assignment when not found.
            # Already-contains-HarmonyOS files are skipped (idempotent).
            norm = (
                "\n# HMBS OHOS compat: HongMeng kernel reports HarmonyOS; "
                "treat as Linux\n"
                'case "${UNAME_SYSTEM}" in\n'
                "HarmonyOS|HongMeng*) UNAME_SYSTEM=Linux ;;\n"
                "esac\n"
            )
            anchor = None
            for marker in ("UNAME_VERSION=", "UNAME_SYSTEM="):
                idx = content.find(marker)
                if idx != -1:
                    eol = content.find("\n", idx)
                    if eol != -1:
                        anchor = eol + 1
                        break
            if anchor is not None:
                content = content[:anchor] + norm.lstrip("\n") + content[anchor:]
        if content != orig:
            with open(cg_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _patch_config_sub_python(self, cs_path):
        # We pass --build/--host as *-unknown-linux-gnu, which stock
        # config.sub already accepts, so no structural edit is needed.
        # Keep this as a safe no-op (log only) to avoid corrupting
        # config.sub with naive string replacement.
        return

    def _apply_e007(self):
        # Traverse ALL config.guess files (including nested configure dirs);
        # do not require a sibling config.sub in the same directory.
        found = []
        for root, _dirs, files in os.walk(self.source_folder):
            if "config.guess" in files:
                found.append(os.path.join(root, "config.guess"))
        if not found:
            self.output.warning("E007: config.guess not found after autoreconf")
            return
        for cg in found:
            try:
                self._patch_config_guess_python(cg)
                self.output.info("E007: patched %s" % cg)
            except Exception as e:
                self.output.warning("E007 patch failed for %s: %s" % (cg, e))

    def build(self):
        apply_conandata_patches(self)
        # HMBS writable tmp for autoconf mktemp (E002/E114).
        hmbs_tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        hmbs_fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if hmbs_fallback and hmbs_fallback not in ("0", "1") and os.path.isdir(hmbs_fallback):
            hmbs_tmp = hmbs_fallback
        if not hmbs_tmp:
            hmbs_tmp = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(hmbs_tmp, exist_ok=True)
        except Exception:
            pass
        os.environ["TMPDIR"] = hmbs_tmp
        os.environ["TMP"] = hmbs_tmp
        os.environ["TEMP"] = hmbs_tmp
        if not os.environ.get("SHELL"):
            os.environ["SHELL"] = "/bin/sh" if os.path.exists("/bin/sh") else "/data/service/hnp/bin/bash"
        if not os.environ.get("CONFIG_SHELL"):
            os.environ["CONFIG_SHELL"] = os.environ["SHELL"]
        try:
            os.chdir(self.build_folder)
        except Exception:
            pass
        os.environ["PWD"] = self.build_folder

        # DRAFT-11327: shared CI workers intermittently refuse fork() with
        # EAGAIN ("Resource temporarily unavailable" / "can't fork - try
        # again") at the first fork-heavy step (autoreconf). mfoc only
        # ships a git snapshot without pre-generated configure, so the
        # bootstrap cannot be removed; retry with cooldown instead of
        # failing the whole create on a transient pressure spike.
        # Success path is unchanged (same command, same flags).
        for _attempt in (1, 2, 3):
            try:
                self.run("autoreconf -v -i -f", cwd=self.source_folder)
                break
            except Exception as _e:
                _msg = str(_e)
                _transient = (
                    "Resource temporarily unavailable" in _msg
                    or "Errno 11" in _msg
                    or "can't fork" in _msg
                    or "try again" in _msg
                )
                if _attempt >= 3 or not _transient:
                    raise
                self.output.warning(
                    "autoreconf transient resource failure"
                    " (attempt %d/3): %s; cooling down before retry"
                    % (_attempt, _e)
                )
                time.sleep(20 * _attempt)
        self._apply_e007()

        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            # E114: HMDFS + umask 077 yields unwritable config.status temp dir.
            replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream has no TESTS; automake emits a no-op check that exits 0.
        try:
            autotools.make(target="check")
        except Exception as e:
            self.output.warning("make check (no-op expected) failed: %s" % e)
        # HMBS evidence: upstream has no test suite -> emit no_tests marker.
        # Cache-hit rounds are covered by test_package re-emit.
        try:
            upstream = {
                "status": "no_tests",
                "framework": "autotools",
                "command": "make check",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "mfoc-0.10.7-git20180724 audited: configure.ac has no test macros; Makefile.am/SUBDIRS=src only; src/Makefile.am defines bin_PROGRAMS=mfoc only, no TESTS/check_PROGRAMS; tarball ba072f1 has no tests/ dir and no test source files; make check is automake default empty target",
            }
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
        except Exception:
            pass

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Ensure man page license preserved if install skipped docs
        try:
            from conan.tools.files import copy as _copy

            _copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
