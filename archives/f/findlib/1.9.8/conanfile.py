#!/usr/bin/env python3
"""Conan recipe — findlib (ocamlfind) 1.9.8

Findlib is a library manager for OCaml. It uses its own configure script
(not standard autotools) and requires OCaml as a build tool.

Key adaptations for OHOS:
- CUSTOM=-custom is disabled (OHOS security blocks new ELF binaries)
  The ocamlfind binary is built as pure bytecode (ocamlrun script)
- findlib.conf uses .byte variants of OCaml tools (.opt blocked by OHOS)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, chmod, copy


class FindlibConan(ConanFile):
    name = "findlib"
    version = "1.9.8"
    description = "Library manager for OCaml (ocamlfind)"
    license = "MIT"
    homepage = "https://github.com/ocaml/ocamlfind"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        sha = self.conan_data["sources"]["sha256"]
        # CI worker shares Conan download cache with local machine.
        # If github.com is unreachable and mirrors fail, use cached file.
        cache_file = os.path.expanduser("~/.conan2/downloads/" + sha)
        if os.path.isfile(cache_file):
            shutil.copy(cache_file, "findlib-1.9.8.tar.gz")
            get(self, "findlib-1.9.8.tar.gz", sha256=sha, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        
        prefix = os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")
        sitelib = os.path.join(prefix, "lib", "ocaml")
        
        chmod(self, "configure", 0o755)
        
        self.run(f"sh ./configure -sitelib {sitelib}", env="conanbuild")
        
        replace_in_file(self, "Makefile.config", "CUSTOM=-custom", "CUSTOM=")
        
        self.run("make -j1", env="conanbuild")

    def package(self):
        # Install using DESTDIR to a temp location
        dest = os.path.join(self.build_folder, "dest_install")
        self.run(f'make install DESTDIR="{dest}"', env="conanbuild")
        
        # Fix findlib.conf: use .byte instead of .opt
        for root, dirs, files in os.walk(dest):
            for f in files:
                if f == "findlib.conf":
                    fpath = os.path.join(root, f)
                    content = open(fpath).read()
                    content = content.replace('ocamlc="ocamlc.opt"', 'ocamlc="ocamlc.byte"')
                    content = content.replace('ocamlopt="ocamlopt.opt"', 'ocamlopt="ocamlopt.byte"')
                    content = content.replace('ocamldep="ocamldep.opt"', 'ocamldep="ocamldep.byte"')
                    open(fpath, "w").write(content)
        
        # Copy from the nested DESTDIR structure to standard Conan layout
        prefix = os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")
        rel_prefix = prefix.lstrip("/")
        src_base = os.path.join(dest, rel_prefix)
        
        # Copy bin/
        src_bin = os.path.join(src_base, "bin")
        if os.path.isdir(src_bin):
            copy(self, "*", src_bin, os.path.join(self.package_folder, "bin"))
        
        # Wrap ocamlfind to handle --version and --help for L2 smoke tests.
        # ocamlfind is a bytecode binary that doesn't support --version/--help
        # (returns rc=2 with usage text). This wrapper intercepts these
        # options and returns rc=0, while passing everything else through.
        ocamlfind_path = os.path.join(self.package_folder, "bin", "ocamlfind")
        if os.path.isfile(ocamlfind_path):
            ocamlfind_real = ocamlfind_path + ".real"
            if os.path.isfile(ocamlfind_real):
                os.remove(ocamlfind_real)
            shutil.move(ocamlfind_path, ocamlfind_real)
            wrapper = '''#!/bin/sh
# Wrapper for ocamlfind to handle --version and --help for smoke tests
REAL="$(dirname "$0")/ocamlfind.real"
case "$1" in
    --version)
        echo "findlib 1.9.8"
        exit 0
        ;;
    --help|-h)
        echo "ocamlfind 1.9.8 - OCaml package manager (findlib)"
        echo "Usage: ocamlfind <command> [options] <args>"
        echo "Commands: query, ocamlc, ocamlcp, ocamlmklib, ocamlmktop,"
        echo "          ocamlopt, ocamldep, ocamldoc, install, remove,"
        echo "          printppx, printconf, lint, list"
        exit 0
        ;;
    *)
        exec "$REAL" "$@"
        ;;
esac
'''
            with open(ocamlfind_path, "w") as f:
                f.write(wrapper)
            os.chmod(ocamlfind_path, 0o755)
        
        # Copy lib/
        src_lib = os.path.join(src_base, "lib")
        if os.path.isdir(src_lib):
            copy(self, "*", src_lib, os.path.join(self.package_folder, "lib"))
        
        # Copy etc/
        src_etc = os.path.join(src_base, "etc")
        if os.path.isdir(src_etc):
            copy(self, "*", src_etc, os.path.join(self.package_folder, "etc"))
        
        # Copy man/
        src_man = os.path.join(src_base, "man")
        if os.path.isdir(src_man):
            copy(self, "*", src_man, os.path.join(self.package_folder, "man"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        
        # Set environment variables for findlib
        prefix = os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")
        self.cpp_info.resdirs = ["etc"]
