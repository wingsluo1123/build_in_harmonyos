#!/usr/bin/env python3
"""Conan recipe — libsigrokcxx 0.5.2 (HarmonyOS PC, custom build system).

libsigrokcxx lives in the libsigrok tarball under bindings/cxx/ and ships no
separate tarball of its own. Upstream requires doxygen to generate enums.hpp
from the C headers; we replace that with a direct header parser
(patches/gen_enums.py) because doxygen is not available in the CI environment.
Upstream's autotools/libtool target is bypassed as well: classes.cpp is
compiled and linked directly with the OHOS clang++ (see build()).
"""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches
from conan.tools.layout import basic_layout


class LibsigrokcxxConan(ConanFile):
    name = "libsigrokcxx"
    version = "0.5.2"
    package_type = "library"
    description = "C++ bindings for the libsigrok signal-acquisition library"
    homepage = "https://sigrok.org/"
    license = "GPL-3.0-or-later"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("libsigrok/0.5.2",
                      transitive_headers=True, transitive_libs=True)
        self.requires("glibmm/2.66.7.1",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libsigc/2.10.8",
                      transitive_headers=True, transitive_libs=True)
        # Resolve the GLib pin conflict between the two families:
        #   libsigrok/0.5.2   -> glib/2.88.0   (static build: options shared=False)
        #   glibmm/2.66.7.1   -> glib/2.84.0.1 (shared build)
        # A graph cannot carry two glib versions, so one side must be overridden.
        # glib/2.88.0 is a STATIC glib: linking it into the two shared libraries
        # glibmm-2.4 and giomm-2.4 gives every process two independent GLib
        # states, and glibmm's own test suite aborts immediately with
        #   GLib:ERROR:../glib/g_quark.c: g_quark_init: assertion failed:
        #   (quark_seq_id == 0)
        # Aligning on the shared glib/2.84.0.1 instead keeps glibmm's published
        # binary usable as-is and leaves libsigrok (a C library that accepts
        # glib >= 2.32) as the only side that has to be rebuilt.
        self.requires("glib/2.84.0.1", override=True)

    def layout(self):
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _cxx(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = ce.get("cpp") or ce.get("c++") or ""
        if not cxx or not os.path.isfile(cxx):
            # Fallback: search PATH
            cxx = shutil.which("clang++") or shutil.which("g++") or "clang++"
        return cxx

    @staticmethod
    def _sign_elf(path):
        """Sign an OHOS ELF with binary-sign-tool and verify .codesign.

        Mandatory, mirroring libsigrok/0.5.2: every OHOS binary shipped by
        this repository carries a .codesign section, and an unsigned ELF is
        rejected by the OHOS loader. Silently skipping signing would publish
        a library that cannot be loaded on device, so a missing signer is a
        configuration error rather than a no-op.
        """
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("OHOS ELF signer/readelf missing")
        original = Path(path)
        pending = original.with_name(original.name + ".sigrokcxx-signing")
        signed = original.with_name(original.name + ".sigrokcxx-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale signing sibling")
        previous_umask = os.umask(0o022)
        try:
            shutil.copy2(original, pending)
            existing = subprocess.run([readelf, "-S", str(pending)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" in existing.stdout:
                objcopy = shutil.which("llvm-objcopy")
                if not objcopy:
                    raise ConanInvalidConfiguration(
                        "Existing signature requires llvm-objcopy")
                # Re-sign only this disposable build-tree copy, never cache inputs.
                subprocess.run([objcopy, "--remove-section=.codesign", str(pending)],
                               check=True, capture_output=True, text=True, timeout=20)
                stripped = subprocess.run([readelf, "-S", str(pending)], check=True,
                                          capture_output=True, text=True, timeout=20)
                if ".codesign" in stripped.stdout:
                    raise ConanException("Old signature was not removed from private copy")
            result = subprocess.run([signer, "sign", "-inFile", str(pending),
                                     "-outFile", str(signed), "-selfSign", "1"],
                                    capture_output=True, text=True, timeout=40)
            if result.returncode:
                raise ConanException("OHOS ELF signing failed (rc=" +
                                     str(result.returncode) + "): " +
                                     (result.stdout + result.stderr)[-2000:])
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed ELF has no .codesign")
            os.chmod(signed, original.stat().st_mode)
            os.replace(signed, original)
        finally:
            os.umask(previous_umask)
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def generate(self):
        # Generate enums.hpp and enums.cpp from libsigrok.h
        header_src = Path(self.dependencies["libsigrok"].package_folder,
                           "include", "libsigrok", "libsigrok.h")
        gen_script = Path(self.export_sources_folder, "patches", "gen_enums.py")

        out_dir = Path(self.build_folder, "gen")
        out_dir.mkdir(exist_ok=True)

        python3 = shutil.which("python3")
        result = subprocess.run(
            [python3, str(gen_script), str(header_src), str(out_dir)],
            capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ConanException(f"gen_enums.py failed: {result.stderr}")

        self.output.info(f"Generated enums in {out_dir}")

    def build(self):
        if str(self.settings.os) != "OHOS":
            self.output.info("libsigrokcxx build only implemented for OHOS")
            return

        cxx = self._cxx()
        src_dir = Path(self.source_folder, "bindings", "cxx")
        gen_dir = Path(self.build_folder, "gen")
        out_dir = Path(self.build_folder, "build")
        out_dir.mkdir(exist_ok=True)

        libsigrok_dep = self.dependencies["libsigrok"]
        glibmm_dep = self.dependencies["glibmm"]
        glib_dep = self.dependencies["glib"]
        libsigc_dep = self.dependencies["libsigc"]

        # Collect include paths from dependencies
        include_paths = set()
        for dep in [libsigrok_dep, glibmm_dep, glib_dep, libsigc_dep]:
            pkg = dep.package_folder
            if not pkg:
                continue
            pkg_inc = Path(pkg, "include")
            if pkg_inc.exists():
                # Add the include root and its immediate subdirectories
                include_paths.add(str(pkg_inc))
                for subdir in pkg_inc.iterdir():
                    if subdir.is_dir():
                        include_paths.add(str(subdir))
            # Check lib/<component>/include for build-time generated headers
            pkg_lib = Path(pkg, "lib")
            if pkg_lib.exists():
                for component_dir in pkg_lib.iterdir():
                    if component_dir.is_dir():
                        comp_inc = component_dir / "include"
                        if comp_inc.exists():
                            include_paths.add(str(comp_inc))
            # Handle glib config.h location
            glib_lib_inc = Path(pkg, "lib", "glib-2.0", "include")
            if glib_lib_inc.exists():
                include_paths.add(str(glib_lib_inc))

        include_args = []
        for p in sorted(include_paths):
            include_args.append(f"-I{p}")

        # Source-specific includes
        include_args.extend([
            f"-I{Path(src_dir, 'include')}",
            f"-I{Path(gen_dir, 'include')}",
            f"-I{gen_dir}",  # For #include <enums.cpp> in classes.cpp
        ])

        # Create minimal config.h (classes.cpp includes it)
        config_h_path = Path(out_dir, "config.h")
        with open(config_h_path, 'w') as cf:
            cf.write("/* Auto-generated config for libsigrokcxx build */\n")
            cf.write("#define HAVE_STOI_STOD 1\n")
        include_args.append(f"-I{out_dir}")

        # Link paths
        lib_paths = []
        for dep in [libsigrok_dep, glibmm_dep, glib_dep, libsigc_dep]:
            lib = Path(dep.package_folder, "lib")
            if lib.exists():
                lib_paths.append(str(lib))

        link_path_args = []
        for p in lib_paths:
            link_path_args.append(f"-L{p}")

        # Build the shared library
        # classes.cpp includes enums.cpp, so compile classes.cpp alone
        cmd = [
            cxx, "-shared", "-fPIC", "-std=c++11",
            "-fvisibility=hidden", "-O2", "-DNDEBUG",
            "-DHAVE_STOI_STOD=1",
            f"-Wl,-soname,libsigrokcxx.so.0",
            f"-o", str(Path(out_dir, "libsigrokcxx.so.0.5.2")),
            str(Path(src_dir, "classes.cpp")),
        ]
        cmd.extend(include_args)
        cmd.extend(link_path_args)
        cmd.extend(["-lsigrok", "-lglibmm-2.4", "-lgiomm-2.4", "-lglib-2.0", "-lsigc-2.0"])

        self.output.info(f"Building libsigrokcxx: {' '.join(cmd[:15])} ...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode:
            self.output.error(f"STDOUT: {result.stdout}")
            self.output.error(f"STDERR: {result.stderr}")
            raise ConanException(f"libsigrokcxx build failed (rc={result.returncode})")

        # Produced shared library
        so_path = Path(out_dir, "libsigrokcxx.so.0.5.2")
        if not so_path.exists():
            raise ConanException("shared library not produced")

        # Sign the real ELF first; the symlinks below point at it by name and
        # stay valid because signing replaces the file in place.
        if str(self.settings.os) == "OHOS":
            self._sign_elf(so_path)
            self.output.info("libsigrokcxx.so.0.5.2 signed (.codesign verified)")

        soname_link = Path(out_dir, "libsigrokcxx.so.0")
        if not soname_link.exists():
            os.symlink(so_path.name, soname_link)
        plain_link = Path(out_dir, "libsigrokcxx.so")
        if not plain_link.exists():
            os.symlink(so_path.name, plain_link)

        self.output.info("libsigrokcxx built successfully")

    def package(self):
        src = Path(self.build_folder, "build")
        dst_lib = Path(self.package_folder, "lib")
        dst_inc = Path(self.package_folder, "include", "libsigrokcxx")
        dst_lib.mkdir(parents=True, exist_ok=True)
        dst_inc.mkdir(parents=True, exist_ok=True)

        # Install shared library
        so_path = src / "libsigrokcxx.so.0.5.2"
        if so_path.exists():
            shutil.copy2(so_path, dst_lib / so_path.name)

        # Install soname symlink
        soname_link = src / "libsigrokcxx.so.0"
        if soname_link.exists():
            if soname_link.is_symlink():
                link_target = os.readlink(soname_link)
                os.symlink(link_target, dst_lib / soname_link.name)
            else:
                shutil.copy2(soname_link, dst_lib / soname_link.name, follow_symlinks=False)

        # Install unversioned .so symlink
        plain_link = src / "libsigrokcxx.so"
        if plain_link.exists():
            if plain_link.is_symlink():
                link_target = os.readlink(plain_link)
                os.symlink(link_target, dst_lib / plain_link.name)
            else:
                shutil.copy2(plain_link, dst_lib / plain_link.name, follow_symlinks=False)
        src_inc = Path(self.source_folder, "bindings", "cxx", "include", "libsigrokcxx")
        if src_inc.exists():
            for h in src_inc.glob("*.hpp"):
                copy(self, h.name, str(src_inc), str(dst_inc))

        # Install generated enums.hpp
        gen_inc = Path(self.build_folder, "gen", "include", "libsigrokcxx")
        if gen_inc.exists():
            for h in gen_inc.glob("*.hpp"):
                copy(self, h.name, str(gen_inc), str(dst_inc))

        # Install license from source tarball root
        license_src = Path(self.source_folder, "COPYING")
        if license_src.exists():
            copy(self, "COPYING",
                 Path(self.source_folder),
                 Path(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sigrokcxx"]
        self.cpp_info.set_property("pkg_config_name", "libsigrokcxx")
        if str(self.settings.os) == "OHOS":
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH",
                os.path.join(self.package_folder, "lib"))

    def package_id(self):
        self.info.clear()
