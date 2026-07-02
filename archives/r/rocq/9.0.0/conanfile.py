#!/usr/bin/env python3
"""Conan recipe for Rocq Prover 9.0.0 (formerly Coq).

Rocq 9.0.0 is the first release after the Coq -> Rocq renaming.
It uses the Dune build system (not autotools).

Build: dune build --root . -j1 rocq-runtime.install coq-core.install coqide-server.install
Install: manual copy from _build/install/default/ (dune install has path traversal issues on OHOS)

Platform notes:
  - OHOS: native ELF binaries are blocked by security mechanism; bytecode workers used
  - Findlib native libs (.cmxa) must be built from source (findlib installed as bytecode-only)

System dependencies (pre-installed, not managed by Conan):
  - OCaml 4.14.1 (bytecode)
  - Dune 3.17.0
  - Findlib 1.9.8
  - ZArith 1.14
  - Menhir 20260209
  - GMP 6.3.0
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, unzip


class RocqConan(ConanFile):
    name = "rocq"
    version = "9.0.0"
    description = "The Rocq Prover (formerly Coq) — interactive theorem prover and proof assistant"
    license = "LGPL-2.1-only"
    homepage = "https://coq.inria.fr/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # No Conan-managed dependencies — all build deps are system-installed

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Build in-source (Dune uses _build/ internally)
        self.folders.build = "."
        self.folders.generators = "generators"
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

    def source(self):
        # Try local tarball first (for OHOS where GitHub download may fail due to SSL)
        local_tarball = os.environ.get("ROCQ_TARBALL", "")
        if not local_tarball:
            candidates = [
                os.path.join(os.path.expanduser("~/tmp/builds"), f"rocq-{self.version}.tar.gz"),
                os.path.join(os.path.expanduser("~"), "tmp", "builds", f"rocq-{self.version}.tar.gz"),
            ]
            for c in candidates:
                if os.path.isfile(c):
                    local_tarball = c
                    break

        if local_tarball and os.path.isfile(local_tarball):
            # Copy local tarball to source folder and extract with strip_root
            tarball_name = f"rocq-{self.version}.tar.gz"
            copy(self, tarball_name, os.path.dirname(local_tarball), self.source_folder)
            local_copy = os.path.join(self.source_folder, tarball_name)
            unzip(self, local_copy, self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        prefix = os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")

        # Step 1: Configure (use sh to avoid execute permission issues on OHOS)
        self.run(f"sh ./configure -prefix {prefix} -no-ask "
                 f"-native-compiler no -bytecode-compiler yes",
                 env="conanrun")

        # Step 2: Build packages (single-threaded for OHOS)
        targets = "rocq-runtime.install coq-core.install coqide-server.install"
        self.run(f"dune build --root . -j1 {targets}", env="conanrun")

    def package(self):
        # Manual copy from _build/install/default/ (dune install has path issues on OHOS)
        install_dir = os.path.join(self.build_folder, "_build", "install", "default")
        if not os.path.isdir(install_dir):
            install_dir = os.path.join(self.source_folder, "_build", "install", "default")

        if os.path.isdir(install_dir):
            for subdir in ["bin", "lib", "share", "man", "doc"]:
                src = os.path.join(install_dir, subdir)
                dst = os.path.join(self.package_folder, subdir)
                if os.path.isdir(src):
                    os.makedirs(dst, exist_ok=True)
                    for item in os.listdir(src):
                        s = os.path.join(src, item)
                        d = os.path.join(dst, item)
                        if os.path.islink(s):
                            target = os.path.realpath(s)
                            if os.path.isfile(target):
                                shutil.copy2(target, d)
                        elif os.path.isdir(s):
                            shutil.copytree(s, d, symlinks=False, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s, d)

        # OHOS: Replace native rocqworker with bytecode version (R7 security workaround)
        worker_native = os.path.join(self.package_folder, "lib", "rocq-runtime", "rocqworker")
        worker_byte = os.path.join(self.package_folder, "lib", "rocq-runtime", "rocqworker.byte")
        if self.settings.os in ("Linux", "OHOS"):
            if os.path.isfile(worker_byte):
                if os.path.exists(worker_native):
                    os.remove(worker_native)
                shutil.copy2(worker_byte, worker_native)
                os.chmod(worker_native, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        rocqlib = os.path.join(self.package_folder, "lib", "rocq-runtime")
        self.runenv_info.define("ROCQLIB", rocqlib)
        stublibs = os.path.join(self.package_folder, "lib", "stublibs")
        self.runenv_info.append("CAML_LD_LIBRARY_PATH", stublibs)
        # OCAMLPATH must include rocq-runtime lib dir for findlib to find the package
        self.runenv_info.append("OCAMLPATH", rocqlib)
        self.runenv_info.append("OCAMLPATH", os.path.join(self.package_folder, "lib"))
