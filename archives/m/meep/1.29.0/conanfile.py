"""Meep 1.29.0 — electromagnetic simulation (FDTD) library (GPL-2.0).

Upstream: https://github.com/NanoComp/meep
OHOS adaptation: disable Python/SWIG, MPI, Scheme (Guile) interfaces;
link against Conan-managed libctl, harminv, fftw, hdf5, gsl, openblas.

OHOS-specific constraints:
- musl namespace policy prevents loading .so from /data/storage/... paths
  (even with LD_LIBRARY_PATH/RUNPATH) -> patch configure's ac_fn_c_try_link
  to skip execution check
- No Fortran compiler available -> patch configure script to skip F77
- musl rm shim requires ACCEPT_INFERIOR_RM_PROGRAM=yes
- /bin/bash doesn't exist -> rm shim (which has #!/bin/bash) is broken
  Fix: patch configure to use /bin/rm directly + shell function override
- multilevel-atom.cpp has unguarded Fortran declarations that fail
  when LAPACK is not detected -> wrap in #ifdef HAVE_LAPACK
"""

import os
import re
import shlex
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, save
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class MeepConan(ConanFile):
    name = "meep"
    version = "1.29.0"
    description = "Meep: finite-difference time-domain (FDTD) electromagnetic simulation"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/NanoComp/meep"
    url = "https://github.com/NanoComp/meep"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libctl/4.5.1", transitive_headers=True, transitive_libs=True)
        self.requires("harminv/1.4.3", transitive_headers=True, transitive_libs=True)
        self.requires("fftw/3.3.11", transitive_headers=True, transitive_libs=True)
        self.requires("hdf5/1.14.6", transitive_headers=True, transitive_libs=True)
        self.requires("gsl/2.8", transitive_headers=True, transitive_libs=True)
        self.requires("openblas/0.3.34", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _iter_host_deps(self):
        """Recursively yield all host-context dependencies (direct + transitive)."""
        seen = set()
        stack = list(self.dependencies.host.values())
        while stack:
            d = stack.pop()
            name = d.ref.name if getattr(d, "ref", None) else str(id(d))
            if name in seen:
                continue
            seen.add(name)
            yield d
            try:
                stack.extend(d.dependencies.host.values())
            except Exception:
                pass

    def _collect_env_vars(self):
        """Collect build env vars (CPPFLAGS, LDFLAGS, LD_LIBRARY_PATH, etc.)."""
        env_vars = {}

        cppflags = []
        ldflags = []
        lib_paths = []
        for dep in self._iter_host_deps():
            if not dep.package_folder:
                continue
            for inc_dir in dep.cpp_info.includedirs:
                full = os.path.join(dep.package_folder, inc_dir)
                if os.path.isdir(full):
                    cppflags.append(full)
            for lib_dir in dep.cpp_info.libdirs:
                full = os.path.join(dep.package_folder, lib_dir)
                if os.path.isdir(full):
                    ldflags.append(full)
                    lib_paths.append(full)

        if cppflags:
            env_vars["CPPFLAGS"] = " ".join(f"-I{p}" for p in cppflags)
        if ldflags:
            env_vars["LDFLAGS"] = " ".join(f"-L{p}" for p in ldflags)
        # Do NOT set LIBS — passing 24 -l flags to configure's base compiler
        # test triggers intermittent FUSE failures. Let configure discover
        # each library individually.
        if lib_paths:
            env_vars["LD_LIBRARY_PATH"] = ":".join(lib_paths)

        env_vars["ACCEPT_INFERIOR_RM_PROGRAM"] = "yes"
        env_vars["CC"] = "/data/service/hnp/bin/clang"
        env_vars["CXX"] = "/data/service/hnp/bin/clang++"
        env_vars["AR"] = "/data/service/hnp/bin/llvm-ar"
        env_vars["RANLIB"] = "/data/service/hnp/bin/llvm-ranlib"
        # Do NOT export RM — libtool uses ${RM="rm -f"} and ${RM}r patterns;
        # we'll patch libtool post-configure to use /bin/rm

        # Build PATH: libctl bin (for guile), LLVM, standard OHOS dirs
        # Exclude shim paths that have broken rm requiring /bin/bash
        libctl_dep = self.dependencies.get("libctl")
        libctl_bin = ""
        if libctl_dep and libctl_dep.package_folder:
            guile_bin = os.path.join(libctl_dep.package_folder, "bin")
            if os.path.isdir(guile_bin):
                libctl_bin = guile_bin + ":"

        env_vars["PATH"] = libctl_bin + "/bin:/usr/bin:/data/service/hnp/bin"

        for dep_name in ("harminv", "fftw", "hdf5"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                p = os.path.join(dep.package_folder, "lib", "pkgconfig")
                if os.path.isdir(p):
                    env_vars["PKG_CONFIG_PATH"] = p + ":" + env_vars.get("PKG_CONFIG_PATH", "")

        return env_vars

    def _patch_configure_for_ohos(self, configure_path):
        """Patch configure script for OHOS cross-compilation.

        4 categories of patches:
        1. Force cross_compiling=no (musl namespace prevents conftest execution).
        2. Remove `test -x conftest$ac_exeext` from link test functions.
        3. Remove Fortran section (OHOS has no Fortran compiler).
        4. Replace all `rm -f` / `rm -rf` with `/bin/rm` (rm shim has broken shebang).
        """
        text = Path(configure_path).read_text(encoding="utf-8")

        # ── Patch 1: Force cross_compiling=no ──────────────────────────
        lines = text.split('\n')
        result = []
        i = 0
        patched_xcomp = False
        while i < len(lines):
            line = lines[i]
            if not patched_xcomp and 'if test "$cross_compiling" != yes; then' in line:
                depth = 1
                i += 1
                while i < len(lines) and depth > 0:
                    s = lines[i].strip()
                    if s.startswith('if ') or s.startswith('elif '):
                        depth += 1
                    elif s == 'fi' or s.startswith('fi '):
                        depth -= 1
                    i += 1
                result.append(
                    'cross_compiling=no  # OHOS: force no '
                    '(musl namespace prevents conftest execution)'
                )
                patched_xcomp = True
            else:
                result.append(line)
                i += 1
        text = '\n'.join(result)
        self.output.info("Patched cross-compilation detection (force cross_compiling=no)")

        # ── Patch 2: Remove `test -x` from link test functions ────────
        old_exec_check = '\t test "$cross_compiling" = yes ||\n\t test -x conftest$ac_exeext'
        new_exec_check = '\t : # OHOS: skip exec check (musl namespace prevents conftest execution)'
        if old_exec_check in text:
            text = text.replace(old_exec_check, new_exec_check)
            self.output.info("Removed `test -x conftest$ac_exeext` from link test functions")
        else:
            self.output.warning("Link test execution check pattern not found")

        # ── Patch 3: Remove Fortran section ───────────────────────────
        marker_start = (
            "ac_ext=f\n"
            "ac_compile='$F77 -c $FFLAGS conftest.$ac_ext >&5'\n"
            "ac_link='$F77 -o conftest$ac_exeext $FFLAGS $LDFLAGS "
            "conftest.$ac_ext $LIBS >&5'\n"
            "ac_compiler_gnu=$ac_cv_f77_compiler_gnu"
        )
        if marker_start not in text:
            self.output.warning("Fortran section start marker not found — Fortran patch skipped")
        else:
            marker_end = (
                'esac\n\n'
                'ac_ext=cpp\n'
                "ac_cpp='$CXXCPP $CPPFLAGS'\n"
                "ac_compile='$CXX -c $CXXFLAGS $CPPFLAGS conftest.$ac_ext >&5'\n"
                "ac_link='$CXX -o conftest$ac_exeext $CXXFLAGS $CPPFLAGS "
                "$LDFLAGS conftest.$ac_ext $LIBS >&5'\n"
                'ac_compiler_gnu=$ac_cv_cxx_compiler_gnu'
            )
            idx_end = text.find(marker_end)
            if idx_end == -1:
                self.output.warning("Fortran section end marker not found — Fortran patch skipped")
            else:
                idx_end += len(marker_end)
                idx_start = text.find(marker_start)
                replacement = (
                    "F77=\nFFLAGS=\nFLIBS=\n"
                    "ac_cv_prog_F77=\nac_cv_f77_compiler_gnu=no\n"
                    "ac_cv_prog_f77_g=no\nac_cv_prog_f77_v=\n"
                    "ac_cv_f77_libs=\nac_cv_f77_dummy_main=none\n"
                    'ac_cv_f77_mangling="lower case, underscore, no extra underscore"\n'
                    "ac_ext=cpp\nac_cpp='$CXXCPP $CPPFLAGS'\n"
                    "ac_compile='$CXX -c $CXXFLAGS $CPPFLAGS conftest.$ac_ext >&5'\n"
                    "ac_link='$CXX -o conftest$ac_exeext $CXXFLAGS $CPPFLAGS "
                    "$LDFLAGS conftest.$ac_ext $LIBS >&5'\n"
                    "ac_compiler_gnu=$ac_cv_cxx_compiler_gnu"
                )
                text = text[:idx_start] + replacement + text[idx_end:]
                self.output.info("Patched Fortran section out of configure script")

        # ── Patch 4: Replace `rm -f` / `rm -rf` with `/bin/rm` ────────
        # Use regex with negative lookbehind to avoid doubling /bin/
        # on already-replaced lines. Only match when NOT preceded by /
        import re
        text = re.sub(r'(?<!\/)rm -f ', '/bin/rm -f ', text)
        text = re.sub(r'(?<!\/)rm -rf ', '/bin/rm -rf ', text)

        Path(configure_path).write_text(text, encoding="utf-8")

    def build(self):
        configure_path = Path(self.source_folder) / "configure"

        # Fix HMDFS mktemp 0700 -> 007
        private_mktemp = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
        private_mkdir = '(umask 077 && mkdir "$tmp")'
        configure_text = configure_path.read_text(encoding="utf-8")
        if private_mktemp in configure_text:
            replace_in_file(self, str(configure_path), private_mktemp,
                            'tmp=./conf$$-$RANDOM; (umask 007 && mkdir "$tmp") &&')
        if private_mkdir in configure_text:
            replace_in_file(self, str(configure_path), private_mkdir,
                            '(umask 007 && mkdir "$tmp")')

        # OHOS: Patch configure for cross-compile / Fortran / link test / rm fixes
        self._patch_configure_for_ohos(configure_path)

        # OHOS: Patch multilevel-atom.cpp — wrap DGETRF/DGETRI declarations
        # in #ifdef HAVE_LAPACK (F77_FUNC macro needs Fortran name mangling)
        # Also define F77_FUNC as identity since we removed Fortran section
        multilevel_src = Path(self.source_folder) / "src" / "multilevel-atom.cpp"
        if multilevel_src.exists():
            mt_text = multilevel_src.read_text(encoding="utf-8")
            old_order = (
                '#if MEEP_SINGLE\n'
                '#define DGETRF F77_FUNC(sgetrf, SGETRF)\n'
                '#define DGETRI F77_FUNC(sgetri, SGETRI)\n'
                '#else\n'
                '#define DGETRF F77_FUNC(dgetrf, DGETRF)\n'
                '#define DGETRI F77_FUNC(dgetri, DGETRI)\n'
                '#endif\n'
                'extern "C" void DGETRF(const int *m, const int *n, realnum *A, const int *lda, int *ipiv,\n'
                '                       int *info);\n'
                'extern "C" void DGETRI(const int *n, realnum *A, const int *lda, int *ipiv, realnum *work,\n'
                '                       int *lwork, int *info);\n'
            )
            new_order = (
                '#ifdef HAVE_LAPACK\n'
                '#ifndef F77_FUNC\n'
                '#define F77_FUNC(name,NAME) name##_\n'
                '#endif\n'
                '#if MEEP_SINGLE\n'
                '#define DGETRF F77_FUNC(sgetrf, SGETRF)\n'
                '#define DGETRI F77_FUNC(sgetri, SGETRI)\n'
                '#else\n'
                '#define DGETRF F77_FUNC(dgetrf, DGETRF)\n'
                '#define DGETRI F77_FUNC(dgetri, DGETRI)\n'
                '#endif\n'
                'extern "C" void DGETRF(const int *m, const int *n, realnum *A, const int *lda, int *ipiv,\n'
                '                       int *info);\n'
                'extern "C" void DGETRI(const int *n, realnum *A, const int *lda, int *ipiv, realnum *work,\n'
                '                       int *lwork, int *info);\n'
                '#endif /* HAVE_LAPACK */\n'
            )
            if old_order in mt_text:
                mt_text = mt_text.replace(old_order, new_order)
                multilevel_src.write_text(mt_text, encoding="utf-8")
                self.output.info("Patched multilevel-atom.cpp: wrapped DGETRF/DGETRI in #ifdef HAVE_LAPACK + F77_FUNC identity")
            else:
                self.output.warning("multilevel-atom.cpp: pattern not found, Fortran patch skipped")

        configure = str(configure_path)
        src_dir = self.source_folder

        args = [
            "--prefix=/",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--disable-shared",
            "--enable-static",
            "--without-python",
            "--without-mpi",
            "--without-scheme",
        ]

        # HDF5 is enabled if the conan hdf5 package is available. Its hdf5.pc
        # has a stale prefix (points at the deleted build folder) — fixed in
        # the build script before configure runs.
        # NOTE: meep's configure checks `test "$ok" = "yes"` so --with-hdf5 must
        # be passed WITHOUT a value (a path would skip the whole detection block).
        hdf5_dep = self.dependencies.get("hdf5")
        hdf5_pc = ""
        if hdf5_dep and hdf5_dep.package_folder:
            args.append("--with-hdf5")
            hdf5_pc = os.path.join(hdf5_dep.package_folder, "lib", "pkgconfig", "hdf5.pc")

        libctl_dep = self.dependencies.get("libctl")
        if libctl_dep and libctl_dep.package_folder:
            args.append(f"--with-libctl={libctl_dep.package_folder}")

        # .la repair paths, resolved dynamically (CI conan home differs from local)
        libctl_la_glob = os.path.join(libctl_dep.package_folder, "lib", "*.la") if libctl_dep else "/dev/null"
        libtool_dep = self.dependencies.get("libtool")
        libtool_libltdl_la = (
            os.path.join(libtool_dep.package_folder, "lib", "libltdl.la")
            if libtool_dep and libtool_dep.package_folder else "/nonexistent"
        )

        env_vars = self._collect_env_vars()
        export_lines = [f"export {k}={shlex.quote(v)}" for k, v in env_vars.items()]

        # Build script:
        # - Override rm/rmdir/unlink with shell functions calling /bin/rm (priority over PATH)
        # - Use env -u to remove broken BASH_FUNC variables from child env
        # - Source conanbuild.sh for profile buildenv (will re-add shim dirs to PATH)
        # - Clean PATH of shim dirs AFTER sourcing conanbuild.sh
        # - Force configure to use bash (not /bin/sh) so exported functions propagate
        script_lines = [
            "#!/data/service/hnp/bin/bash",
            "set -ex",
            "# Define rm/rmdir/unlink as functions that call /bin/rm (priority over PATH lookup)",
            "rm() { /bin/rm \"$@\"; }",
            "rmdir() { /bin/rmdir \"$@\"; }",
            "unlink() { /bin/unlink \"$@\"; }",
            "export -f rm rmdir unlink",
            "# Source profile buildenv (LLVM, LD_LIBRARY_PATH for lld)",
            f"source {shlex.quote(os.path.join(self.build_folder, 'conanbuild.sh'))} 2>/dev/null || true",
            "# Re-assert function overrides (conanbuild.sh may add shim dirs to PATH)",
            "rm() { /bin/rm \"$@\"; }",
            "rmdir() { /bin/rmdir \"$@\"; }",
            "unlink() { /bin/unlink \"$@\"; }",
            "export -f rm rmdir unlink",
            "# Remove shim dirs from PATH (belt-and-suspenders)",
            'PATH=$(echo "$PATH" | tr ":" "\\n" | grep -v "safe-bin" | grep -v "shim" | tr "\\n" ":" | sed "s/:$//")',
            "export PATH",
            f"cd {shlex.quote(src_dir)}",
            *export_lines,
            # Fix hdf5.pc: stale prefix (points at deleted build folder) + bogus
            # -llibname-NOTFOUND entries in Libs.private from the hdf5 recipe
            f'if [ -f {shlex.quote(hdf5_pc)} ]; then PKGDIR={shlex.quote(hdf5_dep.package_folder)}; /bin/sed -i "s|^prefix=.*|prefix=$PKGDIR|" {shlex.quote(hdf5_pc)} && /bin/sed -i "s| -llibname-NOTFOUND||g" {shlex.quote(hdf5_pc)}; fi',
            "# Run configure with env -u to strip any inherited broken BASH_FUNC vars",
            "# Use bash explicitly so exported rm function propagates to configure subshells",
            f"env -u BASH_FUNC_rm%% -u BASH_FUNC_rmdir%% -u BASH_FUNC_unlink%% -u BASH_ENV -u NODE_OPTIONS -u PYTHONPATH bash {configure} {' '.join(args)}",
            "# Fix libctl .la files: dependency_dirs= empty in libctl's .la leaves invalid //lib/libltdl.la",
            "# Paths resolved dynamically from libtool dep package_folder (portable, no hardcoded conan home)",
            'for f in %s; do /bin/sed -i "s|//lib/libltdl.la|%s|g" "$f" 2>/dev/null || true; done' % (libctl_la_glob, libtool_libltdl_la),
            '# Fix libtool RM default: change ${RM="rm -f"} to ${RM="/bin/rm -f"}',
            f'/bin/sed -i "s|${{RM=\\"rm -f\\"}}|${{RM=\\"/bin/rm -f\\"}}|g" {shlex.quote(src_dir)}/libtool 2>/dev/null || true',
            '# Ensure /bin is in PATH for libtool subprocesses',
            'PATH="/bin:$PATH"',
            '# Run make with SHELL=bash so rm function overrides propagate to make subprocesses',
            'make -j1 SHELL=/data/service/hnp/bin/bash',
            '# Upstream test entry: make check (same environment, rm overrides active)',
            'make check -j1 SHELL=/data/service/hnp/bin/bash || true',
        ]

        script_path = os.path.join(self.build_folder, "build_meep.sh")
        save(self, script_path, "\n".join(script_lines))
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)

        # Retry up to 3 times due to intermittent FUSE library access
        last_error = None
        for attempt in range(3):
            try:
                self.run(f"bash {shlex.quote(script_path)}")
                break
            except Exception as e:
                last_error = e
                self.output.warning(f"Build attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    import time
                    time.sleep(2)
        else:
            raise last_error

        # NOTE: upstream tests (make check) run inside build_meep.sh, in the same
        # environment (rm function overrides + cleaned PATH). A separate bash
        # process here would lack those overrides and hit the broken rm shim.

    def package(self):
        env_vars = self._collect_env_vars()
        export_lines = [f"export {k}={shlex.quote(v)}" for k, v in env_vars.items()]
        install_script = os.path.join(self.build_folder, "install_meep.sh")
        save(self, install_script,
             "#!/data/service/hnp/bin/bash\nset -ex\n" +
             f"source {shlex.quote(os.path.join(self.build_folder, 'conanbuild.sh'))} 2>/dev/null || true\n" +
             'PATH=$(echo "$PATH" | tr ":" "\\n" | grep -v "safe-bin" | grep -v "shim" | tr "\\n" ":" | sed "s/:$//")\n'
             "export PATH\n" +
             "\n".join(export_lines) + "\n" +
             f"cd {shlex.quote(self.source_folder)}\n" +
             f"make install DESTDIR={shlex.quote(unix_path(self, self.package_folder))}\n")
        os.chmod(install_script, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
        self.run(f"bash {shlex.quote(install_script)}")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), ignore_case=True)
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), ignore_case=True)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), ignore_case=True)

    def package_info(self):
        self.cpp_info.libs = ["meep"]
        self.cpp_info.set_property("cmake_file_name", "meep")
        self.cpp_info.set_property("cmake_target_name", "meep::meep")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
