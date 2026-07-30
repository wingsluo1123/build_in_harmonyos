#!/usr/bin/env python3
"""Conan recipe for GNU bison 2.7 — parser generator tool for HarmonyOS PC.

bison 2.7 is a standard GNU Autotools project producing the `bison` and
`yacc` command-line executables. It is packaged as an application so that
downstream packages can consume it via tool_requires("bison/2.7").

Known OHOS adaptation (see notes.md):
  * config.guess does not recognize HarmonyOS → patch 0001
  * flex-generated scan-gram.c has a variable-scope issue → patch 0002
  * gnulib mbschr/mbsrchr declarations missing → patch 0003
  * hmdfs FUSE filesystem breaks autotools' config.status temp dirs
    (SELinux/umask 077 quirk) → build redirected to tmpfs
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BisonConan(ConanFile):
    name = "bison"
    version = "2.7"
    description = "GNU Bison 2.7 — parser generator that converts grammar rules into LALR/GLR parsers"
    license = "GPL-3.0"
    homepage = "https://www.gnu.org/software/bison/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _choose_build_root(self):
        """Return a build root suitable for autotools.

        On OHOS dev hosts the Conan build folder sits on hmdfs FUSE,
        which breaks autotools' config.status (umask 077 → unwritable
        temp dirs).  We probe for this and fall back to tmpfs when
        detected.  See archives/s/sed/4.9 for the same workaround.
        """
        default = self.build_folder
        probe_parent = os.path.join(default, ".hmdfs-probe")
        os.makedirs(probe_parent, exist_ok=True)
        import subprocess as _sp
        probe_script = f'umask 077 && mktemp -d "{probe_parent}/confXXXXXX"'
        try:
            try:
                out = _sp.run(["bash", "-c", probe_script],
                              capture_output=True, text=True, timeout=10)
                probe_dir = out.stdout.strip()
                if probe_dir and os.path.isdir(probe_dir):
                    test_file = os.path.join(probe_dir, "probe")
                    with open(test_file, "w") as f:
                        f.write("x")
                    os.unlink(test_file)
                    os.rmdir(probe_dir)
                    return default  # normal filesystem
            except (IOError, OSError, RuntimeError, _sp.TimeoutExpired):
                pass
        finally:
            if os.path.isdir(probe_parent):
                try:
                    os.rmdir(probe_parent)
                except OSError:
                    pass
        alt = "/data/storage/el2/base/.conan-build-bison-2.7"
        self.output.info("hmdfs detected (umask 077 write fails), "
                         "building on tmpfs: " + alt)
        return alt

    def build(self):
        apply_conandata_patches(self)

        build_root = self._choose_build_root()

        # PATH with OHOS toolchain locations (clang lives here)
        path_entries = [
            "/data/app/bin",
            "/data/service/hnp/bin",
            "/system/bin",
            "/usr/bin",
        ]
        usr_local = "/storage/Users/currentUser/usr/local/bin"
        if os.path.isdir(usr_local):
            path_entries.insert(0, usr_local)
        safe_path = os.pathsep.join(path_entries) + os.pathsep + os.environ.get("PATH", "")

        tmpdir = os.path.join(build_root, ".build-tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # Copy patched sources to build root (avoids hmdfs issues in
        # the source tree itself)
        work = os.path.join(build_root, "src")
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        self.run(f'cp -a "{self.source_folder}/." "{work}/"')

        install_dir = os.path.join(build_root, "install")
        env = f"PATH={safe_path} TMPDIR={tmpdir}"

        # configure
        self.run(f'bash -c "cd {work} && export {env}'
                 f' && ./configure --prefix={install_dir}"')

        # make + install (use -j1 for reproducibility on OHOS)
        self.run(f'bash -c "cd {work} && export {env} && make -j1"')
        self.run(f'bash -c "cd {work} && export {env} && make install"')

        self._install_dir = install_dir

    def package(self):
        install_dir = getattr(self, "_install_dir", None)
        if install_dir is None:
            return
        bin_src = os.path.join(install_dir, "bin")
        if os.path.isdir(bin_src):
            bin_dst = os.path.join(self.package_folder, "bin")
            shutil.copytree(bin_src, bin_dst, dirs_exist_ok=True)
        share_src = os.path.join(install_dir, "share", "bison")
        if os.path.isdir(share_src):
            share_dst = os.path.join(self.package_folder, "share", "bison")
            shutil.copytree(share_src, share_dst, dirs_exist_ok=True)

    def package_info(self):
        # Application package: no libraries or include dirs to export.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # package_type = "application" is sufficient for build-time tool
        # discovery via tool_requires("bison/2.7") in downstream recipes.
