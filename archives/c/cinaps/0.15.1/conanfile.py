#!/usr/bin/env python3
"""Conan recipe — cinaps 0.15.1

Cinaps is a lightweight OCaml metaprogramming tool: it evaluates the OCaml
code embedded in special (*$ ... *) comments and keeps the following block in
sync with that output (expect-test style). ppxlib's upstream test suite runs
the cinaps binary over several source files, so the cinaps package is
required for ppxlib's `dune runtest` to execute the upstream tests on OHOS.

OHOS adaptations (pattern proven by camlp-streams 5.0.1 / sexplib0 0.17.0 /
ocaml-re 1.13.2 in this registry):
  - Registry-provided OCaml 4.14.1 + dune 3.17.0 toolchain (R36).
  - ocaml-re/1.13.2 (registry) provides the findlib `re` library this tool
    links against (and the empty `seq` stub that re's META requires).
  - OCAMLLIB / CAML_LD_LIBRARY_PATH / OCAMLPATH / PATH injected from the
    dependency package folders (ocamlc -where returns a stale build-time path
    after the conan cache is relocated).
  - Defensive launcher-shebang fix for the ocaml package scripts.
  - The dune @install tree is entirely relative symlinks into _build/
    (dangling after a plain copy, problematic on HMDFS) — package()
    dereferences every symlink and copies real files only.
  - R51: the upstream test/ directory requires ppx_jane (`(pps ppx_jane)`),
    i.e. the downstream ppxlib ecosystem — circular at the dependency stage.
    Not runnable in this registry; the packaged binary is exercised
    end-to-end by the test_package consumer cases (check mode, staged mode,
    negative control with a corrupted expectation block).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class CinapsConan(ConanFile):
    name = "cinaps"
    version = "0.15.1"
    description = "Trivial metaprogramming tool (in-comment evaluation + expectation sync)"
    license = "MIT"
    homepage = "https://github.com/ocaml-ppx/cinaps"
    url = "https://github.com/ocaml-ppx/cinaps"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OCaml toolchain + dune + re (findlib `re`), all registry-provided
        # (R36). Declared as requires (camlp-streams 5.0.1 precedent) so
        # consumers automatically get the toolchain.
        self.requires("ocaml/4.14.1.1.2")
        self.requires("dune/3.17.0")
        self.requires("ocaml-re/1.13.2")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        pass

    def build(self):
        # No patches for this version (upstream builds unmodified); the call
        # is kept so future patches flow through the standard pipeline.
        apply_conandata_patches(self)
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.2"]
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")
        dune_pkg = self.dependencies["dune/3.17.0"]
        dune_bin = os.path.join(dune_pkg.package_folder, "bin")
        re_root = os.path.join(
            self.dependencies["ocaml-re/1.13.2"].package_folder,
            "lib", "ocaml")

        self._fix_launcher_shebangs(ocaml_bin)

        env_prefix = (
            f"OCAMLLIB={shlex.quote(ocaml_lib)} "
            f"CAML_LD_LIBRARY_PATH={shlex.quote(os.path.join(ocaml_lib, 'stublibs'))} "
            f"OCAMLPATH={shlex.quote(re_root)} "
            f"PATH={shlex.quote(ocaml_bin)}:{shlex.quote(dune_bin)}:$PATH "
        )
        self.run(f"{env_prefix} dune build -p cinaps @install", env="conanbuild")

    def _fix_launcher_shebangs(self, ocaml_bin):
        """Rewrite dangling absolute shebangs in ocaml package launcher scripts."""
        for fname in os.listdir(ocaml_bin):
            fpath = os.path.join(ocaml_bin, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, "rb") as f:
                    data = f.read()
                if not data.startswith(b"#!"):
                    continue
                nl = data.index(b"\n")
                parts = data[:nl].decode(errors="replace")[2:].strip().split()
                if not parts or os.path.exists(parts[0]):
                    continue
                candidate = os.path.join(ocaml_bin, os.path.basename(parts[0]))
                if os.path.exists(candidate):
                    data = ("#!" + candidate).encode() + data[nl:]
                    with open(fpath, "wb") as f:
                        f.write(data)
                    self.output.info(f"Fixed shebang: {fname} -> {candidate}")
            except Exception as e:
                self.output.warning(f"Could not fix shebang for {fname}: {e}")

    def package(self):
        install_root = os.path.join(
            self.build_folder, "_build", "install", "default")
        bin_src = os.path.join(install_root, "bin", "cinaps")
        if not os.path.isfile(bin_src):
            raise ConanException(f"dune install binary missing: {bin_src}")

        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(bin_src, os.path.join(bin_dir, "cinaps"))
        os.chmod(os.path.join(bin_dir, "cinaps"), 0o755)

        lib_src = os.path.join(install_root, "lib", "cinaps")
        if not os.path.isdir(lib_src):
            raise ConanException(f"dune install tree missing: {lib_src}")
        lib_dir = os.path.join(self.package_folder, "lib", "ocaml", "cinaps")
        self._copy_real_tree(lib_src, lib_dir)

        for root, _dirs, files in os.walk(lib_dir):
            for f in files:
                p = os.path.join(root, f)
                if os.path.islink(p) or not os.path.isfile(p):
                    raise ConanException(f"package artifact is not a real file: {p}")
                if os.path.getsize(p) == 0:
                    raise ConanException(f"package artifact is empty: {p}")

        # The main `cinaps` library is private (no public_name), so dune
        # does not install it; consumers use the binary and the
        # `cinaps.runtime` sub-library only.
        for mandatory in ("META",
                          os.path.join("runtime", "cinaps_runtime.cma"),
                          os.path.join("runtime", "cinaps_runtime.cmxa")):
            if not os.path.isfile(os.path.join(lib_dir, mandatory)):
                raise ConanException(f"mandatory artifact missing: {mandatory}")
        if not os.path.isfile(os.path.join(self.package_folder, "bin", "cinaps")):
            raise ConanException("mandatory artifact missing: bin/cinaps")

    def _copy_real_tree(self, src, dst):
        """Copy a dune install tree dereferencing every symlink to a real file."""
        for root, _dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            out = os.path.join(dst, rel) if rel != "." else dst
            os.makedirs(out, exist_ok=True)
            for f in files:
                sp = os.path.join(root, f)
                if os.path.islink(sp):
                    tp = os.path.realpath(sp)
                    if not os.path.isfile(tp):
                        raise ConanException(f"dangling symlink in install tree: {sp}")
                    shutil.copy2(tp, os.path.join(out, f))
                elif os.path.isfile(sp):
                    shutil.copy2(sp, os.path.join(out, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/ocaml/cinaps"]
        self.cpp_info.includedirs = ["lib/ocaml/cinaps"]
        # Conan 2 environment API (Conan 1.x env_info is a deprecated
        # no-op): tool consumers need bin/ on PATH (build + run); OCaml
        # consumers of the cinaps.runtime library locate it via OCAMLPATH.
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.append_path(
            "OCAMLPATH", os.path.join(self.package_folder, "lib", "ocaml"))
        self.runenv_info.append_path(
            "OCAMLPATH", os.path.join(self.package_folder, "lib", "ocaml"))
