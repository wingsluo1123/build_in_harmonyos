#!/usr/bin/env python3
"""Conan recipe for aliyun-cli — Alibaba Cloud CLI tool.

Go-based CLI application. Uses go build with version injection via ldflags.
The aliyun-openapi-meta submodule must be populated from a separate download
(it is not included in the GitHub release tarball).

R38: Command-line tool — requires commands.json at software level.
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AliyunCliConan(ConanFile):
    name = "aliyun-cli"
    version = "3.0.229"
    description = "Alibaba Cloud CLI — universal command-line tool for Alibaba Cloud services"
    license = "Apache-2.0"
    homepage = "https://github.com/aliyun/aliyun-cli"
    url = ""

    package_type = "application"

    settings = "os", "arch", "build_type", "compiler"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # Populate aliyun-openapi-meta submodule (not in GitHub tarball)
        meta_dir = Path(self.source_folder) / "aliyun-openapi-meta"
        if meta_dir.exists() and not any(meta_dir.iterdir()):
            meta_data = self.conan_data.get("submodule", {})
            if meta_data:
                meta_tmp = Path(self.source_folder) / "meta_tmp"
                # Try original URL first, then ghfast.top mirror (E017)
                urls = [meta_data["url"]]
                if "github.com" in meta_data["url"]:
                    urls.append(f"https://ghfast.top/{meta_data['url']}")
                for url in urls:
                    try:
                        get(self, url, sha256=meta_data.get("sha256", ""),
                            strip_root=True, destination=str(meta_tmp))
                        break
                    except Exception:
                        if url == urls[-1]:
                            raise
                        continue
                # Copy contents into the submodule directory
                for item in meta_tmp.iterdir():
                    dest = meta_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
                shutil.rmtree(meta_tmp)

    def build(self):
        apply_conandata_patches(self)

        # Locate Go binary
        go_bin = shutil.which("go")
        if not go_bin:
            # Try common HarmonyOS locations
            candidates = [
                os.path.expanduser("~/usr/local/go/bin/go"),
                "/data/storage/el2/base/haps/entry/files/carapace-conan-go/1.11.7/go-sdk/go1.24.0-arm64/go/bin/go",
            ]
            for c in candidates:
                if os.path.isfile(c) and os.access(c, os.X_OK):
                    go_bin = c
                    break
        if not go_bin:
            raise Exception("Go binary not found on PATH or known locations")

        # Set up Go environment on ext2 (HMDFS causes mmap failures)
        ext2_base = "/data/storage/el2/base/haps/entry/files"
        go_cache = os.path.join(ext2_base, "aliyun-cli-conan-go", "3.0.229", "go-build-cache")
        go_mod_cache = os.path.join(ext2_base, "aliyun-cli-conan-go", "3.0.229", "go-mod-cache")
        link_out = os.path.join(ext2_base, "aliyun-cli-conan-go", "3.0.229", "link-out")
        tmp_dir = os.path.join(ext2_base, "aliyun-cli-conan-go", "3.0.229", "tmp")
        for d in [go_cache, go_mod_cache, link_out, tmp_dir]:
            os.makedirs(d, exist_ok=True)

        env = os.environ.copy()
        env["CGO_ENABLED"] = "0"
        env["GOOS"] = "linux"
        env["GOARCH"] = "arm64"
        env["GOPROXY"] = "https://goproxy.cn,direct"
        env["GOTOOLCHAIN"] = "local"
        env["GOCACHE"] = go_cache
        env["GOPATH"] = go_mod_cache
        env["TMPDIR"] = tmp_dir
        env["GOROOT"] = os.path.dirname(os.path.dirname(go_bin))

        output_bin = os.path.join(link_out, "aliyun")
        version = str(self.version)

        ldflags = f"-s -w -X 'github.com/aliyun/aliyun-cli/cli.Version={version}'"
        cmd = [go_bin, "build", "-ldflags", ldflags, "-o", output_bin, "main/main.go"]

        self.output.info(f"Building: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, cwd=self.source_folder,
                                capture_output=True, text=True, timeout=600)
        if result.stdout:
            self.output.info(result.stdout)
        if result.stderr:
            self.output.warning(result.stderr)
        if result.returncode != 0:
            raise Exception(f"go build failed with exit code {result.returncode}")

        # Sign ELF binary for HarmonyOS execution
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(sign_tool) and os.path.isfile(objcopy):
            # Remove old signature
            subprocess.run([objcopy, "--remove-section", ".codesign", output_bin],
                           capture_output=True, timeout=30)
            # Sign
            tmp_signed = output_bin + ".signed.tmp"
            subprocess.run([sign_tool, "sign", "-inFile", output_bin,
                            "-outFile", tmp_signed, "-selfSign", "1"],
                           capture_output=True, timeout=30)
            if os.path.isfile(tmp_signed):
                shutil.move(tmp_signed, output_bin)
                os.chmod(output_bin, 0o755)

    def package(self):
        # Find the built binary
        ext2_base = "/data/storage/el2/base/haps/entry/files"
        link_out = os.path.join(ext2_base, "aliyun-cli-conan-go", "3.0.229", "link-out")
        aliyun_bin = os.path.join(link_out, "aliyun")

        if os.path.isfile(aliyun_bin):
            copy(self, "aliyun", link_out, os.path.join(self.package_folder, "bin"))
        else:
            # Fallback: check source folder
            copy(self, "aliyun", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
