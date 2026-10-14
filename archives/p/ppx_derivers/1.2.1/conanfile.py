#!/usr/bin/env python3
"""Conan recipe — ppx_derivers 1.2.1

ppx_derivers is a tiny shared registry that lets ppx_deriving and
ppx_type_conv interoperate when linked into the same PPX driver
(a dependency of ppxlib).

OHOS adaptations (pattern proven by camlp-streams 5.0.1 / csexp in this
registry):
  - Registry-provided OCaml 4.14.1 + dune 3.17.0 toolchain (R36).
  - OCAMLLIB / CAML_LD_LIBRARY_PATH / PATH injected from the dependency
    package folders (ocamlc -where returns a stale build-time path after
    the conan cache is relocated).
  - Defensive launcher-shebang fix for the ocaml package scripts whose
    absolute interpreter path may be dangling after cache relocation.
  - The dune @install tree is entirely relative symlinks into _build/
    (dangling after a plain copy, problematic on HMDFS) — package()
    dereferences every symlink and copies real files only.
  - R51: upstream has no test suite (src/ only, no test/ directory;
    verified against the v1.2.1 tarball listing). Adaptation regression
    coverage is provided by the test_package consumer cases.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class PpxDeriversConan(ConanFile):
    name = "ppx_derivers"
    version = "1.2.1"
    description = "Shared [@@deriving] plugin registry for PPX tooling"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ocaml-ppx/ppx_derivers"
    url = "https://github.com/ocaml-ppx/ppx_derivers"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # OCaml archives (cma/cmxa/a/cmxs) are static by nature; shared=False is
    # the only meaningful value and does not change the build.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # OCaml toolchain + dune build system, both registry-provided (R36).
        # Declared as requires (following the camlp-streams 5.0.1 precedent)
        # so consumers automatically get the toolchain.
        self.requires("ocaml/4.14.1.1.2")
        self.requires("dune/3.17.0")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def export_sources(self):
        export_conandata_patches(self)

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

        self._fix_launcher_shebangs(ocaml_bin)

        env_prefix = (
            f"OCAMLLIB={shlex.quote(ocaml_lib)} "
            f"CAML_LD_LIBRARY_PATH={shlex.quote(os.path.join(ocaml_lib, 'stublibs'))} "
            f"PATH={shlex.quote(ocaml_bin)}:{shlex.quote(dune_bin)}:$PATH "
        )
        self.run(f"{env_prefix} dune build -p ppx_derivers @install",
                 env="conanbuild")

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
        install_lib = os.path.join(
            self.build_folder, "_build", "install", "default", "lib", "ppx_derivers")
        if not os.path.isdir(install_lib):
            raise ConanException(f"dune install tree missing: {install_lib}")
        lib_dir = os.path.join(self.package_folder, "lib", "ocaml", "ppx_derivers")
        self._copy_real_tree(install_lib, lib_dir)

        for root, _dirs, files in os.walk(lib_dir):
            for f in files:
                p = os.path.join(root, f)
                if os.path.islink(p) or not os.path.isfile(p):
                    raise ConanException(f"package artifact is not a real file: {p}")
                if os.path.getsize(p) == 0:
                    raise ConanException(f"package artifact is empty: {p}")

        for mandatory in ("ppx_derivers.cma", "ppx_derivers.cmxa",
                          "ppx_derivers.cmxs", "ppx_derivers.a",
                          "ppx_derivers.cmi", "META"):
            if not os.path.isfile(os.path.join(lib_dir, mandatory)):
                raise ConanException(f"mandatory artifact missing: {mandatory}")

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
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib/ocaml/ppx_derivers"]
        self.cpp_info.includedirs = ["lib/ocaml/ppx_derivers"]
        # OCaml consumers (dune/ocamlc) locate the library via OCAMLPATH.
        self.env_info.OCAMLPATH.append(
            os.path.join(self.package_folder, "lib", "ocaml"))
