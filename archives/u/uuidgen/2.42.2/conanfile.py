#!/usr/bin/env python3
"""Conan recipe for uuidgen 2.42.2 from util-linux."""
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


class UuidgenConan(ConanFile):
    name = "uuidgen"
    version = "2.42.2"
    description = "UUID generation command from util-linux"
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

    def generate(self):
        awk = self._prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"AWK={awk}",
            f"ac_cv_prog_AWK={awk}",
            "--disable-all-programs",
            "--enable-uuidgen",
            "--enable-libuuid",
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
        ])
        tc.generate()

        env = Environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.vars(self, scope="build").save_script("conanuuidgentmpdir")

    def build(self):
        apply_conandata_patches(self)
        self._prepare_autotools_env()

        # E011: configure creates temporary directories with umask 077; on
        # OHOS HMDFS those directories are unwritable. Use 022 instead.
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            with open(configure, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                text = text.replace("umask 077", "umask 022")
                with open(configure, "w", encoding="utf-8") as f:
                    f.write(text)
                self.output.info("patched configure: umask 077->022 (E011)")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])
        autotools.make(target="test_uuid_parser", args=["-j1"])

        if not can_run(self):
            self.output.info("Skipping upstream uuidgen tests: target binaries cannot run in this context")
            return

        uuidgen = os.path.join(self.build_folder, "uuidgen")
        parser = os.path.join(self.build_folder, "test_uuid_parser")
        test_env = (
            f"TS_CMD_UUIDGEN={shlex.quote(uuidgen)} "
            f"TS_HELPER_UUID_PARSER={shlex.quote(parser)}"
        )
        self.run(f"{test_env} bash tests/ts/uuidgen/uuidgen",
                 cwd=self.source_folder, env=["conanbuild"])
        self.run(f"{test_env} bash tests/ts/uuidgen/oids",
                 cwd=self.source_folder, env=["conanbuild"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Keep only the command and license; this recipe does not export the
        # internal static libuuid or headers.
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
