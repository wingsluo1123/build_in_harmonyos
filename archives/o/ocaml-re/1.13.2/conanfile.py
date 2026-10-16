#!/usr/bin/env python3
"""Conan recipe — ocaml-re (re) 1.13.2

re is a pure OCaml regular expression library (Perl / Posix / Emacs / Glob /
Str syntaxes). It is the build-time and runtime dependency of the cinaps
tool, which in turn is required by ppxlib's upstream test suite.

OHOS adaptations (pattern proven by camlp-streams 5.0.1 / sexplib0 0.17.0 in
this registry):
  - Registry-provided OCaml 4.14.1 + dune 3.17.0 toolchain (R36).
  - OCAMLLIB / CAML_LD_LIBRARY_PATH / PATH injected from the dependency
    package folders (ocamlc -where returns a stale build-time path after the
    conan cache is relocated).
  - seq compatibility stub: OCaml 4.14 merged Seq into the Stdlib and the
    registry findlib package ships no `seq` META, while re's dune file and
    its generated META both require the `seq` findlib library. The recipe
    builds an empty seq.cma / seq.cmxa plus META in a private site-lib
    (.ohc-site) for its own build and installs the same stub under
    lib/ocaml/seq/ of the package, so downstream consumers (cinaps, ppxlib
    tests) transparently resolve re's `requires = "seq"`.
  - Defensive launcher-shebang fix for the ocaml package scripts whose
    absolute interpreter path may be dangling after cache relocation.
  - The dune @install tree is entirely relative symlinks into _build/
    (dangling after a plain copy, problematic on HMDFS) — package()
    dereferences every symlink and copies real files only.
  - R51: the upstream test suite (lib_test/{expect,fort_unit,str}) depends on
    the unpublished ppx_expect / ppx_inline_test / base / ounit2 stack
    (ppx_expect belongs to the downstream ppxlib ecosystem — circular at the
    dependency stage). Not runnable in this registry; adaptation regression
    coverage is provided by the test_package consumer cases.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class OcamlReConan(ConanFile):
    name = "ocaml-re"
    version = "1.13.2"
    description = "Pure OCaml regular expression library (Perl/Posix/Emacs/Glob/Str)"
    license = "LGPL-2.1-or-later WITH OCaml-LGPL-linking-exception"
    homepage = "https://github.com/ocaml/ocaml-re"
    url = "https://github.com/ocaml/ocaml-re"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # OCaml archives (cma/cmxa/a/cmxs) are static by nature; shared=False is
    # the only meaningful value and does not change the build.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OCaml toolchain + dune build system, both registry-provided (R36).
        # Declared as requires (following the camlp-streams 5.0.1 precedent)
        # so consumers automatically get the toolchain.
        self.requires("ocaml/4.14.1.1.2")
        self.requires("dune/3.17.0")

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

        self._fix_launcher_shebangs(ocaml_bin)

        site = os.path.join(self.build_folder, ".ohc-site")
        self._make_seq_stub(site, ocaml_bin, ocaml_lib)

        env_prefix = (
            f"OCAMLLIB={shlex.quote(ocaml_lib)} "
            f"CAML_LD_LIBRARY_PATH={shlex.quote(os.path.join(ocaml_lib, 'stublibs'))} "
            f"OCAMLPATH={shlex.quote(site)} "
            f"PATH={shlex.quote(ocaml_bin)}:{shlex.quote(dune_bin)}:$PATH "
        )
        self.run(f"{env_prefix} dune build -p re @install", env="conanbuild")

    def _make_seq_stub(self, site, ocaml_bin, ocaml_lib):
        """Empty `seq` findlib library (Seq lives in the 4.14 Stdlib)."""
        seq_dir = os.path.join(site, "seq")
        os.makedirs(seq_dir, exist_ok=True)
        env_prefix = (
            f"OCAMLLIB={shlex.quote(ocaml_lib)} "
            f"PATH={shlex.quote(ocaml_bin)}:$PATH "
        )
        self.run(
            f"{env_prefix} ocamlc -a -o {shlex.quote(os.path.join(seq_dir, 'seq.cma'))}",
            env="conanbuild")
        self.run(
            f"{env_prefix} ocamlopt -a -o {shlex.quote(os.path.join(seq_dir, 'seq.cmxa'))}",
            env="conanbuild")
        with open(os.path.join(seq_dir, "META"), "w") as f:
            f.write('version = "[distributed with OCaml]"\n'
                    'description = "Seq (part of the OCaml Stdlib since 4.14)"\n'
                    'archive(byte) = "seq.cma"\n'
                    'archive(native) = "seq.cmxa"\n')

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
            self.build_folder, "_build", "install", "default", "lib", "re")
        if not os.path.isdir(install_lib):
            raise ConanException(f"dune install tree missing: {install_lib}")
        lib_dir = os.path.join(self.package_folder, "lib", "ocaml", "re")
        self._copy_real_tree(install_lib, lib_dir)

        # seq stub travels with the package: re's META declares
        # `requires = "seq"`, and this registry has no seq findlib package.
        site_seq = os.path.join(self.build_folder, ".ohc-site", "seq")
        dst_seq = os.path.join(self.package_folder, "lib", "ocaml", "seq")
        os.makedirs(dst_seq, exist_ok=True)
        for fname in ("META", "seq.cma", "seq.cmxa"):
            shutil.copy2(os.path.join(site_seq, fname),
                         os.path.join(dst_seq, fname))

        for root, _dirs, files in os.walk(lib_dir):
            for f in files:
                p = os.path.join(root, f)
                if os.path.islink(p) or not os.path.isfile(p):
                    raise ConanException(f"package artifact is not a real file: {p}")
                if os.path.getsize(p) == 0:
                    raise ConanException(f"package artifact is empty: {p}")

        for mandatory in ("re.cma", "re.cmxa", "re.cmxs", "re.a", "META",
                          "re.cmi",
                          os.path.join("emacs", "re_emacs.cmxa"),
                          os.path.join("glob", "re_glob.cmxa"),
                          os.path.join("pcre", "re_pcre.cmxa"),
                          os.path.join("str", "re_str.cmxa")):
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
        self.cpp_info.libdirs = ["lib/ocaml/re"]
        self.cpp_info.includedirs = ["lib/ocaml/re"]
        # OCaml consumers (dune/ocamlc) locate the library via OCAMLPATH;
        # the seq stub in this package's lib root is found the same way.
        # Conan 2 environment API (Conan 1.x env_info is a deprecated no-op).
        self.buildenv_info.append_path(
            "OCAMLPATH", os.path.join(self.package_folder, "lib", "ocaml"))
        self.runenv_info.append_path(
            "OCAMLPATH", os.path.join(self.package_folder, "lib", "ocaml"))
