#!/usr/bin/env python3
"""Conan recipe for kubent (Kube No Trouble) — Go project.

kubent is a Kubernetes deprecation API checker built with Go.
It uses `go build` to compile a single static binary.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment


class KubentConan(ConanFile):
    name = "kubent"
    version = "latest"
    description = "Kube No Trouble — easily check your clusters for use of deprecated APIs"
    license = "MIT"
    homepage = "https://github.com/doitintl/kube-no-trouble"
    url = ""  # CI fills this

    settings = "os", "arch", "build_type", "compiler"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as e:
            # Fallback: use local copy when GitHub is unreachable (CI environment)
            import tarfile
            import hashlib
            self.output.warning(f"Download failed, trying local copy: {e}")
            local_tarball = os.path.expanduser("~/tmp/builds/kubent-latest.tar.gz")
            if not os.path.exists(local_tarball):
                local_tarball = os.path.join(os.environ.get("TMPDIR", "/tmp"), "builds", "kubent-latest.tar.gz")
            if os.path.exists(local_tarball):
                # Verify SHA256
                sha = hashlib.sha256(open(local_tarball, "rb").read()).hexdigest()
                expected = self.conan_data["sources"].get("sha256", "")
                if expected and sha != expected:
                    raise ConanInvalidConfiguration(
                        f"Local tarball SHA256 mismatch: {sha} != {expected}"
                    )
                # Extract
                with tarfile.open(local_tarball, "r:gz") as tf:
                    try:
                        tf.extractall(path=self.source_folder, filter="data")
                    except TypeError:
                        tf.extractall(path=self.source_folder)
                # Promote nested directory if needed
                import glob
                subdirs = [d for d in os.listdir(self.source_folder)
                           if os.path.isdir(os.path.join(self.source_folder, d))
                           and not d.startswith(".")]
                if len(subdirs) == 1:
                    subdir = os.path.join(self.source_folder, subdirs[0])
                    for item in os.listdir(subdir):
                        src = os.path.join(subdir, item)
                        dst = os.path.join(self.source_folder, item)
                        if os.path.exists(dst):
                            if os.path.isdir(dst):
                                shutil.rmtree(dst)
                            else:
                                os.remove(dst)
                        shutil.move(src, dst)
                    os.rmdir(subdir)
                self.output.info("Source extracted from local tarball")
            else:
                raise

    def validate(self):
        # R32: OHOS platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kubent is only supported on Linux and OHOS, not {self.settings.os}"
            )

    def generate(self):
        # Set Go environment for CI (proxy.golang.org and sum.golang.org unreachable)
        env = Environment()
        env.define("GOPROXY", "https://goproxy.cn,direct")
        env.define("GONOSUMDB", "*")
        env.define("GOSUMDB", "off")
        env.define("GOFLAGS", "-mod=mod")
        env.define("CGO_ENABLED", "0")
        envvars = env.vars(self)
        envvars.save_script("go_env")

    def build(self):
        apply_conandata_patches(self)
        # Find go binary
        go_bin = shutil.which("go")
        if not go_bin:
            # Try harmonybrew
            hb_go = os.path.expanduser("~/.harmonybrew/bin/go")
            if os.path.exists(hb_go):
                go_bin = hb_go
            else:
                raise ConanInvalidConfiguration(
                    "Go compiler not found. Install via: "
                    "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- go"
                )

        # Build the kubent binary
        ldflags = '-ldflags="-s -w -X main.version=latest -X main.gitSha=latest"'
        self.run(
            f'{go_bin} build {ldflags} -o bin/kubent ./cmd/kubent',
            env=["go_env"],
        )

    def package(self):
        copy(self, "kubent", src=os.path.join(self.build_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
