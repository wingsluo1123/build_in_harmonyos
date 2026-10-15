#!/usr/bin/env python3
"""Conan recipe - asterisk-odbc 22.10.1.

Packages the Asterisk ODBC module set from the canonical Asterisk 22.10.1
source tarball.  The package intentionally contains only loadable Asterisk
modules and sample ODBC configs, not the full PBX application.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"

ODBC_MODULES = [
    ("res", "res_odbc_transaction.so"),
    ("res", "res_odbc.so"),
    ("res", "res_config_odbc.so"),
    ("funcs", "func_odbc.so"),
    ("cdr", "cdr_odbc.so"),
    ("cdr", "cdr_adaptive_odbc.so"),
    ("cel", "cel_odbc.so"),
]

ODBC_SAMPLES = [
    "res_odbc.conf.sample",
    "res_config_odbc.conf.sample",
    "func_odbc.conf.sample",
    "cdr_odbc.conf.sample",
    "cdr_adaptive_odbc.conf.sample",
    "cel_odbc.conf.sample",
]


def _replace_text(path, replacements):
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.read()
    changed = False
    for old_text, new_text in replacements.items():
        if old_text in content:
            content = content.replace(old_text, new_text)
            changed = True
    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass
    return changed


class AsteriskOdbcConan(ConanFile):
    name = "asterisk-odbc"
    version = "22.10.1"
    description = "Asterisk PBX ODBC modules (res_odbc, func_odbc, CDR/CEL ODBC)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.asterisk.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} supports only Linux/OHOS, got os={self.settings.os}")

    def requirements(self):
        self.requires("unixodbc/2.3.12")
        self.requires("libedit/20240808")
        self.requires("uuid/2.40.1")
        self.requires("jansson/2.15.1")
        self.requires("libxml2/2.15.3")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    @property
    def _pc_dir(self):
        path = os.path.join(self.build_folder, "gen-pkgconfig")
        os.makedirs(path, exist_ok=True)
        return path

    def _shell_path(self):
        # Prefer the profile-provided bash on OHOS; configure is sensitive to shell quirks.
        return (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )

    def _dependency_libdirs(self):
        libdirs = []
        for dep_name in ("unixodbc", "libedit", "uuid", "jansson", "libxml2", "sqlite3"):
            dep = self.dependencies[dep_name]
            libdirs.extend(dep.cpp_info.libdirs)
        return [path for path in libdirs if path]

    def _dependency_incdirs(self):
        incdirs = []
        for dep_name in ("unixodbc", "libedit", "uuid", "jansson", "libxml2", "sqlite3"):
            dep = self.dependencies[dep_name]
            incdirs.extend(dep.cpp_info.includedirs)
        return [path for path in incdirs if path]

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
            tc.extra_cflags.append("-Qunused-arguments")
            tc.extra_cxxflags.append("-Qunused-arguments")
            tc.extra_cflags.append("-fblocks")
            tc.extra_cxxflags.append("-fblocks")
            tc.extra_ldflags.append(self._ohos_linker_flag())

        unixodbc = self.dependencies["unixodbc"]
        tc.configure_args.extend([
            f"--with-unixodbc={unixodbc.package_folder}",
            "--without-iodbc",
            "--without-pjproject",
            "--without-x11",
            "--without-gtk2",
        ])

        for incdir in self._dependency_incdirs():
            tc.extra_cflags.append(f"-I{incdir}")
        for libdir in self._dependency_libdirs():
            tc.extra_ldflags.append(f"-L{libdir}")
        tc.generate()

        self._write_pc("libedit", self.dependencies["libedit"], ["-ledit"])
        xml2 = self.dependencies["libxml2"]
        self._write_pc("libxml-2.0", xml2, ["-lxml2"],
                       extra_cflags=["-I" + path for path in xml2.cpp_info.includedirs])

    def _write_pc(self, name, dep, libs, extra_cflags=None):
        libdir = dep.cpp_info.libdirs[0]
        incdir = dep.cpp_info.includedirs[0]
        content = "\n".join([
            f"prefix={dep.package_folder}",
            "exec_prefix=${prefix}",
            f"libdir={libdir}",
            f"includedir={incdir}",
            "",
            f"Name: {name}",
            f"Description: {name} (conan package shim)",
            f"Version: {dep.ref.version}",
            f"Libs: -L${{libdir}} {' '.join(libs)}",
            f"Cflags: -I${{includedir}} {' '.join(extra_cflags or [])}",
        ]) + "\n"
        with open(os.path.join(self._pc_dir, f"{name}.pc"), "w", encoding="utf-8") as handle:
            handle.write(content)

    def _build_env(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("ASTTOPDIR", self.source_folder)
        env.define("ASTCFLAGS", f"-I{os.path.join(self.source_folder, 'include')}")
        env.define("PWD", self.source_folder)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        shell = self._shell_path()
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        env.define("PKG_CONFIG_PATH", self._pc_dir)
        libdirs = self._dependency_libdirs()
        if self.settings.os == "OHOS":
            # lld is a target-side executable on the device, but it loads
            # libxml2 from the device toolchain at link time.  Keep these
            # paths in the build environment only; they must not leak into
            # the package's consumer run environment.
            tool_libdirs = self._ohos_toolchain_libdirs()
            inherited = os.environ.get("LD_LIBRARY_PATH", "")
            ld_library_path = os.pathsep.join(
                path for path in tool_libdirs + libdirs + ([inherited] if inherited else [])
                if path
            )
            if ld_library_path:
                env.define("LD_LIBRARY_PATH", ld_library_path)
        elif libdirs:
            env.define("LD_LIBRARY_PATH", os.pathsep.join(libdirs))
        if libdirs:
            env.define("LIBRARY_PATH", os.pathsep.join(libdirs))
        libedit = self.dependencies["libedit"]
        if libedit.cpp_info.includedirs and libedit.cpp_info.libdirs:
            libedit_cflags = [f"-I{path}" for path in libedit.cpp_info.includedirs]
            libedit_cflags.extend(
                f"-I{os.path.join(path, 'editline')}"
                for path in libedit.cpp_info.includedirs
                if os.path.isdir(os.path.join(path, "editline"))
            )
            env.define("LIBEDIT_CFLAGS", " ".join(libedit_cflags))
            env.define(
                "LIBEDIT_LIBS",
                " ".join([f"-L{path}" for path in libedit.cpp_info.libdirs] + ["-ledit"]),
            )
        xml2 = self.dependencies["libxml2"]
        if xml2.cpp_info.includedirs and xml2.cpp_info.libdirs:
            env.define(
                "LIBXML2_CFLAGS",
                " ".join(f"-I{path}" for path in xml2.cpp_info.includedirs),
            )
            env.define(
                "LIBXML2_LIBS",
                " ".join([f"-L{path}" for path in xml2.cpp_info.libdirs] + ["-lxml2"]),
            )
        if xml2.cpp_info.includedirs:
            env.define("OHOS_XML2_INCDIR", os.path.join(xml2.cpp_info.includedirs[0], "libxml2"))
        return env

    def _patch_configure_tmpdir(self):
        replacements = {
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&':
                'tmp=`(umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` &&',
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")':
                'tmp="${TMPDIR:-.}"/conf$$-$RANDOM\n  (umask 022 && mkdir -p "$tmp")',
            '"cannot create a temporary directory in ."':
                '"cannot create a temporary directory"',
        }
        for script in ("configure", os.path.join("menuselect", "configure")):
            path = os.path.join(self.source_folder, script)
            if _replace_text(path, replacements):
                self.output.info(f"patched {script}: umask 077 -> 022 and TMPDIR")

    def _patch_blocks_runtime_check(self):
        configure = os.path.join(self.source_folder, "configure")
        changed = _replace_text(configure, {
            'as_fn_error $? "BlocksRuntime is required for clang, please install libblocksruntime"':
                '# OHOS: blocks disabled; no libblocksruntime package is available\n'
                'AST_CLANG_BLOCKS=""; AST_CLANG_BLOCKS_LIBS=""'
        })
        if changed:
            self.output.info("patched configure: disabled clang BlocksRuntime hard failure")

    def _patch_ohos_recursive_mutex_init(self):
        if self.settings.os != "OHOS":
            return
        lock_header = os.path.join(self.source_folder, "include", "asterisk", "lock.h")
        changed = _replace_text(lock_header, {
            "#if (defined(SOLARIS) || defined(BSD))\n"
            "#define AST_MUTEX_INIT_W_CONSTRUCTORS\n"
            "#endif /* SOLARIS || BSD */":
                "#if (defined(SOLARIS) || defined(BSD) || defined(__OHOS__))\n"
                "#define AST_MUTEX_INIT_W_CONSTRUCTORS\n"
                "#endif /* SOLARIS || BSD || __OHOS__ */"
        })
        if changed:
            self.output.info(
                "patched include/asterisk/lock.h: use constructor-based recursive mutex initialization on OHOS"
            )

    def _patch_menuselect_xml2_include(self):
        makefile = os.path.join(self.source_folder, "menuselect", "Makefile")
        changed = _replace_text(makefile, {
            "CFLAGS+=-g -D_GNU_SOURCE -Wall -Wno-deprecated-declarations":
                "CFLAGS+=-g -D_GNU_SOURCE -Wall -Wno-deprecated-declarations\n"
                "CFLAGS+=-I$(OHOS_XML2_INCDIR)"
        })
        if changed:
            self.output.info("patched menuselect/Makefile: libxml2 include via OHOS_XML2_INCDIR")

    def _patch_menuselect_runner_permissions(self):
        if self.settings.os != "OHOS":
            return
        makefile = os.path.join(self.source_folder, "Makefile")
        changed = _replace_text(makefile, {
            "ifeq ($(filter %.menuselect,$(MAKECMDGOALS)),)\n"
            "\tmenuselect/menuselect --check-deps $@":
                "ifeq ($(filter %.menuselect,$(MAKECMDGOALS)),)\n"
                "\tchmod 755 menuselect/menuselect\n"
                "\tmenuselect/menuselect --check-deps $@"
        })
        if changed:
            self.output.info("patched Makefile: make menuselect executable before dependency checks")

    def _patch_menuselect_pkg_config_requirement(self):
        configure = os.path.join(self.source_folder, "menuselect", "configure")
        changed = _replace_text(configure, {
            'if test -z "$PKG_CONFIG"; then\n\tas_fn_error $? "pkg-config not found" "$LINENO" 5\nfi':
                'if test -z "$PKG_CONFIG"; then\n'
                '\t{ printf "%s\\n" "$as_me:${as_lineno-$LINENO}: WARNING: pkg-config not found; using explicit dependency flags" >&5\n'
                'printf "%s\\n" "$as_me: WARNING: pkg-config not found; using explicit dependency flags" >&2;}\n'
                '\tPKG_CONFIG=""\n'
                'fi'
        })
        if changed:
            self.output.info("patched menuselect/configure: allow explicit flags without pkg-config")

    def _patch_astmm_libc_ignore(self):
        for subdir, module in ODBC_MODULES:
            path = os.path.join(self.source_folder, subdir, module[:-3] + ".c")
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            if "#define ASTMM_LIBC ASTMM_IGNORE" in content:
                continue
            patched = content.replace(
                '#include "asterisk.h"',
                '#define ASTMM_LIBC ASTMM_IGNORE\n#include "asterisk.h"',
                1,
            )
            if patched == content:
                continue
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(patched)
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
            self.output.info(
                f"patched {os.path.relpath(path, self.source_folder)}: ASTMM_LIBC -> ASTMM_IGNORE"
            )

    def _prepare_source(self):
        self._patch_configure_tmpdir()
        self._patch_blocks_runtime_check()
        self._patch_ohos_recursive_mutex_init()
        self._patch_menuselect_xml2_include()
        self._patch_menuselect_runner_permissions()
        self._patch_menuselect_pkg_config_requirement()
        self._patch_astmm_libc_ignore()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_source()
        env = self._build_env()
        shell_env = f'CONFIG_SHELL="{self._shell_path()}" SHELL="{self._shell_path()}"'
        menuselect_make_vars = self._menuselect_make_vars()
        with env.vars(self, scope="build").apply():
            args = " ".join(f'"{arg}"' for arg in self._configure_args())
            self.run(f"{shell_env} ./configure {args}", cwd=self.source_folder, env="conanbuild")

            menuselect_dir = os.path.join(self.source_folder, "menuselect")
            if os.path.isdir(menuselect_dir):
                margs = " ".join(f'"{arg}"' for arg in self._menuselect_configure_args())
                self.run(f"{shell_env} ./configure {margs}", cwd=menuselect_dir, env="conanbuild")

            menuselect_binary = os.path.join(menuselect_dir, "menuselect")
            self.run(
                f"make -j1 {menuselect_make_vars} menuselect/menuselect",
                cwd=self.source_folder,
                env="conanbuild",
            )
            if not os.path.isfile(menuselect_binary):
                raise ConanInvalidConfiguration(
                    f"expected menuselect tool was not built: {menuselect_binary}"
                )
            self._sign_ohos_executable(menuselect_binary)
            try:
                os.chmod(menuselect_binary, 0o755)
            except OSError:
                pass
            self.run(
                f'chmod 755 "{menuselect_binary}"',
                cwd=self.source_folder,
                env="conanbuild",
            )
            self.run(
                f"make -j1 {menuselect_make_vars} menuselect.makeopts",
                cwd=self.source_folder,
                env="conanbuild",
            )
            modules = " ".join(module[:-3] for _, module in ODBC_MODULES)
            self.run(f"menuselect/menuselect --enable {modules} menuselect.makeopts",
                     cwd=self.source_folder, env="conanbuild")
            self.run(
                f"make -j1 {menuselect_make_vars} include/asterisk/buildopts.h main/version.c "
                "include/asterisk/build.h defaults.h",
                cwd=self.source_folder,
                env="conanbuild",
            )

            for subdir, module in ODBC_MODULES:
                self.run(
                    "make -j1 -C {subdir} SUBDIR={subdir} ASTTOPDIR={topdir} "
                    "ASTCFLAGS=-I{include_dir} SOLINK=-shared {module}".format(
                        subdir=subdir,
                        topdir=self.source_folder,
                        include_dir=os.path.join(self.source_folder, "include"),
                        module=module,
                    ),
                    cwd=self.source_folder,
                    env="conanbuild",
                )

    def _configure_args(self):
        args = []
        if self.settings.os == "OHOS":
            args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        args.extend([
            f"--with-unixodbc={self.dependencies['unixodbc'].package_folder}",
            "--without-iodbc",
            "--without-pjproject",
            "--without-x11",
            "--without-gtk2",
        ])
        return args

    def _menuselect_configure_args(self):
        if self.settings.os == "OHOS":
            return [
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ]
        return []

    def _menuselect_make_vars(self):
        """Override Asterisk's generated build-tool defaults for recursive make."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        if self.settings.os == "OHOS":
            return (
                f'BUILD_CC="{cc}" '
                f'BUILD_LDFLAGS="{self._ohos_linker_flag()}"'
            )
        return f'BUILD_CC="{cc}"'

    @staticmethod
    def _ohos_linker_flag():
        """Use a known device lld instead of the unreliable HNP ``ld`` alias."""
        home = os.environ.get("HOME", "/storage/Users/currentUser")
        candidates = [
            os.environ.get("OHOS_LD"),
            os.path.join(home, "usr", "local", "bin", "ld.lld"),
            "/storage/Users/currentUser/usr/local/bin/ld.lld",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return f"-fuse-ld={candidate}"
        return "-fuse-ld=lld"

    @staticmethod
    def _ohos_toolchain_libdirs():
        """Find device-side host libraries needed by the OHOS LLVM tools."""
        candidates = []
        llvm_root = os.environ.get("OHOS_SDK_LLVM_ROOT")
        if llvm_root:
            candidates.append(os.path.join(llvm_root, "lib"))
        sdk_home = os.environ.get("OHOS_SDK_HOME") or os.environ.get("OHOS_SDK")
        if sdk_home:
            candidates.extend([
                os.path.join(sdk_home, "native", "llvm", "lib"),
                os.path.join(sdk_home, "llvm", "lib"),
            ])
        candidates.extend(sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
        ))
        home = os.environ.get("HOME", "/storage/Users/currentUser")
        candidates.extend([
            os.path.join(home, "usr", "local", "lib"),
            "/storage/Users/currentUser/usr/local/lib",
        ])
        result = []
        for path in candidates:
            if path and os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _sign_ohos_executable(self, path):
        """Sign an ELF helper before executing it on HarmonyOS."""
        if self.settings.os != "OHOS" or not self._is_elf(path):
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "OHOS menuselect requires llvm-objcopy and binary-sign-tool for ELF signing"
            )
        original_mode = os.stat(path).st_mode
        staging = path + ".signing"
        signed = path + ".signed"
        try:
            shutil.copy2(path, staging)
            self.run(f'"{objcopy}" --remove-section .codesign "{staging}"',
                     ignore_errors=True)
            self.run(
                f'"{signer}" sign -inFile "{staging}" '
                f'-outFile "{signed}" -selfSign 1'
            )
            os.chmod(signed, original_mode | 0o111)
            os.replace(signed, path)
        finally:
            for temporary in (staging, signed):
                if os.path.exists(temporary):
                    os.remove(temporary)

    def package(self):
        module_dst = os.path.join(self.package_folder, "lib", "asterisk", "modules")
        copied = []
        for subdir, module in ODBC_MODULES:
            src_dir = os.path.join(self.source_folder, subdir)
            src_file = os.path.join(src_dir, module)
            if not os.path.isfile(src_file):
                raise ConanInvalidConfiguration(f"expected ODBC module was not built: {src_file}")
            copy(self, module, src=src_dir, dst=module_dst)
            copied.append(module)
        self.output.info("packaged ODBC modules: " + ", ".join(copied))
        self._sign_packaged_modules(module_dst)

        sample_src = os.path.join(self.source_folder, "configs", "samples")
        for sample in ODBC_SAMPLES:
            copy(self, sample, src=sample_src, dst=os.path.join(self.package_folder, "res"))

        for license_name in ("LICENSE", "COPYING"):
            copy(self, license_name, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

    def _sign_packaged_modules(self, module_dir):
        if self.settings.os != "OHOS":
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("skip OHOS ELF signing: llvm-objcopy or binary-sign-tool not found")
            return
        for _, module in ODBC_MODULES:
            path = os.path.join(module_dir, module)
            if not self._is_elf(path):
                continue
            original_mode = os.stat(path).st_mode
            staging = path + ".signing"
            signed = path + ".signed"
            try:
                shutil.copy2(path, staging)
                self.run(f'"{objcopy}" --remove-section .codesign "{staging}"',
                         ignore_errors=True)
                self.run(
                    f'"{signer}" sign -inFile "{staging}" '
                    f'-outFile "{signed}" -selfSign 1'
                )
                os.chmod(signed, original_mode | 0o111)
                os.replace(signed, path)
            finally:
                for temporary in (staging, signed):
                    if os.path.exists(temporary):
                        os.remove(temporary)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/asterisk/modules"]
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["res"]
