#!/usr/bin/env python3
"""Conan recipe for xlbiff 4.6.11 (X11 Athena mailbox notifier tool).

xlbiff watches a mail spool file and pops up an Athena widget window
showing the mailbox "from/subject" summary.  It is a pure X11 client:
libX11 + Xt + Xaw + Xmu + libXrandr, no other runtime dependencies.

Build notes (OHOS aarch64):

  * The GitHub tag tarball ships only configure.ac / Makefile.am (no
    pre-generated configure / Makefile.in), so build() bootstraps with
    aclocal -> autoconf -> autoheader -> automake --add-missing.
    automake comes from tool_requires(automake/1.18) because the CI
    sandbox cannot see hand-installed $HOME/.local tools (same pattern
    as archives/a/abiword-plugin-docbook/3.0.8).
  * Cross configure: --build=aarch64-unknown-linux-gnu and
    --host=aarch64-linux.  aarch64-linux canonicalizes to
    aarch64-unknown-linux-gnu inside config.sub, so no config.sub
    patch is needed (same approach as the abiword-plugin-* recipes).
    The compiler triplet is still driven by the OHOS profile through
    AutotoolsToolchain (CC/clang --target=aarch64-linux-ohos).
  * autoconf 2.72's config.status creates a ./confXXXXXX scratch
    directory inside the build folder; on the OHOS/HMDFS volume child
    processes cannot write there (E114, seen on the abiword recipes),
    so TMPDIR is redirected to a pre-created writable directory and
    the generated configure's ac_tmp template is patched to match.
  * Upstream installs bin_PROGRAMS=xlbiff plus the mailbox-preview
    helper script; both are declared in commands.json (R38).
"""

import os
import shlex
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import (
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class XlbiffConan(ConanFile):
    name = "xlbiff"
    version = "4.6.11"
    description = "X11 Athena widget mailbox summary pop-up (biff with an X face)"
    license = "MIT"
    homepage = "https://github.com/edsantiago/xlbiff"
    url = "https://github.com/edsantiago/xlbiff"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xlbiff supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Follow the libxaw/1.0.14 dependency track: libx11/1.8.13 is the
        # root track used by libxt/1.3.1 and libxmu/1.3.1.1 in this repo.
        self.requires(
            "libx11/1.8.13", force=True, transitive_headers=True, transitive_libs=True
        )
        # force=True: libxrandr/1.5.5 pins libxext/6.4.0; the root track
        # is 6.4.0.1 (libxaw/libxmu track), which wins per conan override
        # semantics and makes libxrandr rebuild from source.
        self.requires(
            "libxext/6.4.0.1",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires(
            "libxmu/1.3.1.1", transitive_headers=True, transitive_libs=True
        )
        self.requires("libxaw/1.0.14", transitive_headers=True, transitive_libs=True)
        self.requires("libxrandr/1.5.5", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def build_requirements(self):
        # The tag tarball has no configure/Makefile.in: bootstrap needed.
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        # xt.pc / xmu.pc etc. so configure's pkg-config lookups can resolve;
        # the appdefaultdir lookup falls back to datadir if the variable is
        # absent, and the install dir is pinned explicitly anyway.
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()
        AutotoolsDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        self._bootstrap()
        self._configure_ohos()
        if str(self.settings.os) == "OHOS":
            # E182/E188: the HMBS install shim only accepts single-file
            # two-argument calls; automake's batched "install -c -m 644
            # f1 f2 dir/" exits 64 (EX_USAGE).  Redirect the generated
            # Makefiles' INSTALL variable to a cp/mkdir shim (adms 2.3.7
            # / xeyes 1.3.1 precedent).
            shim = self._write_install_shim()
            self._redirect_install_to_shim(shim)
        self._run_ohos("make -j1")
        # Upstream has no automake TESTS in Makefile.am (tests/ are manual
        # shell scripts needing nmh + a running X server), so `make check`
        # is a no-op; the smoke test lives in test_package (xlbiff -version).
        self._run_ohos("make -j1 check")

    def package(self):
        destination = shlex.quote(self.package_folder)
        self._run_ohos(f"make -j1 install DESTDIR={destination}")
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                # Explicit cross build: autoconf must not try to run a
                # conftest binary on the OHOS worker, and aarch64-linux
                # canonicalizes without needing a config.sub patch.
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-linux",
                # Keep the app-defaults file under the package prefix so
                # DESTDIR installs stay relocatable (make expands ${datadir}
                # at install time, relative to the DESTDIR-staged prefix).
                "--with-appdefaultdir=${datadir}/X11/app-defaults",
            ]
        )
        return toolchain

    def _bootstrap(self):
        """aclocal -> autoconf -> autoheader -> automake --add-missing.

        OHOS HMDFS: the autoreconf wrapper chain trips over autoconf.m4f
        load conflicts (E114 / abiword-plugin-* precedent), so the four
        tools are invoked directly.  aclocal/automake binaries are located
        via the ACLOCAL/AUTOMAKE env vars that the automake package
        exports into the conanbuild environment - the CI sandbox does not
        have them on PATH.
        """
        self.run(
            '"${ACLOCAL:-aclocal}" --force', cwd=self.source_folder, env="conanbuild"
        )
        self.run(
            "autoconf -o configure configure.ac",
            cwd=self.source_folder,
            env="conanbuild",
        )
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoconf failed to generate configure")
        # xlbiff's configure.ac has no AC_CONFIG_HEADERS: autoheader would
        # error out ("AC_CONFIG_HEADERS not found"), so only run it when
        # the macro is actually present.
        configure_ac = Path(self.source_folder, "configure.ac")
        if "AC_CONFIG_HEADERS" in configure_ac.read_text(encoding="utf-8"):
            self.run("autoheader", cwd=self.source_folder, env="conanbuild")
        self.run(
            '"${AUTOMAKE:-automake}" --add-missing --copy --foreign',
            cwd=self.source_folder,
            env="conanbuild",
        )
        for generated in ("Makefile.in", "install-sh", "missing"):
            if not Path(self.source_folder, generated).is_file():
                raise ConanException(f"automake bootstrap did not produce {generated}")

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanException(f"OHOS configure shell is missing: {shell}")
        fixed_tmp = self._prepare_configure_tmpdir()
        configure_args = [
            f"--srcdir={self.source_folder}",
            *self._autotools_toolchain().configure_args,
        ]
        arguments = " ".join(shlex.quote(argument) for argument in configure_args)
        configure = self.source_folder + "/configure"
        self._run_ohos(
            f'TMPDIR={shlex.quote(str(fixed_tmp))} "{shell}" "{configure}" {arguments}'
        )

    def _prepare_configure_tmpdir(self):
        """E114: redirect autoconf's ac_tmp to a writable directory.

        config.status creates ./confXXXXXX scratch dirs and the security
        framework refuses child-process writes there on HMDFS; pre-create
        a fixed writable dir, point TMPDIR at it (inline in the configure
        invocation), and rewrite the generated configure's ac_tmp
        assignment to use it.
        """
        fixed_tmp = Path(tempfile.gettempdir(), "xlbiff-ac-tmp")
        fixed_tmp.mkdir(parents=True, exist_ok=True)
        configure = Path(self.source_folder, "configure")
        content = configure.read_text(encoding="utf-8")
        if "ac_tmp=$tmp" not in content:
            raise ConanException(
                "E114: ac_tmp=$tmp pattern not found in configure; "
                "autoconf may have changed the template"
            )
        content = content.replace("ac_tmp=$tmp", f"ac_tmp={fixed_tmp}")
        # config.status's trap removes $ac_tmp on exit, which would leave
        # the pre-created directory gone for later rounds; keep the dir.
        old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
        content = content.replace(old_trap, "exit $exit_status")
        configure.write_text(content, encoding="utf-8")
        os.chmod(configure, 0o755)
        return fixed_tmp

    def _write_install_shim(self):
        """E182/E188: write a cp/mkdir install shim for OHOS/HMFS.

        The HMBS install shim (runtime/<task>/bin/install) only accepts
        single-file two-argument invocations; automake's batched installs
        ("install -c -m 644 f1 f2 dir/") fail with exit 64 and there is
        no GNU coreutils install.  autotools 'make install' only needs
        file copy + mkdir + optional chmod, so replace INSTALL with a
        shim that does cp/mkdir and skips chmod failures (HMFS has no
        chmod capability, E046/E087).  Returns the shim absolute path.
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        # HMFS assigns permissions from the open mode (chmod is a no-op),
        # so create the shim directly executable via os.open(0o755).
        descriptor = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(
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
                    "mkdir -p \"$(dirname \"$dest\")\"\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  # HMFS does not support chmod (E046/E087); do not block.\n"
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
            os.close(descriptor)
            raise
        os.chmod(install, 0o755)
        return install

    def _redirect_install_to_shim(self, shim_install):
        """Point the INSTALL variable of every generated Makefile at shim.

        configure hard-writes the probed install path into INSTALL;
        INSTALL_DATA/INSTALL_PROGRAM derive from ${INSTALL}, so a line
        rewrite of "INSTALL = ..." redirects the whole make install
        (adms 2.3.7 precedent).
        """
        for root, _dirs, files in os.walk(self.build_folder):
            for name in files:
                if name != "Makefile":
                    continue
                makefile = os.path.join(root, name)
                with open(makefile, "r", encoding="utf-8", errors="ignore") as handle:
                    content = handle.read()
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[: len(line) - len(stripped)]
                        lines.append(f"{indent}INSTALL = {shim_install}\n")
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(makefile, "w", encoding="utf-8") as handle:
                        handle.write("".join(lines))

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")
