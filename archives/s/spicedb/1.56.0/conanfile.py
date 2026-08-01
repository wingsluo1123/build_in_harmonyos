#!/usr/bin/env python3
"""Conan recipe for spicedb 1.56.0."""

import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SpicedbConan(ConanFile):
    name = "spicedb"
    version = "1.56.0"
    description = "Open-source permissions database inspired by Google Zanzibar"
    license = "Apache-2.0"
    homepage = "https://github.com/authzed/spicedb"
    url = "https://github.com/authzed/spicedb"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        self._goarch()

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        go = self._go_executable()
        env = self._go_environment()
        binary = self.conan_data["build"]["binary"]
        output_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, binary)
        command = [
            go,
            "build",
            "-trimpath",
            "-ldflags",
            self.conan_data["build"]["ldflags"],
            "-o",
            output_path,
            self.conan_data["build"]["main"],
        ]
        subprocess.run(command, cwd=self.source_folder, env=env, check=True)
        os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)

    def package(self):
        binary = self.conan_data["build"]["binary"]
        copy(self, binary, src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "spicedb"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _go_environment(self):
        env = os.environ.copy()
        cache_root = os.path.join(self.build_folder, "go-cache")
        env.update({
            "CGO_ENABLED": "0",
            "GOOS": "linux",
            "GOARCH": self._goarch(),
            "GOCACHE": os.path.join(cache_root, "build"),
            "GOMODCACHE": os.path.join(cache_root, "mod"),
            "GOPATH": os.path.join(cache_root, "gopath"),
            "GOPROXY": env.get("GOPROXY", "https://goproxy.cn,direct"),
            "TMPDIR": os.path.join(self.build_folder, "tmp"),
        })
        for path in ("GOCACHE", "GOMODCACHE", "GOPATH", "TMPDIR"):
            os.makedirs(env[path], exist_ok=True)
        return env

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "arm64", "aarch64"):
            return "arm64"
        if arch in ("x86_64", "amd64"):
            return "amd64"
        if arch.startswith("armv7"):
            return "arm"
        raise ConanInvalidConfiguration(f"Unsupported Go arch mapping: {arch}")

    def _go_executable(self):
        candidates = [
            os.environ.get("GO"),
            shutil.which("go"),
            os.path.expanduser("~/usr/local/go1263/bin/go"),
            os.path.expanduser("~/sdk/go1.26.3/bin/go"),
            "/data/storage/el2/base/cache/harmonybrew/bin/go",
            "/data/storage/el2/base/cache/usr/local/go1263/bin/go",
            "/usr/local/go/bin/go",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "Go toolchain not found; expected go in PATH, GO, harmonybrew, "
            "or ~/usr/local/go1263/bin/go on the OHOS CI worker"
        )
