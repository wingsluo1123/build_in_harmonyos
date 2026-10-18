#!/usr/bin/env python3
"""Conan recipe — inn 1.7.2q (InterNetNews 1.x Usenet server suite + libinn).

Custom-make build (no configure script). INN 1.x configures itself through
``config/config.data`` (edited copy of ``config/config.dist``) plus the
``config/subst`` tool, which expands ``@<VAR>@`` placeholders in Makefiles,
headers and sample scripts. The recipe therefore:

1. writes ``config/config.data`` from ``config.dist`` with OHOS values
   (compiler/flags/paths/libc knobs, modelled on the values Debian ships
   for this exact tarball in ``extra/config.data.debian``);
2. builds ``config/subst`` (``make subst``; falls back to the ``subst.sh``
   shell version automatically if the C version failed to compile);
3. runs ``make substitutions`` in ``config/`` — deliberately *not* ``make
   all``/``quiet``, because the ``interpreters`` step needs a system perl
   and HarmonyOS ships none (same reason inn2 passes ``--without-perl``);
4. builds every directory in dependency order (``lib`` first — the other
   directories relink ``../libinn.a`` through their ``$(LIBNEWS)`` rule);
5. installs directory by directory with ``make install`` into absolute
   package paths baked into ``config.data``. The top-level ``make
   install`` (``makedirs.sh``, which unconditionally ``chown news``) is
   never invoked — there is no ``news`` account and no usable chown in the
   build sandbox; ``installit.sh -O/-G`` already skips chown for non-root.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class InnConan(ConanFile):
    name = "inn"
    version = "1.7.2q"
    description = "InterNetNews (INN) 1.x Usenet news server suite and the libinn C library"
    license = "ISC"
    homepage = "https://www.eyrie.org/~eagle/software/inn/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        # Vendored bison output for lib/parsedate.c (see _stage_parsedate()).
        copy(self, "*",
             os.path.join(self.recipe_folder, "files"),
             os.path.join(self.export_sources_folder, "files"),
             keep_path=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("inn is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # toolchain + config.data helpers
    # ------------------------------------------------------------------
    def _toolchain(self):
        """Resolve compiler and tools. Values come from Conan conf or PATH
        probes (R33: never bare CC/CFLAGS shell variables).

        The CI profile pins compilers to absolute DevBox paths
        (/data/service/hnp/bin/clang). Preflight proved that path can be
        absent on the real machine (make: /data/service/hnp/bin/clang: No
        such file or directory) while a usable clang exists via PATH or the
        OHOS SDK. So every conf value is verified executable before use;
        a stale absolute path falls back to PATH/SDK probes instead of
        poisoning CC/AR/RANLIB in config.data.
        """
        executables = self.conf.get("tools.build:compiler_executables",
                                    default=None, check_type=dict) or {}

        def _usable(path_or_name):
            if not path_or_name:
                return False
            if os.path.isabs(path_or_name):
                return (os.path.isfile(path_or_name)
                        and os.access(path_or_name, os.X_OK))
            return shutil.which(path_or_name) is not None

        def _resolve(conf_val, *names, sdk_candidates=()):
            if conf_val and _usable(conf_val):
                return conf_val
            if conf_val:
                self.output.warning(
                    "toolchain: conf value %r not executable, probing PATH/SDK"
                    % (conf_val,))
            for tool in names:
                found = shutil.which(tool)
                if found:
                    return found
            for cand in sdk_candidates:
                if (cand and os.path.isfile(cand)
                        and os.access(cand, os.X_OK)):
                    return cand
            # Let the build fail loudly with a clear missing-tool error.
            return names[0] if names else conf_val

        _sdk_roots = [r for r in (
            os.environ.get("OHOS_SDK"),
            os.environ.get("OHOS_SDK_ROOT"),
            os.path.expanduser("~/.ohos-sdk"),
            os.path.expanduser("~/ohos-sdk"),
        ) if r]
        _sdk_clang = tuple(
            ["/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang"]
            + [r.rstrip("/") + "/native/llvm/bin/clang" for r in _sdk_roots]
        )
        _sdk_ar = tuple(
            ["/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ar"]
            + [r.rstrip("/") + "/native/llvm/bin/llvm-ar" for r in _sdk_roots]
        )
        _sdk_ranlib = tuple(
            ["/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ranlib"]
            + [r.rstrip("/") + "/native/llvm/bin/llvm-ranlib" for r in _sdk_roots]
        )
        cc = _resolve(executables.get("c"), "clang", "clang-15", "cc", "gcc",
                      sdk_candidates=_sdk_clang)

        def _probe(*names):
            for tool in names:
                if shutil.which(tool):
                    return tool
            return None

        ar = _resolve(executables.get("ar"), "llvm-ar", "ar",
                      sdk_candidates=_sdk_ar)
        ranlib = _resolve(executables.get("ranlib"), "llvm-ranlib", "ranlib",
                          sdk_candidates=_sdk_ranlib)
        # YACC is kept for config.data substitution completeness, but the
        # build never invokes it: _stage_parsedate() vendors a pre-generated
        # parsedate.c (bison -y output) newer than parsedate.y, so make's
        # `parsedate.c: parsedate.y` rule stays up-to-date. Probe PATH only
        # to fill the knob; no tool_requires (conancenter bison would pull
        # m4/flex source builds that fail on preflight with
        # `/data/service/hnp/bin/bash: inaccessible or not found`).
        if _probe("yacc"):
            yacc = "yacc"
        elif _probe("bison"):
            yacc = "bison -y"
        else:
            # Never executed (vendored parsedate.c skips the rule); keep the
            # historical literal so config.data substitution stays valid.
            yacc = "yacc"
        opt = "-O0" if self.settings.build_type == "Debug" else "-O2"
        # $(DEFS) is a make variable expanded per directory (-I../include).
        cflags = "$(DEFS) -std=gnu17 %s -g" % opt
        return {"cc": cc, "cflags": cflags, "ldflags": "",
                "cppflags": "", "ar": ar, "ranlib": ranlib, "yacc": yacc}

    def _config_overrides(self, package_folder, tc):
        """config.data values. Toolchain rows come from conf; libc rows follow
        the values Debian validates for this exact tarball on modern Linux
        (extra/config.data.debian); install roots point into the package so
        `make install` lands directly in Conan layout (same trade-off as the
        inn2 recipe, whose binaries bake the package prefix)."""
        pf = package_folder.replace("\\", "/")
        overrides = {
            # Toolchain (R33: from Conan conf / PATH probes, never shell env).
            "CC": tc["cc"],
            "CFLAGS": tc["cflags"],
            "LDFLAGS": tc["ldflags"],
            "LIBS": "",
            "RANLIB": tc["ranlib"],
            "YACC": tc["yacc"],
            "AR": tc["ar"],
            # Modern-compiler tolerance (Debian -52: K&R sources need gnu17).
            "USE_CHAR_CONST": "DO",
            # Modern 64-bit libc (musl/glibc): types and feature probes.
            "OFFSET_T": "off_t",
            "ALIGNPTR": "void",
            "LOCK_STYLE": "FCNTL",
            "CLX_STYLE": "FCNTL",
            "NBIO_STYLE": "FCNTL",
            "HAVE_SETPROCTITLE": "DONT",
            "FORK": "fork",
            "NEED_TIME": "DO",
            "CTYPE": "isXXXXX((c))",
            "ACT_STYLE": "MMAP",
            "MMAP_PTR": "void *",
            "MSYNC_3_ARG": "DO",
            # No perl/Tcl on HarmonyOS (perl.c/tcl.c compile to stubs when
            # PERL_SUPPORT/TCL_SUPPORT are DONT, same as inn2 --without-perl).
            "PERL_SUPPORT": "DONT",
            "PERL_LIB": "",
            "PERL_INC": "",
            # Install roots: binaries, config samples and man pages land
            # directly in the Conan package tree.
            "_PATH_NEWSBIN": pf + "/bin",
            "_PATH_NEWSLIB": pf + "/etc",
            "_PATH_CONTROLPROGS": pf + "/bin/control",
            # _PATH_RNEWS is the rnews binary; _PATH_RNEWSPROGS is the
            # directory holding its unpacker helpers (upstream defaults
            # /usr/news/bin/rnews vs /usr/news/bin/rnews.libexec). They
            # must stay distinct: collapsing both to bin/rnews installs the
            # binary as a file first, then installit.sh fails to create
            # bin/rnews/<tmp> with "Not a directory" for c7unbatch.
            "_PATH_RNEWSPROGS": pf + "/bin/rnews.libexec",
            "_PATH_INEWS": pf + "/bin/inews",
            "_PATH_RNEWS": pf + "/bin/rnews",
            "_PATH_INND": pf + "/bin/innd",
            "_PATH_INNDSTART": pf + "/bin/inndstart",
            "_PATH_NNRPD": pf + "/bin/nnrpd",
            "_PATH_NNTPD": pf + "/bin/nnrpd",
            "_PATH_NNQRD": pf + "/bin/nnrpd",
            "_PATH_NEWSBOOT": pf + "/bin/rc.news",
            "_PATH_CONFIG": pf + "/etc/inn.conf",
            "_PATH_CONTROLCTL": pf + "/etc/control.ctl",
            "_PATH_EXPIRECTL": pf + "/etc/expire.ctl",
            "_PATH_INNDHOSTS": pf + "/etc/hosts.nntp",
            "_PATH_MODERATORS": pf + "/etc/moderators",
            "_PATH_DISTPATS": pf + "/etc/distrib.pats",
            "_PATH_NEWSFEEDS": pf + "/etc/newsfeeds",
            "_PATH_NNRPACCESS": pf + "/etc/nnrp.access",
            "_PATH_SCHEMA": pf + "/etc/overview.fmt",
            "_PATH_SHELLVARS": pf + "/etc/innshellvars",
            "_PATH_PERL_SHELLVARS": pf + "/etc/innshellvars.pl",
            "_PATH_TCL_SHELLVARS": pf + "/etc/innshellvars.tcl",
            "_PATH_CSH_SHELLVARS": pf + "/etc/innshellvars.csh",
            "_PATH_NNTPPASS": pf + "/etc/passwd.nntp",
            "_PATH_PARSECTL": pf + "/bin/parsecontrol",
            "_PATH_CTLWATCH": pf + "/etc/innwatch.ctl",
            "_PATH_PERL_STARTUP_INND": pf + "/bin/control/startup_innd.pl",
            "_PATH_PERL_FILTER_INND": pf + "/bin/control/filter_innd.pl",
            "_PATH_PERL_FILTER_NNRPD": pf + "/bin/control/filter_nnrpd.pl",
            "_PATH_TCL_STARTUP": pf + "/bin/control/startup.tcl",
            "_PATH_TCL_FILTER": pf + "/bin/control/filter.tcl",
            "_PATH_ACTSYNC_CFG": pf + "/etc/actsync.cfg",
            "_PATH_ACTSYNC_IGN": pf + "/etc/actsync.ign",
            "MAN1": pf + "/share/man/man1",
            "MAN3": pf + "/share/man/man3",
            "MAN5": pf + "/share/man/man5",
            "MAN8": pf + "/share/man/man8",
        }
        return overrides

    def _write_config_data(self, src, tc):
        """Derive config/config.data from config/config.dist.

        Every non-comment line keeps a TAB after the key (config/checkconf.sh
        rejects lines without one). Unknown keys (AR, added by our own patch)
        are appended; everything else replaces the distributed default."""
        dist = os.path.join(src, "config", "config.dist")
        data = os.path.join(src, "config", "config.data")
        overrides = self._config_overrides(self.package_folder, tc)
        replaced = set()
        out = []
        for line in open(dist, encoding="utf-8", errors="replace").read().split("\n"):
            m = re.match(r"^([A-Z_][A-Z0-9_]*)\s", line)
            key = m.group(1) if m else None
            if key and key in overrides and key not in replaced and not line.startswith("#"):
                out.append("%s\t%s" % (key, overrides[key]))
                replaced.add(key)
            else:
                out.append(line)
        missing = [k for k in overrides if k not in replaced]
        if missing:
            out.append("")
            for key in missing:
                out.append("%s\t%s" % (key, overrides[key]))
        with open(data, "w", encoding="utf-8", newline="\n") as f:
            text = "\n".join(out)
            # subst.c reads config.data with fgets(LINESIZE=1024) and
            # treats any line without a trailing newline as "too long".
            # Appended keys (AR) leave the last line unterminated, which
            # surfaced as "Line 918 of config.data is too long" once the
            # compiler fallback let the build reach substitutions.
            if not text.endswith("\n"):
                text += "\n"
            f.write(text)
        if missing:
            self.output.info("config.data: appended non-dist keys %s" % ", ".join(missing))
        self._verify_config_data(data)

    def _verify_config_data(self, data):
        """Deterministic TAB audit mirroring config/checkconf.sh.

        checkconf.sh finds TAB lines through a sed/grep/diff shell
        pipeline; HarmonyOS ships toybox userland, which is known to
        diverge on such constructs (knowledge E010 for sed, plus the
        toybox-grep BRE notes). This audit implements the identical
        rule without shell tools: every non-comment, non-empty line
        must contain a TAB. A violation raises with the offending
        lines rendered by repr() so invisible characters stay
        unambiguous in the preflight log; a pass is logged with the
        line count so a later shell-gate failure can be told apart
        from a genuinely bad file.
        """
        lines = open(data, encoding="utf-8", errors="replace").read().split("\n")
        bad = [(i, l) for i, l in enumerate(lines, start=1)
               if l and not l.startswith("#") and "\t" not in l]
        if bad:
            for i, l in bad[:10]:
                self.output.error("config.data line %d lacks TAB: %r" % (i, l))
            raise ConanException(
                "generated config.data has %d line(s) without TAB "
                "separators (first: line %d: %r)"
                % (len(bad), bad[0][0], bad[0][1]))
        self.output.info("config.data TAB audit passed (%d lines checked)"
                         % len(lines))

    def _audit_upstream_tests(self, src):
        """Upstream test audit. INN 1.7.2q ships no test suite (no tests/
        directory, no check/test make targets anywhere), so build() records
        a no_tests marker instead of running anything. If the audit ever
        finds tests, the recipe assumption is broken and the build stops."""
        tests_dir = os.path.join(src, "tests")
        has_tests_dir = os.path.isdir(tests_dir)
        makefiles = []
        check_targets = []
        for root, _dirs, files in os.walk(src):
            for name in files:
                if name == "Makefile":
                    path = os.path.join(root, name)
                    makefiles.append(os.path.relpath(path, src))
                    with open(path, encoding="utf-8", errors="replace") as f:
                        for line in f.read().split("\n"):
                            if re.match(r"^(check|test)\s*:", line):
                                check_targets.append("%s: %s" % (
                                    os.path.relpath(path, src), line.strip()))
        self.output.info("upstream test audit: %d Makefiles scanned, tests/ dir %s, "
                         "check/test targets %s"
                         % (len(makefiles),
                            "PRESENT" if has_tests_dir else "absent",
                            check_targets if check_targets else "none"))
        if has_tests_dir or check_targets:
            raise ConanInvalidConfiguration(
                "upstream test audit found a test suite where none was expected; "
                "the no_tests wiring in this recipe must be revisited")
        upstream = {
            "status": "no_tests",
            "framework": "none - upstream tarball contains no test suite",
            "command": "audit: scan all Makefiles for check/test targets, look for tests/",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("inn-1.7.2q ships no test suite: no tests/ directory and no "
                       "check/test target (strict ^(check|test)\\s*:) in any of the "
                       "%d Makefiles (audited from inn_1.7.2q.orig.tar.gz file list and "
                       "per-Makefile target scan; test-adjacent strings are not tests: "
                       "lib parsedate is a -DTEST debug helper never run by any target, "
                       "config sedtest is a sed-capability probe, lib/checkart.c is a "
                       "library source file, samples/inncheck is a runtime script)" % len(makefiles)),
        }
        res_dir = os.path.join(self.build_folder, "res")
        os.makedirs(res_dir, exist_ok=True)
        with open(os.path.join(res_dir, "upstream_test_result.json"),
                  "w", encoding="utf-8") as f:
            json.dump(upstream, f, ensure_ascii=False)
        print("HMBS_UPSTREAM_TEST_RESULT=%s"
              % json.dumps(upstream, ensure_ascii=False), flush=True)

    def _stage_parsedate(self, src):
        """Stage vendored lib/parsedate.c so make skips the yacc rule.

        lib/Makefile has `parsedate.c: parsedate.y` running
        `$(YACC) parsedate.y` + `mv y.tab.c parsedate.c`. The preflight
        machine has no yacc/bison, and tool_requires bison/3.8.2 from
        conancenter drags m4/flex source builds that fail with
        `/data/service/hnp/bin/bash: inaccessible or not found`.
        files/parsedate.c is bison -y output for the patched parsedate.y
        (verified: 6 shift/reduce conflicts as the Makefile expects,
        global `int date_lex()` per patch 0001). Copying it over lib/
        with a newer mtime keeps the make target up-to-date, so YACC is
        never executed.
        """
        staged = os.path.join(self.export_sources_folder, "files", "parsedate.c")
        dst = os.path.join(src, "lib", "parsedate.c")
        if not os.path.isfile(staged):
            raise ConanException(
                "vendored files/parsedate.c missing: %s" % staged)
        shutil.copyfile(staged, dst)
        # Ensure dst is strictly newer than parsedate.y (same-second
        # ties could still trigger the rule on some make implementations).
        yacc_src = os.path.join(src, "lib", "parsedate.y")
        try:
            base = os.path.getmtime(yacc_src)
        except OSError:
            base = None
        import time as _time
        target = max(_time.time(), (base or 0) + 5)
        os.utime(dst, (target, target))
        self.output.info("staged vendored lib/parsedate.c (%d bytes)" % os.path.getsize(dst))

    # ------------------------------------------------------------------
    # standard methods
    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        self._stage_parsedate(src)
        tc = self._toolchain()
        self.output.info("inn toolchain: CC=%s AR=%s RANLIB=%s YACC=%s"
                         % (tc["cc"], tc["ar"], tc["ranlib"], tc["yacc"]))

        # config/Makefile is not substituted yet, so the subst build takes
        # CC/CFLAGS/LDFLAGS/CPPFLAGS from the environment. Values below come
        # from Conan conf (R33); sub-directory Makefiles assign their own
        # (substituted) values afterwards, so nothing leaks past this step.
        saved_env = dict(os.environ)
        try:
            os.environ["CC"] = tc["cc"]
            os.environ["CFLAGS"] = "-std=gnu17 -O2 -g"
            os.environ["CPPFLAGS"] = tc["cppflags"]
            os.environ["LDFLAGS"] = tc["ldflags"]
            self._write_config_data(src, tc)
            cfg = os.path.join(src, "config")
            # Fail fast if config.data lost its TAB separators.
            self.run("sh ./checkconf.sh config.data", cwd=cfg)
            # Build config/subst (falls back to subst.sh automatically).
            self.run("make subst -j1", cwd=src)
            # Substitute only; skip the `interpreters` step (needs perl).
            self.run("make substitutions -j1", cwd=cfg)
            # dbz.c includes <dbz.h>: generate it via the upstream rule.
            self.run("make ../include/dbz.h -j1",
                     cwd=os.path.join(src, "lib"))
            # config first, then lib (the rest relink ../libinn.a itself).
            self.run("make -j1 all", cwd=os.path.join(src, "lib"))
            for sub in ("frontends", "innd", "nnrpd", "backends",
                        "expire", "doc", "site"):
                self.run("make -j1 all", cwd=os.path.join(src, sub))
        finally:
            os.environ.clear()
            os.environ.update(saved_env)
        self._audit_upstream_tests(src)

    def package(self):
        src = self.source_folder
        for sub in ("bin", "bin/control", "bin/rnews.libexec", "etc", "lib", "include",
                    "share/man/man1", "share/man/man3",
                    "share/man/man5", "share/man/man8"):
            os.makedirs(os.path.join(self.package_folder, sub), exist_ok=True)
        # Per-directory install (never the top-level `install`: makedirs.sh
        # unconditionally chowns to the news account, which does not exist
        # in the build sandbox; installit.sh -O/-G already skip chown when
        # not running as root).
        for sub in ("lib", "frontends", "innd", "nnrpd", "backends",
                    "expire", "doc", "site"):
            self.run("make -j1 install", cwd=os.path.join(src, sub))
        copy(self, "libinn.a", src=src,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(src, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYRIGHT", src=src,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "upstream_test_result.json",
             src=os.path.join(self.build_folder, "res"),
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = ["inn"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
