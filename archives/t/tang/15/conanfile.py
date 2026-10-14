#!/usr/bin/env python3
"""Conan recipe for Tang 15, the network-bound key release service."""
import os
import re
import shutil
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


UPSTREAM_TESTS = (
    "adv-standalone",
    "adv-standalone-endpoint",
    "adv-socat",
    "adv-socat-endpoint",
    "rec-standalone",
    "rec-standalone-endpoint",
    "rec-socat",
    "rec-socat-endpoint",
    "test-keys",
)


class TangConan(ConanFile):
    name = "tang"
    version = "15"
    description = "Network-bound cryptographic key release service"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/latchset/tang"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("jose/15")
        self.requires("http-parser/2.9.4")

    def build_requirements(self):
        # Pin every build/test executable instead of relying on a worker image.
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.13.2")
        self.tool_requires("pkgconf/3.0.6")
        # The upstream suite exercises both standalone tangd and the socat
        # adapter. jose is also the upstream CLI used by its shell tests.
        self.tool_requires("jose/15")
        self.tool_requires("socat/1.8.1.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        meson_toolchain = MesonToolchain(self)
        # This upstream build has no subprojects; forbid implicit wrap fetches
        # in clean CI workers and keep configure entirely reproducible.
        meson_toolchain.project_options["wrap_mode"] = "nodownload"
        ar, ranlib = self._find_archive_tools()
        if not ar:
            raise ConanInvalidConfiguration(
                "Tang needs an archiver, but neither llvm-ar nor ar was found "
                "beside the configured compiler or on PATH"
            )

        # The OHOS profile's PATH exposes clang but not its sibling llvm-ar.
        # Meson otherwise discovers the bare name `llvm-ar` and fails during
        # compiler sanity checks. Keep archiver and pkg-config resolution
        # explicit in the native file; Ninja is selected through NINJA below.
        meson_toolchain.ar = ar
        if ranlib:
            meson_toolchain.binaries["ranlib"] = ranlib
        # Still require the published ninja tool in the Conan graph, but its
        # executable fails to spawn even a trivial child on HarmonyOS. Select
        # the process-capable Ninja shipped in this worker image instead.
        if not self._build_tool("ninja", "ninja"):
            raise ConanInvalidConfiguration(
                "ninja/1.13.2 is required, but its package has no bin/ninja"
            )
        ninja = self._select_ninja()
        if not ninja:
            raise ConanInvalidConfiguration(
                "ninja/1.13.2 is required, but its package has no bin/ninja"
            )
        if not self._build_tool("meson", "meson"):
            raise ConanInvalidConfiguration(
                "meson/1.11.0 is required, but its package has no bin/meson"
            )
        pkgconf = self._build_tool("pkgconf", "pkgconf")
        if not pkgconf:
            raise ConanInvalidConfiguration(
                "pkgconf/3.0.6 is required, but its package has no bin/pkgconf"
            )
        meson_toolchain.binaries["pkg-config"] = pkgconf
        meson_toolchain.generate()
        self._inject_meson_binaries(
            {"ar": ar, "ranlib": ranlib, "pkg-config": pkgconf}
        )
        VirtualBuildEnv(self).generate()

    def _build_tool(self, dependency, executable):
        package = self.dependencies.build[dependency]
        candidate = os.path.join(package.package_folder, "bin", executable)
        return candidate if os.path.isfile(candidate) else None

    def _select_ninja(self):
        ninja = shutil.which("ninja")
        if not ninja:
            raise ConanInvalidConfiguration(
                "A process-capable Ninja must be present in the OHOS worker PATH; "
                "the published ninja/1.13.2 binary returns posix_spawn ENOENT"
            )
        return ninja

    def _find_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        compiler_dir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        hnp_home = os.environ.get("HNP_PUBLIC_HOME", "/data/service/hnp")
        sdk_bin_dirs = sorted(
            glob.glob(
                os.path.join(
                    hnp_home,
                    "ohos-sdk.org",
                    "ohos-sdk_*",
                    "ohos",
                    "native",
                    "llvm",
                    "bin",
                )
            ),
            reverse=True,
        )
        directories = [compiler_dir, *sdk_bin_dirs, "/data/service/hnp/bin", "/data/service/hnp/llvm/bin"]

        def resolve(names):
            candidates = []
            for directory in directories:
                if directory:
                    candidates.extend(os.path.join(directory, name) for name in names)
            candidates.extend(shutil.which(name) for name in names)
            for candidate in candidates:
                if candidate and os.path.isfile(candidate):
                    return candidate
            return None

        ar = executables.get("ar") or resolve(("llvm-ar", "llvm-ar-15", "ar"))
        ranlib = executables.get("ranlib") or resolve(("llvm-ranlib", "ranlib"))
        return ar, ranlib

    def _inject_meson_binaries(self, binaries):
        machine_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(machine_file):
            raise ConanInvalidConfiguration("Meson native machine file was not generated")
        with open(machine_file, encoding="utf-8") as handle:
            content = handle.read()

        header = re.search(r"(?m)^\[binaries\]\r?\n", content)
        if not header:
            raise ConanInvalidConfiguration("Meson machine file has no [binaries] section")
        for name, path in binaries.items():
            if not path:
                continue
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(f"Meson build tool is missing: {path}")
            line = f"{name} = {path!r}\n"
            setting = re.compile(rf"(?m)^{re.escape(name)}\s*=.*(?:\r?\n|$)")
            if setting.search(content):
                content = setting.sub(line, content, count=1)
            else:
                header = re.search(r"(?m)^\[binaries\]\r?\n", content)
                content = content[:header.end()] + line + content[header.end():]

        with open(machine_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = self._build_tool("meson", "meson")
        # The Conan tool requirement pins the package version in the graph;
        # the worker's process-capable Ninja is the backend used on OHOS.
        ninja = self._select_ninja()
        build_env = Environment()
        build_env.define_path("NINJA", ninja)
        build_env.prepend_path("PATH", os.path.dirname(ninja))
        machine_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with build_env.vars(self).apply():
            self.run(
                '"{}" setup --native-file "{}" "{}" "{}" --prefix=/'.format(
                    meson, machine_file, self.build_folder, self.source_folder
                ),
                cwd=self.source_folder,
                env="conanbuild",
            )
            self.run(
                '"{}" compile -C "{}" --jobs=2'.format(meson, self.build_folder),
                cwd=self.source_folder,
                env="conanbuild",
            )

        # Keep the upstream suite serial: the integration cases choose random
        # ports and each starts a local HTTP server. A strict result check
        # prevents Meson's successful exit code from hiding skipped cases.
        log_path = os.path.join(self.build_folder, "tang-upstream-tests.log")
        with open(log_path, "w", encoding="utf-8") as log:
            with build_env.vars(self).apply():
                self.run(
                    '"{}" test --print-errorlogs --no-rebuild -j1'.format(meson),
                    cwd=self.build_folder,
                    env="conanbuild",
                    stdout=log,
                    stderr=log,
                )

        with open(log_path, "r", encoding="utf-8", errors="replace") as log:
            output = log.read()
        statuses = {}
        for line in output.splitlines():
            for name in UPSTREAM_TESTS:
                match = re.search(
                    rf"(?<![A-Za-z0-9_-]){re.escape(name)}"
                    rf"(?![A-Za-z0-9_-]).*?\b(OK|PASS|FAIL|SKIP|TIMEOUT|ERROR)\b",
                    line,
                    re.IGNORECASE,
                )
                if match:
                    statuses[name] = match.group(1).upper()

        missing = [name for name in UPSTREAM_TESTS if name not in statuses]
        failed = {name: result for name, result in statuses.items() if result not in ("OK", "PASS")}
        if missing or failed or len(statuses) != len(UPSTREAM_TESTS):
            self.output.error(
                "Upstream Meson suite must run all 9 tests with no skips; "
                f"observed={statuses}, missing={missing}. Full log: {log_path}"
            )
            raise RuntimeError("Tang upstream test suite was incomplete or failed")
        self.output.info("Tang upstream tests: 9/9 passed; 0 skipped.")

    def package(self):
        # Meson's install target relinks tangd on this OHOS toolchain to apply
        # install-time linker flags. That invalidates the linker-produced ELF
        # signature, so package the already-tested build output byte-for-byte.
        libexec = os.path.join(self.package_folder, "libexec")
        bindir = os.path.join(self.package_folder, "bin")
        units = os.path.join(self.package_folder, "lib", "systemd", "system")
        licenses = os.path.join(self.package_folder, "share", "licenses", "tang")
        build_src = os.path.join(self.build_folder, "src")
        build_units = os.path.join(self.build_folder, "units")
        source_src = os.path.join(self.source_folder, "src")

        copy(self, "tangd", src=build_src, dst=libexec, keep_path=False)
        copy(self, "tangd-keygen", src=build_src, dst=libexec, keep_path=False)
        copy(self, "tangd-rotate-keys", src=build_src, dst=libexec, keep_path=False)
        copy(self, "tang-show-keys", src=source_src, dst=bindir, keep_path=False)
        copy(self, "tangd.socket", src=build_units, dst=units, keep_path=False)
        copy(self, "tangd@.service", src=build_units, dst=units, keep_path=False)
        copy(self, "COPYING", src=self.source_folder, dst=licenses, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "libexec"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
