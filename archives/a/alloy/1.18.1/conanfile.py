#!/usr/bin/env python3
"""Conan recipe for alloy 1.18.1 (Go, OpenTelemetry Collector distribution).

Grafana Alloy — OpenTelemetry Collector distribution with programmable
pipelines. Pure Go (CGO_ENABLED=0) linux/arm64 static executable for
OHOS compatibility.

Pattern follows the murex Go recipe: fallback Go toolchain bootstrap,
OHOS signing of built binaries, Go caches/linker output under an hmfs
work root (HMDFS mmap restriction), upstream `go test ./...` before build.
"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout


class AlloyConan(ConanFile):
    name = "alloy"
    version = "1.18.1"
    description = ("Alloy — OpenTelemetry Collector distribution with "
                   "programmable pipelines (metrics/logs/traces/profiles)")
    license = "Apache-2.0"
    homepage = "https://grafana.com/oss/alloy"
    url = "https://github.com/grafana/alloy"
    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        go = self._go_executable()
        env = self._go_environment(go)
        self._run_upstream_tests(go, env)
        binary = self.conan_data["build"]["binary"]
        output_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, binary)
        link_output_path = self._go_link_output_path(binary)
        ldflags = self.conan_data["build"].get("ldflags", "-s -w")
        # alloy's main is the generated otel_engine module under collector/
        module_dir = os.path.join(self.source_folder,
                                  self.conan_data["build"].get("main", "collector"))
        command = [
            go, "build", "-trimpath", "-ldflags", ldflags,
            "-o", link_output_path, ".",
        ]
        subprocess.run(command, cwd=module_dir, env=env, check=True)
        shutil.copy2(link_output_path, output_path)
        self._chmod_exec(output_path)
        self._sign_ohos_executable(output_path)

    def _run_upstream_tests(self, go, env):
        command = [go, "test"]
        if self.settings.os == "OHOS":
            command.append(f"-exec={self._go_test_exec_wrapper(env)}")
        command.append("./...")
        subprocess.run(command, cwd=self.source_folder, env=env, check=True)

    def _go_test_exec_wrapper(self, env):
        signer = self._find_binary_sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute Go tests on OHOS")
        wrapper = os.path.join(self._go_work_root(), "go-test-exec.sh")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as script:
            script.write(
                "#!/bin/sh\n"
                "set -eu\n"
                "test_binary=\"$1\"\n"
                "shift\n"
                "\"$OHOS_GO_TEST_SIGNER\" sign "
                "-inFile \"$test_binary\" -outFile \"$test_binary\" "
                "-selfSign 1\n"
                "exec \"$test_binary\" \"$@\"\n"
            )
        self._chmod_exec(wrapper)
        env["OHOS_GO_TEST_SIGNER"] = signer
        return wrapper

    def package(self):
        binary = self.conan_data["build"]["binary"]
        copy(self, binary, src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "alloy"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------
    # Go environment / work root (HMDFS mmap restriction workaround)
    # ------------------------------------------------------------------

    def _go_environment(self, go):
        env = os.environ.copy()
        cache_root = self._go_work_root()
        go_root = os.path.dirname(os.path.dirname(os.path.abspath(go)))
        env.update({
            "CGO_ENABLED": "0",
            "GOOS": "linux",
            "GOARCH": self._goarch(),
            "GOCACHE": os.path.join(cache_root, "cache", "build"),
            "GOMODCACHE": os.path.join(cache_root, "cache", "mod"),
            "GOPATH": os.path.join(cache_root, "cache", "gopath"),
            "GOPROXY": env.get("GOPROXY", "https://goproxy.cn,direct"),
            "GOROOT": go_root,
            "GOTOOLCHAIN": "local",
            "PATH": os.path.dirname(go) + os.pathsep + env.get("PATH", ""),
            "TMPDIR": os.path.join(cache_root, "tmp"),
            "GOTMPDIR": os.path.join(cache_root, "gotmp"),
        })
        for path in ("GOCACHE", "GOMODCACHE", "GOPATH", "TMPDIR", "GOTMPDIR"):
            os.makedirs(env[path], exist_ok=True)
        return env

    def _go_link_output_path(self, binary):
        output_dir = os.path.join(self._go_work_root(), "out")
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, binary)

    def _go_work_root(self):
        if self.settings.os == "OHOS":
            candidates = [
                os.environ.get("OHOS_GO_BUILD_ROOT"),
                "/data/storage/el2/base/cache",
                "/data/storage/el2/base/haps/entry/files",
                os.environ.get("TMPDIR"),
            ]
        else:
            candidates = [
                os.environ.get("ALLOY_GO_BUILD_ROOT"),
                os.path.join(os.path.dirname(os.path.abspath(self.build_folder)),
                             "go-work"),
                os.environ.get("TMPDIR"),
            ]
        for candidate in candidates:
            if not candidate:
                continue
            root = os.path.join(candidate, "conan-go-build",
                                f"{self.name}-{self.version}")
            if self._is_under_source_tree(root):
                continue
            try:
                os.makedirs(root, exist_ok=True)
                return root
            except OSError:
                continue
        raise ConanInvalidConfiguration(
            "No writable Go build root is available for linker output")

    def _is_under_source_tree(self, path):
        try:
            source = os.path.abspath(self.source_folder)
            target = os.path.abspath(path)
            return os.path.commonpath([source, target]) == source
        except (OSError, ValueError):
            return False

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "arm64", "aarch64"):
            return "arm64"
        if arch in ("x86_64", "amd64"):
            return "amd64"
        if arch.startswith("armv7"):
            return "arm"
        raise ConanInvalidConfiguration(f"Unsupported Go arch mapping: {arch}")

    def _host_goarch(self):
        import platform
        m = platform.machine().lower()
        if m in ("aarch64", "arm64"):
            return "arm64"
        return "amd64"

    def _go_executable(self):
        candidates = [
            os.environ.get("GO"),
            shutil.which("go"),
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go1.26.5/bin/go"),
            "/data/storage/el2/base/cache/harmonybrew/bin/go",
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
        tools_dir = os.path.join(self._go_work_root(), "go-toolchain")
        archive = os.path.join(tools_dir, package["filename"])
        go_root = os.path.join(tools_dir, "go")
        go = os.path.join(go_root, "bin", "go")
        if not os.path.isfile(go):
            os.makedirs(tools_dir, exist_ok=True)
            download(self, package["url"], archive, sha256=package["sha256"])
            result = self.run(
                f'tar xzf "{archive}" -C "{tools_dir}"', ignore_errors=True)
            if result != 0:
                raise ConanInvalidConfiguration(
                    f"Failed to extract bootstrapped Go toolchain archive: {archive}")
        self._ensure_go_toolchain_permissions(tools_dir, go_root)
        return go

    def _ensure_go_toolchain_permissions(self, tools_dir, go_root):
        for directory in (tools_dir, go_root):
            if os.path.isdir(directory):
                self._chmod_read_exec(directory, is_dir=True)
        for dirpath, _dirnames, filenames in os.walk(go_root):
            self._chmod_read_exec(dirpath, is_dir=True)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if os.access(path, os.X_OK) or self._is_elf(path):
                    self._chmod_read_exec(path, is_dir=False)
        if not os.access(go_root, os.X_OK | os.R_OK):
            raise ConanInvalidConfiguration(
                "Go toolchain root not traversable after chmod")

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _chmod_read_exec(self, path, is_dir=False):
        try:
            if is_dir:
                os.chmod(path, 0o755)
            else:
                os.chmod(path, 0o755)
        except OSError:
            pass

    def _chmod_exec(self, path):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/storage/el2/base/cache/harmonybrew/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_ohos_executable(self, path):
        signer = self._find_binary_sign_tool()
        if not signer:
            # OHOS requires signed binaries to execute; without the tool the
            # package is still built but marked un-runnable (CI validates).
            self.output.warning(
                "binary-sign-tool not found; built binary left unsigned")
            return
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path,
             "-selfSign", "1"],
            check=True)
