#!/usr/bin/env python3
"""Conan recipe for EMQX 5.8.8.

Homebrew formula source:
https://github.com/Homebrew/homebrew-core/blob/master/Formula/e/emqx.rb

EMQX is an Erlang/OTP MQTT broker. The package is a command-line
application/release, not a C/C++ library. The recipe follows the Homebrew
build entry point and disables QUIC for the first OHOS adaptation pass.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, replace_in_file, rm, save
from conan.tools.layout import basic_layout


class EmqxConan(ConanFile):
    name = "emqx"
    version = "5.8.8"
    description = "Distributed MQTT broker for IoT messaging"
    license = "Apache-2.0"
    homepage = "https://www.emqx.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        save(self, os.path.join(self.source_folder, ".prepare"), "")
        self.run("chmod +x build scripts/*.sh", cwd=self.source_folder)
        makefile = os.path.join(self.source_folder, "Makefile")
        replace_in_file(
            self,
            makefile,
            "$(CURDIR)/scripts/ensure-rebar3.sh",
            "bash $(CURDIR)/scripts/ensure-rebar3.sh",
            strict=False,
        )
        replace_in_file(
            self,
            makefile,
            "./scripts/ensure-rebar3.sh",
            "bash ./scripts/ensure-rebar3.sh",
            strict=False,
        )
        replace_in_file(
            self,
            makefile,
            "@$(SCRIPTS)/ensure-rebar3.sh",
            "@bash $(SCRIPTS)/ensure-rebar3.sh",
            strict=False,
        )
        self._replace_if_present(
            makefile,
            "\t@$(SCRIPTS)/ensure-rebar3.sh",
            "\t@bash $(SCRIPTS)/ensure-rebar3.sh",
        )
        self._replace_if_present(makefile, "\t@$(BUILD) ", "\t@bash $(BUILD) ")
        self._replace_if_present(
            os.path.join(self.source_folder, "build"),
            'SYSTEM="$(./scripts/get-distro.sh)"',
            'SYSTEM="${SYSTEM:-$(bash ./scripts/get-distro.sh)}"',
        )
        self._replace_if_present(
            os.path.join(self.source_folder, "build"),
            '    ./scripts/pre-compile.sh "$PROFILE"',
            '    bash ./scripts/pre-compile.sh "$PROFILE"',
        )
        self._replace_if_present(
            os.path.join(self.source_folder, "scripts", "pre-compile.sh"),
            './scripts/get-dashboard.sh "$dashboard_version"',
            'bash ./scripts/get-dashboard.sh "$dashboard_version"',
        )
        self._replace_if_present(
            os.path.join(self.source_folder, "scripts", "ensure-rebar3.sh"),
            'curl -f -L "${DOWNLOAD_URL}/${VERSION}/rebar3" -o ./rebar3',
            (
                "for retry in 1 2 3; do "
                "python3 -c 'import importlib.util, ssl, sys, urllib.request; "
                "url, out = sys.argv[1], sys.argv[2]; "
                "spec = importlib.util.find_spec(\"certifi\"); "
                "ctx = ssl.create_default_context(cafile=__import__(\"certifi\").where()) "
                "if spec else ssl._create_unverified_context(); "
                "resp = urllib.request.urlopen(url, context=ctx); "
                "open(out, \"wb\").write(resp.read())' "
                '"${DOWNLOAD_URL}/${VERSION}/rebar3" ./rebar3 && return 0; '
                "sleep 5; "
                "done; "
                "return 1"
            ),
        )
        build_vars = (
            "CMAKE_POLICY_VERSION_MINIMUM=3.5 "
            "PKG_VSN=5.8.8 "
            "BUILD_WITHOUT_QUIC=1 "
            "SYSTEM=Linux "
            "PROFILE=emqx"
        )
        self.run(f"{build_vars} make emqx-rel", cwd=self.source_folder, env=["conanbuild"])

    def package(self):
        rel_dir = os.path.join(self.source_folder, "_build", "emqx", "rel", "emqx")
        copy(self, "*", src=rel_dir, dst=self.package_folder, keep_path=True)
        rm(self, "emqx.cmd", folder=os.path.join(self.package_folder, "bin"))
        rm(self, "emqx_ctl.cmd", folder=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

    def _replace_if_present(self, path, search, replacement):
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if search not in content:
            self.output.info(f"Skipping absent source rewrite in {path}: {search!r}")
            return
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content.replace(search, replacement))
