#!/usr/bin/env python3
"""Conan recipe for devcontainers/cli 0.87.0.

A Node.js CLI tool for creating and managing development containers.
Build system: npm (Node.js/TypeScript with native module node-pty).
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DevcontainerConan(ConanFile):
    name = "devcontainer"
    version = "0.87.0"
    description = "Dev Containers CLI - create and manage development containers"
    license = "MIT"
    homepage = "https://github.com/devcontainers/cli"
    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}. Only OHOS is supported (requires HarmonyOS system paths).")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        # R33: Get compiler paths from Conan configuration, not raw shell vars
        ce = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(ce, str):
            try:
                ce = json.loads(ce)
            except (json.JSONDecodeError, ValueError):
                ce = {}
        cc = ce.get("c", "clang") if isinstance(ce, dict) else "clang"
        cxx = ce.get("cpp", "clang++") if isinstance(ce, dict) else "clang++"
        env.define("CC", cc)
        env.define("CXX", cxx)
        # Python library path needed by node-gyp (runs Python subprocess)
        env.prepend("LD_LIBRARY_PATH", "/data/service/hnp/python.org/python_3.12/lib")
        env.prepend("LD_LIBRARY_PATH", "/data/service/hnp/lib")
        # npm needs a writable temp directory (E002: /tmp is read-only on OHOS)
        tmpdir = os.environ.get("TMPDIR", "/storage/Users/currentUser/tmp")
        env.define("TMPDIR", tmpdir)
        envvars = env.vars(self, scope="build")
        envvars.save_script("devcontainer_build_env")

    def build(self):
        apply_conandata_patches(self)
        # Step 1: Install npm dependencies without running native build scripts
        self.run("npm install --ignore-scripts", env="conanbuild")

        # Step 2: Build node-pty native module with node-gyp
        node_pty = os.path.join(self.source_folder, "node_modules", "node-pty")
        node_bin = shutil.which("node") or "/data/service/hnp/bin/node"
        node_bin = os.path.realpath(node_bin)  # Resolve symlink to actual binary
        nodedir = os.path.dirname(os.path.dirname(node_bin))
        self.run(
            f'npx node-gyp rebuild --nodedir="{nodedir}"',
            cwd=node_pty,
            env="conanbuild",
        )

        # Step 3: Compile TypeScript/JavaScript via esbuild
        self.run("npm run compile", env="conanbuild")

    def package(self):
        libdir = os.path.join(self.package_folder, "lib", "devcontainer")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)

        # Copy main application files
        for f in ("devcontainer.js", "package.json", "CHANGELOG.md",
                  "LICENSE.txt", "README.md", "ThirdPartyNotices.txt"):
            copy(self, f, src=self.source_folder, dst=libdir, keep_path=False)

        # Copy compiled output (dist/spec-node/devContainersSpecCLI.js)
        dist_src = os.path.join(self.source_folder, "dist")
        if os.path.isdir(dist_src):
            copy(self, "*", src=dist_src, dst=os.path.join(libdir, "dist"))

        # Copy node_modules (including compiled native module pty.node)
        nm_src = os.path.join(self.source_folder, "node_modules")
        if os.path.isdir(nm_src):
            copy(self, "*", src=nm_src, dst=os.path.join(libdir, "node_modules"))

        # Copy scripts
        scripts_src = os.path.join(self.source_folder, "scripts")
        if os.path.isdir(scripts_src):
            copy(self, "*", src=scripts_src, dst=os.path.join(libdir, "scripts"))

        # Create wrapper script (resolves its own location to find devcontainer.js)
        wrapper = os.path.join(bindir, "devcontainer")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n")
            f.write('case "$0" in\n')
            f.write('  */*) wrapper_path=$0 ;;\n')
            f.write('  *) wrapper_path=$(command -v "$0") || exit 127 ;;\n')
            f.write('esac\n')
            f.write('script_dir=$(CDPATH= cd -- "$(dirname -- "$wrapper_path")" && pwd)\n')
            f.write('exec node "$script_dir/../lib/devcontainer/devcontainer.js" "$@"\n')
        os.chmod(wrapper, 0o755)

        # Copy license
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["lib"]
        # Ensure node is in PATH at runtime (wrapper script calls 'node')
        self.runenv_info.prepend_path("PATH", "/data/service/hnp/bin")
