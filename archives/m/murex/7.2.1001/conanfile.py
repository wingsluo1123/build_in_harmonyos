#!/usr/bin/env python3
"""Conan recipe for murex 7.2.1001."""

import os
import platform
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout


class MurexConan(ConanFile):
    name = "murex"
    version = "7.2.1001"
    description = "Bash-like shell designed for greater command-line productivity and safer scripts"
    license = "GPL-2.0-only"
    homepage = "https://github.com/lmorg/murex"
    url = "https://github.com/lmorg/murex"
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
        env = self._go_environment(go)
        binary = self.conan_data["build"]["binary"]
        output_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, binary)
        ldflags = self.conan_data["build"].get("ldflags", "-s -w")
        command = [
            go,
            "build",
            "-trimpath",
            "-ldflags",
            ldflags,
            "-o",
            output_path,
            self.conan_data["build"].get("main", "."),
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
             dst=os.path.join(self.package_folder, "share", "doc", "murex"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _go_environment(self, go):
        env = os.environ.copy()
        cache_root = os.path.join(self.build_folder, "go-cache")
        go_root = os.path.dirname(os.path.dirname(os.path.abspath(go)))
        env.update({
            "CGO_ENABLED": "0",
            "GOOS": "linux",
            "GOARCH": self._goarch(),
            "GOCACHE": os.path.join(cache_root, "build"),
            "GOMODCACHE": os.path.join(cache_root, "mod"),
            "GOPATH": os.path.join(cache_root, "gopath"),
            "GOPROXY": env.get("GOPROXY", "https://goproxy.cn,direct"),
            "GOROOT": go_root,
            "GOTOOLCHAIN": "local",
            "PATH": os.path.dirname(go) + os.pathsep + env.get("PATH", ""),
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
        return self._bootstrapped_go_executable()

    def _bootstrapped_go_executable(self):
        go_toolchain = self.conan_data["go_toolchain"]
        host_key = f"linux-{self._host_goarch()}"
        package = go_toolchain[host_key]
        tools_dir = os.path.join(self.build_folder, "go-toolchain")
        archive = os.path.join(tools_dir, package["filename"])
        go_root = os.path.join(tools_dir, "go")
        go = os.path.join(go_root, "bin", "go")
        if not os.path.isfile(go):
            os.makedirs(tools_dir, exist_ok=True)
            download(self, package["url"], archive, sha256=package["sha256"])
            self.run(f'tar xzf "{archive}" -C "{tools_dir}"')
        self._ensure_go_toolchain_permissions(tools_dir, go_root)
        if not os.access(go, os.X_OK):
            raise ConanInvalidConfiguration(
                f"Bootstrapped Go executable is not runnable after chmod: {go}"
            )
        return go

    def _ensure_go_toolchain_permissions(self, tools_dir, go_root):
        # Some OHOS/HMDFS workers unpack cached tarballs without traversable
        # directory bits, so normalize the whole toolchain tree first instead
        # of touching only go/bin and go/pkg/tool.
        for directory in (tools_dir, go_root):
            if os.path.isdir(directory):
                self._chmod_read_exec(directory, is_dir=True)
        executable_prefixes = (
            os.path.join(go_root, "bin"),
            os.path.join(go_root, "pkg", "tool"),
        )
        for dirpath, dirnames, filenames in os.walk(go_root):
            self._chmod_read_exec(dirpath, is_dir=True)
            for dirname in dirnames:
                self._chmod_read_exec(os.path.join(dirpath, dirname), is_dir=True)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                executable = any(
                    os.path.commonpath([path, root]) == root
                    for root in executable_prefixes
                    if os.path.isdir(root)
                )
                self._chmod_read_exec(path, executable=executable)

    def _chmod_read_exec(self, path, is_dir=False, executable=False):
        mode = os.stat(path).st_mode
        read_exec = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        if executable or is_dir:
            read_exec |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if is_dir:
            mode |= stat.S_IWUSR
        if not is_dir:
            mode |= stat.S_IWUSR
        try:
            os.chmod(path, mode | read_exec)
        except PermissionError:
            # HMDFS: chmod on non-owned files fails even when we only add bits.
            # If the file is already executable (or readable for non-exec), skip.
            if not (executable or is_dir):
                raise
            if os.access(path, os.X_OK):
                return
            raise

    def _host_goarch(self):
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "amd64"
        if machine in ("aarch64", "arm64"):
            return "arm64"
        raise ConanInvalidConfiguration(f"Unsupported Go host architecture: {machine}")

