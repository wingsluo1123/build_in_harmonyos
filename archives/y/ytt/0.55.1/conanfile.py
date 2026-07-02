#!/usr/bin/env python3
"""Conan recipe — ytt 0.55.1 (Go project).

ytt is a Go language YAML templating tool from Carvel.
Build system: go build (not autotools/cmake).
Uses vendored dependencies (vendor/ directory).

Key OHOS adaptations:
- GODEBUG=mmap=0: Disable Go linker mmap output (OHOS SELinux restriction)
- Binary signing: Output ELF must be signed with binary-sign-tool
- go.mod version downgrade: 1.26.3 → 1.24.0 (match available signed Go toolchain)
"""
import os
import shlex
import shutil
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class YttConan(ConanFile):
    name = "ytt"
    version = "0.55.1"
    description = "ytt is a YAML templating tool from Carvel Dev"
    license = "Apache-2.0"
    homepage = "https://carvel.dev/ytt"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Go binary, no runtime dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # Go uses its own build system, no CMake/Autotools toolchain needed

    def build(self):
        apply_conandata_patches(self)

        # R32: Platform check — settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}. Only Linux and OHOS are supported.")

        # Determine GOOS and GOARCH from Conan settings (not hardcoded)
        # OHOS uses Linux kernel, so GOOS=linux for both
        goos = "linux"  # Both Linux and OHOS use linux GOOS
        arch_map = {
            "armv8": "arm64",
            "arm64": "arm64",
            "x86_64": "amd64",
            "x86": "386",
        }
        goarch = arch_map.get(str(self.settings.arch), "arm64")

        # Modify go.mod to match available Go toolchain
        go_mod = os.path.join(self.source_folder, "go.mod")
        if os.path.exists(go_mod):
            with open(go_mod, "r") as f:
                content = f.read()
            content = content.replace("go 1.26.3", "go 1.24.0")
            with open(go_mod, "w") as f:
                f.write(content)

        # Find Go binary
        go_bin = shutil.which("go")
        if not go_bin:
            for candidate in [
                os.path.expanduser("~/goinstall/go/bin/go"),
                "/storage/Users/currentUser/goinstall/go/bin/go",
            ]:
                if os.path.exists(candidate):
                    go_bin = candidate
                    break
        if not go_bin:
            raise Exception("Go binary not found in PATH or common locations")

        # Determine GOROOT
        goroot = os.environ.get("GOROOT", "")
        if not goroot:
            goroot = os.path.dirname(os.path.dirname(go_bin))

        # Build environment as list of KEY=VALUE strings (Conan 2.x format)
        gocache = os.environ.get("GOCACHE", os.path.join(os.environ.get("TMPDIR", "/tmp"), "go-cache"))
        gopath = os.environ.get("GOPATH", os.path.join(os.path.expanduser("~"), "go"))
        
        build_env = [
            "GODEBUG=mmap=0",          # Critical: OHOS SELinux restricts Go linker mmap
            "GOTOOLCHAIN=local",        # Don't try to download newer Go
            "CGO_ENABLED=0",            # Pure Go, no C dependencies
            "GOOS={}".format(goos),
            "GOARCH={}".format(goarch),
            "GOPATH={}".format(gopath),
            "GOCACHE={}".format(gocache),
            "GOROOT={}".format(goroot),
        ]

        # Build ytt with version injection - must run from source folder
        ldflags = "-X carvel.dev/ytt/pkg/version.Version=0.55.1"
        output_path = os.path.join(self.build_folder, "ytt")
        cmd = "{go} build -mod=vendor -ldflags {ldflags} -trimpath -o {output} ./cmd/ytt".format(
            go=shlex.quote(go_bin),
            ldflags=shlex.quote(ldflags),
            output=shlex.quote(output_path),
        )
        
        # Run from source folder
        self.run(cmd, cwd=self.source_folder, env=build_env)

        # Ensure execute permission
        os.chmod(output_path, 0o770)

        # Sign the binary for OHOS execution (if binary-sign-tool available)
        sign_tool = shutil.which("binary-sign-tool")
        if sign_tool:
            module_json = os.path.join(self.source_folder, "module.json")
            if not os.path.exists(module_json):
                with open(module_json, "w") as f:
                    f.write('{"module":{"name":"ytt","type":"feature","deviceTypes":["default"]}}')
            signed_path = output_path + ".signed"
            sign_cmd = '{tool} sign -keyAlias "default" -signAlg SHA256withECDSA -inFile {input} -outFile {output} -selfSign 1 -moduleFile {module}'.format(
                tool=shlex.quote(sign_tool),
                input=shlex.quote(output_path),
                output=shlex.quote(signed_path),
                module=shlex.quote(module_json),
            )
            self.run(sign_cmd, env=build_env)
            # Replace original with signed version, preserving permissions
            shutil.move(signed_path, output_path)
            os.chmod(output_path, 0o770)
        else:
            self.output.warning("binary-sign-tool not found, binary will not be executable on OHOS")

    def package(self):
        copy(self, "ytt", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Ensure execute permission on the packaged binary
        ytt_path = os.path.join(self.package_folder, "bin", "ytt")
        if os.path.exists(ytt_path):
            os.chmod(ytt_path, 0o770)
            # Re-sign the binary in the package folder (signature may be lost on copy)
            sign_tool = shutil.which("binary-sign-tool")
            if sign_tool:
                module_json = os.path.join(self.package_folder, "module.json")
                if not os.path.exists(module_json):
                    with open(module_json, "w") as f:
                        f.write('{"module":{"name":"ytt","type":"feature","deviceTypes":["default"]}}')
                signed_path = ytt_path + ".signed"
                sign_cmd = '{tool} sign -keyAlias "default" -signAlg SHA256withECDSA -inFile {input} -outFile {output} -selfSign 1 -moduleFile {module}'.format(
                    tool=shlex.quote(sign_tool),
                    input=shlex.quote(ytt_path),
                    output=shlex.quote(signed_path),
                    module=shlex.quote(module_json),
                )
                self.run(sign_cmd)
                shutil.move(signed_path, ytt_path)
                os.chmod(ytt_path, 0o770)

    def package_info(self):
        self.cpp_info.libs = []  # Go binary, no libraries
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
