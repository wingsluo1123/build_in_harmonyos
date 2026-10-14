#!/usr/bin/env python3
"""Conan recipe for the Janus WebRTC server on HarmonyOS PC."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class JanusConan(ConanFile):
    name = "janus"
    version = "1.4.1"
    description = "Janus WebRTC Server with REST/WebSocket transports and common plugins"
    license = "GPL-3.0-or-later"
    homepage = "https://janus.conf.meetecho.com/"
    url = "https://github.com/meetecho/janus-gateway"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    tool_requires = (
        "autoconf/2.72",
        "automake/1.19",
        "libtool/2.5.4.1",
        "m4/1.4.19",
        "perl/5.42.2",
        "pkgconf/3.0.6",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1.1", options={"shared": True})
        self.requires("libnice/0.1.21")
        self.requires("jansson/2.15.1.1")
        self.requires("libconfig/1.7.3")
        self.requires("libsrtp2/2.8.0")
        self.requires("libmicrohttpd/1.0.1")
        self.requires("libwebsockets/4.3.5.1")
        self.requires("libuv/1.52.1")
        self.requires("zlib/1.3.1.1")

        # The published HarmonyOS libnice binary is built against OpenSSL 1.1.1w.
        # Keep that artifact's ABI and rebuild libwebsockets from source against
        # this graph-wide OpenSSL version (its recipe otherwise requests 3.5.6).
        self.requires("openssl/1.1.1w", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # Janus 1.4.1 requests the OpenSSL modules as `libssl` and
        # `libcrypto`; Conan's OpenSSL generator exposes the same package as
        # `openssl.pc`. Provide pkg-config aliases without changing its paths
        # or link flags.
        openssl_pc = os.path.join(self.generators_folder, "openssl.pc")
        if os.path.isfile(openssl_pc):
            with open(openssl_pc, encoding="utf-8") as stream:
                openssl_metadata = stream.read()
            for module in ("libssl", "libcrypto"):
                alias = openssl_metadata.replace(
                    "Name: openssl", f"Name: {module}", 1
                )
                with open(
                    os.path.join(self.generators_folder, f"{module}.pc"),
                    "w",
                    encoding="utf-8",
                ) as stream:
                    stream.write(alias)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-data-channels",
                "--enable-libsrtp2",
                "--disable-all-plugins",
                "--enable-plugin-echotest",
                "--enable-plugin-videocall",
                "--enable-plugin-videoroom",
                "--disable-all-transports",
                "--enable-rest",
                "--enable-websockets",
                "--disable-all-handlers",
                "--disable-all-loggers",
                "--disable-turn-rest-api",
                "--disable-docs",
                "--disable-post-processing",
            ]
        )
        # Native HarmonyOS reports `uname -s` as `HarmonyOS`, which GNU
        # config.guess does not recognize. Pin the native build/host triplet
        # to the HNP Clang target; cross builds still let Conan select build.
        if str(self.settings.os) == "OHOS" and not cross_building(self):
            tc.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )

        # Janus probes libwebsockets with AC_CHECK_LIB instead of pkg-config.
        # Add Conan dependency include/lib paths so those configure probes and
        # the WebSocket transport compile use the selected graph, not host libs.
        for dependency in self.dependencies.host.values():
            package_folder = dependency.package_folder
            for include_dir in dependency.cpp_info.includedirs:
                path = os.path.join(package_folder, include_dir)
                if os.path.isdir(path):
                    tc.extra_cflags.append(f"-I{path}")
            if dependency.ref.name == "libnice":
                nice_include = os.path.join(package_folder, "include", "nice")
                if os.path.isdir(nice_include):
                    # Janus includes libnice headers as <agent.h>, while the
                    # published Conan artifact installs them under include/nice.
                    tc.extra_cflags.append(f"-I{nice_include}")
            for lib_dir in dependency.cpp_info.libdirs:
                path = os.path.join(package_folder, lib_dir)
                if os.path.isdir(path):
                    tc.extra_ldflags.append(f"-L{path}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HNP puts its Perl 5.42.0 autoreconf first on PATH, while the Conan
        # Autotools tools use Perl 5.42.2. Run the bootstrap with the declared
        # Conan toolchain as a unit to avoid mixing incompatible Perl modules.
        autotools_path = os.pathsep.join(
            os.path.join(self.dependencies.build[name].package_folder, "bin")
            for name in (
                "autoconf",
                "automake",
                "libtool",
                "m4",
                "perl",
                "pkgconf",
            )
        )
        self.run(
            f"env PATH={shlex.quote(autotools_path)}:$PATH sh ./autogen.sh",
            cwd=self.source_folder,
        )
        autotools = Autotools(self)
        # Conan changes the subprocess cwd but may preserve a stale PWD from
        # the caller. Keep the shell's logical cwd aligned with the build tree;
        # HarmonyOS HMDFS shells can fail getcwd while Autoconf probes it.
        previous_pwd = os.environ.get("PWD")
        os.environ["PWD"] = self.build_folder
        try:
            autotools.configure()
            # HarmonyOS HMDFS does not support GNU make's jobserver FIFO.
            autotools.make(args=["-j1"])
        finally:
            if previous_pwd is None:
                os.environ.pop("PWD", None)
            else:
                os.environ["PWD"] = previous_pwd

        if not cross_building(self):
            self._run_upstream_fuzzers()
        else:
            self.output.info(
                "Cross build: upstream check-fuzzers builds and executes target binaries; "
                "execution is deferred to native HarmonyOS validation."
            )

    def _run_upstream_fuzzers(self):
        # Janus's make target assumes an in-source tree and /bin/bash. Conan
        # builds out of tree, while HarmonyOS provides Bash through HNP. Copy
        # only the upstream scripts into the build tree and invoke them with
        # the installed Bash; the three upstream seed-corpus runs remain intact.
        source_root = self.source_folder
        build_root = self.build_folder
        source_fuzzers = os.path.join(source_root, "fuzzers")
        work = os.path.join(build_root, "fuzzers")
        if not os.path.isfile(os.path.join(source_fuzzers, "build.sh")):
            raise ConanException(f"Janus upstream fuzzer scripts are missing: {source_fuzzers}")
        os.makedirs(work, exist_ok=True)
        for script in ("build.sh", "config.sh", "run.sh"):
            shutil.copy2(os.path.join(source_fuzzers, script), os.path.join(work, script))

        for obj in (
            "janus-log.o",
            "janus-utils.o",
            "janus-rtcp.o",
            "janus-rtp.o",
            "janus-sdp-utils.o",
        ):
            shutil.copy2(
                os.path.join(build_root, "src", obj),
                os.path.join(source_root, "src", obj),
            )

        bash = shutil.which("bash") or "bash"
        env = {
            # Conan changes the subprocess cwd without updating PWD. HNP Bash
            # validates that variable at startup and its getcwd syscall is not
            # supported for these HarmonyOS directories.
            "PWD": build_root,
            "SRC": os.path.dirname(source_root),
            "JANUSGW": os.path.basename(source_root),
            "WORK": work,
            "OUT": os.path.join(work, "out"),
            "SKIP_JANUS_BUILD": "1",
            "LIB_FUZZING_ENGINE": "fuzzers/standalone.o",
        }
        prefix = " ".join(f"{key}={shlex.quote(value)}" for key, value in env.items())
        self.run(
            f"{prefix} {shlex.quote(bash)} -eu ./fuzzers/build.sh",
            cwd=build_root,
            env="conanbuild",
        )
        for fuzzer in ("rtcp_fuzzer", "rtp_fuzzer", "sdp_fuzzer"):
            self.run(
                f"{prefix} {shlex.quote(bash)} -eu ./fuzzers/run.sh "
                f"{fuzzer} out/{fuzzer}_seed_corpus",
                cwd=build_root,
                env="conanrun",
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
