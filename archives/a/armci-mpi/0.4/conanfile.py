#!/usr/bin/env python3
"""Conan recipe for armci-mpi 0.4 — ARMCI MPI implementation.

armci-mpi provides the ARMCI (Aggregate Remote Memory Copy Interface) API
using MPI one-sided communication (RMA). It depends on an MPI implementation
(mpich) and is built as a static library (libarmci.a).
"""
import os
import shutil
from shlex import quote

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ArmcimpiConan(ConanFile):
    name = "armci-mpi"
    version = "0.4"
    description = "ARMCI (Aggregate Remote Memory Copy Interface) MPI implementation using MPI one-sided communication (RMA)"
    license = "MIT"
    homepage = "https://github.com/pmodels/armci-mpi"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mpich/5.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _config_shell(self):
        configured = os.environ.get("CONFIG_SHELL")
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        return shutil.which("bash") or shutil.which("sh") or "/system/bin/sh"

    def _perl(self):
        """Real perl binary path (avoid HMDFS symlink issue)."""
        for p in ("/data/service/hnp/bin/perl",
                  "/data/service/hnp/perl.org/perl_5.42.0/bin/perl"):
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return shutil.which("perl")

    def _tool_cmd(self, tool):
        """Build a command string for perl-based autotools tools.

        On HarmonyOS, the kernel cannot execve() scripts with shebang lines
        from /storage/ directories. We invoke perl explicitly to bypass this.
        """
        path = shutil.which(tool)
        if not path:
            return tool
        perl = self._perl()
        if perl:
            # Check if it's a perl script
            try:
                with open(path, "r", errors="ignore") as f:
                    first_line = f.readline()
                if "perl" in first_line:
                    return f"{perl} {path}"
            except Exception:
                pass
        return path

    def _relax_autoconf_tmp_permissions(self):
        """Fix umask 077 in configure scripts (HarmonyOS setgid issue)."""
        shell = self._config_shell()
        for root, _, files in os.walk(self.source_folder):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                relaxed = content
                if filename in ("configure", "config.status"):
                    relaxed = relaxed.replace("umask 077", "umask 022")
                first_line, sep, rest = relaxed.partition("\n")
                if first_line.startswith("#!") and "/bin/sh" in first_line:
                    relaxed = f"#!{shell}{sep}{rest}"
                if relaxed != content:
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(relaxed)
                    except Exception:
                        pass

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Get mpich include/lib paths for direct compilation (mpicc wrapper can't exec from /storage/)
        mpich = self.dependencies.get("mpich")
        if mpich:
            mpich_inc = os.path.join(mpich.package_folder, "include")
            mpich_lib = os.path.join(mpich.package_folder, "lib")
            # Add MPI paths to compiler/linker flags (R33: from Conan deps, not shell env)
            tc.extra_cflags.append(f"-I{mpich_inc}")
            tc.extra_ldflags.append(f"-L{mpich_lib}")
            tc.extra_ldflags.append("-lmpi")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        bash = self._config_shell()
        src = self.source_folder

        # Step 1: Run autogen steps manually (bypass HMDFS shebang exec issue)
        configure_path = os.path.join(src, "configure")
        if not os.path.isfile(configure_path):
            perl = self._perl()
            bash = self._config_shell()
            # Ensure ltmain.sh is in m4/ before automake runs
            # Detect ltmain.sh from libtool's share directory via shutil.which
            m4_dir = os.path.join(src, "m4")
            ltmain_dst = os.path.join(m4_dir, "ltmain.sh")
            if not os.path.isfile(ltmain_dst):
                libtoolize_path = shutil.which("libtoolize")
                if libtoolize_path:
                    # Derive share dir from libtoolize install location
                    libtool_root = os.path.dirname(os.path.dirname(os.path.dirname(libtoolize_path)))
                    for candidate in [
                        os.path.join(libtool_root, "share", "libtool", "build-aux", "ltmain.sh"),
                        os.path.join(libtool_root, "share", "aclocal", "ltmain.sh"),
                    ]:
                        if os.path.isfile(candidate):
                            try:
                                shutil.copy2(candidate, ltmain_dst)
                            except Exception:
                                pass
                            break

            # Detect autoconf tools via PATH (avoid hardcoded paths)
            autom4te_path = shutil.which("autom4te") or "autom4te"
            autoconf_path = shutil.which("autoconf") or "autoconf"
            autoheader_path = shutil.which("autoheader") or "autoheader"
            # Derive PERL5LIB from autoconf share directory
            autoconf_share = ""
            ac_dir = os.path.dirname(os.path.dirname(autoconf_path)) if autoconf_path != "autoconf" else ""
            if ac_dir:
                share_candidate = os.path.join(ac_dir, "share", "autoconf")
                if os.path.isdir(share_candidate):
                    autoconf_share = share_candidate
            env_parts = [f"AUTOM4TE={autom4te_path}", f"AUTOCONF={autoconf_path}", f"AUTOHEADER={autoheader_path}"]
            if autoconf_share:
                env_parts.append(f"PERL5LIB={autoconf_share}")
            env_prefix = " ".join(env_parts)
            for tool, args in [
                ("aclocal", "--force -I m4"),
                ("libtoolize", "--copy --force"),
                ("autoheader", "--force"),
                ("autoconf", "--force"),
                ("automake", "--add-missing --copy --force-missing"),
            ]:
                tool_path = shutil.which(tool)
                if not tool_path:
                    continue
                try:
                    with open(tool_path, "r", errors="ignore") as f:
                        first_line = f.readline()
                except Exception:
                    first_line = ""
                if "perl" in first_line and perl:
                    cmd = f"{env_prefix} {perl} {tool_path} {args}"
                elif "bash" in first_line or "/sh" in first_line:
                    cmd = f"{env_prefix} {bash} {tool_path} {args}"
                else:
                    cmd = f"{env_prefix} {tool_path} {args}"
                self.run(f"{quote(bash)} -c {quote(cmd)}", cwd=src, env="conanbuild")

        # Step 2: Fix umask 077 in configure
        self._relax_autoconf_tmp_permissions()

        # Step 3: Run configure (use clang directly, not mpicc wrapper)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        configure_args = [
            "--prefix=/",
            "--enable-static",
            "--disable-shared",
        ]
        # Get mpich paths for direct compilation
        mpich = self.dependencies.get("mpich")
        if mpich:
            mpich_inc = os.path.join(mpich.package_folder, "include")
            mpich_lib = os.path.join(mpich.package_folder, "lib")
            # Use clang directly (mpicc wrapper can't exec from /storage/ on HMDFS)
            # Do NOT set MPICC - configure.ac would override CC with mpicc
            configure_args.append("CC=clang")
            configure_args.append(f"CFLAGS=-fPIC -O2 -I{mpich_inc}")
            configure_args.append(f"LDFLAGS=-L{mpich_lib} -lmpi")

        configure_args_str = " ".join(quote(a) for a in configure_args)
        mpich_lib_path = ""
        if mpich:
            mpich_lib_path = os.path.join(mpich.package_folder, "lib")
        ld_path = f"LD_LIBRARY_PATH={mpich_lib_path}:${{LD_LIBRARY_PATH}}"
        self.run(
            f"TMPDIR={quote(tmpdir)} {ld_path} {quote(bash)} {quote(os.path.join(src, 'configure'))} {configure_args_str}",
            cwd=src, env="conanbuild"
        )

        # Step 4: Fix config.status and re-run it
        self._relax_autoconf_tmp_permissions()
        config_status = os.path.join(src, "config.status")
        if os.path.isfile(config_status):
            self.run(f"{quote(bash)} {quote(config_status)}", cwd=src, env="conanbuild")

        # Step 5: Run make
        ld_path = ""
        if mpich:
            mpich_lib_path = os.path.join(mpich.package_folder, "lib")
            ld_path = f"LD_LIBRARY_PATH={mpich_lib_path}:${{LD_LIBRARY_PATH}} "
        self.run(f"{quote(bash)} -c '{ld_path}make -j1'", cwd=src, env="conanbuild")

    def package(self):
        bash = self._config_shell()
        src = self.source_folder
        # Run make install in the source folder (where Makefile was generated)
        mpich = self.dependencies.get("mpich")
        ld_path = ""
        if mpich:
            mpich_lib_path = os.path.join(mpich.package_folder, "lib")
            ld_path = f"LD_LIBRARY_PATH={mpich_lib_path}:${{LD_LIBRARY_PATH}} "
        self.run(f"{quote(bash)} -c '{ld_path}make install DESTDIR={self.package_folder} -j1'", cwd=src, env="conanbuild")
        copy(self, "COPYRIGHT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["armci"]
        self.cpp_info.set_property("cmake_file_name", "armci-mpi")
        self.cpp_info.set_property("cmake_target_name", "armci-mpi::armci-mpi")
        self.cpp_info.set_property("pkg_config_name", "armci-mpi")
