#!/usr/bin/env python3
"""Conan recipe for the Dropbear SSH server and client suite."""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DropbearConan(ConanFile):
    name = "dropbear"
    version = "2025.88"
    description = "Small SSH server and client suite"
    license = "MIT"
    homepage = "https://matt.ucc.asn.au/dropbear/dropbear.html"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Dropbear supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend(
                [
                    "--disable-zlib",
                    "--disable-syslog",
                    "--disable-shadow",
                    "--disable-openpty",
                    "--disable-lastlog",
                    "--disable-utmp",
                    "--disable-utmpx",
                    "--disable-wtmp",
                    "--disable-wtmpx",
                    "--disable-loginfunc",
                    "--disable-pututline",
                    "--disable-pututxline",
                ]
            )
        tc.generate()

    def _prepare_upstream_test_auth(self):
        test_home = os.path.join(self.build_folder, "test-home")
        ssh_dir = os.path.join(test_home, ".ssh")
        authorized_keys = os.path.join(ssh_dir, "authorized_keys")
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
        with open(authorized_keys, "w", encoding="utf-8"):
            pass

        keygen = os.path.join(self.build_folder, "dropbearkey")
        keyconvert = os.path.join(self.build_folder, "dropbearconvert")
        keys = (
            ("id_dropbear", ""),
            ("id_dropbear_key2", "key2 extra"),
            ("id_dropbear_key3", "key3%char"),
            ("id_dropbear_key4", "key4,char"),
        )
        for name, comment in keys:
            keyfile = os.path.join(ssh_dir, name)
            command = f'"{keygen}" -t ecdsa -f "{keyfile}"'
            if comment:
                command += (
                    f' | sed -n "s/^[e]cdsa.*/&/p" | '
                    f'sed "s/[^ ]*$/{comment}/" >> "{authorized_keys}"'
                )
            else:
                command += f' | grep "^ecdsa" >> "{authorized_keys}"'
            self.run(command)

        self.run(
            f'"{keyconvert}" dropbear openssh '
            f'"{os.path.join(ssh_dir, "id_dropbear")}" '
            f'"{os.path.join(ssh_dir, "id_dropbear_openssh")}"'
        )

        os.chmod(authorized_keys, 0o600)
        return test_home

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            save(
                self,
                "localoptions.h",
                "#define DROPBEAR_SVR_PASSWORD_AUTH 0\n"
                "/* Use public-key authentication where crypt() is unavailable. */\n",
            )
            for config_script in ("config.guess", "config.sub"):
                path = os.path.join(self.source_folder, "src", config_script)
                if os.path.isfile(path):
                    mode = os.stat(path).st_mode
                    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        previous_tmpdir = None
        if str(self.settings.os) == "OHOS":
            # HMDFS rejects config.status files created with umask 077. Use the
            # user's verified writable tmp directory instead of the build path.
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
            if not os.path.isdir(tmpdir):
                os.makedirs(tmpdir, mode=0o700, exist_ok=True)
            if not os.path.isdir(tmpdir):
                raise RuntimeError(f"OHOS temporary directory is unavailable: {tmpdir}")
            previous_tmpdir = os.environ.get("TMPDIR")
            os.environ["TMPDIR"] = tmpdir

        try:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

            if can_run(self):
                test_home = self._prepare_upstream_test_auth()
                previous_home = os.environ.get("HOME")
                previous_dbtest = os.environ.get("DBTEST_IN_ACTION")
                previous_auth_dir = os.environ.get("DROPBEAR_TEST_AUTHORIZED_KEYS_DIR")
                previous_identity = os.environ.get("DROPBEAR_TEST_IDENTITY_FILE")
                previous_asyncssh_identity = os.environ.get(
                    "DROPBEAR_TEST_ASYNCSSH_IDENTITY_FILE"
                )
                os.environ["HOME"] = test_home
                os.environ["DBTEST_IN_ACTION"] = "1"
                os.environ["DROPBEAR_TEST_AUTHORIZED_KEYS_DIR"] = os.path.join(test_home, ".ssh")
                os.environ["DROPBEAR_TEST_IDENTITY_FILE"] = os.path.join(
                    test_home, ".ssh", "id_dropbear"
                )
                os.environ["DROPBEAR_TEST_ASYNCSSH_IDENTITY_FILE"] = os.path.join(
                    test_home, ".ssh", "id_dropbear_openssh"
                )
                try:
                    autotools.make(target="check")
                finally:
                    if previous_home is None:
                        os.environ.pop("HOME", None)
                    else:
                        os.environ["HOME"] = previous_home
                    if previous_dbtest is None:
                        os.environ.pop("DBTEST_IN_ACTION", None)
                    else:
                        os.environ["DBTEST_IN_ACTION"] = previous_dbtest
                    if previous_auth_dir is None:
                        os.environ.pop("DROPBEAR_TEST_AUTHORIZED_KEYS_DIR", None)
                    else:
                        os.environ["DROPBEAR_TEST_AUTHORIZED_KEYS_DIR"] = previous_auth_dir
                    if previous_identity is None:
                        os.environ.pop("DROPBEAR_TEST_IDENTITY_FILE", None)
                    else:
                        os.environ["DROPBEAR_TEST_IDENTITY_FILE"] = previous_identity
                    if previous_asyncssh_identity is None:
                        os.environ.pop("DROPBEAR_TEST_ASYNCSSH_IDENTITY_FILE", None)
                    else:
                        os.environ["DROPBEAR_TEST_ASYNCSSH_IDENTITY_FILE"] = (
                            previous_asyncssh_identity
                        )
            else:
                self.output.info("cross-building: upstream make check requires a runnable target")
        finally:
            if str(self.settings.os) == "OHOS":
                if previous_tmpdir is None:
                    os.environ.pop("TMPDIR", None)
                else:
                    os.environ["TMPDIR"] = previous_tmpdir

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Dropbear's Autotools build maps both bindir and sbindir to bin.
        self.cpp_info.bindirs = ["bin"]
