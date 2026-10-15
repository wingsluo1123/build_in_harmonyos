#!/usr/bin/env python3
"""Conan recipe — kafs-client 0.5 (Makefile).

kAFS userspace client tools (David Howells): libkafs_client shared
library (config/cell DB parsing, DNS lookup helpers) plus the
aklog-kafs / kafs-check-config / kafs-preload / kafs-dns programs.

Build system: plain Makefile (top Makefile + src/Makefile + version.lds).
No configure step, no upstream test suite (no check/test target, no
tests/ directory — audit in test_package/MANIFEST.yml, status no_tests).

OHOS/aarch64 notes (see notes.md):
- Top Makefile + src/Makefile.config probe word size via
  `file /usr/bin/make | sed ...` and append -m32/-m64 (x86-only flags).
  The recipe passes BUILDFOR= on every make invocation so neither flag
  is added on OHOS aarch64 (clang rejects -m64 there).
- src/Makefile.config probes LIBDIR via `ldd /usr/bin/make | grep libc`,
  which fails on OHOS. The recipe passes LIBDIR/INCLUDEDIR/BINDIR/
  SBINDIR/LIBEXECDIR/ETCDIR explicitly into package_folder.
- Only `make -C src install` is used for packaging (top-level install
  would write /etc/kafs, systemd units, man pages to the host).
- Deps: krb5/1.22.1 (aklog-kafs needs krb5/krb5.h) and
  libkeyutils/1.6.3 (aklog-kafs + kafs-dns need keyutils.h).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.layout import basic_layout


class KafsClientConan(ConanFile):
    name = "kafs-client"
    version = "0.5"
    description = "kAFS userspace client tools and config parsing library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.infradead.org/~dhowells/kafs/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    # Conan 2.x requires a 'shared' option when package_type is
    # 'library' (true-device graph validation:
    # "Package type is 'library', but no 'shared' option declared").
    # Upstream builds libkafs_client as a shared object only
    # (libkafs_client.so.0.1 + SONAME symlinks, see notes.md), so the
    # option is declared for graph compliance; the Makefile always
    # produces the shared library regardless of its value.
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kafs-client supports Linux and OHOS, got %s" % self.settings.os
            )

    def requirements(self):
        self.requires("krb5/1.22.1", transitive_headers=True, transitive_libs=True)
        self.requires("libkeyutils/1.6.3", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Debian pristine orig.tar.gz is flat (45 files at root, no
        # top-level directory); strip_root=True fails with "Can't untar
        # a tgz containing files in the root".
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # Persist writable TMPDIR through build scope (HMDFS /tmp may be
        # read-only on the true device; only redirects temp root).
        tmpdir = self._ensure_writable_tmp()
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.vars(self, scope="build").save_sh("hmbs_tmpdir")

    def _ensure_writable_tmp(self):
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                return cand
            except Exception:
                continue
        return None

    def _dep_paths(self, ref):
        dep = self.dependencies[ref]
        incs = list(dep.cpp_info.includedirs or ["include"])
        libs = list(dep.cpp_info.libdirs or ["lib"])
        inc = incs[0] if os.path.isabs(incs[0]) else os.path.join(dep.package_folder, incs[0])
        lib = libs[0] if os.path.isabs(libs[0]) else os.path.join(dep.package_folder, libs[0])
        return inc, lib

    def _compiler(self, key, fallback):
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        configured = exes.get(key)
        if configured:
            first = str(configured).split()[0].strip("\"'")
            if os.path.isfile(first):
                return str(configured)
        found = shutil.which(fallback)
        return found or fallback

    def _make_base_args(self):
        # R33: compilers from Conan conf, never bare $CC from shell env.
        cc = self._compiler("c", "clang")
        # Explicit install dirs (upstream auto-detection via
        # file/ldd /usr/bin/make fails on OHOS).
        pkg = self.package_folder.replace("\\", "/")
        libdir = os.path.join(pkg, "lib").replace("\\", "/")
        incdir = os.path.join(pkg, "include").replace("\\", "/")
        bindir = os.path.join(pkg, "bin").replace("\\", "/")
        etcdir = os.path.join(pkg, "etc").replace("\\", "/")
        krb5_inc, krb5_lib = self._dep_paths("krb5")
        ku_inc, ku_lib = self._dep_paths("libkeyutils")
        # BUILDFOR= neutralises the upstream -m32/-m64 probe (x86-only).
        args = [
            "BUILDFOR=",
            "CC=%s" % cc,
            "LIBDIR=%s" % libdir,
            "INCLUDEDIR=%s" % incdir,
            "BINDIR=%s" % bindir,
            "SBINDIR=%s" % bindir,
            "LIBEXECDIR=%s" % bindir,
            "ETCDIR=%s" % etcdir,
            "DATADIR=%s" % os.path.join(pkg, "share/kafs-client").replace("\\", "/"),
            "MANDIR=%s" % os.path.join(pkg, "share/man").replace("\\", "/"),
        ]
        cflags_extra = "-I%s -I%s" % (krb5_inc, ku_inc)
        # Upstream src/*.c does '#include <kafs/cellserv.h>'; the kafs/
        # header dir is src/include/kafs/ (tar -tf of the pristine
        # orig.tar.gz lists src/include/kafs/cellserv.h, profile.h,
        # reporting.h; src/Makefile uses CPPFLAGS += -Iinclude relative
        # to src/). Command-line CFLAGS=/CPPFLAGS=... overrides that
        # relative -I, so expose the exact absolute dir explicitly;
        # otherwise clang fails with
        # "fatal error: 'kafs/cellserv.h' file not found".
        # NOTE: previous round added -I<src> -I<src>/src -I<src>/include
        # (wrong depth, verified still failing on true device); the only
        # correct extra dir is -I<src>/src/include.
        try:
            _src = (self.source_folder or "").replace("\\", "/")
        except Exception:
            _src = ""
        if _src:
            cflags_extra += " -I%s/src/include" % (_src,)
        # OHOS/musl portability (new failure domain, unrelated to the
        # earlier -I depth / -DETCDIR rounds): src/lib_dns_lookup.c uses
        # BSD `u_char` + NS_PACKETSZ/ns_msg (arpa/nameser.h). glibc pulls
        # `u_char` transitively, but the OHOS clang headers are strict and
        # error out with `unknown type name 'u_char'`. Forcing the include
        # first defines the BSD types before every TU without needing an
        # exact-context source patch.
        cflags_extra += " -include sys/types.h"
        # OHOS/musl portability (true-device link evidence 2026-10-14):
        # dns_main.c calls BSD legacy `rindex()' (POSIX-specified equivalent
        # of strrchr). OHOS libc exports no `rindex' symbol (ld.lld:
        # `undefined symbol: rindex' when linking kafs-dns), so alias it to
        # strrchr for every TU via -D. OHOS-only; glibc keeps its real symbol.
        try:
            _is_ohos = (str(self.settings.os) == "OHOS")
        except Exception:
            _is_ohos = True
        if _is_ohos:
            cflags_extra += " -Drindex=strrchr"
        # NOTE (strategy change): do NOT re-add -DETCDIR here and do NOT
        # pass CPPFLAGS= on the make command line (see build()/package()).
        # Upstream src/Makefile owns `CPPFLAGS += -Iinclude
        # -DETCDIR=\"$(ETCDIR)\"` plus Makefile.config's -DVERSION; any
        # command-line CPPFLAGS=... wipes those appends (command-line vars
        # win over +=) and -D string macros need two shell/make quoting
        # layers that are brittle from a recipe. Carrying our extras in
        # CFLAGS only lets the makefile's own CPPFLAGS survive, so -DETCDIR
        # is generated from the ETCDIR make var we already pass.
        ldflags_extra = "-L%s -L%s -Wl,-rpath,%s -Wl,-rpath,%s" % (
            krb5_lib, ku_lib, krb5_lib, ku_lib)
        # Upstream src/Makefile does `LDFLAGS += -L.` so its progs link
        # `-lkafs_client` from the just-built src/ dir. Command-line
        # LDFLAGS=... overrides that += (same wipe as CPPFLAGS), so without
        # an explicit -L the link fails with `unable to find library
        # -lkafs_client` (true-device evidence). Restore it here: relative
        # -L. for `make -C src` plus absolute src dir for `make -C <root>`.
        ldflags_extra += " -L."
        if _src:
            ldflags_extra += " -L%s/src" % (_src,)
        return args, cflags_extra, ldflags_extra

    def _emit_upstream_no_tests(self):
        payload = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "kafs-client_0.5.orig.tar.gz audited (sha256 "
                "561b6416f8f7234ddc1e66d8e479d96625c1655463365ea0f954e469ba8aa051): "
                "flat tarball holds 45 files with no tests/ or test/ directory; "
                "top Makefile defines only all/install/clean/distclean/tarball/rpm, "
                "src/Makefile defines only all/lib/progs/install/clean/distclean; "
                "no check/test target, no ctest/pytest/gtest registration "
                "(see test_package/MANIFEST.yml audit)"
            ),
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception as e:
            self.output.warning("HMBS persist upstream marker failed: %s" % e)

    def _ensure_musl_res_n_compat(self):
        # OHOS/musl failure domain (true-device evidence 2026-10-14):
        # - round 1: src/*.c use the reentrant res_n* API plus the glibc
        #   `_res' global; OHOS/musl declares neither -> `use of undeclared
        #   identifier _res' (8 errors) + res_nclose implicit-decl conflict.
        # - round 2: after the _res fallback, one `conflicting types for
        #   res_nclose' remained (fixed with forward prototypes).
        # - round 3 (this round): compile passes, but linking kafs-check-config
        #   fails with `undefined reference due to --no-allow-shlib-undefined:
        #   res_nquery/res_ninit/res_nclose referenced by ./libkafs_client.so'.
        #   Upstream src/Makefile links the shared lib with `-lresolv', but
        #   OHOS/musl libresolv provides no res_n* (only res_init/res_query),
        #   so the .so keeps undefined symbols and the strict OHOS linker
        #   rejects the consumer link.
        # Root cause of round 3: the previous "already defined" detection ran
        # AFTER prepending our own forward prototypes, and its regex also
        # matches a prototype line ending in `;', so every symbol looked
        # "defined" (missing==[]) and the shims were NEVER appended -- the .so
        # kept the undefined res_n* references.
        # Fix: detect upstream DEFINITIONS (brace-aware, tolerant of
        # static/extern) BEFORE adding our prototypes; strip stale V1 HMBS
        # blocks first (idempotent re-patch); gate on recipe-level
        # settings.os == OHOS (deterministic, no __GLIBC__ macro detection);
        # define res_ninit/res_nclose/res_nquery/res_nsearch inside
        # libkafs_client.so atop musl's res_init/res_query. Offline paths
        # (use_dns=no, kafs-check-config -N dns) never call DNS at runtime;
        # this only satisfies compile+link.
        import re
        try:
            is_ohos = (str(self.settings.os) == "OHOS")
        except Exception:
            is_ohos = True
        if not is_ohos:
            return
        src_root = self.source_folder or ""
        rels = [
            os.path.join("src", "lib_object.c"),
            os.path.join("src", "lib_dns_lookup.c"),
            "lib_object.c",
        ]
        # Only lib_object.c carries global definitions (one TU) to avoid
        # duplicate symbols; other TUs just get the _res fallback so
        # their references compile and link against lib_object.c.
        definer_rel = os.path.join("src", "lib_object.c")
        for rel in rels:
            path = os.path.join(src_root, rel) if src_root else rel
            if not path or not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                self.output.warning("musl compat read failed %s: %s" % (rel, e))
                continue
            # Strip previous-round (V1) HMBS blocks so a stale/partial patch
            # can never block re-patch. V1 markers carry a trailing colon;
            # V2 markers use `_V2:' and contain no `#endif', so this cannot
            # touch V2 blocks.
            stripped = re.sub(
                r"/\* HMBS_MUSL_RES_(FALLBACK|N_SHIM):[\s\S]*?#endif[^\n]*\n?",
                "", content)
            if stripped != content:
                content = stripped
                self.output.info("musl compat: stripped stale V1 HMBS block in %s" % rel)
            is_definer = (rel == definer_rel or rel == "lib_object.c")
            # Detect UPSTREAM definitions BEFORE our prototypes are added.
            # Brace-aware: a prototype ends with `;' and must not count.
            upstream_defined = set()
            if is_definer and "HMBS_MUSL_RES_N_SHIM_V2" not in content:
                for sym in ("res_ninit", "res_nclose", "res_nquery", "res_nsearch"):
                    if re.search(
                        r"(^|\n)\s*(?:static\s+|extern\s+)?(?:int|void)\s+%s\s*\([^;]*?\)\s*\{" % re.escape(sym),
                        content):
                        upstream_defined.add(sym)
            changed = False
            # 1) _res storage + forward prototypes (V2, unguarded: this patch
            # is applied on OHOS only; glibc builds are never touched).
            if ("HMBS_MUSL_RES_FALLBACK_V2" not in content
                    and (re.search(r"\b_res\b", content)
                         or re.search(r"\bres_n(close|init|query|search)\b", content))):
                fallback = (
                    "\n/* HMBS_MUSL_RES_FALLBACK_V2: OHOS/musl lacks the glibc "
                    "`_res` global and res_n* decls; provide per-TU storage "
                    "plus forward prototypes so upstream compiles. Recipe "
                    "applies this on OHOS only, so no __GLIBC__ guard. */\n"
                    "#include <resolv.h>\n"
                    "static struct __res_state _hmbs_res_fallback;\n"
                    "#define _res _hmbs_res_fallback\n"
                    "int res_ninit(res_state statp);\n"
                    "void res_nclose(res_state statp);\n"
                    "int res_nquery(res_state statp, const char *dname, int qclass, int qtype,\n"
                    "               unsigned char *answer, int anslen);\n"
                    "int res_nsearch(res_state statp, const char *dname, int qclass, int qtype,\n"
                    "                unsigned char *answer, int anslen);\n"
                )
                content = fallback + content
                changed = True
                self.output.info("musl compat: _res fallback prepended to %s" % rel)
            # 2) res_n* definitions in the defining TU for symbols upstream
            # does NOT define (no _res use at all).
            if is_definer and "HMBS_MUSL_RES_N_SHIM_V2" not in content:
                missing = [s for s in ("res_ninit", "res_nclose", "res_nquery", "res_nsearch")
                           if s not in upstream_defined]
                if missing:
                    parts = [
                        "\n/* HMBS_MUSL_RES_N_SHIM_V2: provide %s atop "
                        "res_init/res_query inside libkafs_client.so; "
                        "OHOS-only, no _res reference. */"
                        % "/".join(missing),
                        "#include <string.h>",
                    ]
                    if "res_ninit" in missing:
                        parts += [
                            "int res_ninit(res_state statp)",
                            "{",
                            "    if (statp)",
                            "        memset(statp, 0, sizeof(*statp));",
                            "    return res_init();",
                            "}",
                        ]
                    if "res_nclose" in missing:
                        parts += [
                            "void res_nclose(res_state statp)",
                            "{",
                            "    (void)statp;",
                            "}",
                        ]
                    if "res_nquery" in missing:
                        parts += [
                            "int res_nquery(res_state statp, const char *dname,",
                            "             int qclass, int qtype,",
                            "             unsigned char *answer, int anslen)",
                            "{",
                            "    (void)statp;",
                            "    return res_query(dname, qclass, qtype, answer, anslen);",
                            "}",
                        ]
                    if "res_nsearch" in missing:
                        parts += [
                            "int res_nsearch(res_state statp, const char *dname,",
                            "              int qclass, int qtype,",
                            "              unsigned char *answer, int anslen)",
                            "{",
                            "    (void)statp;",
                            "    return res_query(dname, qclass, qtype, answer, anslen);",
                            "}",
                        ]
                    content = content + "\n" + "\n".join(parts) + "\n"
                    changed = True
                    self.output.info(
                        "musl compat: appended %s to %s (upstream already defines: %s)"
                        % ("/".join(missing), rel,
                           "/".join(sorted(upstream_defined)) or "none"))
            if changed:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                except Exception as e:
                    raise ConanException("musl compat write failed %s: %s" % (rel, e))
    def _write_install_shim(self):
        # OHOS install shim (E182/E188 family: cvechecker/cubelib/adms
        # precedent): the HMBS/toybox `install` on the true device only
        # accepts the single-source form; kafs src/Makefile:84 calls
        # `install -D -m 0644 h1 h2 h3 dest/` (3 sources) which exits 64
        # (EX_USAGE). Provide a cp/mkdir shim tolerating -D/-c/-p/-s/-m/-d/--
        # and copying each source into the dest dir; chmod is best-effort
        # (HMBS_CAP_CHMOD=0). Created with os.open(0o755) so it is executable
        # even where chmod is unsupported.
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c|-D|-s) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -m*) mode=${1#-m}; shift ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        self.output.info("kafs-client install shim: %s" % install)
        return install

    def build(self):
        self._ensure_writable_tmp()
        old_umask = os.umask(0o022)
        try:
            apply_conandata_patches(self)
            self._ensure_musl_res_n_compat()
            args, cflags_extra, ldflags_extra = self._make_base_args()
            # Merge dep flags with toolchain-provided flags (conanbuild env).
            # Deliberately NOT passing CPPFLAGS= on the command line: that
            # would wipe the makefile's own `CPPFLAGS += -Iinclude
            # -DETCDIR=... -DVERSION=...` appends. Toolchain env CPPFLAGS
            # is folded into CFLAGS instead (same compiler invocation:
            # %.os uses $(CPPFLAGS) $(CFLAGS)); make still imports env
            # CPPFLAGS for its own appends.
            env_cflags = os.environ.get("CFLAGS", "")
            env_cppflags = os.environ.get("CPPFLAGS", "")
            env_ldflags = os.environ.get("LDFLAGS", "")
            full_cflags = " ".join(x for x in [env_cflags, env_cppflags, cflags_extra] if x).strip()
            full_ldflags = " ".join(x for x in [env_ldflags, ldflags_extra] if x).strip()
            make = self.conf.get("tools.gnu:make_program", default="make")
            base = " ".join(args)
            self.output.info("kafs-client make base: %s" % base)
            self.run(
                '%s -C "%s" %s CFLAGS="%s" LDFLAGS="%s" -j1 all' % (
                    make, self.source_folder, base, full_cflags, full_ldflags),
                env="conanbuild",
            )
            # No upstream test suite to run inside build() (no_tests).
            self._emit_upstream_no_tests()
        finally:
            os.umask(old_umask)

    def package(self):
        old_umask = os.umask(0o022)
        try:
            args, cflags_extra, ldflags_extra = self._make_base_args()
            env_cflags = os.environ.get("CFLAGS", "")
            env_cppflags = os.environ.get("CPPFLAGS", "")
            env_ldflags = os.environ.get("LDFLAGS", "")
            full_cflags = " ".join(x for x in [env_cflags, env_cppflags, cflags_extra] if x).strip()
            full_ldflags = " ".join(x for x in [env_ldflags, ldflags_extra] if x).strip()
            make = self.conf.get("tools.gnu:make_program", default="make")
            base = " ".join(args)
            # Only src/ is installed (libs + headers + programs); top-level
            # install would write /etc/kafs + systemd units to the host.
            # No CPPFLAGS= override here either (see build()).
            # True-device fix 2026-10-14: install dirs are absolute inside
            # package_folder and src/Makefile prefixes them with $(DESTDIR),
            # so DESTDIR must NOT be passed (it doubled the path); plus a
            # multi-source cp/mkdir shim shadows the single-file HMBS install.
            shim = self._write_install_shim()
            shim_dir = os.path.dirname(shim)
            self.run(
                'export PATH="%s:$PATH"; %s -C "%s/src" %s INSTALL="%s" CFLAGS="%s" LDFLAGS="%s" -j1 install' % (
                    shim_dir, make, self.source_folder, base, shim, full_cflags, full_ldflags),
                env="conanbuild",
            )
        finally:
            os.umask(old_umask)
        # Upstream installs libkafs_client.so.0.1 + .so.0/.so symlinks plus
        # four programs into bin/; keep them, drop nothing else.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "LICENCE.GPL", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # Carry the no_tests evidence for cache-hit re-emit.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst_dir, "hmbs_upstream.json"))
        except Exception as e:
            self.output.warning("HMBS package upstream copy failed: %s" % e)
        for name in ("aklog-kafs", "kafs-check-config", "kafs-preload", "kafs-dns"):
            bin_path = os.path.join(self.package_folder, "bin", name)
            if os.path.isfile(bin_path):
                try:
                    os.chmod(bin_path, 0o755)
                except Exception:
                    pass
                if str(self.settings.os) == "OHOS":
                    self._sign_elf(bin_path)

    def package_info(self):
        self.cpp_info.libs = ["kafs_client"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["resolv"]
        # Consumers (test_package) need krb5/keyutils run paths.
        for ref in ("krb5", "libkeyutils"):
            try:
                dep = self.dependencies[ref]
                libdirs = dep.cpp_info.libdirs or ["lib"]
                lib_dir = libdirs[0]
                if not os.path.isabs(lib_dir):
                    lib_dir = os.path.join(dep.package_folder, lib_dir)
                self.runenv_info.append_path("LD_LIBRARY_PATH", lib_dir)
            except Exception:
                pass

    def _sign_elf(self, path):
        objcopy = self._find_tool("llvm-objcopy")
        signer = self._find_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("OHOS ELF signing tools are unavailable")
        self.run('"%s" --remove-section .codesign "%s"' % (objcopy, path), ignore_errors=True)
        signed = path + ".signed"
        self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, path, signed))
        os.replace(signed, path)
        os.chmod(path, 0o755)

    @staticmethod
    def _find_tool(command):
        for directory in (os.environ.get("SIGN_TOOL_PATH"), "/data/service/hnp/bin"):
            if not directory:
                continue
            candidate = os.path.join(directory, command)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(command)
