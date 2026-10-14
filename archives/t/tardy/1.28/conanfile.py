#!/usr/bin/env python3
"""Conan recipe for tardy 1.28 — tar archive post-processor.

tardy (Peter Miller) manipulates tar file headers (prefix, clean, format
conversion).  C++ with a generated configure script shipped in the upstream
tarball — no autoreconf bootstrap needed (unlike zvbi).  Three external
library dependencies: bzip2 (hard probe for BZ2_bzopen), xz (hard
probe for lzma), both already published in the ohpcd registry
(bzip2/1.0.8 and xz/5.6.2, the fleet-wide consensus versions) and
referenced directly, plus boost (hard `#include <boost/shared_ptr.hpp>`
in five libtardy headers — header-only use, no boost library linked)
and libexplain (hard `#include <libexplain/...>` in 29 sources).

OHOS machinery (same proven set as this archive's zvbi/rnnoise ports):

* **Compilers pinned from the profile** (R33: conanautotoolstoolchain.sh is
  sourced only by conan's own Autotools() helper, never by a raw
  subprocess).
* **Shell**: `/data/service/hnp/bin/bash` (generated configure contains
  `exec 7<&0`, rejected by toybox sh).
* **umask 077 -> 022** in the generated configure (hmdfs traversal, same
  device-verified workaround as ncrack/libcaca/libabw/zvbi).
* **In-tree build**: source copied into the build folder before configuring.
* **Install only the binary** (`make install-bin`): `install-doc` needs
  GROFF+ps2pdf (PDF manuals, unavailable on the device/CI) and `install-man`
  needs the same roff toolchain.  Documented as降级边界 in notes.md.
* **`make check`: the 56 upstream shell tests (aegis `sure` harness, R51/L1)
  ARE run in build()** against the just-built bin/tardy.  `make -o all check`
  skips the PDF-only `all-doc` prerequisite.  The platform's tar/cpio are
  toybox and lack GNU semantics; GNU-compatible tar/cpio front-ends ship at
  test/ (patches 0004/0005) and are prepended to PATH.  See notes.md and
  test_package/MANIFEST.yml for the accounting.
"""

import hashlib
import os
import shlex
import ssl
import subprocess
import time
import urllib.request
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, unzip)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")


class TardyConan(ConanFile):
    name = "tardy"
    version = "1.28"
    description = "Tar archive post-processor (header manipulation, format conversion)"
    license = "GPL-3.0-or-later"
    homepage = "https://tardy.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # Hard configure requirement (BZ2_bzopen probe fails without it).
        # Already published in the ohpcd registry — direct reference,
        # no import needed (§3.7 "依赖已发布" row).
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        # 依赖已发布：libexplain 1.4.d001 于 2026-09-29 06:40 合入 main
        # (f23d8e705)，制品仓 07:03 发布 revision 1877eab4（含 OHOS/armv8
        # Release clang15 二进制）。tardy 29 个源文件硬 #include <libexplain/>，
        # 无开关可关，故此处直接 requires。
        self.requires("libexplain/1.4.d001")
        # Hard source requirement: libtardy/file/input.h, file/output.h,
        # filenamelist.h, tar/input.h and tar/output.h all
        # `#include <boost/shared_ptr.hpp>` (5 headers, 12 boost::shared_ptr
        # uses).  No HAVE_ switch, no --without option.  shared_ptr is
        # header-only, so no boost library is linked — the headers are the
        # whole dependency.
        self.requires("boost/1.84.0")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tardy is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack the official SourceForge release tarball.

        Explicit download rather than conan's get()/download(): the CA trust
        store is resolved from conan's own certifi or $CONAN_HOME/cacert.pem
        with a hard failure when neither exists, and a failing download
        reports its URL and HTTP status instead of a FileNotFoundError
        naming the destination.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "tardy-source.tar.gz")
        self._fetch(source["url"], archive, source["sha256"])
        unzip(self, str(archive), destination=self.source_folder,
              strip_root=True)
        archive.unlink()

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._configure_args())
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._build_ohos()
        else:
            autotools = Autotools(self)
            autotools.configure()
            # install-doc/install-man build a PDF manual and need groff's
            # PDF backend, which neither the device nor CI workers carry
            # (Error 127 on etc/BUILDING.pdf).  Install the binary only and
            # declare the dropped manuals in notes.md (same degradation
            # boundary as tarlz/wavegain).
            autotools.make(args=["install-bin"])

    def package(self):
        if str(self.settings.os) == "OHOS":
            self._package_ohos()
        else:
            Autotools(self).install(args=["install-bin"])
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            # Same triplet convention as the merged rnnoise/zvbi recipes:
            # the shipped config.sub (autoconf 2.68 era) is not guaranteed
            # to know "ohos"; aarch64-unknown-linux-gnu is accepted.
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--disable-dependency-tracking",
        ]

    # ── OHOS build machinery ────────────────────────────────────────────

    def _build_ohos(self):
        shell = self._resolve_shell()
        copy(self, "*", src=self.source_folder, dst=self.build_folder)
        self._restore_script_modes()
        self._relax_umask_in_configure()
        with self._build_environment().vars(self).apply():
            self._run_ohos(
                f"{shlex.quote(shell)} ./configure "
                f"{' '.join(shlex.quote(a) for a in self._configure_args())}"
            )
            # The default `all` target also builds etc/BUILDING.pdf via
            # `ps2pdf` (Error 127: no ghostscript on this platform).  Build the
            # library and the tardy binary by their own targets and leave the
            # PDF manual out; notes.md declares the dropped documentation.
            self._run_ohos("make -j1 libtardy/libtardy.a")
            self._run_ohos("make -j1 bin/tardy")
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream test/00 suite (R51/L1) against the built tardy.

        All 56 cases are aggregated by the `sure` target (aegis harness) and
        exercise bin/tardy.  Four platform details are handled here rather
        than by editing the tests:

        * `make -o all check` — `check: sure` aggregates the 56 tests.  Every
          test target also depends on `all`, which builds the PDF manuals
          (ps2pdf, absent here); `-o all` treats it as up to date so only the
          tests run.
        * `bin/test_prelude` — the harness sourced by every test (`all-bin`).
        * `test/tar` + `test/cpio` — GNU-compatible front-ends (patches
          0004/0005) because the platform's toybox tar/cpio lack append,
          crc/odc and GNU `tvf` formatting.  Prepend them to PATH.
        * `umask 022` — the hmdfs filesystem ignores chmod, so the test tar
          front-end synthesises the standard creation modes (0755/0644).
        TMPDIR is exported by _build_environment (/tmp is read-only here).
        """
        build = shlex.quote(self.build_folder)
        self.output.info("running upstream test/00 suite: make -o all check "
                         "(56 cases, aegis sure harness)")
        self._run_ohos(
            "chmod +x test/tar test/cpio && "
            "make -j1 bin/test_prelude && "
            "umask 022 && "
            f'PATH="{build}/test:{build}/bin:$PATH" make -o all check'
        )

    def _restore_script_modes(self):
        """Make the autotools helper scripts executable again (E490)."""
        candidates = [
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "depcomp", "compile", "ltmain.sh", "config.status",
            "ar-lib", "mkinstalldirs", "test-driver",
        ]
        for relative in candidates:
            path = Path(self.build_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)
        for helper in Path(self.build_folder, "build-aux").glob("*"):
            if helper.is_file():
                helper.chmod(helper.stat().st_mode | 0o111)

    def _relax_umask_in_configure(self):
        """Rewrite `umask 077` -> `umask 022` in the generated configure.

        Device-verified (ncrack, libcaca, libcdaudio, libabw, zvbi): the
        scratch dir is created with `umask 077` giving mode 2700, and hmdfs
        decides traversal on the group bits where `chmod` is a no-op, so
        the directory is untraversable (EACCES on everything inside it).
        022 yields `drwxr-s--x`.
        """
        path = Path(self.build_folder, "configure")
        if not path.is_file():
            raise ConanException(f"configure script is missing: {path}")
        content = path.read_text(encoding="utf-8")
        count = content.count("umask 077")
        self.output.info(f"umask 077 occurrences in configure: {count}")
        if count == 0:
            raise ConanException(
                "umask contract changed in configure: no 'umask 077' found, "
                "hmdfs workaround has nothing to rewrite"
            )
        path.write_text(content.replace("umask 077", "umask 022"),
                        encoding="utf-8", newline="\n")

    def _package_ohos(self):
        shell = self._resolve_shell()
        with self._build_environment().vars(self).apply():
            destination = shlex.quote(self.package_folder)
            # install-bin only: install-doc/install-man need GROFF+ps2pdf
            # (PDF manuals), unavailable on the device/CI fleet.
            self._run_ohos(f"make -j1 install-bin DESTDIR={destination}")

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        # Raw subprocess never sees conan's dependency flags, so expose
        # the direct host dependencies' headers/libraries explicitly
        # (configure probes -lbz2 itself; it only needs -I/-L to find it).
        cppflags, ldflags, libs, defines = [], [], [], []
        for dep in self.dependencies.values():
            info = dep.cpp_info
            cppflags.extend(f"-I{d}" for d in info.includedirs)
            ldflags.extend(f"-L{d}" for d in info.libdirs)
            libs.extend(f"-l{name}" for name in info.libs)
            # Component-ized dependencies (boost/1.84.0 exports 7 components)
            # carry their include dir and their platform defines on the
            # component, not on the aggregate cpp_info.  boost_headers holds
            # both the include dir and BOOST_SP_NO_PTHREAD_SETCANCELSTATE —
            # that define is what keeps OHOS's musl (no
            # pthread_setcancelstate) out of boost/core/detail/
            # sp_thread_sleep.hpp.  Device-verified: a raw compile against
            # <boost/shared_ptr.hpp> with the aggregate flags alone fails
            # with "use of undeclared identifier 'pthread_setcancelstate'".
            #
            # Only headers and defines are taken from components, never their
            # libs: tardy uses boost::shared_ptr, which is header-only.  Its
            # sibling components (filesystem/regex/program_options/iostreams)
            # are compiled archives that tardy never calls, and linking them
            # in would make the binary depend on boost .a files for nothing.
            for component in info.components.values():
                cppflags.extend(f"-I{d}" for d in component.includedirs)
                defines.extend(component.defines)
        # libexplain ships libexplain.a only (its recipe deliberately drops
        # the .so — this platform's loader refuses shared resolution for it),
        # and the archive's cap_* symbols are undefined.  configure's
        # AC_CHECK_LIB(explain,...) probe links standalone, so it needs those
        # transitive archives on the line: walk the full dependency graph.
        for dep in self._conan_dependencies.values():
            for name in dep.cpp_info.libs:
                if f"-l{name}" not in libs:
                    libs.append(f"-l{name}")
        if defines:
            environment.append("CPPFLAGS",
                               " ".join(cppflags + [f"-D{d}" for d in defines]))
        elif cppflags:
            environment.append("CPPFLAGS", " ".join(cppflags))
        if ldflags:
            environment.append("LDFLAGS", " ".join(ldflags))
        if libs:
            environment.append("LIBS", " ".join(libs))
        # No LD_LIBRARY_PATH here, on purpose (see libabw recipe: the SDK's
        # lld resolves libraries from LD_LIBRARY_PATH before its own rpath
        # and this recipe's consumers run under conan's conanrun env).
        for name, value in self._compiler_environment_items().items():
            environment.define(name, value)
        return environment

    def _compiler_environment_items(self):
        """CC/CXX from the profile's tools.build:compiler_executables.

        The toolchain script holding them is sourced only by conan's own
        Autotools() helper, so a raw subprocess must be given them directly
        (R33: the toolchain comes from a declared source, not from PATH).
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if not compilers:
            return {}
        if isinstance(compilers, str):
            import json
            try:
                compilers = json.loads(compilers)
            except ValueError:
                return {}
        mapping = {"c": "CC", "cpp": "CXX"}
        return {variable: compilers[key]
                for key, variable in mapping.items() if compilers.get(key)}

    def _resolve_shell(self):
        for candidate in OHOS_SHELL_CANDIDATES:
            if os.path.sep in candidate:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
                continue
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                path = os.path.join(directory, candidate)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
        raise ConanInvalidConfiguration(
            "no suitable shell found on OHOS (need the hnp bash or zsh; "
            "zsh cannot run automake's recursive make)"
        )

    def _run_ohos(self, command, cwd=None):
        shell = self._resolve_shell()
        environment = dict(os.environ)
        environment["SHELL"] = shell
        environment["CONFIG_SHELL"] = shell
        completed = subprocess.run(
            command + " < /dev/null", shell=True, env=environment,
            cwd=cwd or self.build_folder, stdin=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            self._dump_failure_diagnostics(cwd or self.build_folder,
                                           environment)
            raise ConanException(
                f"OHOS build step failed (rc={completed.returncode}): {command}"
            )

    def _dump_failure_diagnostics(self, directory, environment):
        """Evidence for a failed step, printed into the captured build log.

        A CI worker's log is the only observation point this recipe gets on
        that fleet and it is truncated to the last 4000 characters, so the
        output stays deliberately compact (OP-8).
        """
        self.output.info("---- ohos diagnostics: environment ----")
        for name in ("CC", "CXX", "CPPFLAGS", "LDFLAGS", "LIBS", "CFLAGS",
                     "TMPDIR"):
            if name in environment:
                self.output.info(f"{name}={environment[name]}")
        config_log = Path(directory, "config.log")
        if not config_log.is_file():
            self.output.info("no config.log in the failing directory")
            return
        text = config_log.read_text(errors="replace")
        marker = "checking whether the C compiler works"
        start = text.rfind(marker)
        window = text[start:] if start != -1 else text[-2000:]
        self.output.info("---- config.log: last compiler-test block ----")
        for line in window.splitlines()[:14]:
            self.output.info(line)

    # ── download helpers ────────────────────────────────────────────────

    def _ca_bundle(self):
        candidates = []
        try:
            import certifi
            candidates.append(certifi.where())
        except ImportError:
            pass
        conan_home = os.getenv("CONAN_HOME") or os.path.join(
            os.path.expanduser("~"), ".conan2")
        candidates.append(os.path.join(conan_home, "cacert.pem"))
        candidates.append(os.getenv("SSL_CERT_FILE") or "")
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "no CA bundle found for the source download: looked for certifi's "
            "cacert, $CONAN_HOME/cacert.pem and $SSL_CERT_FILE"
        )

    def _fetch(self, url, destination, sha256, attempts=3):
        destination = Path(destination)
        staging = destination.with_name(destination.name + ".part")
        if url.startswith("file:"):
            from urllib.parse import urlparse
            from urllib.request import url2pathname
            import shutil
            shutil.copyfile(url2pathname(urlparse(url).path), staging)
        else:
            context = ssl.create_default_context(cafile=self._ca_bundle())
            last = None
            for attempt in range(1, attempts + 1):
                try:
                    request = urllib.request.Request(
                        url, headers={"User-Agent": "conan"})
                    with urllib.request.urlopen(request, timeout=120,
                                                context=context) as response:
                        payload = response.read()
                        status = response.status
                    staging.write_bytes(payload)
                    self.output.info(
                        f"downloaded {len(payload)} bytes (HTTP {status}) "
                        f"from {url}")
                    break
                except Exception as error:  # noqa: BLE001 - reported verbatim
                    last = error
                    self.output.warning(
                        f"download attempt {attempt}/{attempts} failed for "
                        f"{url}: {type(error).__name__}: {error}")
                    if staging.exists():
                        staging.unlink()
                    if attempt < attempts:
                        time.sleep(5)
            else:
                raise ConanException(f"could not download {url}: {last}")

        digest = hashlib.sha256(staging.read_bytes()).hexdigest()
        if digest != sha256:
            staging.unlink()
            raise ConanException(
                f"sha256 mismatch for {url}: expected {sha256}, got {digest}")
        os.replace(staging, destination)
