#!/usr/bin/env python3
"""Conan recipe for zvbi 0.2.44 — VBI capturing and decoding library.

zvbi (formerly libzvbi) decodes Vertical Blanking Interval data (teletext,
closed caption, VPS, WSS, XDS).  Build system is autotools, but the GitHub
tag archive ships only `configure.ac` — no generated `configure`.  The
generated tree is therefore bootstrapped on the build machine with
`autoreconf -fi` (rnnoise 0.1.1 precedent: automake/libtool via
tool_requires; recode 3.7.15 precedent: gettext macros via ACLOCAL_PATH and
AUTOPOINT=true to skip the autopoint version check — upstream already ships
its po/ infrastructure).

Dependency footprint (deliberately minimal):

* **iconv** — required by configure.ac (`AM_ICONV_LINK`, hard error when
  missing).  OHOS musl libc provides iconv; device-verified with a
  Latin-1 -> UTF-8 conversion probe before this recipe was written.
* **gettext/NLS** — `AM_GNU_GETTEXT([external])` degrades automatically:
  with no gettext runtime on the device the configure probe finds neither
  libc nor libintl gettext and switches NLS off (`USE_NLS=no`).  No
  --disable-nls switch exists upstream and none is needed.
* **libpng/zlib** — optional (PNG page export).  When neither library is
  present configure simply sets HAVE_PNG=no and the export layer skips
  PNG.  Not wired here to keep the dependency surface at zero.
* **X11, V4L, V4L2, DVB, bktr, vbi proxy** — capture/display back ends,
  all `--disable-*`-able and meaningless on a PC without VBI hardware;
  disabled.

OHOS machinery (carried over from this archive's libabw / rnnoise ports,
each item re-probed against this tarball first):

* **Compilers pinned from the profile.**  conan's AutotoolsToolchain writes
  `CC`/`CXX` into conanautotoolstoolchain.sh, but that script is sourced
  only by conan's own Autotools() helper; a raw subprocess never sees it
  (R33).  Left unset, configure falls back to a bare `clang` that cannot
  link OHOS executables on a CI worker.
* **Shell**: `/data/service/hnp/bin/bash`.  The generated configure
  contains `exec 7<&0`, which toybox `/system/bin/sh` rejects, and bash
  provides the POSIX IFS splitting automake's recursive make needs.
* **umask 077 -> 022** in the generated configure: its scratch directory
  is created with `umask 077` giving mode 2700, and hmdfs decides
  traversal on the group bits where `chmod` is a no-op, so the
  directory is untraversable (EACCES on everything inside it).  022
  yields `drwxr-s--x` (device-verified on ncrack, libcaca, libabw).
* **In-tree build**: the bootstrapped source tree is copied into the
  build folder before configuring, as in the other recipes in this archive.
* **`make check` is not run in build()**: kept for CI time-budget
  stability only.  Note the earlier rationale recorded in the first
  revision of this file (hardware entries / GCC-only pedantic flags) was
  *wrong*: on 2026-10-08 the full upstream suite was run on the device
  with this recipe's configure arguments except `--disable-tests`, and
  all 18 binaries/scripts (all 11 TESTS entries) PASS — the suites are
  data-driven and OHOS clang accepts every `-std=` variant.  See
  test_package/MANIFEST.yml for the R51 accounting and the evidence.
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


class ZvbiConan(ConanFile):
    name = "zvbi"
    version = "0.2.44"
    description = "VBI capturing and decoding library (teletext, closed caption, VPS, WSS, XDS)"
    license = ("LGPL-2.0-or-later", "GPL-2.0-only", "MIT")
    homepage = "https://github.com/zapping-vbi/zvbi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The GitHub tag tarball ships configure.ac/Makefile.am only, so the
        # build must bootstrap with autoreconf.  The sandbox only has the
        # autoconf family under /data/service/hnp/bin (no automake/libtool/
        # gettext), so pull them via tool_requires (rnnoise 0.1.1 + recode
        # 3.7.15 precedents, all published in the ohpcd artifact registry).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("gettext/0.22.5.1")
        self.tool_requires("m4/1.4.19")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"zvbi is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack the official GitHub release tarball.

        Explicit download rather than conan's get()/download(): the CA trust
        store is resolved from conan's own certifi or $CONAN_HOME/cacert.pem
        with a hard failure when neither exists (AGENTS.md §1.2), and a
        failing download reports its URL and HTTP status instead of a
        FileNotFoundError naming the destination.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "zvbi-source.tar.gz")
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
            autotools.make()

    def package(self):
        if str(self.settings.os) == "OHOS":
            self._package_ohos()
        else:
            Autotools(self).install()
        copy(self, "COPYING.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "zvbi")
        self.cpp_info.set_property("cmake_target_name", "zvbi::zvbi")
        # Upstream ships zvbi-0.2.pc; keep the same pkg-config name so
        # consumers detecting via pkg-config find this package (unique
        # across the archive — no other recipe emits zvbi-0.2.pc).
        self.cpp_info.set_property("pkg_config_name", "zvbi-0.2")
        self.cpp_info.libs = ["zvbi"]
        # libzvbi links -lm (its .pc carries Libs: -lzvbi -lm) and is
        # packaged as a static archive here, so consumers need the maths
        # library on the link line as well.
        self.cpp_info.system_libs = ["m"]

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            # Same triplet convention as the merged rnnoise recipe: the
            # device-regenerated config.sub is not guaranteed to know
            # "ohos", and aarch64-unknown-linux-gnu is accepted everywhere.
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            "--disable-dependency-tracking",
            # Capture/display back ends and their consumers: no VBI
            # hardware exists on the target; each has a clean off switch.
            "--disable-v4l",
            "--disable-dvb",
            "--disable-bktr",
            "--disable-proxy",
            "--without-x",
            "--without-doxygen",
            "--disable-tests",
            "--disable-examples",
        ]

    # ── OHOS build machinery ────────────────────────────────────────────

    def _build_ohos(self):
        self._bootstrap_autotools()
        shell = self._resolve_shell()
        copy(self, "*", src=self.source_folder, dst=self.build_folder)
        self._restore_script_modes()
        self._relax_umask_in_configure()
        with self._build_environment().vars(self).apply():
            self._run_ohos(
                f"{shlex.quote(shell)} ./configure "
                f"{' '.join(shlex.quote(a) for a in self._configure_args())}"
            )
            self._run_ohos("make -j1")

    def _bootstrap_autotools(self):
        """Generate configure/Makefile.in in the source tree (rnnoise +
        recode precedents): gettext m4 macros come from the gettext
        tool_require via ACLOCAL_PATH, and AUTOPOINT=true skips autopoint
        (upstream already ships its po/ infrastructure, and this dodges the
        AM_GNU_GETTEXT_VERSION 0.21 vs gettext 0.22 version complaint).
        """
        try:
            gettext_aclocal = os.path.join(
                self.dependencies.build["gettext"].package_folder,
                "share", "aclocal",
            )
        except KeyError:
            gettext_aclocal = None
        if gettext_aclocal and os.path.isdir(gettext_aclocal):
            existing = os.environ.get("ACLOCAL_PATH", "")
            os.environ["ACLOCAL_PATH"] = os.pathsep.join(
                path for path in (gettext_aclocal, existing) if path
            )
        about_nls = None
        try:
            about_nls = os.path.join(
                self.dependencies.build["gettext"].package_folder,
                "share", "gettext", "ABOUT-NLS",
            )
        except KeyError:
            pass
        if about_nls and os.path.isfile(about_nls):
            copy(self, "ABOUT-NLS", src=os.path.dirname(about_nls),
                 dst=self.source_folder)
        # NOTE: must go through self.run(env="conanbuild") rather than raw
        # subprocess: only conan's aggregate env carries the tool_requires
        # bin dirs (automake's aclocal, libtoolize, gettext) on PATH.
        # Device-verified: raw subprocess fails with `Can't exec "aclocal"`.
        self.run("AUTOPOINT=true autoreconf -fi < /dev/null",
                 cwd=self.source_folder, env="conanbuild")
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            raise ConanException(
                "autoreconf finished but produced no configure script"
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

        Device-verified (ncrack, libcaca, libcdaudio, libabw): the scratch
        dir is created with `umask 077` giving mode 2700, and hmdfs decides
        traversal on the group bits where `chmod` is a no-op, so the
        directory is untraversable (EACCES on everything inside it).  022
        yields `drwxr-s--x`.
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
            self._run_ohos(f"make -j1 install DESTDIR={destination}")

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
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
                     "TMPDIR", "ACLOCAL_PATH", "AUTOPOINT"):
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
        # CI 会把 conandata 的 url 改写成 [镜像, 官方] 列表形态（§5）——归一化再判定。
        candidates = list(url) if isinstance(url, list) else [url]
        if candidates and candidates[0].startswith("file:"):
            from urllib.parse import urlparse
            from urllib.request import url2pathname
            import shutil
            shutil.copyfile(url2pathname(urlparse(candidates[0]).path), staging)
        else:
            context = ssl.create_default_context(cafile=self._ca_bundle())
            last = None
            for attempt in range(1, attempts + 1):
                try:
                    request = urllib.request.Request(
                        candidates[0], headers={"User-Agent": "conan"})
                    with urllib.request.urlopen(request, timeout=120,
                                                context=context) as response:
                        payload = response.read()
                        status = response.status
                    staging.write_bytes(payload)
                    self.output.info(
                        f"downloaded {len(payload)} bytes (HTTP {status}) "
                        f"from {candidates[0]}")
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
