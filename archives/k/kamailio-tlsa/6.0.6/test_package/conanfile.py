#!/usr/bin/env python3
"""Build a matching Kamailio core and exercise the packaged TLSA over TLS."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import get, patch
from conan.tools.layout import basic_layout


class KamailioTlsaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "*.py", "*.c", "upstream/*", "upstream_support/*"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self)

    def build(self):
        source = os.path.join(self.build_folder, "host-source")
        get(self, url="https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz",
            sha256="32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48",
            destination=source, strip_root=True)
        package = self.dependencies["kamailio-tlsa"].package_folder
        patch(self, base_path=source, patch_file=os.path.join(
            package, "share", "kamailio-tlsa", "0001-src-core-daemonize.c.patch"))
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or ("clang" if str(self.settings.compiler) == "clang" else "gcc")
        variables = [
            "CC=" + cc,
            "ARCH=" + ("aarch64" if self.settings.arch == "armv8" else "x86_64"),
            "OS=" + ("harmonyos" if self.settings.os == "OHOS" else "linux"),
            "mode=" + ("debug" if self.settings.build_type == "Debug" else "release"),
            "extra_defs=-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD "
            "-DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H "
            "-DHAVE_TIMEGM -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN",
        ]
        args = " ".join(shlex.quote(value) for value in variables)
        env = Environment()
        if self.settings.os == "OHOS":
            env.define("DEFS", "-UHAVE_RESOLV_RES")
        with env.vars(self).apply():
            self.run("make cfg include_modules=sl " + args, cwd=source)
            self.run("make -C src -j2 kamailio " + args, cwd=source)
            self.run("make modules modules=modules/sl -j2 " + args, cwd=source)
        openssl = self.dependencies["openssl"].package_folder
        libraries = [os.path.join(openssl, "lib", "libssl.a"),
                     os.path.join(openssl, "lib", "libcrypto.a"), "-ldl", "-pthread"]
        for filename, output, flags in [
            ("foreign_state.c", "foreign_ssl.so", ["-shared", "-fPIC"]),
            ("make_certificate.c", "make_certificate", ["-fPIE", "-pie"]),
        ]:
            command = [cc, "-I" + os.path.join(openssl, "include"), *flags,
                       os.path.join(self.source_folder, filename), *libraries,
                       "-o", os.path.join(self.build_folder, output)]
            self.run(" ".join(shlex.quote(value) for value in command))

    def test(self):
        if can_run(self):
            command = [sys.executable, os.path.join(self.source_folder, "test_tlsa.py"),
                       "--package", self.dependencies["kamailio-tlsa"].package_folder,
                       "--build", self.build_folder, "--arch", str(self.settings.arch)]
            self.run(" ".join(shlex.quote(value) for value in command), env="conanrun")
            command = [sys.executable, os.path.join(self.source_folder, "run_upstream.py"),
                       "--host", os.path.join(self.build_folder, "host-source", "src"),
                       "--output", os.path.join(self.build_folder, "upstream-results")]
            self.run(" ".join(shlex.quote(value) for value in command), env="conanrun")
        else:
            raise RuntimeError("TLSA consumers require native execution")
