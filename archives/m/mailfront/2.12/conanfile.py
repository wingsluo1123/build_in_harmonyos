#!/usr/bin/env python3
"""Conan recipe for mailfront 2.12, a modular SMTP/QMTP/QMQP front end."""

import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"


class MailfrontConan(ConanFile):
    name = "mailfront"
    version = "2.12"
    description = "Modular SMTP, QMTP and QMQP mail protocol front ends"
    license = "GPL-2.0-only"
    homepage = "https://untroubled.org/mailfront/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("smtp", "mail", "starttls", "ucspi", "server")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _programs = (
        "mailfront",
        "imapfront-auth",
        "pop3front-auth",
        "pop3front-maildir",
        "qmqpfront-echo",
        "qmqpfront-qmail",
        "qmtpfront-echo",
        "qmtpfront-qmail",
        "smtpfront-echo",
        "smtpfront-qmail",
    )
    _modules = (
        "backend-echo.so",
        "backend-qmail.so",
        "backend-queuedir.so",
        "plugin-add-received.so",
        "plugin-check-fqdn.so",
        "plugin-clamav.so",
        "plugin-counters.so",
        "plugin-cvm-authenticate.so",
        "plugin-cvm-validate.so",
        "plugin-lua.so",
        "plugin-mailrules.so",
        "plugin-patterns.so",
        "plugin-qmail-validate.so",
        "plugin-rbl.so",
        "plugin-spamassassin.so",
        "plugin-starttls-ucspi.so",
        "protocol-qmqp.so",
        "protocol-qmtp.so",
        "protocol-smtp.so",
    )

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "mailfront/2.12 is validated for OHOS only"
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "mailfront/2.12 is validated for OHOS armv8 only"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "bglibs/2.04",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("cvm/0.97")
        self.requires("lua/5.1.5")

    def build_requirements(self):
        self.test_requires("cdb/20251021")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_flags(self):
        include_dirs = []
        lib_dirs = []
        for dependency in ("bglibs", "cvm", "lua"):
            package = self.dependencies[dependency].package_folder
            include_dirs.append(os.path.join(package, "include"))
            lib_dirs.append(os.path.join(package, "lib"))
        return include_dirs, lib_dirs

    def _write_configuration(self):
        variables = AutotoolsToolchain(self).vars()
        cc = variables.get("CC", "clang")
        cflags = variables.get("CFLAGS", "")
        ldflags = variables.get("LDFLAGS", "")
        include_dirs, lib_dirs = self._dependency_flags()
        source_map = "/usr/src/mailfront-2.12"
        compile_flags = [
            cflags,
            "-g0",
            "-ffile-prefix-map={}={}".format(self.source_folder, source_map),
            "-fmacro-prefix-map={}={}".format(self.source_folder, source_map),
        ] + ["-I" + shlex.quote(path) for path in include_dirs]
        link_flags = [ldflags] + ["-L" + shlex.quote(path) for path in lib_dirs]

        save(
            self,
            os.path.join(self.source_folder, "conf-cc"),
            " ".join(item for item in [cc] + compile_flags if item) + "\n",
        )
        save(
            self,
            os.path.join(self.source_folder, "conf-ccso"),
            " ".join(
                item
                for item in [cc]
                + compile_flags
                + link_flags
                + ["-fPIC", "-shared"]
                if item
            )
            + "\n",
        )
        save(
            self,
            os.path.join(self.source_folder, "conf-ld"),
            " ".join(item for item in [cc] + link_flags if item) + "\n",
        )
        save(self, os.path.join(self.source_folder, "conf-bin"), "/usr/bin\n")
        save(
            self,
            os.path.join(self.source_folder, "conf-include"),
            "/usr/include/mailfront\n",
        )
        save(
            self,
            os.path.join(self.source_folder, "conf-modules"),
            "/usr/lib/mailfront\n",
        )
        save(self, os.path.join(self.source_folder, "conf-qmail"), "/var/qmail\n")
        save(
            self,
            os.path.join(self.source_folder, "auto_testcvm.c"),
            "#define TESTCVM_UID {}\n"
            "#define TESTCVM_GID {}\n"
            '#define TESTCVM_PWD "{}"\n'.format(
                os.getuid(),
                os.getgid(),
                self.source_folder.replace("\\", "\\\\").replace('"', '\\"'),
            ),
        )

        for generated in (
            "compile",
            "load",
            "makeso",
            "makelib",
            "socket.lib",
            "dl.lib",
            "conf_modules.c",
            "conf_qmail.c",
        ):
            path = os.path.join(self.source_folder, generated)
            if os.path.lexists(path):
                os.unlink(path)

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.info("Cross-building: 128 upstream test instances deferred")
            return
        environment = Environment()
        for dependency in ("bglibs", "cvm", "lua"):
            environment.prepend_path(
                "LD_LIBRARY_PATH",
                os.path.join(self.dependencies[dependency].package_folder, "lib"),
            )
        environment.prepend_path(
            "PATH",
            os.path.join(self.dependencies["cdb"].package_folder, "bin"),
        )
        environment.define("MODULE_PATH", self.source_folder)
        environment.define("MAILFRONT_TEST_SOURCE", self.source_folder)
        environment.define("MAILFRONT_TEST_UID", str(os.getuid()))
        environment.define("MAILFRONT_TEST_GID", str(os.getgid()))
        environment.define("TMPDIR", self.source_folder)
        with environment.vars(self).apply():
            self.run("sh tests.sh -v", cwd=self.source_folder)

    def build(self):
        apply_conandata_patches(self)
        self._write_configuration()
        self.run("make -j1 all lua", cwd=self.source_folder)
        self._run_upstream_tests()

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        module_dir = os.path.join(self.package_folder, "lib", "mailfront")
        include_dir = os.path.join(self.package_folder, "include", "mailfront")
        for program in self._programs:
            copy(
                self,
                program,
                src=self.source_folder,
                dst=bin_dir,
                keep_path=False,
            )
        for module in self._modules:
            copy(
                self,
                module,
                src=self.source_folder,
                dst=module_dir,
                keep_path=False,
            )
        for header in ("constants.h", "mailfront.h", "responses.h"):
            copy(
                self,
                header,
                src=self.source_folder,
                dst=include_dir,
                keep_path=False,
            )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if str(self.settings.os) == "OHOS":
            self._sign_and_validate_elfs(bin_dir, module_dir)

    def _sign_and_validate_elfs(self, *roots):
        with VirtualBuildEnv(self).vars().apply():
            objcopy = shutil.which("llvm-objcopy")
            readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
            strip = shutil.which("llvm-strip")
            signer = shutil.which("binary-sign-tool")
        if not all((objcopy, readelf, strip, signer)):
            raise ConanException(
                "llvm-objcopy, llvm-readelf, llvm-strip and binary-sign-tool are required"
            )

        for root in roots:
            for path in sorted(glob.glob(os.path.join(root, "*"))):
                if not os.path.isfile(path):
                    continue
                with open(path, "rb") as stream:
                    if stream.read(4) != b"\x7fELF":
                        continue
                subprocess.run([strip, "--strip-debug", path], check=True)
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                result = subprocess.run(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        path,
                        "-outFile",
                        path,
                        "-selfSign",
                        "1",
                    ],
                    capture_output=True,
                    text=True,
                )
                sections = subprocess.run(
                    [readelf, "-SW", path],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
                dynamic = subprocess.run(
                    [readelf, "-d", path],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
                with open(path, "rb") as stream:
                    data = stream.read()
                if result.returncode != 0 or sections.count(".codesign") != 1:
                    raise ConanException(
                        "failed to sign {}: {}".format(
                            path, result.stderr or result.stdout
                        )
                    )
                if "RPATH" in dynamic or "RUNPATH" in dynamic:
                    raise ConanException("packaged ELF contains RPATH/RUNPATH: " + path)
                if b".conan2" in data or os.fsencode(self.package_folder) in data:
                    raise ConanException("packaged ELF leaks a Conan path: " + path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
