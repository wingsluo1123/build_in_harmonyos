#!/usr/bin/env python3
"""Conan recipe for smartlist 3.15 (procmail SmartList mailing-list manager).

SmartList is a mailing-list manager built on top of procmail: a suite of
Bourne-shell scripts (SmartList/bin, SmartList/etc, SmartList/examples)
plus small C helpers (src/hsort.c, src/gethome.c). The full flist/multigram
binary requires blending with the procmail source tree (see upstream
SmartList/README); on HarmonyOS we build the standalone helpers with an
OHOS shim header and ship the script suite verbatim.

Key adaptation points:
  - Standalone helpers compiled with clang from Conan conf (R33), -std=gnu17
    for K&R definitions, -fPIC, single invocations (R9, no -j needed).
  - src/includes.h OHOS shim (generated in build()) supplies uchar/P/Q/DIRSEP/EX_*
    without procmail headers; no generated files are modified (R6).
  - No Conan dependencies: procmail/sendmail is a runtime MTA requirement,
    documented in notes.md, not a Conan requires() (R36 verified: nothing
    to download).
  - Upstream ships no test suite (audited); build() performs no make check
    and test_package/MANIFEST.yml declares upstream_tests_exist: false.
"""
import os
import json
import shutil
import subprocess
import time

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class SmartlistConan(ConanFile):
    name = "smartlist"
    version = "3.15"
    description = "SmartList mailing-list manager on top of procmail (scripts + C helpers)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/procmail-org/SmartList"
    url = "https://github.com/procmail-org/SmartList"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        pass

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tool(self, keys, fallbacks):
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        if isinstance(compilers, dict):
            for k in keys:
                cand = compilers.get(k)
                if cand:
                    if os.path.isabs(str(cand)):
                        if os.path.isfile(cand) and os.access(cand, os.X_OK):
                            self.output.info("hmbs tool %s: using conf value %s" % (keys[0], cand))
                            return cand
                        self.output.warning("hmbs tool %s: conf path missing %s, falling back to PATH" % (keys[0], cand))
                    else:
                        found = shutil.which(cand)
                        self.output.info("hmbs tool %s: conf name %s resolves to %s" % (keys[0], cand, found or cand))
                        return found or cand
        for fb in fallbacks:
            found = shutil.which(fb)
            if found:
                self.output.info("hmbs tool %s: PATH fallback %s" % (keys[0], found))
                return found
        self.output.warning("hmbs tool %s: no PATH hit, using %s" % (keys[0], fallbacks[0]))
        return fallbacks[0]

    def _compiler(self):
        return self._resolve_tool(["c"], ["clang", "cc", "gcc"])

    def _archiver(self):
        return self._resolve_tool(["ar"], ["llvm-ar", "ar"])

    def _run_noshell(self, argv):
        # OOM mitigation: argv list direct-exec without /bin/sh (saves one
        # fork per tool call); product checks are in-process os.path calls
        # below (saves the second fork). Retry ONLY on fork/resource
        # signatures; real compile errors fail immediately.
        forksigs = ("out of memory", "can't fork", "cannot fork",
                    "resource temporarily unavailable", "cannot allocate memory")
        delays = (1, 2, 4)
        for attempt in range(4):
            try:
                subprocess.run(argv, check=True)
                return
            except OSError as exc:
                msg = str(exc).lower()
                if any(s in msg for s in forksigs) or getattr(exc, "errno", None) in (11, 12):
                    if attempt < 3:
                        self.output.warning(
                            f"fork/resource retry {attempt + 1}/3 for {argv[0]}: {exc}")
                        time.sleep(delays[attempt])
                        continue
                raise
            except subprocess.CalledProcessError as exc:
                out = str(exc).lower()
                if any(s in out for s in forksigs) and attempt < 3:
                    self.output.warning(
                        f"fork/resource retry {attempt + 1}/3 for {argv[0]}: {exc}")
                    time.sleep(delays[attempt])
                    continue
                raise

    @staticmethod
    def _ohos_includes_h():
        return (
            "/* SmartList OHOS standalone build shim.\n"
            " *\n"
            ' * Upstream src/hsort.c and src/gethome.c include "includes.h" from the\n'
            " * procmail source tree (upstream README blending design: SmartList and\n"
            " * procmail sources are unpacked on top of each other, and ../config.h is\n"
            " * required by install.sh). For the HarmonyOS adaptation we only build the\n"
            " * two standalone helpers, so this shim supplies the small subset they\n"
            " * actually need (uchar, P/Q macros, DIRSEP, EX_*), drawn from standard\n"
            " * POSIX headers. No upstream logic is altered.\n"
            " */\n"
            "#ifndef SMARTLIST_OHOS_INCLUDES_H\n"
            "#define SMARTLIST_OHOS_INCLUDES_H\n"
            "\n"
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "#include <string.h>\n"
            "#include <strings.h>\n"
            "#include <unistd.h>\n"
            "#include <sys/types.h>\n"
            "#include <sys/stat.h>\n"
            "#include <pwd.h>\n"
            "#include <ctype.h>\n"
            "#include <errno.h>\n"
            "\n"
            "/* procmail-style short type used by hsort.c */\n"
            "typedef unsigned char uchar;\n"
            "\n"
            "/* procmail-style prototype macros: upstream headers define P/Q for\n"
            " * K&R/C89 compatibility; plain expansion is correct on modern clang. */\n"
            "#ifndef P\n"
            "#define P(x) x\n"
            "#endif\n"
            "#ifndef Q\n"
            "#define Q(x) x\n"
            "#endif\n"
            "\n"
            "/* Directory separator used by gethome.c */\n"
            "#ifndef DIRSEP\n"
            '#define DIRSEP "/"\n'
            "#endif\n"
            "\n"
            "/* sysexits(3) codes used by gethome.c; prefer the system header and fall\n"
            " * back to the BSD values if the header is unavailable. */\n"
            "#if defined(__has_include)\n"
            "#if __has_include(<sysexits.h>)\n"
            "#include <sysexits.h>\n"
            "#endif\n"
            "#endif\n"
            "#ifndef EX_USAGE\n"
            "#define EX_USAGE 64\n"
            "#endif\n"
            "#ifndef EX_NOINPUT\n"
            "#define EX_NOINPUT 66\n"
            "#endif\n"
            "#ifndef EX_UNAVAILABLE\n"
            "#define EX_UNAVAILABLE 69\n"
            "#endif\n"
            "#ifndef EXIT_SUCCESS\n"
            "#define EXIT_SUCCESS 0\n"
            "#endif\n"
            "\n"
            "#endif /* SMARTLIST_OHOS_INCLUDES_H */\n"
        )

    def build(self):
        # OHOS standalone shim: upstream src/hsort.c and src/gethome.c include
        # "includes.h" from the procmail source tree (README blending design).
        # The SmartList tarball itself ships no such header, and a git-style
        # new-file patch proved fragile across patch(1) implementations
        # (hunk-count strictness, /dev/null handling), so generate the minimal
        # POSIX shim in place instead of patching. No upstream file is altered.
        cc = self._compiler()
        ar = self._archiver()
        src = os.path.join(self.source_folder, "src").replace("\\", "/")
        shim = os.path.join(src, "includes.h")
        if not os.path.isfile(shim):
            with open(shim, "w", encoding="utf-8", newline="\n") as f:
                f.write(self._ohos_includes_h())
        if not (os.path.isfile(shim) and os.path.getsize(shim) > 0):
            raise RuntimeError(f"includes.h shim not produced: {shim}")
        # Standalone helpers only: hsort (heapsort lib) + gethome (install helper).
        # multigram/flist need the procmail source tree (upstream README blending
        # design) and are intentionally not built here; see notes.md.
        # -std=gnu17 keeps the K&R definitions in hsort.c/gethome.c compiling
        # on clang 15; -fPIC keeps objects relocatable on OHOS aarch64.
        hsort_c = os.path.join(src, "hsort.c")
        hsort_o = os.path.join(src, "hsort.o")
        libhsort = os.path.join(src, "libhsort.a")
        gethome_c = os.path.join(src, "gethome.c")
        gethome_o = os.path.join(src, "gethome")
        self._run_noshell([cc, "-std=gnu17", "-O2", "-fPIC", f"-I{src}",
                           "-c", hsort_c, "-o", hsort_o])
        if not (os.path.isfile(hsort_o) and os.path.getsize(hsort_o) > 0):
            raise RuntimeError(f"hsort.o not produced: {hsort_o}")
        self._run_noshell([ar, "rcs", libhsort, hsort_o])
        if not (os.path.isfile(libhsort) and os.path.getsize(libhsort) > 0):
            raise RuntimeError(f"libhsort.a not produced: {libhsort}")
        self._run_noshell([cc, "-std=gnu17", "-O2", "-fPIC", f"-I{src}",
                           gethome_c, libhsort, "-o", gethome_o])
        if not (os.path.isfile(gethome_o) and os.path.getsize(gethome_o) > 0):
            raise RuntimeError(f"gethome not produced: {gethome_o}")
        # Upstream ships no test suite (audited: no tests/, TESTS,
        # check_PROGRAMS, ctest or make-check target). Emit the no_tests
        # evidence marker here; test_package re-emits it every round so
        # the gate sees it even on cache hits (fancy-cat precedent).
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": "none (upstream ships no test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Upstream SmartList 3.15 ships no tests/, test/, TESTS, check_PROGRAMS, ctest or make-check target; audited tarball top level, SmartList/, src/ and install scripts.",
        }, ensure_ascii=False))

    def package(self):
        src_root = self.source_folder.replace("\\", "/")
        copy(self, "gethome", os.path.join(src_root, "src"), os.path.join(self.package_folder, "bin"))
        copy(self, "libhsort.a", os.path.join(src_root, "src"), os.path.join(self.package_folder, "lib"))
        copy(self, "hsort.h", os.path.join(src_root, "src"), os.path.join(self.package_folder, "include"))
        # Upstream src/hsort.h is not self-contained: it uses procmail's Q()
        # prototype macro and size_t without defining/including them (the
        # build-time shim src/includes.h supplies both). Consumers include
        # only hsort.h, so make the installed header self-contained by
        # prepending stddef.h + P/Q fallbacks when missing. No upstream
        # logic is altered; the original declaration bytes are preserved.
        hdr = os.path.join(self.package_folder, "include", "hsort.h")
        try:
            with open(hdr, "r", encoding="utf-8", errors="replace") as f:
                htxt = f.read()
        except OSError:
            htxt = ""
        if htxt and "#define Q(" not in htxt and "#define Q " not in htxt:
            prefix = (
                "/* OHOS: self-containment prefix (stddef + P/Q fallbacks). */\n"
                "#include <stddef.h>\n"
                "#ifndef P\n"
                "#define P(x) x\n"
                "#endif\n"
                "#ifndef Q\n"
                "#define Q(x) x\n"
                "#endif\n"
            )
            with open(hdr, "w", encoding="utf-8", newline="\n") as f:
                f.write(prefix + htxt)
        copy(self, "*", os.path.join(src_root, "SmartList", "bin"), os.path.join(self.package_folder, "bin", "smartlist"))
        copy(self, "*", os.path.join(src_root, "SmartList", "etc"), os.path.join(self.package_folder, "share", "smartlist", "etc"))
        copy(self, "*", os.path.join(src_root, "SmartList", "examples"), os.path.join(self.package_folder, "share", "smartlist", "examples"))
        copy(self, "README", os.path.join(src_root, "SmartList"), os.path.join(self.package_folder, "share", "smartlist"))
        copy(self, "INSTALL", os.path.join(src_root, "SmartList"), os.path.join(self.package_folder, "share", "smartlist"))
        copy(self, "Manual", os.path.join(src_root, "SmartList"), os.path.join(self.package_folder, "share", "smartlist"))

    def package_info(self):
        self.cpp_info.libs = ["hsort"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
