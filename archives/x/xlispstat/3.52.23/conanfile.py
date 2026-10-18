#!/usr/bin/env python3
"""Conan recipe for xlispstat 3.52.23.

XLISP-STAT is Luke Tierney's interactive statistical computing and dynamic
graphics environment built on the XLISP dialect. Upstream is an old autoconf
project with no `make check`; the build itself must run the freshly compiled
`xlisp` interpreter natively to compile the .lsp runtime into .fsl files and
to dump the default workspace (xlisp.wks). A native build step is therefore
mandatory (same constraint as zenlisp on this platform).

Graphics: upstream supports --without-x, which selects the GNUPLOT graphics
system (terminal-only, no libX11/Xaw link). That is the configuration used
here; the X11/Athena build would require libxaw/libxmu/libxt which are not
yet available as Conan packages on this platform.
"""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class XlispstatConan(ConanFile):
    name = "xlispstat"
    version = "3.52.23"
    description = (
        "Interactive statistical computing and dynamic graphics environment "
        "based on the XLISP Lisp dialect"
    )
    license = "HPND-sell-variant"
    homepage = "https://homepage.stat.uiowa.edu/~luke/xls/xlsinfo/"
    url = "https://github.com/jhbadger/xlispstat"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # Canonical upstream release archive (same URL/SHA256 as the Homebrew
    # formula). The GitHub mirror (jhbadger/xlispstat) has no tags, so the
    # uiowa tarball is the only reproducible pin.
    _source_url = (
        "https://homepage.cs.uiowa.edu/~luke/xls/xlispstat/"
        "current/xlispstat-3-52-23.tar.gz"
    )
    _source_sha256 = (
        "9bf165eb3f92384373dab34f9a56ec8455ff9e2bf7dff6485e807767e6ce6cf4"
    )

    _test_files = [
        "arith", "complex", "manip", "matrix", "matrix2",
        "blas", "math", "prob", "trig", "rans",
    ]

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xlispstat is supported only on Linux and HarmonyOS"
            )

    def export_sources(self):
        copy(
            self,
            "patches/*.patch",
            src=self.recipe_folder,
            dst=self.export_sources_folder,
        )

    def requirements(self):
        # --without-x build: libc + libm only. No ncurses/readline/X11.
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # URL/SHA256 are pinned in the recipe (not conandata.yml) to avoid
        # the CI pre-download BUILD_DIR defect; .tar.gz suffix is required
        # so Conan recognizes the archive format.
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            strip_root=True,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _shell(self):
        # E386: probe candidate shells from the real build directory and
        # accept one only when it can determine its working directory there
        # (the hnp bash emits getcwd errors and breaks autoconf's re-exec).
        # The result is cached for the whole build.
        if getattr(self, "_picked_shell", None):
            return self._picked_shell
        import subprocess
        candidates = [
            "/system/bin/sh",
            "/bin/sh",
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
        ]
        conf_dir = self._conf_dir()
        for cand in filter(None, candidates):
            if not os.path.exists(cand):
                continue
            try:
                p = subprocess.run(
                    [cand, "-c", "pwd"],
                    cwd=conf_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except Exception:
                continue
            if p.returncode == 0 and not p.stderr.strip():
                self._picked_shell = cand
                self.output.info(
                    "E386: HMDFS cwd probe passed for shell {}".format(cand)
                )
                return cand
            self.output.warning(
                "E386: shell {} failed the HMDFS cwd probe (rc={}, stderr={!r})"
                .format(cand, p.returncode, (p.stderr or "")[:80])
            )
        raise ConanInvalidConfiguration(
            "no HMDFS-capable shell found for the xlispstat build"
        )

    def _run_shell(self, command, cwd, env="conanbuild"):
        self.run(
            '"{}" -c {}'.format(self._shell(), shlex.quote(command)),
            cwd=cwd,
            env=env,
        )

    def _conf_dir(self):
        # basic_layout: build_folder is the generators dir; the copy of the
        # source tree (with configure) may be in build_folder's parent or in
        # source_folder. Probe both (HMDFS-safe pattern from esekeyd).
        for cand in (self.build_folder, self.source_folder):
            if os.path.isfile(os.path.join(cand, "configure")):
                return cand
        raise ConanInvalidConfiguration("configure script not found")

    def _apply_source_patches(self):
        conf_dir = self._conf_dir()
        patch_dir = os.path.join(self.export_sources_folder, "patches")
        for name in sorted(os.listdir(patch_dir)):
            if not name.endswith(".patch"):
                continue
            self._run_shell(
                "patch -p1 -i {}".format(shlex.quote(os.path.join(patch_dir, name))),
                cwd=conf_dir,
            )

    def _patch_config_guess(self, conf_dir):
        # E007, in-recipe idempotent injection (the posh/zephyr precedent).
        # The bundled config.guess is 2002-03-20 echo/exit style without any
        # HarmonyOS branch, and its vintage config.sub rejects both aarch64
        # and *-linux-ohos triples, so the native branch reports the plain
        # linux-gnu triple this script family already emits for Linux.
        # Implemented here instead of a .patch file: the hunk only applies
        # with fuzz on desktop patch(1) and fails on the device's patch.
        path = os.path.join(conf_dir, "config", "config.guess")
        with open(path, encoding="utf-8", errors="surrogateescape") as f:
            content = f.read()
        if "HarmonyOS" in content:
            self.output.info("E007: config.guess already has a HarmonyOS branch")
            return
        anchor = '    *:NetBSD:*:*)'
        if anchor not in content:
            raise ConanException(
                "config.guess anchor '*:NetBSD:*:*)' not found; cannot inject "
                "the HarmonyOS branch"
            )
        injection = (
            "    # HarmonyOS (OHOS) native build: uname -s is \"HarmonyOS\",\n"
            "    # which this 2002-era script does not know. Report the plain\n"
            "    # linux-gnu triple this script already emits for Linux.\n"
            "    *:HarmonyOS:*:*)\n"
            "\techo \"$UNAME_MACHINE\"-unknown-linux-gnu\n"
            "\texit 0;;\n"
        )
        content = content.replace(anchor, injection + anchor, 1)
        with open(path, "w", encoding="utf-8", errors="surrogateescape",
                  newline="") as f:
            f.write(content)
        self.output.info(
            "E007: config.guess HarmonyOS branch injected "
            "(reports <machine>-unknown-linux-gnu)"
        )

    def _patch_configure_umask(self, conf_dir):
        # E011/E114: autoconf's config.status does `umask 077` before
        # creating ./confXXXXXX; on HMDFS that yields an unwritable
        # drwx--S--- directory ("can't create ./confXXXX/subs1.awk:
        # Permission denied", r4). The repo prescription (rsyslog 8.2404.0,
        # esekeyd 1.2.7 r5; combine 0.4.0 A/B test) is to relax it in the
        # generated configure; 002 keeps an explicit, deterministic mask.
        # Idempotent in-recipe edit, same rationale as _patch_config_guess.
        path = os.path.join(conf_dir, "configure")
        with open(path, encoding="utf-8", errors="surrogateescape") as f:
            content = f.read()
        count = content.count("umask 077")
        if count == 0:
            self.output.info("E011: no `umask 077` found in configure")
            return
        content = content.replace("umask 077", "umask 002")
        with open(path, "w", encoding="utf-8", errors="surrogateescape",
                  newline="") as f:
            f.write(content)
        self.output.info(
            "E011: relaxed {} `umask 077` occurrence(s) to `umask 002` "
            "in configure".format(count)
        )

    def _patch_makefile_hardlink(self, conf_dir):
        # E050 / PSCAN-HMDFS-001: src/c/Makefile.in links the interpreter
        # into place with a hard link (`ln ${GRAPHSYS}xlisp xlisp`); HMDFS
        # rejects hard links ("Operation not permitted", r5) and the `-`
        # prefixed rule leaves src/c/xlisp missing, so the top-level `cp`
        # fails. Replace the hard link with a copy (the surrounding rules
        # already `rm -f xlisp` first, so cp is semantically identical).
        path = os.path.join(conf_dir, "src", "c", "Makefile.in")
        with open(path, encoding="utf-8", errors="surrogateescape") as f:
            content = f.read()
        for old, new in (
            ("\t-ln ${GRAPHSYS}xlisp xlisp", "\tcp ${GRAPHSYS}xlisp xlisp"),
            ("\tln ${GRAPHSYS}xlisp xlisp", "\tcp ${GRAPHSYS}xlisp xlisp"),
        ):
            if old in content:
                content = content.replace(old, new, 1)
                break
        else:
            if "\tcp ${GRAPHSYS}xlisp xlisp" in content:
                self.output.info("E050: src/c/Makefile.in already uses cp")
                return
            raise ConanException(
                "src/c/Makefile.in hard-link rule not found; cannot apply "
                "the HMDFS ln->cp fix"
            )
        with open(path, "w", encoding="utf-8", errors="surrogateescape",
                  newline="") as f:
            f.write(content)
        self.output.info(
            "E050: replaced the src/c xlisp hard link with a copy (HMDFS)"
        )

    def _patch_makefile_setup_shell(self, conf_dir):
        # E087: the top-level Makefile invokes ./setup.shell directly; on
        # noexec HMDFS mounts that is "Permission denied" (r17). Invoke it
        # through the shell instead.
        path = os.path.join(conf_dir, "Makefile.in")
        with open(path, encoding="utf-8", errors="surrogateescape") as f:
            content = f.read()
        old = "\t./setup.shell xlispstat ${XLSLIB}"
        new = "\tsh ./setup.shell xlispstat ${XLSLIB}"
        if old not in content:
            if new in content:
                self.output.info("E087: Makefile.in already uses sh setup.shell")
                return
            raise ConanException("setup.shell rule not found in Makefile.in")
        content = content.replace(old, new, 1)
        with open(path, "w", encoding="utf-8", errors="surrogateescape",
                  newline="") as f:
            f.write(content)
        self.output.info(
            "E087: setup.shell now invoked via sh (noexec HMDFS)"
        )

    def _patch_init_headless(self, conf_dir):
        # r14-r16 diagnosis chain: with --without-x (GNUPLOT/dummygraph
        # build) the dynamic-graphics Lisp stack segfaults the interpreter:
        # auto-init reaches (require "graphics") -> graphics.lsp ends with
        # (require "graph2") -> graph2.lsp line 31
        # (send spin-proto :depth-cuing t) dispatches into the dummygraph C
        # stubs -> deterministic SIGSEGV (repro 20/20; binary search through
        # init.lsp, graphics.lsp and graph2.lsp on the device).
        # A headless device has no dynamic-graphics backend by definition;
        # upstream ships nongraph.lsp as the gnuplot-based replacement for
        # exactly this situation. Swap the graphics require for nongraph
        # and drop the same require from regress.lsp.
        edits = [
            (
                os.path.join(conf_dir, "src", "lsp", "init.lsp"),
                '(require "graphics")',
                '(load "nongraph") ; headless OHOS: gnuplot plotting instead of the dynamic-graphics stack',
            ),
            (
                os.path.join(conf_dir, "src", "lsp", "regress.lsp"),
                '(require "graphics")',
                "; headless OHOS: dynamic graphics stack is not loaded",
            ),
        ]
        for path, old, new in edits:
            with open(path, encoding="utf-8", errors="surrogateescape") as f:
                content = f.read()
            if old not in content:
                if "headless OHOS" in content or new.split("#")[0].strip() in content:
                    self.output.info(
                        "headless patch already applied: {}".format(path)
                    )
                    continue
                raise ConanException(
                    "headless patch anchor not found in {}: {!r}".format(path, old)
                )
            content = content.replace(old, new, 1)
            with open(path, "w", encoding="utf-8", errors="surrogateescape",
                      newline="") as f:
                f.write(content)
            self.output.info(
                "headless patch applied to {}".format(os.path.basename(path))
            )

    def _sign_binary(self, path):
        if self.settings.os != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; native OHOS execution may "
                "require post-build signing"
            )
            return
        signed = path + ".signed"
        self.run(
            '"{}" sign -inFile "{}" -outFile "{}" '
            "-selfSign 1 -signAlg SHA256withECDSA".format(signer, path, signed)
        )
        if not os.path.isfile(signed):
            raise ConanException("binary-sign-tool did not create {}".format(signed))
        os.replace(signed, path)
        os.chmod(path, 0o755)

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    def generate(self):
        # Produces conanbuild.sh (CC/CFLAGS/CPPFLAGS/LDFLAGS from the OHOS
        # profile). Without this the build steps run with an empty toolchain
        # environment and configure falls back to `cc` (r3 root cause).
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        self._apply_source_patches()
        conf_dir = self._conf_dir()
        self._patch_config_guess(conf_dir)
        self._patch_configure_umask(conf_dir)
        self._patch_makefile_hardlink(conf_dir)
        self._patch_makefile_setup_shell(conf_dir)
        self._patch_init_headless(conf_dir)

        if not can_run(self):
            raise ConanInvalidConfiguration(
                "xlispstat's build must run the freshly compiled xlisp "
                "interpreter natively (it compiles src/lsp/*.lsp to .fsl and "
                "dumps xlisp.wks); cross-compilation without a runnable "
                "target is not supported. Build on the HarmonyOS device via "
                "shadow CI."
            )

        # Old autoconf Makefiles ignore the environment CFLAGS; UCFLAGS is
        # the upstream hook. --without-x selects the GNUPLOT (terminal)
        # graphics system so nothing links against X11. Upstream does not
        # support parallel builds (-jN), keep -j1.
        # ULDFLAGS: with GCC=yes (clang defines __GNUC__), the *linux*
        # configure branch appends "-export-dynamic", which the OHOS
        # clang driver may not accept; override with the portable ld form.
        # Each step is written as a script file (LF, written by Python) so
        # the $CFLAGS expansions go through exactly one shell layer; nested
        # sh -c quoting on the device split UCFLAGS (r3 evidence).
        picked = self._shell()

        def write_step(name, body):
            # E002: /tmp is a read-only erofs on some OHOS devices (r11 on
            # device 134); mksh and autoconf need a writable TMPDIR. Prepend
            # a build-tree temp dir to every step script.
            prologue = (
                'TMPDIR="$PWD/_xls_tmp"\n'
                'export TMPDIR\n'
                'mkdir -p "$TMPDIR"\n'
                # r14/r16: the xlisp GC's mark phase recurses per cons cell;
                # the device default stack is too small and loading the
                # statistics runtime segfaults (Signal 11). 10/10 clean with
                # a raised limit.
                'ulimit -s unlimited 2>/dev/null || '
                'ulimit -s 65536 2>/dev/null || true\n'
            )
            body = body.replace("#!/bin/sh\nset -e\n",
                                "#!/bin/sh\nset -e\n" + prologue, 1)
            path = os.path.join(conf_dir, name)
            with open(path, "w", encoding="ascii", newline="\n") as f:
                f.write(body)
            return "sh {}".format(name)

        # E386: conanbuild.sh re-exports CONFIG_SHELL/SHELL pointing at the
        # hnp bash; reassert the capability-tested shell after it is sourced
        # so autoconf's re-exec does not fall back to a shell that cannot
        # getcwd in HMDFS.
        configure_script = (
            "#!/bin/sh\n"
            "set -e\n"
            # E087: some HMDFS mounts reject direct exec of ./configure
            # (r10 on device 134: "exec ./configure: Permission denied");
            # explicit interpreter invocation works on both devices.
            "exec env CONFIG_SHELL='{s}' SHELL='{s}' "
            '{s} ./configure --prefix=/ --without-x UCFLAGS="$CFLAGS -O1 -fno-strict-aliasing"\n'
        ).format(s=picked)
        self._run_shell(
            write_step("xls-configure.sh", configure_script),
            cwd=conf_dir,
            env="conanbuild",
        )

        # 1) Interpreter only; the lsp-compile step inside the default top
        #    target needs to execute ./xlisp, which must be signed first on
        #    OHOS (HMDFS requires signed/flagged ELFs for exec).
        make_step = (
            "#!/bin/sh\n"
            "set -e\n"
            'exec make -j1 {target} UCFLAGS="$CFLAGS -O1 -fno-strict-aliasing" '
            'ULDFLAGS="-Wl,--export-dynamic"\n'
        )
        self._run_shell(
            write_step("xls-make-xlisp.sh", make_step.format(target="xlisp")),
            cwd=conf_dir,
            env="conanbuild",
        )
        xlisp_path = os.path.join(conf_dir, "xlisp")
        if not os.path.isfile(xlisp_path):
            raise ConanException("xlisp interpreter was not built")
        self._sign_binary(xlisp_path)

        # 2) Default workspace: compiles src/lsp/*.lsp -> .fsl and saves
        #    xlisp.wks (executes the interpreter many times).
        self._run_shell(
            write_step("xls-make-wks.sh", make_step.format(target="xlisp.wks")),
            cwd=conf_dir,
            env="conanbuild",
        )
        if not os.path.isfile(os.path.join(conf_dir, "xlisp.wks")):
            raise ConanException("xlisp.wks default workspace was not generated")

        # 3) Wrapper script bin entry point.
        self._run_shell(
            write_step("xls-make-wrapper.sh", make_step.format(target="xlispstat")),
            cwd=conf_dir,
            env="conanbuild",
        )
        if not os.path.isfile(os.path.join(conf_dir, "xlispstat")):
            raise ConanException("xlispstat wrapper was not generated")

        self._run_upstream_tests(conf_dir)

    def _run_upstream_tests(self, conf_dir):
        # Upstream has no `make check`. Documented upstream procedure
        # (tests/README, also used by Guix): run ./xlisp from the source top
        # dir and load tests/test. Upstream test files are silent on success
        # and print "test failed in <file> at check <n>" on failure, so the
        # totals would stay invisible. We therefore use a recipe-owned
        # runner (xls-test-runner.lsp, written by build(), not shipped
        # upstream) that replicates tests/test.lsp verbatim (same
        # *test-files* list, same check/loop code) and additionally echoes
        # the executed check count per file. Upstream test files themselves
        # are unmodified.
        runner = os.path.join(conf_dir, "xls-test-runner.lsp")
        files_lisp = " ".join('"{}"'.format(name) for name in self._test_files)
        with open(runner, "w", encoding="ascii") as f:
            f.write(
                "(setf *test-files* (list {files}))\n"
                '(setf *testdir* "tests/")\n'
                "(defun check (f a b)\n"
                "  (flet ((as-list (x)\n"
                "           (if (compound-data-p x) "
                "(coerce (element-seq x) 'list) (list x))))\n"
                "    (let ((res (as-list (map-elements f a b))))\n"
                "      (if (member nil res)\n"
                "          (format t \"test failed in ~s at check ~d~%\"\n"
                "                  *current-test-file* count))))\n"
                "  (setf count (+ count 1)))\n"
                "(dolist (f *test-files*)\n"
                "  (progv '(*current-test-file* count) (list f 1)\n"
                "    (load (merge-pathnames f *testdir*))\n"
                '    (format t "[xls-test] ~a checks=~d~%" f (- count 1))))\n'
                "(exit)\n".format(files=files_lisp)
            )

        output_path = os.path.join(
            self.build_folder, "xlispstat-upstream-test.out"
        )
        command = './xlisp xls-test-runner.lsp > "{}"'.format(output_path)
        self._run_shell(command, cwd=conf_dir)

        with open(output_path, encoding="utf-8", errors="replace") as f:
            actual = f.read()
        failures = re.findall(r"test failed in (.+?) at cke?ck (\d+)", actual)
        if failures:
            raise ConanException(
                "upstream test suite reported {} failure(s): {}".format(
                    len(failures), failures[:10]
                )
            )
        done = re.findall(r"\[xls-test\] (\S+) checks=(\d+)", actual)
        done_files = [name for name, _ in done]
        missing = [n for n in self._test_files if n not in done_files]
        if missing:
            raise ConanException(
                "upstream test output lacks evidence for test file(s): {} "
                "(output tail: {!r})".format(missing, actual[-400:])
            )
        total = sum(int(n) for _, n in done)
        self.output.info(
            "upstream tests: {}/{} files, {} checks executed, 0 failed".format(
                len(done), len(self._test_files), total
            )
        )

    # ------------------------------------------------------------------
    # package
    # ------------------------------------------------------------------

    def package(self):
        conf_dir = self._conf_dir()
        lib_dir = os.path.join(self.package_folder, "share", "xlispstat")
        copy(self, "xlispstat", src=conf_dir, dst=os.path.join(self.package_folder, "bin"))
        for name in ("xlisp", "xlisp.wks", "xlisp.hlp"):
            copy(self, name, src=conf_dir, dst=lib_dir)
        for sub in ("Autoload", "Data", "Examples"):
            copy(
                self,
                "*",
                src=os.path.join(conf_dir, sub),
                dst=os.path.join(lib_dir, sub),
                keep_path=False,
            )
        copy(self, "COPYING", src=conf_dir, dst=os.path.join(self.package_folder, "licenses"))
        copy(
            self,
            "README",
            src=conf_dir,
            dst=os.path.join(self.package_folder, "share", "doc", "xlispstat"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        runtime_dir = os.path.join(self.package_folder, "share", "xlispstat")
        # The patched wrapper prefers an inherited XLISPLIB over its baked
        # /lib/xlispstat path, so the package stays relocatable.
        self.runenv_info.define("XLISPLIB", runtime_dir)


