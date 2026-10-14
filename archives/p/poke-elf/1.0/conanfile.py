#!/usr/bin/env python3
"""Conan recipe for poke-elf 1.0 -- GNU poke pickle for ELF files.

Installs the ELF pickles (elf.pk and friends) to share/poke/pickles,
the prebuilt info manual, and the prelinkr example utility to bin/.

OHOS adaptation notes (see also notes.md):
  * patches/0001: umask 077 -> 022 in configure so config.status can
    write its temp files on HMDFS (E011, same as the poke/5.0 recipe).
  * makeinfo is not available on OHOS: the tarball ships the prebuilt
    poke-elf.info and the recipe pins its timestamps after configure
    so make never tries to regenerate it; MAKEINFO=true is additionally
    passed to make as a command-line override (poke/5.0 precedent).
  * Upstream tests (make check, single TAP test test-elf.pk) require an
    installed poke >= 4.0 with pktest.pk; the recipe requires poke/5.0
    and puts its bin/ on PATH for configure and make check.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _pick_shell():
    """Return a shell executable that exists on this machine.

    ci/conan/profiles/ohos-aarch64 pins SHELL/CONFIG_SHELL to
    /data/service/hnp/bin/bash (present on CI workers, absent on the
    HMBS true device where only /bin/sh is guaranteed). Autoconf's
    configure re-execs $CONFIG_SHELL early (line ~139); a stale absolute
    path aborts with 127 "inaccessible or not found". Probe the
    environment first, then well-known fallbacks. The full-featured
    bash is preferred when present (CI workers: matches the profile
    and the proven poke/5.0 build; avoids the minimal /system/bin/sh
    under load) and /bin/sh remains the fallback for the HMBS device.
    """
    candidates = [
        "/data/service/hnp/bin/bash",
        os.environ.get("SHELL"),
        os.environ.get("CONFIG_SHELL"),
        "/bin/sh",
        "/system/bin/sh",
    ]
    for cand in candidates:
        if cand and os.path.exists(cand):
            return cand
    return "sh"


def _automake_count(text, label):
    """Parse `# LABEL: N` from an automake parallel-tests test-suite.log."""
    for line in text.splitlines():
        if line.startswith("# " + label + ":"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


class PokeElfConan(ConanFile):
    name = "poke-elf"
    version = "1.0"
    description = "GNU poke pickle for editing ELF object files, executables, shared libraries and core dumps"
    license = "GPL-3.0-or-later"
    homepage = "https://www.jemarch.net/poke-elf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("poke/5.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                "poke-elf is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        tc.generate()
        # Override the profile's stale SHELL/CONFIG_SHELL
        # (/data/service/hnp/bin/bash exists on CI workers but not on the
        # HMBS true device) inside the aggregated conanbuild env. A recipe
        # Environment saved here takes precedence over profile [buildenv];
        # the previous attempt using only vars(self).apply() in build()
        # failed because the aggregation is re-applied on top of os.environ
        # (2nd preflight still re-execed the stale path, line 140).
        shell = _pick_shell()
        shell_env = Environment()
        shell_env.define("SHELL", shell)
        shell_env.define("CONFIG_SHELL", shell)
        shell_env.vars(self, scope="build").save_sh("conanbuild_shell")

    def _fs_env(self):
        """HMDFS workarounds: PWD for getcwd() denial, writable TMPDIR,
        plus a valid SHELL/CONFIG_SHELL for autoconf re-exec."""
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("PWD", self.build_folder)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        shell = _pick_shell()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        return env

    _DOC_STAMPS = [
        "stamp-vti",
    ]
    _DOC_VERSIONS = [
        "version.texi",
    ]
    _DOC_OUTPUTS = [
        "poke-elf.info",
    ]

    def _pin_prebuilt_docs(self):
        for rel in (self._DOC_STAMPS + self._DOC_VERSIONS
                    + self._DOC_OUTPUTS):
            path = os.path.join(self.source_folder, rel)
            if os.path.isfile(path):
                os.utime(path, None)

    def _poke_runtime_env(self, poke_folder):
        """poke needs its relocated datadir at configure/make-check time.

        poke was built with --prefix=/, so without relocation it looks for
        //share/poke/pkl-rt.pk, crashes (Signal 6) and configure records
        version "unknown" + RUN_TESTS=no (3rd preflight: discovered 0).
        Same variables the poke test_package uses (POKEDATADIR is the master
        switch; POKEPICKLESDIR is NOT derived from it and must be explicit).
        """
        poke_data = os.path.join(poke_folder, "share", "poke")
        env = Environment()
        env.define("POKEDATADIR", poke_data)
        env.define("POKECONFIGDIR", poke_data)
        env.define("POKEPICKLESDIR", os.path.join(poke_data, "pickles"))
        env.define("POKEFMTAPPDIR", os.path.join(poke_data, "pokefmt"))
        return env

    def _write_install_shim(self):
        # HMBS install shim (runtime/<task>/bin/install, install_shim:true)
        # only accepts single-file two-arg calls (`[ $# -eq 2 ] || exit 64`,
        # EX_USAGE); automake's install-dist_picklesDATA copies all 17
        # pickles in one `$(INSTALL_DATA) files... dir/` call -> Error 64
        # (3rd preflight; xeyes/libICE + adms 2.3.7 E182/E188 precedent).
        # Write a cp/mkdir shim; chmod is best-effort (HMFS chmod cap is 0).
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        # HMFS grants permissions from open mode (libfstconst precedent);
        # create with 0o755 directly so no chmod is needed to execute it.
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
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
                    "if [ \"$count\" -gt 1 ]; then mkdir -p \"$dest\"; fi\n"
                    "mkdir -p \"$(dirname \"$dest\")\"\n"
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
            os.close(fd)
            raise
        os.chmod(install, 0o755)
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the probed install path into every generated
        # Makefile's INSTALL variable; point it at the shim so that
        # INSTALL_DATA/INSTALL_PROGRAM (which reference ${INSTALL}) all
        # go through cp/mkdir (adms 2.3.7 precedent). Idempotent.
        for root, _, files in os.walk(self.build_folder):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append(f"{indent}INSTALL = {shim_install}\n")
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8") as f:
                        f.write("".join(lines))

    def build(self):
        apply_conandata_patches(self)
        poke = self.dependencies["poke"]
        poke_bin = os.path.join(poke.package_folder, "bin")
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = poke_bin + os.pathsep + old_path
        try:
            autotools = Autotools(self)
            with self._fs_env().vars(self).apply():
                with self._poke_runtime_env(poke.package_folder).vars(self).apply():
                    # Immune to conanbuild aggregation order: prefix the shell
                    # assignments inline so the configure re-exec (line ~134
                    # `exec $CONFIG_SHELL ...`) can never see the stale profile
                    # value, regardless of which env layer wins.
                    shell = _pick_shell()
                    os.environ["SHELL"] = shell
                    os.environ["CONFIG_SHELL"] = shell
                    configure = os.path.join(
                        self.source_folder, "configure").replace("\\", "/")
                    self.run(
                        'CONFIG_SHELL="{}" SHELL="{}" "{}" --prefix=/ '
                        "'--bindir=${{prefix}}/bin' '--sbindir=${{prefix}}/bin' "
                        "'--libdir=${{prefix}}/lib' "
                        "'--includedir=${{prefix}}/include' "
                        "'--oldincludedir=${{prefix}}/include'".format(
                            shell, shell, configure))
                    self._pin_prebuilt_docs()
                    if str(self.settings.os) == "OHOS":
                        self._redirect_install_to_shim(self._write_install_shim())
                    autotools.make(args=["-j1", "MAKEINFO=true"])
                    autotools.make(target="check", args=["-j1"])
        finally:
            os.environ["PATH"] = old_path
        self._emit_upstream_test_result()

    def _emit_upstream_test_result(self):
        """Emit the hmbs upstream-test gate marker from automake's real
        test-suite.log counts (parallel-tests TAP harness output)."""
        suite_logs = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "test-suite.log" in files:
                suite_logs.append(os.path.join(root, "test-suite.log"))
        if not suite_logs:
            raise ConanException(
                "make check produced no test-suite.log under "
                + self.build_folder)
        with open(suite_logs[0], "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        passed = _automake_count(content, "PASS")
        xfailed = _automake_count(content, "XFAIL")
        skipped = _automake_count(content, "SKIP")
        failed = (_automake_count(content, "FAIL")
                  + _automake_count(content, "XPASS")
                  + _automake_count(content, "ERROR"))
        total = _automake_count(content, "TOTAL")
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "automake-tap",
            "command": "make check",
            "discovered": total,
            "executed": total - skipped,
            "passed": passed + xfailed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            self.output.error(
                "upstream make check did not pass: " + json.dumps(result))

    def package(self):
        autotools = Autotools(self)
        with self._fs_env().vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._redirect_install_to_shim(self._write_install_shim())
            autotools.install(args=["MAKEINFO=true"])
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
