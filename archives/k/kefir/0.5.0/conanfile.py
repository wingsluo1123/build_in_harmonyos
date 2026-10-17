#!/usr/bin/env python3
"""Conan recipe — kefir 0.5.0 (Makefile, C11 independent C17/C23 compiler)."""
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
import subprocess


# Upstream kefir 0.5.0 `make test` registers ~1883 fixed test cases via
# custom Makefile harness (not ctest/gtest/autotools):
#   unit: 1 suite binary (76 .c files, many assertions each)
#   integration: 231 *.test.c
#   system: 152 *.test.c
#   end2end: 832 test dirs + 255 *.kefir.asmgen.c + 412 *.kefir.also.asmgen
# csmith (random) and external (60+ real-world projects) are separate
# targets, not part of `make test` fixed total.
UPSTREAM_TEST_DISCOVERED = 1883
UPSTREAM_TEST_FRAMEWORK = "make"
UPSTREAM_TEST_COMMAND = "make -k test"


class KefirConan(ConanFile):
    name = "kefir"
    version = "0.5.0"
    description = "Independent C17/C23 compiler targeting x86_64 System-V ABI"
    license = "GPL-3.0-only"
    homepage = "https://kefir.protopopov.lv"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kefir supports Linux and OHOS only, got %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool_alive(self, cand):
        # Direct-exec probe (no shell): distinguishes a truly broken
        # compiler path from shell quoting issues. `--version` needs no
        # SDK env and returns 0 for a healthy clang/make.
        if not cand:
            return False
        try:
            r = subprocess.run([cand, "--version"], capture_output=True,
                               text=True, timeout=30)
            return r.returncode == 0
        except Exception:
            return False

    def _tool_version(self, cand):
        try:
            r = subprocess.run([cand, "--version"], capture_output=True,
                               text=True, timeout=30)
            if r.returncode == 0:
                return (r.stdout or "") + (r.stderr or "")
        except Exception:
            pass
        return ""

    def _cc_dumpmachine(self, cand):
        # Reliable OHOS-flavor signal: hnp/SDK clang reports
        # `aarch64-unknown-linux-ohos` while `--version` shows only a
        # generic `clang version 15.0.4` line.
        try:
            r = subprocess.run([cand, "-dumpmachine"], capture_output=True,
                               text=True, timeout=30)
            if r.returncode == 0:
                return (((r.stdout or "") + (r.stderr or "")).strip())
        except Exception:
            pass
        return ""

    def _pick_live(self, label, candidates):
        # Deduplicate preserving order, probe each candidate, return the
        # first that actually executes. Falls back to the first candidate
        # so the downstream error stays meaningful if none is alive.
        seen = []
        for c in candidates:
            if c and c not in seen:
                seen.append(c)
        for c in seen:
            if self._tool_alive(c):
                if c != seen[0]:
                    self.output.info("kefir: %s %s broken, using live %s"
                                     % (label, seen[0], c))
                else:
                    self.output.info("kefir: %s %s" % (label, c))
                return c
        self.output.warning("kefir: no live %s among %s, keeping %s"
                            % (label, seen, seen[0] if seen else None))
        return seen[0] if seen else None

    def _pick_live_ohos_first(self, label, candidates):
        # Flavor-aware variant for CC: a generic clang may answer
        # `--version` yet emit glibc/GNU-ld binaries OHOS refuses to
        # execute (`Permission denied`, exit 126; DRAFT-6048: only lld
        # products run). `clang -dumpmachine` is the reliable signal
        # (hnp/SDK clang reports `aarch64-unknown-linux-ohos`, keyd
        # precedent); the `--version` substring is only a fallback.
        seen = []
        for c in candidates:
            if c and c not in seen:
                seen.append(c)
        live_ver = []
        for c in seen:
            v = self._tool_version(c)
            if v:
                live_ver.append((c, v))
        if not live_ver:
            self.output.warning("kefir: no live %s among %s, keeping %s"
                                % (label, seen, seen[0] if seen else None))
            return seen[0] if seen else None
        for c, v in live_ver:
            base = os.path.basename(c)
            if "clang" in base or base in ("cc", "c++"):
                if "ohos" in self._cc_dumpmachine(c).lower():
                    self.output.info("kefir: %s OHOS target %s" % (label, c))
                    return c
        for c, v in live_ver:
            if "ohos" in v.lower() or "hnp" in v.lower() or "harmony" in v.lower():
                self.output.info("kefir: %s OHOS-flavored %s" % (label, c))
                return c
        c = live_ver[0][0]
        self.output.warning("kefir: no OHOS-flavored %s among live %s, using %s"
                            % (label, [x for x, _ in live_ver], c))
        return c

    def _path_candidates(self, names):
        # Expand every PATH entry for the given binary names in PATH order,
        # so a working copy in an HMBS-prepended tool dir wins over the
        # profile absolute path when the latter is inaccessible.
        out = []
        for d in (os.environ.get("PATH") or "").split(os.pathsep):
            d = d.strip()
            if not d:
                continue
            for n in names:
                out.append(os.path.join(d, n))
        return out

    def _resolve_cc(self, ce):
        sdk_clang = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang"
        cands = ([os.environ.get("CC"), ce.get("c"), sdk_clang]
                 + self._path_candidates(("clang", "clang-15", "cc"))
                 + ["/storage/Users/currentUser/usr/local/bin/clang",
                     "/data/service/hnp/bin/clang", "clang"])
        return self._pick_live_ohos_first("CC", cands)

    def _resolve_cxx(self, ce):
        sdk_cxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang++"
        cands = ([os.environ.get("CXX"), ce.get("cpp"), sdk_cxx]
                 + self._path_candidates(("clang++", "clang++-15", "c++"))
                 + ["/storage/Users/currentUser/usr/local/bin/clang++",
                     "/data/service/hnp/bin/clang++", "clang++"])
        return self._pick_live_ohos_first("CXX", cands)

    def _resolve_bash(self):
        # Upstream test drivers (tests/*/run.sh, end2end/compile.sh) all
        # use `#!/usr/bin/env bash`; preflight fails every .done target
        # with `env: exec bash: No such file` when bash is not on the
        # build-scope PATH. Resolve a live bash so unit/integration
        # suites (portable C, runnable on aarch64) can genuinely execute;
        # x86_64 link/run suites stay as ohos_feature gaps.
        # (keyd precedent: hnp/tool-dir absolute tool paths vary in
        # reachability per session/mount state, so probe at runtime;
        # ~/usr/local/bin/* are real OHOS wrappers, not fallbacks.)
        cands = ([os.environ.get("BASH"), os.environ.get("KEFIR_BASH"),
                  os.environ.get("CONFIG_SHELL"),
                  "/data/service/hnp/bin/bash"]
                 + self._path_candidates(("bash",))
                 + [os.path.join(os.path.expanduser("~"), "usr", "local",
                                 "bin", "bash"),
                     "/storage/Users/currentUser/usr/local/bin/bash",
                     "/bin/bash", "bash"])
        return self._pick_live("BASH", cands)

    def _drop_static_link(self):
        # Round5: upstream links kefir/kefir-cc1 with `$(CCLD) -static`
        # when USE_SHARED=no (source/driver/Makefile.mk:20,
        # source/cc1/Makefile.mk:25). The -static driver is reported by
        # the fixed ELF probe as aarch64/static-or-none yet dies on OHOS
        # with `Permission denied` exit 126 both in-tree (end2end
        # compile.sh `./bin/kefir`) and packaged (test_package
        # `kefir --version`), while dynamically linked test binaries
        # from the same CC execute normally (unit assertion runs,
        # integration SIGTRAP/Terminated). Fully static OHOS binaries
        # are refused by the loader policy; linking the same objects
        # against libkefir.a WITHOUT -static yields a dynamic musl
        # executable OHOS can run. Patch is build-local (no patch file,
        # no upstream test change): drop the `-static` token only on
        # the two host-driver link lines.
        import io
        for rel in (os.path.join("source", "driver", "Makefile.mk"),
                    os.path.join("source", "cc1", "Makefile.mk")):
            p = os.path.join(self.source_folder, rel)
            try:
                with io.open(p, "r", encoding="utf-8", errors="replace",
                             newline="") as f:
                    text = f.read()
            except Exception as e:
                self.output.warning("kefir: static-link patch read skipped %s: %s" % (p, e))
                continue
            patched = text.replace("$(CCLD) -static -o", "$(CCLD) -o")
            if patched != text:
                try:
                    with io.open(p, "w", encoding="utf-8", newline="") as f:
                        f.write(patched)
                    self.output.info("kefir: dropped -static in %s" % rel)
                except Exception as e:
                    self.output.warning("kefir: static-link patch write skipped %s: %s" % (p, e))
            else:
                self.output.info("kefir: no -static token in %s (already patched?)" % rel)

    def _fix_makefile_dirname(self):
        # Round9: preflight dies in the FIRST compile rule with
        #   /bin/sh: /storage/.../.harmonybrew/bin/dirname: Operation not permitted
        #   mkdir: missing operand
        #   make: *** [Makefile.mk:133: bin/ast/type/qualified.deps] Error 1
        # Every build rule does `mkdir -p $(shell dirname "$@")`, and the
        # device `dirname` (harmonybrew shim, chmod sub-capability 0) is not
        # executable. Fix build-locally with no test-logic change: GNU make's
        # builtin `$(dir ...)` returns the directory part without spawning
        # any external binary, so `mkdir -p $(dir $@)` is equivalent for all
        # mkdir purposes (trailing slash is harmless to mkdir -p).
        import re
        count_files = 0
        count_subs = 0
        for root, _dirs, files in os.walk(self.source_folder):
            for fn in files:
                if fn != "Makefile" and not fn.endswith(".mk"):
                    continue
                p = os.path.join(root, fn)
                try:
                    with open(p, "r", encoding="utf-8", errors="replace",
                              newline="") as f:
                        text = f.read()
                except Exception as e:
                    self.output.warning("kefir: dirname patch read skipped %s: %s" % (p, e))
                    continue
                orig = text
                # Strip quotes while replacing: $(shell dirname "$@") -> $(dir $@)
                # and $(shell dirname $@) -> $(dir $@); loop handles nesting.
                for _ in range(3):
                    text, n1 = re.subn(r"\$\(\s*shell\s+dirname\s+\"([^\")]+)\"\)",
                                       r"$(dir \1)", text)
                    count_subs += n1
                    text, n2 = re.subn(r"\$\(\s*shell\s+dirname\s+([^\"\)][^\)]*)\)",
                                       r"$(dir \1)", text)
                    count_subs += n2
                    if n1 + n2 == 0:
                        break
                if text != orig:
                    try:
                        with open(p, "w", encoding="utf-8", newline="") as f:
                            f.write(text)
                        count_files += 1
                    except Exception as e:
                        self.output.warning("kefir: dirname patch write skipped %s: %s" % (p, e))
        self.output.info("kefir: replaced $(shell dirname) with $(dir) in %d files (%d subs)"
                         % (count_files, count_subs))

    def _sh_posixify_test_drivers(self):
        # Round4 NEW ROUTE (replaces round2 PATH-prepend + round3 shebang-pin,
        # both of which failed with identical `env: exec bash` on every .done
        # target): stop trying to PROVIDE bash. /data/service/hnp/bin/bash is
        # mount-gated per session (round1: sibling clang path from the same
        # dir was `inaccessible or not found`; profile [buildenv] points SHELL
        # at that same dir), PATH carries no other bash, and no live bash
        # exists anywhere on device in this session, so `#!/usr/bin/env bash`
        # can never resolve. Instead eliminate the dependency: the 5 driver
        # scripts (unit/integration/system/end2end run.sh + end2end
        # compile.sh) use only a small bash subset (`[[ a == b ]]`,
        # `function f {`, `source f`), mechanically convertible to POSIX sh,
        # which IS guaranteed (/bin/sh demonstrably runs every make recipe
        # line, including the groff-missing help pipeline). Sourced *.profile
        # files are plain VAR assignments, already sh-compatible. Test logic,
        # commands, exit codes and diff comparisons are unchanged.
        import re
        count = 0
        tests_dir = os.path.join(self.source_folder, "source", "tests")
        for root, _dirs, files in os.walk(tests_dir):
            for fn in files:
                if not fn.endswith(".sh"):
                    continue
                p = os.path.join(root, fn)
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                except Exception as e:
                    self.output.warning("kefir: posixify read skipped %s: %s" % (p, e))
                    continue
                orig = text
                text = text.replace("#!/usr/bin/env bash", "#!/bin/sh")
                text = re.sub(r"(?m)^(\s*)function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{",
                              r"\1\2() {", text)
                text = re.sub(r"(?m)^(\s*)source\s+", r"\1. ", text)
                text = text.replace("[[", "[").replace("]]", "]")
                text = text.replace("==", "=")
                # Round9: same broken-device family as make-time dirname —
                # integration/system run.sh and end2end compile.sh call the
                # external `dirname`/`basename` binaries at RUNTIME
                # (TESTDIR="$(dirname $0)", $(basename $(dirname ...))).
                # PATH resolves to the same EPERM harmonybrew shim, so every
                # test driver would die right after the compile fix. Shadow
                # both with POSIX parameter-expansion functions injected
                # once after the shebang; test commands/exit codes/diffs
                # unchanged. Basename keeps the 2-arg suffix form used as
                # `basename $SYS_TEST .gen`.
                if "hmbs_posix_dirname" not in text:
                    shim = (
                        "# OHOS hmbs_posix_dirname/basename: device dirname shim is EPERM; pure-POSIX fallback.\n"
                        "dirname() {\n"
                        "    _hmbs_d=\"${1:-.}\";\n"
                        "    while [ \"${_hmbs_d%/}\" != \"$_hmbs_d\" ] && [ \"$_hmbs_d\" != \"/\" ]; do _hmbs_d=\"${_hmbs_d%/}\"; done;\n"
                        "    case \"$_hmbs_d\" in */*) printf '%s\\n' \"${_hmbs_d%/*}\";; *) printf '.\\n';; esac;\n"
                        "    unset _hmbs_d;\n"
                        "}\n"
                        "basename() {\n"
                        "    _hmbs_b=\"${1:-/}\";\n"
                        "    while [ \"${_hmbs_b%/}\" != \"$_hmbs_b\" ] && [ \"$_hmbs_b\" != \"/\" ]; do _hmbs_b=\"${_hmbs_b%/}\"; done;\n"
                        "    _hmbs_b=\"${_hmbs_b##*/}\";\n"
                        "    if [ -n \"${2:-}\" ] && [ \"$_hmbs_b\" != \"$2\" ]; then case \"$_hmbs_b\" in *\"$2\") _hmbs_b=\"${_hmbs_b%$2}\";; esac; fi;\n"
                        "    printf '%s\\n' \"$_hmbs_b\";\n"
                        "    unset _hmbs_b;\n"
                        "}\n"
                    )
                    if text.startswith("#!"):
                        nl = text.find("\n")
                        text = text[:nl + 1] + shim + text[nl + 1:]
                    else:
                        text = shim + text
                if text != orig:
                    try:
                        with open(p, "w", encoding="utf-8") as f:
                            f.write(text)
                        count += 1
                    except Exception as e:
                        self.output.warning("kefir: posixify write skipped %s: %s" % (p, e))
        self.output.info("kefir: posixified %d test driver scripts to /bin/sh" % count)

    def _elf_machine_interp(self, path):
        # Fixed ELF probe (round4): the previous _elf_interp mis-unpacked the
        # ELF64 header (`<QIIIII` at 0x20 splits e_shoff and merges
        # e_ehsize/e_phentsize/e_phnum), so e_phentsize/e_phnum were garbage
        # and the loop never found PT_INTERP -> always `static-or-none`.
        # Correct layout: e_machine@0x12(H), e_phoff@0x20(Q),
        # e_phentsize@0x36(H), e_phnum@0x38(H); PHDR64 p_type@0(I),
        # p_offset@8(Q), p_filesz@32(Q).
        import struct
        try:
            with open(path, "rb") as f:
                head = f.read(64)
            if len(head) < 64 or head[:4] != b"\x7fELF" or head[4] != 2:
                return ("not-elf64", "?")
            endian = "<" if head[5] == 1 else ">"
            e_machine = struct.unpack_from(endian + "H", head, 0x12)[0]
            e_phoff = struct.unpack_from(endian + "Q", head, 0x20)[0]
            e_phentsize = struct.unpack_from(endian + "H", head, 0x36)[0]
            e_phnum = struct.unpack_from(endian + "H", head, 0x38)[0]
            names = {62: "x86_64", 183: "aarch64", 40: "arm", 243: "riscv64"}
            machine = names.get(e_machine, "machine-%d" % e_machine)
            interp = "static-or-none"
            with open(path, "rb") as f:
                for i in range(e_phnum):
                    f.seek(e_phoff + i * e_phentsize)
                    ph = f.read(e_phentsize)
                    if len(ph) < 56:
                        break
                    p_type, _, p_offset, _, _, p_filesz, _, _ = struct.unpack_from(
                        endian + "IIQQQQQQ", ph, 0)
                    if p_type == 3:  # PT_INTERP
                        f.seek(p_offset)
                        raw = f.read(p_filesz)
                        interp = raw.split(b"\x00")[0].decode("utf-8", "replace")
                        break
            return (machine, interp)
        except Exception as e:
            return ("unreadable:%s" % e, "?")

    def _log_built_elf(self):
        # Build-time evidence (log only, never fails the build): records the
        # real machine + loader of the just-linked kefir driver so the next
        # round can distinguish wrong-flavor ELF (x86_64/glibc) from
        # permission/mount causes of a test_package 126.
        try:
            kefir_bin = os.path.join(self.source_folder, "bin", "kefir")
            if os.path.isfile(kefir_bin):
                machine, interp = self._elf_machine_interp(kefir_bin)
                st = os.stat(kefir_bin)
                self.output.info("kefir built ELF: path=%s mode=%s size=%s machine=%s interp=%s"
                                 % (kefir_bin, oct(st.st_mode & 0o7777),
                                    st.st_size, machine, interp))
        except Exception as e:
            self.output.warning("kefir built ELF probe failed: %s" % e)

    def _resolve_make(self):
        try:
            conf_make = self.conf.get("user.hmbs:make_path", default=None)
        except Exception:
            conf_make = None
        cands = ([os.environ.get("KEFIR_MAKE"), os.environ.get("HMBS_MAKE"),
                  conf_make]
                 + self._path_candidates(("make", "gmake"))
                 + ["make"])
        return self._pick_live("MAKE", cands)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._resolve_cc(ce)
        cxx = self._resolve_cxx(ce)
        ar = ce.get("ar") or "llvm-ar"
        ranlib = ce.get("ranlib") or "llvm-ranlib"
        make = self._resolve_make()
        e = Environment()
        e.define("CC", cc)
        e.define("CXX", cxx)
        e.define("CCLD", cc)
        e.define("AR", ar)
        e.define("RANLIB", ranlib)
        e.define("KEFIR_MAKE", make)
        bash = self._resolve_bash()
        if bash and os.path.isabs(bash):
            # `#!/usr/bin/env bash` resolves via PATH only; make the live
            # bash discoverable for make-spawned test drivers.
            e.append_path("PATH", os.path.dirname(bash))
            e.define("BASH", bash)
            e.define("KEFIR_BASH", bash)
        # NOTE: script name must NOT be "conanbuild": Conan's
        # generate_aggregated_env() writes the build-scope aggregate to
        # conanbuild.sh, so save_script("conanbuild") gets overwritten by a
        # stub that sources itself -> infinite self-sourcing, env explosion
        # (PATH re-prepended per level), printenv E2BIG + Signal 9/137, make
        # never runs. Every other recipe in archives/ uses a distinct name.
        e.vars(self).save_script("kefirbuild")

    def _run_make(self, args, **kwargs):
        make = self._resolve_make()
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._resolve_cc(ce)
        # OHOS single-job build: 2663 C files at PROFILE=release (-O3) exceed
        # the default 3600s budget and the preflight SSH window (connection
        # closed mid-`.BINARIES` with zero output). Append EXTRA_CFLAGS=-O1
        # after PROFILE_CFLAGS (-O3 … -O1, last -O wins in clang) to cut
        # codegen cost while keeping -DNDEBUG/-DKEFIR_BUILD_RELEASE release
        # semantics. DETECT_HOST_ENV=no skips the Linux-only host probes
        # (uname allowlist + clang GCC-install check, both fail on HongMeng
        # and fall back to an empty config.h anyway) deterministically.
        # -fuse-ld=lld: only lld-linked products execute on OHOS; a GNU-ld
        # product dies with `Permission denied` exit 126 (DRAFT-6048,
        # kakasi precedent). Harmless when the OHOS clang already
        # defaults to lld.
        # -fsigned-char (round5): ARM AAPCS defines plain `char` as
        # unsigned while x86_64 System-V (kefir's sole target) defines it
        # as signed. Upstream unit test ast_constant_expression2.c
        # computes the expected value with host `(char) j` for j in
        # -10..9; with OHOS aarch64 clang (unsigned by default) the
        # expectation is 246..255 where kefir's target model yields
        # -10..-1, so `ASSERT(...->integer == ((char) j))` aborts.
        # Forcing signed char aligns host compilation with the target
        # assumption without touching any upstream test.
        # STRIP=true (round6): upstream strips kefir/kefir-cc1 in release
        # profiles via `$(STRIP) $@` with STRIP?=strip. The device `strip`
        # is unpinned (host-profile absolute path, possibly wrong-arch or
        # LLVM/GNU mismatched); stripping the freshly linked aarch64/musl
        # driver is a corruption suspect for the persistent 126, and test
        # binaries (never stripped) execute normally. Disabling strip is
        # build-local, keeps symbols for diagnosis, and costs only size.
        cmd = "%s %s CC=\"%s\" CCLD=\"%s\" STRIP=\"true\" USE_SHARED=no PROFILE=release DETECT_HOST_ENV=no EXTRA_CFLAGS=\"-O1 -fsigned-char\" EXTRA_LDFLAGS=\"-fuse-ld=lld\"" % (make, args, cc, cc)
        kwargs.setdefault("cwd", self.source_folder)
        return self.run(cmd, **kwargs)

    def _count_suite_done(self):
        # Deterministic per-suite .done counts (filesystem glob, no stdout
        # string counting). Suite filename families are disjoint by
        # construction (see source/tests/{unit,integration,system,end2end}/
        # Makefile.mk): unit.tests.done (1 suite binary), integration
        # *.test.done (231), system *.test.done (152), end2end run
        # *.test.done (832 dirs) vs asmgen *.test.asmgen.done (255) +
        # *.test.also.asmgen.done (412). The asmgen families end with
        # `.asmgen.done`, so they never match the `*.test.done` glob.
        bin_dir = os.path.join(self.source_folder, "bin")
        unit = glob.glob(os.path.join(bin_dir, "tests", "unit.tests.done"))
        integration = glob.glob(os.path.join(bin_dir, "tests", "integration",
                                              "**", "*.done"), recursive=True)
        system = glob.glob(os.path.join(bin_dir, "tests", "system",
                                         "**", "*.test.done"), recursive=True)
        e2e_run = glob.glob(os.path.join(bin_dir, "tests", "end2end",
                                          "**", "*.test.done"), recursive=True)
        e2e_asmgen = (
            glob.glob(os.path.join(bin_dir, "tests", "end2end",
                                    "**", "*.test.asmgen.done"), recursive=True)
            + glob.glob(os.path.join(bin_dir, "tests", "end2end",
                                     "**", "*.test.also.asmgen.done"),
                        recursive=True)
        )
        return {
            "unit": len(unit),
            "integration": len(integration),
            "system": len(system),
            "end2end_run": len(e2e_run),
            "end2end_asmgen": len(e2e_asmgen),
        }

    def _count_done_files(self):
        return sum(self._count_suite_done().values())

    def _emit_upstream_marker(self, status, executed, passed, failed, skipped, reason, gaps=None):
        result = {
            "status": status,
            "framework": UPSTREAM_TEST_FRAMEWORK,
            "command": UPSTREAM_TEST_COMMAND,
            "discovered": UPSTREAM_TEST_DISCOVERED,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": reason,
        }
        if gaps:
            result["gaps"] = gaps
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(result), flush=True)

    def build(self):
        # Round6: daemon umask 027 makes the linker create 750 binaries;
        # per-file umask tricks in _install_bin (rounds 4-5) demonstrably
        # did not survive to the packaged file (still 0o100750 twice).
        # Set the process umask once, up front, and keep it for the whole
        # build so every file the toolchain creates (linker output,
        # makedirs, .d/.o) is born 755-friendly. Different scope from the
        # previous single-open trick; restored only in package().
        try:
            os.umask(0o022)
        except Exception:
            pass
        self._fix_makefile_dirname()
        self._sh_posixify_test_drivers()
        self._drop_static_link()
        self._run_make("-j1 .BINARIES")
        self._log_built_elf()
        self._run_make("-k -j1 test", ignore_errors=True)
        suite_passed = self._count_suite_done()
        suite_discovered = {
            "unit": 1,
            "integration": 231,
            "system": 152,
            "end2end_run": 832,
            "end2end_asmgen": 667,
        }
        # Clamp: a suite can never pass more than it registers; excess
        # would indicate a glob overlap bug, not extra tests.
        for _k in list(suite_passed.keys()):
            if suite_passed[_k] > suite_discovered[_k]:
                self.output.warning(
                    "kefir: suite %s passed %d > discovered %d, clamping"
                    % (_k, suite_passed[_k], suite_discovered[_k]))
                suite_passed[_k] = suite_discovered[_k]
        passed = sum(suite_passed.values())
        if passed > UPSTREAM_TEST_DISCOVERED:
            passed = UPSTREAM_TEST_DISCOVERED
        failed = UPSTREAM_TEST_DISCOVERED - passed
        executed = UPSTREAM_TEST_DISCOVERED
        skipped = 0
        status = "passed" if failed == 0 else "failed"
        gaps = None
        if failed > 0:
            gaps = []
            suite_failed = {k: suite_discovered[k] - suite_passed[k]
                            for k in suite_discovered}
            self.output.info("kefir: per-suite done %s failed %s"
                             % (suite_passed, suite_failed))
            if suite_failed["unit"] > 0:
                gaps.append(
                    {
                        "count": suite_failed["unit"],
                        "category": "ohos_feature",
                        "detail": "unit suite binary aborts in bigint signed/unsigned to-long-double conversion; x86_64 long double is 80-bit extended while OHOS aarch64 clang uses 128-bit long double, so fabsl(value - expected) < 1e-8 fails for large magnitudes",
                        "evidence": "source/tests/unit/bigint1.c:2181 Assertion `fabsl(value - (kefir_long_double_t) (i)) < 1e-8` failed; headers/kefir/core/util.h KEFIR_DISABLE_LONG_DOUBLE_FLAG exists but source/tests/unit/run.sh sets it only under USE_VALGRIND=yes while integration/run.sh sets it unconditionally",
                    }
                )
            if suite_failed["integration"] > 0:
                gaps.append(
                    {
                        "count": suite_failed["integration"],
                        "category": "test_failure",
                        "detail": "integration test binaries terminate with Signal 5 (SIGTRAP, exit 127) before diff comparison, including portable preprocessor/lexer/parser suites; 35 codegen_x86_64 codegen-compare cases are x86_64-specific but preprocessor crashes need per-test stdout triage from full build log",
                        "evidence": "Running bin/tests/integration/preprocessor/preprocessor_fn_macro_def1.test...Terminated Signal 5 (core dumped) Error 127 (same for string_literals1/stringification1/undef1); source/tests/integration/run.sh exit 127 = test binary non-zero, exit 128 = diff mismatch",
                    }
                )
            if suite_failed["system"] > 0:
                gaps.append(
                    {
                        "count": suite_failed["system"],
                        "category": "ohos_feature",
                        "detail": "system tests generate x86_64 assembly then assemble with GNU as and link/run the x86_64 binary; OHOS aarch64 has no x86_64 assembler and cannot execute x86_64 objects",
                        "evidence": "source/tests/system/run.sh: $AS -o gen.o gen.asm then $CC link + run; device log .../run.sh[93]: as: inaccessible or not found, Error 128 for codegen/alloca1.gen onward",
                    }
                )
            if suite_failed["end2end_run"] > 0:
                gaps.append(
                    {
                        "count": suite_failed["end2end_run"],
                        "category": "ohos_feature",
                        "detail": "end2end run tests kefir-compile each .kefir.c with bin/kefir, link with host cc and execute the x86_64 binary; x86_64 objects cannot link/run on OHOS aarch64",
                        "evidence": "source/tests/end2end/compile.sh KEFIRCC=$KEFIR_BIN_DIR/kefir (-c mode) + Makefile.mk link $(CC) host+.,kefir objects -o .test then run.sh executes; TLDR: no non-x86_64 targets yet, README targets x86_64 Linux/BSD only",
                    }
                )
            if suite_failed["end2end_asmgen"] > 0:
                gaps.append(
                    {
                        "count": suite_failed["end2end_asmgen"],
                        "category": "ohos_feature",
                        "detail": "end2end asmgen failures are translate-only diff mismatches (no execution) concentrated in long_double/vararg cases whose expected assembly embeds x86_64 80-bit long-double codegen that differs under the aarch64 host long-double model",
                        "evidence": "Asmgen-Diff bin/tests/end2end/long_double4/lib.test.also.asmgen.done Error 1, long_double_cast1/long_double_ternary1/vararg4 same family; ASMGEN=yes path in source/tests/end2end/compile.sh (-S translate, no as/ld/run)",
                    }
                )
        self._emit_upstream_marker(
            status=status,
            executed=executed,
            passed=passed,
            failed=failed,
            skipped=skipped,
            reason="conanfile.py build() ran `make -k test` on device; passed counts .done files under bin/",
            gaps=gaps,
        )

    def _install_bin(self, src, dst):
        # Round4 NEW ROUTE for the test_package 126 (`Permission denied` with
        # packaged mode 0o100750): the old best-effort `os.chmod(dst, 0o755)`
        # runs AFTER the copy, but where the FS ignores chmod (HMBS chmod
        # sub-capability 0) the 750 mode from the daemon umask (027) sticks
        # and non-owner/group test users get EACCES. Instead control the mode
        # AT CREATION, which no FS capability can ignore: temporarily set
        # umask(022) (process-local, always effective) and create the file
        # with 0o755 so owner/group/other all gain rx. Content copy keeps the
        # artifact bit-identical; the trailing chmod is retained as a no-op
        # fallback where chmod happens to work. Round5 fix: unlink an existing
        # dst first — open(O_TRUNC) on an existing file keeps its old mode
        # (hence packaged 0o100750 survived round4 despite the umask route);
        # a fresh O_CREAT after unlink applies 0755 deterministically.
        with open(src, "rb") as f:
            data = f.read()
        try:
            if os.path.lexists(dst):
                os.unlink(dst)
        except Exception:
            pass
        old_umask = os.umask(0o022)
        try:
            fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
            except Exception:
                try:
                    os.close(fd)
                except Exception:
                    pass
                raise
        finally:
            os.umask(old_umask)
        # NOTE: no copystat here on purpose: it would copy the source's
        # 750 permission bits back over the freshly created 755 mode.
        try:
            os.chmod(dst, 0o755)
        except Exception:
            pass

    def _install_text_755(self, dst, text):
        # Same creation-mode discipline as _install_bin (umask 022 +
        # O_CREAT 0755 after unlink) but for generated text files, so the
        # wrapper stays executable where chmod is ignored (HMBS chmod=0).
        try:
            if os.path.lexists(dst):
                os.unlink(dst)
        except Exception:
            pass
        old_umask = os.umask(0o022)
        try:
            fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            except Exception:
                try:
                    os.close(fd)
                except Exception:
                    pass
                raise
        finally:
            os.umask(old_umask)
        try:
            os.chmod(dst, 0o755)
        except Exception:
            pass

    def _write_kefir_wrapper(self, dst):
        # Upstream install.mk does NOT ship bin/kefir directly: it installs
        # the linked driver as bindir/kefir-cc and generates bindir/kefir
        # from scripts/kefir.m4 (POSIX sh wrapper that defaults KEFIR_RTINC
        # to <prefix>/include/kefir/runtime and execs kefir-cc). The previous
        # recipe copied the raw driver as bin/kefir, so every `kefir -S`
        # died with "Runtime include path shall be passed as KEFIR_RTINC"
        # (target_configuration.c:156) even though -S avoids the link stage.
        # Replicate the wrapper minimally (no m4/realpath dependency): prefer
        # an already-exported KEFIR_RTINC (conanrun runenv, see
        # package_info), else resolve relative to the script location which
        # works for direct-path invocation (<prefix>/bin/kefir).
        wrapper = (
            "#!/bin/sh\n"
            "# Generated by kefir conan recipe (mirrors scripts/kefir.m4).\n"
            "# Defaults KEFIR_RTINC to <prefix>/include/kefir/runtime.\n"
            'if [ -z "$KEFIR_RTINC" ]; then\n'
            '    _kefir_self="$0"\n'
            '    case "$_kefir_self" in\n'
            '        */*) _kefir_dir="$(dirname "$_kefir_self")" ;;\n'
            '        *) _kefir_dir="" ;;\n'
            '    esac\n'
            '    if [ -n "$_kefir_dir" ]; then\n'
            '        if command -v realpath >/dev/null 2>&1; then\n'
            '            _kefir_rtinc="$(realpath "$_kefir_dir/../include/kefir/runtime" 2>/dev/null)"\n'
            '        else\n'
            '            _kefir_rtinc="$_kefir_dir/../include/kefir/runtime"\n'
            '        fi\n'
            '        if [ -d "$_kefir_rtinc" ]; then\n'
            '            KEFIR_RTINC="$_kefir_rtinc"\n'
            '            export KEFIR_RTINC\n'
            '        fi\n'
            '    fi\n'
            'fi\n'
            'if [ -n "$_kefir_dir" ]; then\n'
            '    exec "$_kefir_dir/kefir-cc" "$@"\n'
            'else\n'
            '    exec kefir-cc "$@"\n'
            'fi\n'
        )
        self._install_text_755(dst, wrapper)
        self.output.info("kefir: generated bin/kefir wrapper (KEFIR_RTINC default)")

    def package(self):
        # Round6: keep umask 022 for the whole packaging step as well
        # (package() may run with the daemon 027); _install_bin still
        # unlinks + creates with 0755, now under a guaranteed mask.
        try:
            os.umask(0o022)
        except Exception:
            pass
        src_bin = os.path.join(self.source_folder, "bin")
        dst_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_bin, exist_ok=True)
        # Upstream layout: raw driver -> kefir-cc, plus generated kefir
        # wrapper (see _write_kefir_wrapper). Keep accepting a prebuilt
        # kefir-cc source as well; never ship the raw driver as `kefir`.
        raw_cc = None
        for cand in ("kefir", "kefir-cc"):
            src = os.path.join(src_bin, cand)
            if os.path.isfile(src):
                raw_cc = src
                break
        if raw_cc is not None:
            self._install_bin(raw_cc, os.path.join(dst_bin, "kefir-cc"))
        for name in ("kefir-cc1", "kefir-detect-host-env"):
            src = os.path.join(src_bin, name)
            if os.path.isfile(src):
                self._install_bin(src, os.path.join(dst_bin, name))
        self._write_kefir_wrapper(os.path.join(dst_bin, "kefir"))
        scripts_dir = os.path.join(self.source_folder, "scripts")
        for name in ("kefir.m4", "detect-host-env.sh"):
            src = os.path.join(scripts_dir, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_bin, name))
        src_lib = os.path.join(src_bin, "libs")
        if os.path.isdir(src_lib):
            dst_lib = os.path.join(self.package_folder, "lib")
            os.makedirs(dst_lib, exist_ok=True)
            for name in os.listdir(src_lib):
                if name.startswith("libkefir."):
                    shutil.copy2(os.path.join(src_lib, name), os.path.join(dst_lib, name))
        src_inc = os.path.join(self.source_folder, "headers", "kefir")
        if os.path.isdir(src_inc):
            copy(self, "*.h", src=src_inc, dst=os.path.join(self.package_folder, "include", "kefir"))
        for fname in ("COPYING", "README.md", "TLDR.md", "CHANGELOG"):
            src = os.path.join(self.source_folder, fname)
            if os.path.isfile(src):
                copy(self, fname, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
        # Consumers (including test_package with env="conanrun") resolve
        # `kefir` via PATH where $0 carries no directory, so the wrapper's
        # relative fallback cannot locate the runtime headers. Export the
        # absolute runtime include dir as runenv so `kefir -S` works both
        # via PATH and via direct <prefix>/bin/kefir invocation.
        try:
            rtinc = os.path.join(self.package_folder, "include", "kefir", "runtime")
            self.runenv_info.define("KEFIR_RTINC", rtinc)
        except Exception:
            pass
