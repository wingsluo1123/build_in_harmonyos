#!/usr/bin/env python3
"""Conan recipe for mcookie 2.42.2 from util-linux."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class McookieConan(ConanFile):
    name = "mcookie"
    version = "2.42.2"
    description = "Generate magic cookies for xauth, from util-linux"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/util-linux/util-linux"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        data = self.conan_data["sources"][self.version]
        primary, mirrors = data["url"][0], data["url"][1:]
        for url in [primary] + mirrors:
            try:
                get(self, url, sha256=data["sha256"], strip_root=True)
                return
            except Exception as e:
                self.output.warning(f"source download failed from {url}: {e}")
        raise ConanInvalidConfiguration("source download failed from all mirrors")

    def _prepare_autotools_env(self):
        """Writable TMPDIR and explicit AWK for configure."""
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

        # The OHOS CI worker exports CONFIG_SHELL=/data/service/hnp/bin/bash;
        # that path does not exist on a macOS host doing local W3 simulation,
        # so configure fails to re-exec itself ("No such file or directory").
        # Force a portable POSIX shell for the configure/make phases; harmless
        # on the real OHOS worker where /bin/sh is always present.
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "")
        bindir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        toolchain_awk = ""
        if bindir:
            for name in ("gawk", "awk"):
                candidate = os.path.join(bindir, name)
                if os.path.exists(candidate):
                    toolchain_awk = candidate
                    break
        awk = toolchain_awk or shutil.which("gawk") or shutil.which("awk")
        if not awk:
            raise ConanInvalidConfiguration("An awk implementation is required")
        os.environ["AWK"] = awk
        os.environ["ac_cv_prog_AWK"] = awk
        return awk

    def _configure_args(self, awk):
        # Declare --host explicitly: when host and build use the same Conan
        # profile (CI and local W3 both pass -pr:h=X -pr:b=X), configure
        # otherwise assumes a native build and tries to RUN the OHOS test
        # binary on the host machine ("cannot run C compiled programs").
        arch = str(self.settings.arch)
        osys = str(self.settings.os)
        host = {"armv8": "aarch64"}.get(arch, arch) + "-" + ("linux-ohos" if osys == "OHOS" else "linux")
        return [
            f"--host={host}",
            f"AWK={awk}",
            f"ac_cv_prog_AWK={awk}",
            "--disable-all-programs",
            "--enable-mcookie",
            "--disable-libblkid",
            "--disable-libmount",
            "--disable-libsmartcols",
            "--disable-libfdisk",
            "--without-python",
            "--without-systemd",
            "--without-udev",
            "--disable-makeinstall-chown",
            "--disable-makeinstall-setuid",
            "--enable-static",
            "--disable-shared",
        ]

    def generate(self):
        awk = self._prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args(awk))
        # Stash the full arg list (toolchain defaults like --prefix=/ and
        # --bindir=${prefix}/bin plus ours) for the manual configure call in
        # build(); without the toolchain defaults install lands in usr/bin
        # instead of bin/.
        self._tc_configure_args = list(tc.configure_args)
        tc.generate()

        env = Environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        # The OHOS CI buildenv profile re-exports SHELL/CONFIG_SHELL pointing
        # at /data/service/hnp/bin/bash (real worker path) in a script that is
        # loaded *after* recipe-generated env scripts, so it wins over any
        # define here. build() therefore prefixes configure/make/install with
        # `env CONFIG_SHELL=/bin/sh SHELL=/bin/sh` to force a shell that exists
        # on every host (macOS W3 simulation has no /data/service/hnp/bash).
        env.vars(self, scope="build").save_script("conanmcookietmpdir")

    def build(self):
        apply_conandata_patches(self)
        awk = self._prepare_autotools_env()

        # E011: configure creates temporary directories with umask 077; on
        # OHOS HMDFS those directories are unwritable. Use 022 instead.
        configure = os.path.join(self.build_folder, "configure")
        if not os.path.isfile(configure):
            configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            with open(configure, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                text = text.replace("umask 077", "umask 022")
                with open(configure, "w", encoding="utf-8") as f:
                    f.write(text)
                self.output.info("patched configure: umask 077->022 (E011)")

        # Run configure/make/install manually: the OHOS CI buildenv profile
        # injects SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash which exists
        # only on the real worker. On the macOS W3 host that path is missing and
        # configure cannot re-exec itself. `env ...` overrides win regardless of
        # script load order; harmless on the worker where /bin/sh always exists.
        # Note: self.build_folder points at the <build-type> subfolder while the
        # source tree (and configure) live in its parent, so use the configure
        # directory explicitly.
        build_root = os.path.dirname(configure)
        self._build_root = build_root
        tc_args = getattr(self, "_tc_configure_args", None) or self._configure_args(awk)
        args = " ".join(shlex.quote(a) for a in tc_args)
        self.run(f"env CONFIG_SHELL=/bin/sh SHELL=/bin/sh {shlex.quote(configure)} {args}",
                 cwd=build_root, env="conanbuild")
        self.run(f"env SHELL=/bin/sh make -C {shlex.quote(build_root)} -j4",
                 env="conanbuild")

        if not can_run(self):
            self.output.info("Skipping upstream mcookie test: target binaries cannot run in this context")
            return

        mcookie = os.path.join(build_root, "mcookie")
        test_env = f"TS_CMD_MCOOKIE={shlex.quote(mcookie)}"
        self.run(f"{test_env} bash tests/ts/mcookie/mcookie",
                 cwd=self.source_folder, env=["conanbuild"])

    def package(self):
        # Reuse the source-tree root determined in build(): self.build_folder
        # is unreliable at package() time (points at the <build-type>
        # subfolder), which made `make install` run in a directory without a
        # Makefile ("No rule to make target 'install'").
        build_root = getattr(self, "_build_root", None) or self.source_folder
        self.run(f"env SHELL=/bin/sh make -C {shlex.quote(build_root)} install "
                 f"DESTDIR={shlex.quote(self.package_folder)}",
                 env="conanbuild")

        # Keep only the command and license; this recipe does not export any
        # util-linux internal libraries or headers.
        for folder in ("include", "lib", "share"):
            path = os.path.join(self.package_folder, folder)
            if os.path.isdir(path):
                shutil.rmtree(path)
        rm(self, "*.la", self.package_folder, recursive=True)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = [bindir]
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
