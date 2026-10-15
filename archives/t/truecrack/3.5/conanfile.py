#!/usr/bin/env python3
"""Conan recipe for truecrack 3.5 — TrueCrypt volume password cracker (CLI, autotools).

Build: configure --enable-cpu && make && make install-exec. truecrack's upstream
default build path targets NVIDIA CUDA (nvcc, .cu kernels); HarmonyOS PC has no
NVIDIA GPU, so the recipe forces the pure-C CPU backend via --enable-cpu, which
compiles with the platform C compiler (clang 15) and links only against libm.

The shipped Makefile.am / Makefile.in are hand-rolled and build in-source from
the source root, so the recipe drives configure/make with cwd=source_folder
(same pattern as magicrescue/audioresamplerate). The 2011-era source relies on
the pre-GCC-10 `-fcommon` behaviour; the 0001 patch makes the header globals
real `extern` declarations so the modern clang default (-fno-common) links.

Upstream tests: the source ships 6 TrueCrypt example volumes in test/ (AES-XTS
with ripemd160/whirlpool/sha512 KDF, serpent/twofish ciphers, and a hidden
volume) documented by test/README example dictionary attacks. build() runs all
6 and verifies the expected password is recovered, emitting the HMBS hard-gate
marker from the deterministic per-case results.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class TruecrackConan(ConanFile):
    name = "truecrack"
    version = "3.5"
    description = "TrueCrack 3.5 — bruteforce password cracker for TrueCrypt volumes (CPU backend for HarmonyOS)"
    license = "GPL-3.0-or-later"
    homepage = "http://code.google.com/p/truecrack"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # The 6 upstream example volumes under test/ (documented in test/README).
    # Each is a TrueCrypt volume whose known password ("test", or "hidden" for
    # the hidden volume) must be recovered by the shipped dictionary attack.
    # tuple: (case_name, volume_filename, extra_args) where extra_args are
    # literal flag/value pairs (never file paths).
    _UPSTREAM_CASES = [
        ("ripemd160_aes", "ripemd160_aes.test.tc", []),
        ("whirlpool_aes", "whirlpool_aes.test.tc", ["-k", "whirlpool"]),
        ("sha512_aes", "sha512_aes.test.tc", ["-k", "sha512"]),
        ("ripemd160_serpent", "ripemd160_serpent.test.tc", ["-e", "serpent"]),
        ("ripemd160_twofish", "ripemd160_twofish.test.tc", ["-e", "twofish"]),
        ("hidden_volume", "hidden_ripemd160_aes.test.hidden.tc", ["-H"]),
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generates the conanbuild env (CC=/data/service/hnp/bin/clang etc.)
        # used by all self.run(..., env="conanbuild") invocations below.
        tc = AutotoolsToolchain(self)
        tc.generate()

        # R32: OHOS HMFS kernel paths — the build cwd and the inherited
        # TMPDIR are under HMFS where getcwd() can fail and config.guess's
        # temp probe directory may be read-only, so ./configure aborts with
        # "cannot guess build type" (dummy.c: Permission denied).  Pin a real
        # writable tmp dir and a POSIX shell for configure/make.
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.buildenv.define("TMPDIR", tmpdir)
        self.buildenv.define("TMP", tmpdir)
        self.buildenv.define("TEMP", tmpdir)
        self.buildenv.define("CONFIG_SHELL", "/bin/sh")
        self.buildenv.define("SHELL", "/bin/sh")

    def build(self):
        apply_conandata_patches(self)
        # OHOS HMFS fix (unsafe_local_mktemp): autoconf's AS_TMPDIR — written
        # verbatim into the generated config.status — does
        # `(umask 077 && mktemp -d "./confXXXXXX")` / `(umask 077 && mkdir)`,
        # creating an unwritable 0700 dir (HMFS UID mapping + setgid).  The dir
        # exists so `test -d` passes, then config.status dies writing subs1.awk:
        #   ./config.status: can't create ./confXXXXXX/subs1.awk: Permission denied
        #   config.status: error: could not setup config files machinery
        # Loosen the temp-dir umask to 022 (0755 dir → writable by owner on
        # HMFS), matching the knowledge-base E011/E129/E136 fix.  This happens
        # in configure (the template configure writes into config.status),
        # before configure is run.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022")
        # CPU-only build (no NVIDIA CUDA on HarmonyOS PC). Configure must run
        # from the source root because the hand-rolled Makefile compiles in-place.
        # The 2009-era bundled config.guess does not recognize HarmonyOS, so an
        # explicit GNU build/host triplet is required to bypass the
        # "cannot guess build type" failure (the Conan OHOS toolchain supplies
        # the actual target ABI, as in anubis).
        self.run(
            "./configure --enable-cpu --prefix=/ "
            "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu",
            cwd=self.source_folder, env="conanbuild")
        # R9: -j1
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the 6 upstream example-volume dictionary attacks and emit the
        HMBS_UPSTREAM_TEST_RESULT hard-gate marker. Each case runs the built
        truecrack binary against a shipped test/ volume and succeeds only when
        the documented password is actually recovered; counts come from the
        deterministic PASS/FAIL lines the runner itself prints per executed case.
        """
        src = self.source_folder
        tc_bin = os.path.join(src, "src", "truecrack")
        testdir = os.path.join(src, "test")
        if not os.path.isfile(tc_bin):
            raise RuntimeError(f"truecrack binary not built: {tc_bin}")
        if not os.path.isdir(testdir):
            raise RuntimeError(f"upstream test/ dir missing: {testdir}")

        script = os.path.join(self.build_folder, "run_upstream_tests.sh")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nset -u\n")
            fh.write(f'TC={shlex.quote(tc_bin)}\n')
            fh.write(f'TD={shlex.quote(testdir)}\n')
            fh.write(
                'run_case() {\n'
                '  name="$1"; shift\n'
                '  if timeout 300 "$TC" "$@" 2>&1 | grep -aq "Found password:"; then\n'
                '    printf "HMBS_CASE PASS %s\\n" "$name"\n'
                '  else\n'
                '    printf "HMBS_CASE FAIL %s\\n" "$name"\n'
                '  fi\n'
                '}\n'
            )
            for name, volume, extra in self._UPSTREAM_CASES:
                args = f'-t "$TD/{volume}" -w "$TD/passwords.txt"'
                if extra:
                    args += " " + " ".join(shlex.quote(a) for a in extra)
                fh.write(f"run_case {name} {args}\n")
        os.chmod(script, 0o755)

        log_path = os.path.join(self.build_folder, "upstream_test.log")
        runner_cmd = f'"{script}" > "{log_path}" 2>&1'
        self.run(runner_cmd, env="conanbuild", ignore_errors=True)

        lines = []
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                lines = [ln.strip() for ln in fh.read().splitlines()]
        self.output.info("=== truecrack upstream tests (per case) ===")
        for ln in lines:
            self.output.info(ln)

        passed = sum(1 for ln in lines if ln.startswith("HMBS_CASE PASS"))
        failed = sum(1 for ln in lines if ln.startswith("HMBS_CASE FAIL"))
        discovered = len(self._UPSTREAM_CASES)
        executed = passed + failed
        if executed != discovered:
            raise RuntimeError(
                f"upstream test runner executed {executed} of {discovered} "
                f"cases (missing results in {log_path})"
            )
        status = "passed" if failed == 0 else "failed"
        result = {
            "status": status,
            "framework": "truecrack-example-volumes",
            "command": runner_cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(result, ensure_ascii=False))
        if status != "passed":
            raise RuntimeError(
                f"truecrack upstream tests failed: {passed}/{discovered} passed"
            )

    def package(self):
        # --prefix=/ so make install-exec with DESTDIR lands bin/truecrack in
        # package_root.  We use install-exec (not full "make install") because the
        # latter also runs install-dist_dataDATA / install-man which invoke
        # `install -c -m 644 cudalt.py autogen.sh truecrack.1`.  On OHOS HMFS,
        # chmod is unsupported (HMBS_CAP_CHMOD=0) so those steps fail with
        # `install: Error 64`; the CLI package only needs bin/truecrack anyway.
        self.run(f"make install-exec DESTDIR={self.package_folder}",
                 cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
