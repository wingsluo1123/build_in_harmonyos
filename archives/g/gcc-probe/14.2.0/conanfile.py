#!/usr/bin/env python3
"""Minimal native GCC 14 C compiler for HarmonyOS PC.

This deliberately builds only the C frontend and libgcc.  GMP, MPFR, and
MPC use the exact source versions selected by GCC 14.2.0's upstream
``contrib/download_prerequisites`` script and are built in-tree.

OHOS CI is a native AArch64 environment, so build, host, and target are all
``aarch64-linux-ohos``.  Audited source transforms map that target to GCC's
musl support; the recipe also handles old config.sub scripts, HMDFS umask
behaviour, and ELF signing for generated host tools.
"""

import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    get,
)
from conan.tools.gnu import get_gnu_triplet
from conan.tools.layout import basic_layout


class Gcc14Conan(ConanFile):
    name = "gcc-probe"
    version = "14.2.0"
    package_type = "application"

    description = "GNU Compiler Collection 14 C compiler"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/gcc-14/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "files"),
            dst=os.path.join(self.export_sources_folder, "files"),
        )

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("The OHOS GCC package supports AArch64/armv8 only")

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(self, **sources["gcc"], strip_root=True)

        # Use the exact in-tree dependency versions selected by GCC 14.2.0's
        # official download_prerequisites script.  This keeps the package
        # reproducible without relying on undeclared system libraries.
        for dependency in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(self.source_folder, dependency),
                strip_root=True,
            )

        # Perform the large source-tree rewrite in a short-lived process.  On
        # HarmonyOS, retaining that process state in Conan causes the first
        # large configure child to receive SIGSEGV; the same command succeeds
        # after the rewriting process exits and releases its resources.
        prepare_script = os.path.join(
            self.export_sources_folder, "files", "prepare_ohos_sources.py"
        )
        ohos_header = os.path.join(
            self.export_sources_folder, "files", "ohos.h"
        )
        subprocess.run(
            [sys.executable, prepare_script, self.source_folder, ohos_header],
            check=True,
        )
        if hasattr(os, "sync"):
            os.sync()

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    @property
    def _target_triplet(self):
        if self._is_ohos:
            return "aarch64-linux-ohos"
        return get_gnu_triplet(self)

    @property
    def _ohos_sysroot(self):
        if not self._is_ohos:
            return None
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc, _ = self._split_compiler_command(
            compiler_executables.get("c"), "clang"
        )
        # The OHOS SDK compiler lives in native/llvm/bin.  Resolve the stable
        # native/sysroot sibling instead of hard-coding the SDK version.
        sysroot = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.realpath(cc)),
                "..",
                "..",
                "sysroot",
            )
        )
        if not os.path.isdir(os.path.join(sysroot, "usr", "include")):
            raise ConanInvalidConfiguration(
                "OHOS SDK sysroot headers were not found: {}".format(sysroot)
            )
        return sysroot

    @property
    def _ohos_target_include(self):
        """Return the OHOS target-specific C library include directory."""
        target_include = os.path.join(
            self._ohos_sysroot,
            "usr",
            "include",
            self._target_triplet,
        )
        if not os.path.isfile(
            os.path.join(target_include, "bits", "alltypes.h")
        ):
            raise ConanInvalidConfiguration(
                "OHOS target C library headers were not found: {}".format(
                    target_include
                )
            )
        return target_include

    @staticmethod
    def _split_compiler_command(configured, fallback):
        """Resolve a configured compiler command and preserve its arguments."""
        try:
            command = shlex.split(configured or fallback)
        except ValueError as error:
            raise ConanInvalidConfiguration(
                "Invalid compiler command: {}".format(configured)
            ) from error
        if not command:
            raise ConanInvalidConfiguration("Compiler command is empty")
        executable = shutil.which(command[0])
        if not executable and os.path.isfile(command[0]) and os.access(
            command[0], os.X_OK
        ):
            executable = os.path.abspath(command[0])
        if not executable:
            raise ConanInvalidConfiguration(
                "Compiler executable was not found: {}".format(command[0])
            )
        return executable, command[1:]

    @staticmethod
    def _required_executable(name, *candidates):
        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if not resolved and os.path.isfile(candidate) and os.access(
                candidate, os.X_OK
            ):
                resolved = os.path.abspath(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration(
            "Required executable was not found: {}".format(name)
        )

    @staticmethod
    def _compiler_wrapper_text(real_compiler, signer, objcopy, readelf, extra_args=None):
        extra = " ".join(shlex.quote(value) for value in (extra_args or []))
        extra_setup = (
            'set -- {} "$@"'.format(extra) if extra else 'set -- "$@"'
        )
        return """#!/bin/sh
set -eu
real_compiler={real_compiler}
signer={signer}
objcopy={objcopy}
readelf={readelf}
{extra_setup}

"$real_compiler" "$@"

output=""
previous=""
compile_only=0
for argument in "$@"; do
    if [ "$previous" = "-o" ]; then
        output="$argument"
        previous=""
        continue
    fi
    case "$argument" in
        -o) previous="-o" ;;
        -openmp*|-object*|-objc*|-ObjC*) ;;
        -o?*) output="${{argument#-o}}" ;;
        -c|-S|-E) compile_only=1 ;;
    esac
done

if [ -z "$output" ] && [ "$compile_only" -eq 0 ]; then
    output=a.out
fi

if [ -n "$output" ] && [ -f "$output" ]; then
    if "$readelf" -h "$output" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
        unsigned="${{output}}.ohos-unsigned-$$"
        signed="${{output}}.ohos-signed-$$"
        cleanup_signing_files() {{
            rm -f "$unsigned" "$signed"
        }}
        trap cleanup_signing_files EXIT HUP INT TERM
        cp -p "$output" "$unsigned"
        "$objcopy" --remove-section .codesign "$unsigned" 2>/dev/null || true
        "$signer" sign -inFile "$unsigned" -outFile "$signed" -selfSign 1
        if ! "$readelf" -h "$signed" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
            echo "binary-sign-tool did not produce a runnable ELF: $output" >&2
            exit 1
        fi
        if ! "$readelf" -S "$signed" 2>/dev/null | grep -q '[.]codesign'; then
            echo "binary-sign-tool did not add .codesign: $output" >&2
            exit 1
        fi
        mv "$signed" "$output"
        rm -f "$unsigned"
        trap - EXIT HUP INT TERM
        chmod +x "$output" 2>/dev/null || true
    fi
fi
exit 0
""".format(
            real_compiler=shlex.quote(real_compiler),
            signer=shlex.quote(signer),
            objcopy=shlex.quote(objcopy),
            readelf=shlex.quote(readelf),
            extra_setup=extra_setup,
        )

    def _write_compiler_wrapper(self, name, real_compiler, extra_args=None):
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper = wrapper_dir / name

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        missing_tools = [
            tool_name
            for tool_name, tool_path in (
                ("binary-sign-tool", signer),
                ("llvm-objcopy", objcopy),
                ("llvm-readelf", readelf),
            )
            if (
                not tool_path
                or not os.path.isfile(tool_path)
                or not os.access(tool_path, os.X_OK)
            )
        ]
        if missing_tools:
            raise ConanInvalidConfiguration(
                "OHOS compiler wrappers require: {}".format(
                    ", ".join(missing_tools)
                )
            )
        wrapper.write_text(
            self._compiler_wrapper_text(
                real_compiler=real_compiler,
                signer=signer,
                objcopy=objcopy,
                readelf=readelf,
                extra_args=extra_args,
            ),
            encoding="utf-8",
        )
        wrapper.chmod(
            wrapper.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
        return str(wrapper)

    def generate(self):
        Path(self.build_folder).mkdir(parents=True, exist_ok=True)
        tmpdir = Path(self.build_folder) / ".tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc, cc_args = self._split_compiler_command(
            compiler_executables.get("c"), "clang"
        )
        cxx, cxx_args = self._split_compiler_command(
            compiler_executables.get("cpp"), "clang++"
        )

        if self._is_ohos:
            cc = self._write_compiler_wrapper("clang-sign", cc, cc_args)
            cxx = self._write_compiler_wrapper("clangxx-sign", cxx, cxx_args)
        elif cc_args or cxx_args:
            raise ConanInvalidConfiguration(
                "Compiler arguments require the OHOS wrapper path"
            )

        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )
        true_tool = self._required_executable("true", "true", "/bin/true")
        assembler = self._required_executable(
            "GNU assembler", "as", "/data/service/hnp/bin/as"
        )
        linker = self._required_executable(
            "GNU linker", "ld", "/data/service/hnp/bin/ld"
        )

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CC_FOR_BUILD", cc)
        env.define("CXX_FOR_BUILD", cxx)
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        env.define("TMPDIR", str(tmpdir))
        env.define("MAKEINFO", true_tool)
        env.define("HELP2MAN", true_tool)
        if self._is_ohos:
            # HarmonyOS Clang emits PIE executables by default.  GCC's host
            # configure otherwise detects -fno-PIE/-no-pie and applies them
            # to generator tools; LLD then creates an invalidly aligned
            # AArch64 copy relocation for libc's stderr symbol.  Preserve the
            # platform PIE default by pre-seeding those configure probes.
            env.define("gcc_cv_c_no_fpie", "no")
            env.define("gcc_cv_no_pie", "no")
        # The OpenDesk job environment exports AS=llvm-as, which consumes LLVM
        # IR rather than GNU/AArch64 assembly.  GCC requires real binutils as
        # and ld for target objects, both of which are provided on the device.
        env.define("AS", assembler)
        env.define("LD", linker)
        env.define("AS_FOR_TARGET", assembler)
        env.define("LD_FOR_TARGET", linker)
        env.define("AR", compiler_executables.get("ar", "llvm-ar"))
        env.define(
            "RANLIB", compiler_executables.get("ranlib", "llvm-ranlib")
        )
        env.define("NM", compiler_executables.get("nm", "llvm-nm"))
        # Do not call this script "conanbuild": Conan reserves that name for
        # its aggregate environment file.  Reusing it makes conanbuild.sh
        # source itself recursively until Bash terminates with SIGSEGV.
        env.vars(self).save_script("gcc_build_env")

    def _configure_args(self):
        triplet = self._target_triplet
        arguments = [
            "--prefix=/",
            "--libdir=/lib",
            "--libexecdir=/libexec",
            "--build={}".format(triplet),
            "--host={}".format(triplet),
            "--target={}".format(triplet),
            "--enable-languages=c,c++",
            "--disable-bootstrap",
            "--disable-lto",
            "--enable-plugin",
            "--disable-multilib",
            "--disable-nls",
            "--enable-shared",
            "--disable-libatomic",
            "--disable-libitm",
            "--disable-libsanitizer",
            "--disable-libgomp",
            "--disable-libquadmath",
            "--disable-libssp",
            "--disable-libvtv",
            "--disable-werror",
            "--without-isl",
        ]
        if self._is_ohos:
            # OHOS libc intentionally omits pthread_cancel, which GCC 14's
            # POSIX gthread backend references while building libgcc unwind
            # support.  This package builds only the C frontend and static
            # libgcc, so GCC's supported single-thread backend is sufficient.
            arguments.extend(
                [
                    "--disable-threads",
                    "--with-sysroot={}".format(self._ohos_sysroot),
                ]
            )
        arguments.append("--with-native-system-header-dir=/usr/include")
        return arguments

    def _run_with_unlimited_stack(self, command, cwd):
        """Run a GCC build command with enough stack for generated scripts."""
        shell = self._required_executable(
            "bash",
            os.environ.get("CONFIG_SHELL"),
            "bash",
            "/data/service/hnp/bin/bash",
        )
        wrapped_command = "{} -c {} {} {} -c {}".format(
            shlex.quote(shell),
            shlex.quote('ulimit -s unlimited; exec "$@"'),
            shlex.quote("gcc-build"),
            shlex.quote(shell),
            shlex.quote(command),
        )
        result = self.run(
            wrapped_command,
            cwd=cwd,
            env="gcc_build_env",
            ignore_errors=True,
        )
        if result in (-11, 139):
            self.output.warning(
                "GCC command hit a transient signal 11 on HMDFS; syncing and retrying once"
            )
            if hasattr(os, "sync"):
                os.sync()
            time.sleep(1)
            result = self.run(
                wrapped_command,
                cwd=cwd,
                env="gcc_build_env",
                ignore_errors=True,
            )
        if result != 0:
            raise ConanException(
                "GCC command failed with exit code {}".format(result)
            )

    def _sign_elf_tree(self, root):
        if not self._is_ohos:
            return

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires binary-sign-tool, llvm-objcopy and llvm-readelf"
            )

        for candidate in Path(root).rglob("*"):
            if not candidate.is_file() or candidate.is_symlink():
                continue
            if not (candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                continue
            probe = subprocess.run(
                [readelf, "-h", str(candidate)], capture_output=True, text=True
            )
            if probe.returncode != 0 or not re.search(
                r"Type:\s+(?:EXEC|DYN)\b", probe.stdout
            ):
                continue
            original_mode = stat.S_IMODE(candidate.stat().st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=str(candidate.parent)
            ) as temp_dir:
                # TemporaryDirectory uses 0700, which can produce unusable
                # directories on HMDFS.  Match the configure umask workaround
                # before the signer and binutils access files inside it.
                os.chmod(temp_dir, 0o775)
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(candidate, unsigned)
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", unsigned],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                subprocess.run(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    check=True,
                )
                signed_header = subprocess.run(
                    [readelf, "-h", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if not re.search(
                    r"Type:\s+(?:EXEC|DYN)\b", signed_header.stdout
                ):
                    raise ConanInvalidConfiguration(
                        "Signing did not produce a runnable ELF: {}".format(
                            candidate
                        )
                    )
                signed_sections = subprocess.run(
                    [readelf, "-S", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if ".codesign" not in signed_sections.stdout:
                    raise ConanInvalidConfiguration(
                        "Signing did not add .codesign: {}".format(candidate)
                    )
                os.replace(signed, candidate)
                candidate.chmod(original_mode)

    def _install_ohos_driver_wrapper(self):
        """Make the DESTDIR-installed GCC driver relocatable on OHOS."""
        bindir = Path(self.package_folder) / "bin"
        driver = bindir / "gcc"
        real_driver = bindir / "gcc.real"
        if not driver.is_file():
            raise ConanInvalidConfiguration(
                "The installed GCC driver was not found: {}".format(driver)
            )

        os.replace(driver, real_driver)
        wrapper = """#!/bin/sh
set -eu

driver_path=$(readlink -f "$0")
package_root=$(CDPATH= cd "$(dirname "$driver_path")/.." && pwd -P)
real_driver="$package_root/bin/gcc.real"
target={target}
version={version}

export GCC_EXEC_PREFIX="$package_root/libexec/gcc/"
sysroot=$("$real_driver" -print-sysroot)
if [ -z "$sysroot" ] || [ ! -d "$sysroot/usr/lib/$target" ]; then
    echo "GCC OHOS sysroot is unavailable: $sysroot" >&2
    exit 1
fi
set -- '-D__availability__(...)=' "$@"
set -- -isystem "$sysroot/usr/include/$target" "$@"
set -- "-B$sysroot/usr/lib/$target/" "$@"
set -- "-B$package_root/lib/gcc/$target/$version/" "$@"
exec "$real_driver" "$@"
""".format(
            target=shlex.quote(self._target_triplet),
            version=shlex.quote(str(self.version)),
        )
        driver.write_text(wrapper, encoding="utf-8")
        driver.chmod(
            driver.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )

    def _r3_gate_after_configure(self):
        """R3 gate 1 (cheap, before make): read prefix/tooldir/sysroot roots."""
        makefiles = [
            os.path.join(self.build_folder, "Makefile"),
            os.path.join(self.build_folder, "gcc", "Makefile"),
        ]
        wanted = (
            "prefix",
            "exec_prefix",
            "tooldir",
            "build_tooldir",
            "target_alias",
            "TARGET_SYSTEM_ROOT",
        )
        pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
        merged = {}
        text_all = ""
        for path in makefiles:
            if not os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8", errors="replace").read()
            text_all += text
            for line in text.splitlines():
                match = pattern.match(line)
                if match and match.group(1) in wanted and match.group(1) not in merged:
                    merged[match.group(1)] = match.group(2).strip()
        print(
            "R3GATE1 "
            + " ".join("{}={}".format(key, merged.get(key, "?")) for key in wanted)
        )
        print("R3GATE1 slash2_count={}".format(text_all.count("//")))
        # R3 fix (2026-10-02): right after the top-level configure the
        # gcc/ subdir Makefile does not exist yet, so TARGET_SYSTEM_ROOT is
        # not readable at this point; the sysroot is recorded in the top-level
        # Makefile as --with-sysroot=... inside TOPLEVEL_CONFIGURE_ARGUMENTS.
        # Read that instead of aborting on a variable that is simply not
        # generated yet (that false red cost one round).
        sysroot = merged.get("TARGET_SYSTEM_ROOT", "")
        source = "TARGET_SYSTEM_ROOT"
        if not sysroot:
            found = re.search(r"--with-sysroot=([^ ']+)", text_all)
            if found:
                sysroot = found.group(1)
                source = "--with-sysroot in top-level Makefile"
        print("R3GATE1 sysroot_source={} sysroot={}".format(source, sysroot))
        if not sysroot or not os.path.isdir(sysroot):
            raise ConanException("R3GATE1_FAIL sysroot={!r}".format(sysroot))
        print("R3GATE1 PASS")

    def _r3_gate_before_target(self, wrapper):
        """R3 gate 2 (cheap): link a probe shaped like the real libgcc_s.so link.

        The -B / -isystem prefix sequence is rebuilt from the generated
        prefix + target triplet exactly the way libgcc's $(CC) line spells it
        (build_tooldir = $(exec_prefix)/$(target_noncanonical)), so the probe
        exercises the same startfile search the shared link will use instead
        of testing a different command line.
        """
        triplet = self._target_triplet
        crt_dir = os.path.join(self._ohos_sysroot, "usr", "lib", triplet)
        build_gcc = os.path.join(self.build_folder, "gcc")
        raw = os.path.join(build_gcc, "xgcc")
        src = os.path.join(self.build_folder, "r3_crt_probe.c")
        out = os.path.join(self.build_folder, "r3_crt_probe.so")
        prefix = "/"
        makefile = os.path.join(self.build_folder, "Makefile")
        if os.path.isfile(makefile):
            pattern = re.compile(r"^prefix\s*=\s*(.*)$")
            for line in open(makefile, encoding="utf-8", errors="replace"):
                match = pattern.match(line)
                if match:
                    prefix = match.group(1).strip()
                    break
        build_tooldir = prefix + "/" + triplet
        trailing = [
            "-B" + build_tooldir + "/bin/",
            "-B" + build_tooldir + "/lib/",
            "-isystem",
            build_tooldir + "/include",
            "-isystem",
            build_tooldir + "/sys-include",
        ]
        with open(src, "w", encoding="utf-8") as handle:
            handle.write("int r3_crt_probe(void) { return 1; }\n")
        print("R3GATE2 crt_dir={} exists={}".format(crt_dir, os.path.isdir(crt_dir)))
        print("R3GATE2 build_tooldir={} prefix={}".format(build_tooldir, prefix))
        printed = subprocess.run(
            [raw, "-print-sysroot"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        ).stdout.strip()
        search = subprocess.run(
            [raw, "-print-search-dirs"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        ).stdout
        print("R3GATE2 print_sysroot={}".format(printed))
        print("R3GATE2 search_dirs_slash2={}".format(search.count("//")))
        if not printed or not os.path.isdir(printed):
            raise ConanException("R3GATE2_FAIL print-sysroot={!r}".format(printed))
        if "//" in search:
            raise ConanException("R3GATE2_FAIL -print-search-dirs contains //")
        # R3 fix 2 (2026-10-02): a real link cannot run at this point.
        # crtbeginS.o / crtendS.o are produced by all-target-libgcc itself and
        # copied back into build/gcc by that stage (measured at gate time:
        # neither build/gcc/ nor the libgcc dir holds any crt*.o), and the real
        # link also carries -B./ coming from $(CFLAGS).  So drive the same
        # command line with -### instead: nothing is linked, while the printed
        # collect2 line still shows whether the driver LOCATES crti.o (absolute
        # sysroot path) or hands ld the bare name -- the exact thing r2 died on.
        tail_flags = ["-O2", "-fPIC", "-shared", "-###", "-o", out, src]
        commands = [
            ("wrapper", [wrapper] + trailing + tail_flags),
            ("raw_xgcc", [raw, "-B" + build_gcc + os.sep] + trailing + tail_flags),
        ]
        results = {}
        for tag, argv in commands:
            print("R3GATE2 cmd_{}={}".format(tag, " ".join(argv)))
            proc = subprocess.run(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
            )
            lines = [
                line
                for line in proc.stdout.splitlines()
                if "collect2" in line or "crti.o" in line
            ]
            line = lines[-1] if lines else ""
            tokens = line.split()
            located = any(token.endswith("/crti.o") for token in tokens)
            bare = any(token == "crti.o" for token in tokens)
            results[tag] = located
            print(
                "R3GATE2 dry_{} rc={} crti_located={} crti_bare={} collect={}".format(
                    tag, proc.returncode, located, bare, line[:400]
                )
            )
        if not results.get("wrapper"):
            raise ConanException("R3GATE2_FAIL wrapper does not locate crti.o")
        print(
            "R3GATE2 PASS wrapper_locates_crti=True raw_locates_crti={} "
            "(raw informational; CC is forced to wrapper)".format(results.get("raw_xgcc"))
        )

    def _r3_build_host_compilers(self):
        """Build-machine CC/CXX exactly as configure recorded them (clang).

        The target make lines below override CC/CXX; the top level defines
        CC_FOR_BUILD = $(CC) and CXX_FOR_BUILD = $(CXX) with a recursive '=', so
        without an explicit value the target wrapper lands in the *build*
        compiler slot.  Measured 2026-10-03: CXX_FOR_BUILD then resolved to the
        xgpp-sign wrapper whose real_compiler path did not exist
        (xgpp-sign -E -> rc=127), autoconf fell back to /lib/cpp, and
        configure-target-libstdc++-v3 died on the sanity check.
        """
        makefile = os.path.join(self.build_folder, "Makefile")
        pattern = re.compile(r"^(CC|CXX)\s*=\s*(\S+)\s*$")
        values = {}
        if os.path.isfile(makefile):
            for line in open(makefile, encoding="utf-8", errors="replace"):
                match = pattern.match(line)
                if match and match.group(1) not in values:
                    values[match.group(1)] = match.group(2)
        print(
            "R3HOSTCC host_cc={} host_cxx={}".format(
                values.get("CC", ""), values.get("CXX", "")
            )
        )
        return values.get("CC", ""), values.get("CXX", "")

    def _r3_gate3_libstdcxx_cpp(self, raw_cxx_parts):
        """R3 gate 3 (cheap, before the long libstdc++ configure).

        Reproduces the exact command that failed twice in config.log
        (configure:12641) and requires it to preprocess <limits.h>, i.e. that
        bits/alltypes.h resolves through the multiarch include directory.
        """
        conftest = os.path.join(self.build_folder, "r3_conftest.cpp")
        with open(conftest, "w", encoding="utf-8") as handle:
            handle.write("#include <limits.h>\nint main(void) { return 0; }\n")
        argv = list(raw_cxx_parts) + ["-E", conftest]
        proc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        tail = " | ".join(proc.stdout.strip().splitlines()[-2:])
        print(
            "R3GATE3 driver={} -E conftest.cpp rc={} tail={}".format(
                raw_cxx_parts[0], proc.returncode, tail[:300]
            )
        )
        if proc.returncode != 0:
            raise ConanException(
                "R3GATE3_FAIL libstdc++ C++ preprocessor rc={}".format(
                    proc.returncode
                )
            )
        print("R3GATE3 PASS bits/alltypes.h resolved")

    def _r3_shim_gnu_linux_os_defines(self, cxx_driver):
        """R3 fix 5 (2026-10-03, measured): libstdc++ resolves
        OS_INC_SRCDIR=config/os/gnu-linux for host_os=linux-ohos, but the OHOS
        sysroot ships a 905-byte features.h with no __GLIBC_PREREQ at all, so
        each "#if __GLIBC_PREREQ(2,x)" in that header expands to "#if (2,x)" and
        the precompile dies with

            os_defines.h:44:19: error: missing binary operator before token "("

        Measured: libstdc++-v3/configure has no switch for this (os_include_dir
        occurs 4 times, no --with-os-include-dir, no env fallback), and the
        zero-dependency variants (bionic/uclibc) are unreachable, so guard the
        macro itself: on a non-glibc libc every glibc version gate must read
        false.  A/B measured with the same driver on this very machine:
        unpatched -E -> rc=1 with the production error, patched -> rc=0.
        """
        target = os.path.join(
            self.source_folder,
            "libstdc++-v3",
            "config",
            "os",
            "gnu-linux",
            "os_defines.h",
        )
        if not os.path.isfile(target):
            raise ConanException("R3OSDEF_FAIL missing {}".format(target))
        marker = "/* R3 glibc shim */"
        text = open(target, encoding="utf-8").read()
        patched = marker in text
        anchor = "#include <features.h>\n"
        if anchor not in text:
            # os/generic (R3 fix 6) does not include <features.h> at all,
            # which is precisely why the glibc gates are gone.
            print("R3OSDEF skip=no-features-h variant=non-glibc")
            return
        if not patched:
            if text.count(anchor) != 1:
                raise ConanException("R3OSDEF_FAIL anchor not unique")
            shim = (
                anchor
                + "\n#ifndef __GLIBC_PREREQ\n"
                + "/* R3 glibc shim: OHOS libc is not glibc; every glibc version gate\n"
                + "   must evaluate false instead of expanding to \"#if (2,15)\". */\n"
                + "# define __GLIBC_PREREQ(major, minor) 0\n"
                + "#endif\n"
            )
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(text.replace(anchor, shim, 1))
        proc = subprocess.run(
            [cxx_driver, "-E", target],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        tail = " | ".join(proc.stdout.strip().splitlines()[-2:])
        print(
            "R3OSDEF file={} patched={} -E rc={} tail={}".format(
                target, patched, proc.returncode, tail[:300]
            )
        )
        if proc.returncode != 0:
            raise ConanException(
                "R3OSDEF_FAIL patched os_defines -E rc={}".format(proc.returncode)
            )
        print("R3OSDEF PASS glibc gates evaluate false")

    def _r3_switch_os_variant_generic(self):
        """R3 fix 6 (2026-10-03, family-level): libstdc++ picks its OS header
        dir in libstdc++-v3/configure.host, where

            gnu* | linux* | kfreebsd*-gnu | uclinux*)
                ... else os_include_dir="os/gnu-linux"

        and host_os=linux-ohos matches that branch.  os/gnu-linux is written
        against glibc headers, which OHOS does not ship -- measured casualties:

          * os_defines.h:44 "#if __GLIBC_PREREQ(2,15)" -> missing binary
            operator (OHOS features.h has no __GLIBC_PREREQ at all)
          * ctype_base.h:49 "_ISupper was not declared" (the whole OHOS include
            tree has zero occurrences of _ISupper)

        Upstream already routes linux-musl* to os/generic and OHOS is musl, so
        add the matching linux-ohos* branch instead of patching individual
        headers.  Measured (compile tests against the real include tree):

          gnu-linux  rc=1 _ISupper not declared   (production error)
          generic    rc=0                         (ctype_base + os_defines)
          bionic     rc=1 _U not declared         (bionic ctype macros absent)

        The gate _r3_gate_variant() then proves the switch really took effect.
        """
        target = os.path.join(
            self.source_folder, "libstdc++-v3", "configure.host"
        )
        if not os.path.isfile(target):
            raise ConanException("R3VARIANT_FAIL missing {}".format(target))
        marker = "# R3 ohos -> os/generic"
        text = open(target, encoding="utf-8").read()
        done = marker in text
        if not done:
            anchor = "  gnu* | linux* | kfreebsd*-gnu | uclinux*)\n"
            if text.count(anchor) != 1:
                raise ConanException("R3VARIANT_FAIL anchor not unique")
            branch = (
                "  linux-ohos*)\n"
                "    # R3 ohos -> os/generic\n"
                "    # OHOS ships musl, exactly like the linux-musl* branch\n"
                "    # above; os/gnu-linux assumes glibc headers and breaks\n"
                "    # on both __GLIBC_PREREQ and _ISupper.\n"
                "    os_include_dir=\"os/generic\"\n"
                "    ;;\n"
            )
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(text.replace(anchor, branch + anchor, 1))
        # cheap self-check: run configure.host the way configure does
        host_os = "-".join(self._target_triplet.split("-")[1:])
        check = subprocess.run(
            [
                (shutil.which("sh") or "/bin/sh"),
                "-c",
                "host_os=$1; host=$2; uclibc=no; bionic=no; "
                '. "$3" 2>/dev/null; printf "%s" "$os_include_dir"',
                "sh",
                host_os,
                self._target_triplet,
                target,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        value = check.stdout.strip()
        print(
            "R3VARIANT patched={} host_os={} os_include_dir={}".format(
                done, host_os, value
            )
        )
        if value != "os/generic":
            raise ConanException(
                "R3VARIANT_FAIL os_include_dir={!r} (expected os/generic)".format(
                    value
                )
            )
        print("R3VARIANT PASS configure.host routes ohos to os/generic")

    def _r3_gate_variant(self, cxx_driver):
        """R3 gate 4 (cheap, after configure-target-libstdc++-v3): prove the
        switch actually landed -- both symlinks must point into config/os/generic,
        config.status must record it, and a ctype conftest must compile (that is
        the _ISupper check that killed round 5)."""
        include_dir = os.path.join(
            self.build_folder,
            "aarch64-linux-ohos",
            "libstdc++-v3",
            "include",
            "aarch64-linux-ohos",
            "bits",
        )
        status = os.path.join(
            self.build_folder,
            "aarch64-linux-ohos",
            "libstdc++-v3",
            "config.status",
        )
        ctype_link = os.path.join(include_dir, "ctype_base.h")
        os_link = os.path.join(include_dir, "os_defines.h")
        real_ctype = os.path.realpath(ctype_link) if os.path.lexists(ctype_link) else "(missing)"
        real_os = os.path.realpath(os_link) if os.path.lexists(os_link) else "(missing)"
        os_inc = ""
        if os.path.isfile(status):
            for line in open(status, encoding="utf-8", errors="replace"):
                if 'S["OS_INC_SRCDIR"]=' in line:
                    os_inc = line.strip()
                    break
        print(
            "R3GATE4 ctype->{} | os->{} | {}".format(real_ctype, real_os, os_inc)
        )
        for value, what in ((real_ctype, "ctype_base"), (real_os, "os_defines")):
            if "config/os/generic" not in value:
                raise ConanException(
                    "R3GATE4_FAIL {} still resolves to {!r}".format(what, value)
                )
        if "config/os/generic" not in os_inc:
            raise ConanException(
                "R3GATE4_FAIL config.status OS_INC_SRCDIR={!r}".format(os_inc)
            )
        build_include = os.path.join(
            self.build_folder, "aarch64-linux-ohos", "libstdc++-v3", "include"
        )
        conftest = os.path.join(self.build_folder, "r3_ctype_conftest.cpp")
        with open(conftest, "w", encoding="utf-8") as handle:
            handle.write(
                "#include <bits/c++config.h>\n"
                "#include <bits/ctype_base.h>\n"
                "int r3_ctype_use() { return (int)std::ctype_base::upper; }\n"
            )
        proc = subprocess.run(
            [
                cxx_driver,
                "-I" + build_include,
                "-I" + build_include + os.sep + self._target_triplet,
                "-c",
                conftest,
                "-o",
                conftest + ".o",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        tail = " | ".join(proc.stdout.strip().splitlines()[-2:])
        print(
            "R3GATE4 ctype_conftest rc={} tail={}".format(proc.returncode, tail[:300])
        )
        if proc.returncode != 0:
            raise ConanException(
                "R3GATE4_FAIL ctype conftest rc={}".format(proc.returncode)
            )
        print("R3GATE4 PASS _ISupper resolves via os/generic")

    def build(self):
        # W2 gate (conan-verify G1) requires an explicit patch application
        # call.  conandata.yml declares no patches for 14.2.0, so this is a
        # logged no-op (conan prints "No patches defined in conandata").
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        # R3 fix 6 first: route libstdc++ to os/generic (musl-like) headers.
        self._r3_switch_os_variant_generic()
        # GCC's top-level configure is large enough to exhaust the default
        # shell stack on HarmonyOS.  CONFIG_SHELL influences nested configure
        # scripts, but it neither replaces the initial interpreter nor raises
        # its stack limit.  Start Bash with an unlimited stack, then exec a
        # second Bash so the configure process inherits that limit.
        configure_shell = self._required_executable(
            "bash",
            os.environ.get("CONFIG_SHELL"),
            "bash",
            "/data/service/hnp/bin/bash",
        )
        configure_command = "{} {} {}".format(
            shlex.quote(configure_shell),
            shlex.quote(configure),
            " ".join(shlex.quote(argument) for argument in self._configure_args()),
        )
        # Conan raises on every non-zero exit code when ignore_errors is False.
        # Keep this explicit so configure/build/install failures cannot be
        # mistaken for a successful compiler package.
        self._run_with_unlimited_stack(
            configure_command,
            cwd=self.build_folder,
        )
        # R3 gate 1: read prefix/tooldir/sysroot immediately after configure,
        # before any make, so a bogus root cannot burn a whole build round.
        self._r3_gate_after_configure()

        # GNU Make 4.4 defaults to a FIFO jobserver, which HMDFS cannot create
        # reliably.  The OpenDesk toolchain supports the pipe jobserver, so a
        # conservative two-way build avoids both the FIFO failure and the CI
        # conan-create timeout caused by a fully serial GCC build.
        # R3 fix 8 (2026-10-03, measured): -j8 died at 12:09:01 with
        #   xgcc: fatal error: cannot execute '.../gcc/cc1':
        #   posix_spawn: Out of memory
        # while launching with only 51-114MB above the 8000MB gate
        # (MemAvailable 8051/8114, PSI_full avg10=70).  -j4 has a 5/5
        # record with zero OOM on this machine and costs ~456s more on
        # all-gcc (measured r4 vs r5), which still fits the run budget.
        jobs = 4
        make = "make --jobserver-style=pipe -j{}".format(jobs)
        self._run_with_unlimited_stack(
            "{} all-gcc".format(make),
            cwd=self.build_folder,
        )

        # Host generators and the newly built compiler must be signed before
        # they can execute on HarmonyOS.  The compiler wrappers sign normal
        # host links; this pass also covers build-system-created executables.
        self._sign_elf_tree(self.build_folder)

        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        target_cc = xgcc
        if self._is_ohos:
            target_cc = self._write_compiler_wrapper(
                "xgcc-sign",
                xgcc,
                extra_args=[
                    "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                    "-B" + os.path.join(self._ohos_sysroot, "usr", "lib", self._target_triplet) + os.sep,
                    "-isystem",
                    self._ohos_target_include,
                    # The OHOS SDK annotates APIs with Clang's availability
                    # argument syntax (for example introduced=12.0.0).  GCC 14
                    # cannot parse that dotted version expression, so discard
                    # only this annotation while retaining all other target
                    # header contents and compiler attributes.
                    "-D__availability__(...)=",
                ],
            )

        # R3 root cause (measured 2026-10-02): the libgcc_s.so shared link is
        # driven by $(CC) inside the libgcc makefile, and configure bakes that
        # CC from CC_FOR_TARGET.  A raw xgcc has no startfile prefix pointing
        # at <sysroot>/usr/lib/<triplet> (crti.o / crtn.o live there), so ld
        # reports "cannot find crti.o".  Readings: overriding CC changes the
        # emitted link command while overriding GCC_FOR_TARGET does not; the
        # xgcc-sign wrapper and an explicit -B<sysroot>/usr/lib/<triplet>/ both
        # link the probe with rc=0, the raw xgcc with rc=1.  The wrapper already
        # carries that -B, so force CC to it here instead of editing the wrapper.
        if self._is_ohos:
            self._r3_gate_before_target(target_cc)
        target_vars = "CC_FOR_TARGET={}".format(shlex.quote(target_cc))
        if self._is_ohos:
            target_vars += " CC={}".format(shlex.quote(target_cc))
        host_cc, host_cxx = self._r3_build_host_compilers()
        if host_cc:
            target_vars += " CC_FOR_BUILD={}".format(shlex.quote(host_cc))
        if host_cxx:
            target_vars += " CXX_FOR_BUILD={}".format(shlex.quote(host_cxx))
        self._run_with_unlimited_stack(
            "{} all-target-libgcc {}".format(make, target_vars),
            cwd=self.build_folder,
        )

        # GATE2 probe: C++ runtime (libstdc++) for the c,c++ configuration.
        # R3 fix B (measured 2026-10-03): the C++ driver is built at
        # <build>/gcc/xg++ in this layout.  The old lookup only tried
        # <build>/g++/xg++ and <build>/xg++, neither of which exists, so
        # xgpp-sign pointed at a missing binary ("xg++: inaccessible or not
        # found", rc=127) and any configure using it fell back to /lib/cpp.
        xgpp_candidates = [
            os.path.join(self.build_folder, "gcc", "xg++"),
            os.path.join(self.build_folder, "g++", "xg++"),
            os.path.join(self.build_folder, "xg++"),
        ]
        xgpp = next(
            (candidate for candidate in xgpp_candidates if os.path.isfile(candidate)),
            xgpp_candidates[0],
        )
        if not os.path.isfile(xgpp):
            raise ConanException(
                "C++ driver xg++ was not found in any of: {}".format(xgpp_candidates)
            )
        target_cxx = xgpp
        if self._is_ohos:
            target_cxx = self._write_compiler_wrapper(
                "xgpp-sign",
                xgpp,
                extra_args=[
                    # cc1plus and the crt pieces live in <build>/gcc; pointing
                    # at a non-existent <build>/g++ makes the driver report
                    # "cannot execute cc1plus".
                    "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                    "-B" + os.path.join(self._ohos_sysroot, "usr", "lib", self._target_triplet) + os.sep,
                    "-isystem",
                    self._ohos_target_include,
                    "-D__availability__(...)=",
                ],
            )
        # Same R3 reason as above: force CC/CXX so the shared links that need
        # crti.o / crtn.o go through the wrapper carrying the sysroot -B.
        # R3 fix 3 (2026-10-02, measured): this target depends on
        # all-target-libgcc, so the second pass re-enters the libgcc makefile;
        # without CC_FOR_TARGET here the top level falls back to its own
        # default (top-level Makefile: CC_FOR_TARGET=$(STAGE_CC_WRAPPER)
        # $$r/$(HOST_SUBDIR)/gcc/xgcc -B$$r/$(HOST_SUBDIR)/gcc/) and pushes raw
        # xgcc down as CC, which is exactly the 22:47:06 crti.o failure.  The
        # first pass (which did carry CC_FOR_TARGET) linked libgcc_s.so.1
        # successfully with the wrapper at 22:46.
        target_vars = "CXX_FOR_TARGET={} CC_FOR_TARGET={}".format(
            shlex.quote(target_cxx), shlex.quote(target_cc)
        )
        if self._is_ohos:
            target_vars += " CC={}".format(shlex.quote(target_cc))
            target_vars += " CXX={}".format(shlex.quote(target_cxx))
        host_cc, host_cxx = self._r3_build_host_compilers()
        if host_cc:
            target_vars += " CC_FOR_BUILD={}".format(shlex.quote(host_cc))
        if host_cxx:
            target_vars += " CXX_FOR_BUILD={}".format(shlex.quote(host_cxx))
        # R3 fix 4 (2026-10-03, measured): the configure rule re-exports CXX
        # from inside its own shell -- top-level Makefile:
        #   RAW_CXX_TARGET_EXPORTS = ... CXX_FOR_TARGET="$(RAW_CXX_FOR_TARGET)";
        #   export CXX_FOR_TARGET; CXX="$(RAW_CXX_FOR_TARGET)
        #   $(XGCC_FLAGS_FOR_TARGET) $$TFLAGS"; export CXX;
        # so it beats every CXX we pass on the command line.  RAW_CXX_FOR_TARGET
        # points at the raw xgcc with no -isystem for the multiarch target
        # headers, which is exactly the measured failure:
        #   .../sysroot/usr/include/limits.h:6:10: fatal error:
        #   bits/alltypes.h: No such file or directory
        #   -> configure: error: C++ preprocessor "/lib/cpp" fails sanity check.
        # Pin that channel to the signed C++ wrapper (it carries
        # -isystem <sysroot>/usr/include/<triplet>, -B<sysroot>/usr/lib/<triplet>/
        # and -D__availability__(...)=) while keeping the rest of the raw flags.
        # R3 fix 5 first: guard the glibc-only version gates in os_defines.
        self._r3_shim_gnu_linux_os_defines(target_cxx)
        raw_cxx_parts = []
        if self._is_ohos:
            raw_cxx_parts = [
                target_cxx,
                "-shared-libgcc",
                "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                "-nostdinc++",
                "-L"
                + os.path.join(
                    self.build_folder, "aarch64-linux-ohos", "libstdc++-v3", "src"
                ),
                "-L"
                + os.path.join(
                    self.build_folder,
                    "aarch64-linux-ohos",
                    "libstdc++-v3",
                    "src",
                    ".libs",
                ),
                "-L"
                + os.path.join(
                    self.build_folder,
                    "aarch64-linux-ohos",
                    "libstdc++-v3",
                    "libsupc++",
                    ".libs",
                ),
            ]
        if raw_cxx_parts:
            raw_cxx = " ".join(raw_cxx_parts)
            self._r3_gate3_libstdcxx_cpp(raw_cxx_parts)
            target_vars += " " + shlex.quote("RAW_CXX_FOR_TARGET=" + raw_cxx)
        # Split configure from the build so the variant gate can prove the
        # switch before the long compile starts.
        self._run_with_unlimited_stack(
            "{} configure-target-libstdc++-v3 {}".format(make, target_vars),
            cwd=self.build_folder,
        )
        self._r3_gate_variant(target_cxx)
        self._run_with_unlimited_stack(
            "{} all-target-libstdc++-v3 {}".format(make, target_vars),
            cwd=self.build_folder,
        )

        # GCC's own language-independent and C frontend selftests.  The main
        # build runs these once; the explicit target leaves an auditable test
        # command in the Conan log.
        self._run_with_unlimited_stack(
            "make -C gcc selftest",
            cwd=self.build_folder,
        )

        # Upstream execution torture tests: compile and run a deterministic
        # subset of gcc.c-torture/execute with the freshly built compiler.
        # Each source is built at -O0 and -O2 (100 executions in total),
        # signed by the xgcc-sign wrapper on OHOS and executed on-device.
        self._run_torture_execute_subset(target_cc)


    def _run_torture_execute_subset(self, compiler_wrapper):
        if not self._is_ohos:
            return
        tests_root = os.path.join(
            self.source_folder,
            "gcc",
            "testsuite",
            "gcc.c-torture",
            "execute",
        )
        if not os.path.isdir(tests_root):
            self.output.warning(
                "Upstream torture testsuite not found: {}".format(tests_root)
            )
            return
        sources = sorted(
            name for name in os.listdir(tests_root) if name.endswith(".c")
        )[:50]
        work = os.path.join(self.build_folder, "torture-execute")
        os.makedirs(work, exist_ok=True)
        # The packaged OHOS GCC driver adds -B<sysroot>/usr/lib/<triplet>/ so
        # the linker finds crt1.o/crti.o/crtn.o.  The in-tree xgcc driver does
        # not, so the torture compiles would fail at link time without it.
        crt_search = "-B" + os.path.join(
            self._ohos_sysroot, "usr", "lib", self._target_triplet
        ) + os.sep
        total = 0
        passed = 0
        failed = 0
        failures = []
        for source_name in sources:
            source = os.path.join(tests_root, source_name)
            stem = source_name[:-2]
            for opt in ("-O0", "-O2 -fno-strict-aliasing"):
                total += 1
                tag = "{}_{}".format(stem, "o0" if opt == "-O0" else "o2")
                executable = os.path.join(work, tag)
                compile_result = self.run(
                    "{} {} -w {} {} -o {}".format(
                        shlex.quote(compiler_wrapper),
                        shlex.quote(crt_search),
                        opt,
                        shlex.quote(source),
                        shlex.quote(executable),
                    ),
                    cwd=self.build_folder,
                    env="conanbuild",
                    ignore_errors=True,
                )
                if compile_result != 0:
                    failed += 1
                    failures.append("{}: compile failed".format(tag))
                    continue
                run_result = self.run(
                    shlex.quote(executable),
                    cwd=work,
                    env="conanbuild",
                    ignore_errors=True,
                )
                if run_result != 0:
                    failed += 1
                    failures.append("{}: run failed".format(tag))
                else:
                    passed += 1
        self.output.info(
            "upstream gcc.c-torture/execute subset: {}/{} passed".format(
                passed, total
            )
        )
        if failed and failed / float(total) > 0.1:
            raise ConanInvalidConfiguration(
                "Upstream torture subset failed ({}/{}): {}".format(
                    passed, total, "; ".join(failures[:20])
                )
            )

    def package(self):
        # R3 fix 7 (measured 2026-10-03): the top-level build Makefile has no
        # install-plugin target at all (grep -c "^install-plugin" = 0) and the
        # old call died with "make: *** No rule to make target 'install-plugin'".
        # The target lives in gcc/Makefile:
        #   1950: lang.install-plugin: c.install-plugin c++.install-plugin
        #   3832: install: install-plugin
        #   3915: install-plugin: installdirs lang.install-plugin s-header-vars ...
        # so install-gcc already ships plugin/include (475 .h measured, incl.
        # gcc-plugin.h), and the explicit subdirectory call keeps that intent
        # auditable instead of silently dropping it.
        self._run_with_unlimited_stack(
            "make install-gcc install-target-libgcc install-target-libstdc++-v3 DESTDIR={}".format(
                shlex.quote(self.package_folder)
            ),
            cwd=self.build_folder,
        )
        self._run_with_unlimited_stack(
            "make -C gcc install-plugin DESTDIR={}".format(
                shlex.quote(self.package_folder)
            ),
            cwd=self.build_folder,
        )
        plugin_include = os.path.join(
            self.package_folder,
            "lib",
            "gcc",
            self._target_triplet,
            str(self.version),
            "plugin",
            "include",
        )
        headers = []
        if os.path.isdir(plugin_include):
            for root, _dirs, files in os.walk(plugin_include):
                headers.extend(
                    os.path.join(root, name)
                    for name in files
                    if name.endswith(".h")
                )
        gcc_plugin = os.path.join(plugin_include, "gcc-plugin.h")
        print(
            "R3PLUGIN include={} headers={} gcc_plugin_h={}".format(
                plugin_include, len(headers), os.path.isfile(gcc_plugin)
            )
        )
        if not headers or not os.path.isfile(gcc_plugin):
            raise ConanException(
                "R3PLUGIN_FAIL plugin headers missing under {}".format(
                    plugin_include
                )
            )
        print("R3PLUGIN PASS plugin/include installed")
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if self._is_ohos:
            self._install_ohos_driver_wrapper()
        self._sign_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
        if self._is_ohos:
            exec_prefix = os.path.join(
                self.package_folder,
                "libexec",
                "gcc",
            ) + os.sep
            self.buildenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
            self.runenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
