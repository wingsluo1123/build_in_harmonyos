#!/usr/bin/env python3
"""Conan recipe for GCC 12.5.0."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, mkdir, replace_in_file, save


class Gcc12Conan(ConanFile):
    name = "gcc12"
    version = "12.5.0"
    description = "GNU Compiler Collection 12 release series"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "enable_cxx": [True, False],
    }
    default_options = {
        "enable_cxx": True,
    }

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        self.requires("mpc/1.3.1")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="gcc-12.5.0.tar.xz",
            strip_root=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gcc12 is prepared for Linux/OHOS")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("gcc12 supports OHOS armv8 only")

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _save_if_changed(self, path, content):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", newline="") as existing:
                if existing.read() == content:
                    return
        save(self, path, content)

    def _ohos_command_prefix(self):
        if self.settings.os != "OHOS":
            return ""

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = str(compilers.get("c") or "clang")
        compiler_dir = os.path.dirname(cc) if cc and os.path.isabs(cc) else ""
        sysroot = self._ohos_sysroot(cc)

        def compiler_tool(name):
            candidate = os.path.join(compiler_dir, name)
            if compiler_dir and os.path.exists(candidate):
                return candidate
            return name

        tmp_dir = os.path.join(self.build_folder, "tmp")
        tool_dir = os.path.join(self.build_folder, "ohos-tools")
        mkdir(self, tmp_dir)
        mkdir(self, tool_dir)

        # The OHOS validation filesystem creates inaccessible directories for
        # `mktemp -d` with mode 0700. Autoconf falls back cleanly to mkdir-like
        # semantics when mktemp is not used, so provide that behavior explicitly.
        mktemp = os.path.join(tool_dir, "mktemp")
        self._save_if_changed(
            mktemp,
            """#!/bin/sh
set -eu
make_dir=false
if [ "${1:-}" = "-d" ]; then
  make_dir=true
  shift
fi
template=${1:-tmp.XXXXXX}
case "$template" in
  *XXXXXX) prefix=${template%XXXXXX} ;;
  *) prefix="$template." ;;
esac
i=0
while [ "$i" -lt 100 ]; do
  path="${prefix}$$_$i"
  if [ "$make_dir" = true ]; then
    if mkdir "$path" 2>/dev/null; then
      printf '%s\\n' "$path"
      exit 0
    fi
  else
    if ( : > "$path" ) 2>/dev/null; then
      printf '%s\\n' "$path"
      exit 0
    fi
  fi
  i=$((i + 1))
done
exit 1
""",
        )
        os.chmod(mktemp, 0o755)

        assembler = os.path.join(tool_dir, "as")
        self._save_if_changed(
            assembler,
            f"""#!/bin/sh
for input in "$@"; do
  case "$input" in
    *.s|*.S)
      if [ -f "$input" ]; then
        python3 -c 'import pathlib, sys
p = pathlib.Path(sys.argv[1])
text = p.read_text()
text = text.replace(".eh_frame,\\"aw\\",@progbits", ".eh_frame,\\"a\\",@progbits")
text = text.replace(".eh_frame,\\"aw\\"", ".eh_frame,\\"a\\"")
text = text.replace(".gcc_except_table,\\"aw\\",@progbits", ".gcc_except_table,\\"a\\",@progbits")
text = text.replace(".gcc_except_table,\\"aw\\"", ".gcc_except_table,\\"a\\"")
text = text.replace(".debug_str,\\"\\",@progbits", ".debug_str,\\"MS\\",@progbits,1")
p.write_text(text)' "$input"
      fi
      ;;
  esac
done
exec {shlex.quote(cc)} -c -x assembler "$@"
""",
        )
        os.chmod(assembler, 0o755)

        availability_header = os.path.join(tool_dir, "ohos-availability.h")
        self._save_if_changed(
            availability_header,
            """#ifndef OHOS_AVAILABILITY_H
#define OHOS_AVAILABILITY_H
#define __availability__(...)
#endif
""",
        )

        target_cppflags = f"-include {shlex.quote(availability_header)}"
        target_flags = (
            "-O2 -fPIC -g0 -fno-asynchronous-unwind-tables -fno-unwind-tables "
            f"{target_cppflags}"
        )
        if sysroot:
            target_include = os.path.join(
                sysroot, "usr", "include", "aarch64-linux-ohos"
            )
            target_cppflags = (
                f"{target_cppflags} -isystem {shlex.quote(target_include)}"
            )
            target_flags = f"{target_flags} -isystem {shlex.quote(target_include)}"
            target_libdir = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
            target_ldflags = (
                f"-B{shlex.quote(target_libdir)}/ "
                f"-L{shlex.quote(target_libdir)} "
                f"-Wl,-rpath-link,{shlex.quote(target_libdir)} "
                "-Wl,--code-sign"
            )
        else:
            target_libdir = None
            target_ldflags = ""

        env = [
            f"PATH={shlex.quote(tool_dir)}:$PATH",
            f"TMPDIR={shlex.quote(tmp_dir)}",
            f"TMPPREFIX={shlex.quote(os.path.join(tmp_dir, 'zsh'))}",
            "SHELL=/bin/sh",
            "CONFIG_SHELL=/bin/sh",
            f"AS={shlex.quote(assembler)}",
            f"AS_FOR_TARGET={shlex.quote(assembler)}",
            f"AR={shlex.quote(compiler_tool('llvm-ar'))}",
            f"LD={shlex.quote(compiler_tool('ld.lld'))}",
            f"RANLIB={shlex.quote(compiler_tool('llvm-ranlib'))}",
            f"NM={shlex.quote(compiler_tool('llvm-nm'))}",
            f"OBJCOPY={shlex.quote(compiler_tool('llvm-objcopy'))}",
            f"OBJDUMP={shlex.quote(compiler_tool('llvm-objdump'))}",
            f"READELF={shlex.quote(compiler_tool('llvm-readelf'))}",
            f"STRIP={shlex.quote(compiler_tool('llvm-strip'))}",
            f'CPPFLAGS="$CPPFLAGS {target_cppflags}"',
            'CFLAGS="$CFLAGS -fPIC"',
            'CXXFLAGS="$CXXFLAGS -fPIC"',
            f"CPPFLAGS_FOR_TARGET={shlex.quote(target_cppflags)}",
            f"CFLAGS_FOR_TARGET={shlex.quote(target_flags)}",
            f"CXXFLAGS_FOR_TARGET={shlex.quote(target_flags)}",
            f"LDFLAGS_FOR_TARGET={shlex.quote(target_ldflags)}",
            "ac_cv_header_fcntl_h=yes",
            "ac_cv_header_limits_h=yes",
        ]
        if target_libdir:
            env.append(
                f"LIBRARY_PATH={shlex.quote(target_libdir)}"
                '${LIBRARY_PATH:+:$LIBRARY_PATH}'
            )
        return " ".join(env) + " "

    def _ohos_make_overrides(self):
        if self.settings.os != "OHOS":
            return ""

        return " LIBGCC2_DEBUG_CFLAGS=-g0"

    @staticmethod
    def _ohos_sysroot(cc):
        if not cc or not os.path.isabs(str(cc)):
            return None
        return os.path.normpath(os.path.join(os.path.dirname(str(cc)), "..", "sysroot"))

    def build(self):
        mkdir(self, self.build_folder)
        if self.settings.os == "OHOS":
            libgcc_makefile = os.path.join(
                self.source_folder, "libgcc", "Makefile.in"
            )
            replace_in_file(
                self,
                libgcc_makefile,
                "LIBGCC2_DEBUG_CFLAGS = -g\n",
                "LIBGCC2_DEBUG_CFLAGS = -g0\n",
            )
            replace_in_file(
                self,
                libgcc_makefile,
                "LIB2_DIVMOD_EXCEPTION_FLAGS := -fexceptions -fnon-call-exceptions",
                "LIB2_DIVMOD_EXCEPTION_FLAGS := "
                "-fno-asynchronous-unwind-tables -fno-unwind-tables",
            )
            replace_in_file(
                self,
                libgcc_makefile,
                "c_flags := -fexceptions\n",
                "c_flags := -fexceptions "
                "-fno-asynchronous-unwind-tables -fno-unwind-tables\n",
            )

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or compilers.get("cxx") or "clang++"

        languages = "c,c++" if self.options.enable_cxx else "c"
        args = [
            os.path.join(self.source_folder, "configure"),
            "--prefix=/",
            f"--enable-languages={languages}",
            "--disable-bootstrap",
            "--disable-multilib",
            "--disable-nls",
            "--disable-libsanitizer",
            "--disable-libcc1",
            "--disable-libitm",
            "--disable-libquadmath",
            "--disable-libquadmath-support",
            "--disable-libgomp",
            "--disable-libssp",
            "--disable-libvtv",
            "--without-isl",
            f"--with-gmp={self.dependencies['gmp'].package_folder}",
            f"--with-mpfr={self.dependencies['mpfr'].package_folder}",
            f"--with-mpc={self.dependencies['mpc'].package_folder}",
        ]
        if self.settings.os == "OHOS":
            triplet = "aarch64-unknown-linux-musl"
            sysroot = self._ohos_sysroot(cc)
            args.extend([
                f"--build={triplet}",
                f"--host={triplet}",
                f"--target={triplet}",
            ])
            if sysroot:
                args.extend([
                    f"--with-sysroot={sysroot}",
                    f"--with-build-sysroot={sysroot}",
                    "--with-native-system-header-dir=/usr/include",
                ])
            args.extend([
                f"--with-as={os.path.join(self.build_folder, 'ohos-tools', 'as')}",
                f"--with-ld={os.path.join(os.path.dirname(str(cc)), 'ld.lld')}",
            ])

        command = " ".join(shlex.quote(str(arg)) for arg in args)
        env_prefix = self._ohos_command_prefix()
        self.run(
            f"{env_prefix}{command} CC={shlex.quote(cc)} CXX={shlex.quote(cxx)}",
            cwd=self.build_folder,
            env=["conanbuild"],
        )

        jobs = self.conf.get("tools.build:jobs", default=1, check_type=int) or 1
        make_command = f"make -j{jobs}{self._ohos_make_overrides()}"
        if self.settings.os == "OHOS":
            self.run(
                f"{env_prefix}{make_command} || {env_prefix}{make_command}",
                cwd=self.build_folder,
                env=["conanbuild"],
            )
        else:
            self.run(make_command, cwd=self.build_folder, env=["conanbuild"])
        self.output.info(
            "Upstream DejaGnu tests are deferred to single-package OHOS/shadow CI; "
            "test_package performs the compiler smoke test."
        )

    def package(self):
        env_prefix = self._ohos_command_prefix()
        self.run(
            f"{env_prefix}make install DESTDIR={shlex.quote(self.package_folder)}"
            f"{self._ohos_make_overrides()}",
            cwd=self.build_folder,
            env=["conanbuild"],
        )
        if self.settings.os == "OHOS":
            copy(
                self,
                "ohos-availability.h",
                src=os.path.join(self.build_folder, "ohos-tools"),
                dst=os.path.join(self.package_folder, "include", "gcc12-ohos"),
            )
        for license_file in [
            "COPYING",
            "COPYING.LIB",
            "COPYING.RUNTIME",
            "COPYING3",
            "COPYING3.LIB",
        ]:
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        for libdir in ["lib64", "lib"]:
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, libdir)
            )
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
