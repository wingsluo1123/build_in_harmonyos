#!/usr/bin/env python3
"""Conan recipe for xkbcomp 1.4.7 (X.Org XKB keymap compiler).

Xvfb/Xorg invoke `xkbcomp` at start-up to compile the keymap described by
xkeyboard-config into a binary .xkm consumed by the server:

    "%s%sxkbcomp" -w 1 "-R%s" -xkm "..." -em1 ... -eml ... "...xkm"

Without it the server aborts during keyboard initialisation, so this package is
a run-time requirement of the whole X11 stack on OHOS.

Upstream configure runs

    PKG_CHECK_MODULES(XKBCOMP, [x11 xkbfile xproto >= 7.0.17])

that is libx11 + libxkbfile + the xproto headers from xorgproto; all three are
resolved from the registry with no vendoring.

The build reuses the CI-verified OHOS autotools pattern from libxkbile/libxcb:
clang as CC/CXX, an explicit CONFIG_SHELL, TMPDIR/TMP/TEMP inside the build
folder, and -j1 make.
"""

import os
import re
import shutil
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XkbcompConan(ConanFile):
    name = "xkbcomp"
    version = "1.4.7.1"
    description = "X.Org XKB keymap compiler (consumed by the X server at start-up)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xkbcomp"
    url = "https://gitlab.freedesktop.org/xorg/app/xkbcomp"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xkbcomp supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # PKG_CHECK_MODULES(XKBCOMP, [x11 xkbfile xproto >= 7.0.17]) — all three
        # are required.  libxkbfile brings libx11 transitively, but libx11 is a
        # direct requirement too because the sources include <X11/Xlib.h> and the
        # header's own directory must be contributed by a direct dependency.
        self.requires(
            "libx11/6.4.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxkbfile/1.1.3",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property("libx11", "pkg_config_name", "x11")
        pkg_config.set_property("libxkbfile", "pkg_config_name", "xkbfile")
        pkg_config.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            environment = tc.environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            environment.define_path("CC", self._compiler_executable("c", "clang"))
            environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            environment.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
            environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            environment.define_path(
                "RANLIB", self._tool_executable("llvm-ranlib", "ranlib")
            )
            environment.define_path(
                "STRIP", self._tool_executable("llvm-strip", "strip")
            )
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            # Satisfy PKG_CHECK_MODULES(XKBCOMP, [x11 xkbfile xproto ...]) from
            # the conan packages directly: a non-empty <PREFIX>_CFLAGS/_LIBS
            # makes the macro skip pkg-config entirely, which keeps the build
            # independent of a system pkg-config database.
            environment.define("XKBCOMP_CFLAGS", self._module_cflags())
            # The pkg-config module is "xkbfile" but the installed library is
            # libxkbfile.so, so the linker flag is -lxkbfile (spelling -lxkb
            # fails with "ld.lld: error: unable to find library -lxkb").
            environment.define("XKBCOMP_LIBS", self._module_libs("-lxkbfile", "-lX11"))
            # OHOS works-check trap (proven on libxrender/libxcursor/libxpm):
            # native mode (--build == --host) makes autoconf RUN the conftest
            # binary, which the OHOS sandbox cannot execute.  Force host to the
            # ohos triplet and keep build distinct so configure enters cross
            # mode, where the works-check only links and passes.  config.sub/
            # config.guess patches (conandata) make both triplets recognizable.
            tc.update_configure_args(
                {
                    "--build": "aarch64-unknown-linux-ohos",
                    "--host": "aarch64-linux-ohos",
                }
            )
            tc.extra_cflags.append("-Qunused-arguments")
            tc.extra_cflags.append("-Wno-error=unused-command-line-argument")
            self._add_dependency_flags(tc)
        if str(self.settings.os) == "OHOS":
            tc.generate(env=environment)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._freshen_generated_files()
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime_shell()
        # Mirror the CI-verified toolchain pattern from libxcb/libxkbfile: the
        # OHOS worker has no writable /tmp and the build uid is absent from
        # /etc/passwd, so clang's temp-file creation fails unless TMPDIR/TMP/TEMP
        # point into the build folder.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        build_env = Environment()
        build_env.define("TMPDIR", tmpdir)
        build_env.define("TMP", tmpdir)
        build_env.define("TEMP", tmpdir)
        build_env.define("TMPPREFIX", os.path.join(tmpdir, "zsh"))
        if str(self.settings.os) == "OHOS":
            self._prepend_ohos_tool_paths()
            build_env.define("CK_FORK", "no")
            shell = self._resolve_shell()
            self._patch_conan_env_scripts(shell)
            build_env.define("CONFIG_SHELL", shell)
            build_env.define("SHELL", shell)
            for variable, tool in {
                "LD": "ld.lld",
                "AR": "llvm-ar",
                "RANLIB": "llvm-ranlib",
                "NM": "llvm-nm",
                "STRIP": "llvm-strip",
            }.items():
                build_env.define(variable, self._resolve_ohos_tool(tool))
            self._add_runtime_library_paths(build_env)

        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), build_env.vars(self).apply():
            autotools.configure()
            autotools.make(args=["-j1"])

    def _freshen_generated_files(self):
        """Make the patched Makefile.in files newer than their inputs.

        The recipe's patches rewrite generated files, so their mtimes end up
        unordered relative to the tarball's original timestamps.  When
        aclocal.m4 is newer than Makefile.in, make tries to regenerate the
        latter and shells out to automake, which the OHOS image does not ship:
          missing[81]: automake-1.16: inaccessible or not found
          make: *** [Makefile:477: .../Makefile.in] Error 1
        Touching only the Makefile.in files satisfies
          $(srcdir)/Makefile.in: $(srcdir)/Makefile.am $(am__configure_deps)
        without going stale against the Makefile produced by autotools.configure().

        Do NOT touch `configure`: doing so makes it newer than the generated
        config.status, which makes make run `config.status --recheck`, and that
        re-run fails in the OHOS sandbox:
          ./config.status[796]: can't create ./confDpgkLA/subs1.awk: Permission denied
          config.status: error: could not setup config files machinery
        """
        stamp = time.time() + 1.0
        for index, relative in enumerate(
            ("Makefile.in", os.path.join("man", "Makefile.in"))
        ):
            for root in (self.source_folder, self.build_folder):
                if not root:
                    continue
                path = os.path.join(root, relative)
                if os.path.exists(path):
                    os.utime(path, (stamp + index, stamp + index))

    def package(self):
        Autotools(self).install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "xkbcomp"))

    def _sign_ohos_elf(self, path):
        """Self-sign the produced ELF (OHOS refuses to execve unsigned ones).

        Same approach as the repo's xeyes/clinfo recipes: strip any pre-existing
        .codesign section first so re-signing stays idempotent, then sign in
        place.  Without this, Xvfb's Popen("xkbcomp") fails with EACCES and the
        server dies with "XKB: Failed to compile keymap".
        """
        if not os.path.isfile(path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to sign OHOS executables"
            )
        if os.path.isfile(objcopy):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
        self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # xkbcomp is a run-time tool invoked by the X server, not a link-time
        # dependency; nothing to expose beyond the executable.  Its .pc file is
        # still shipped by upstream (xkbcomp.pc) and is published for consumers
        # that probe for the tool (meson's dependency('xkbcomp')).
        self.cpp_info.set_property("pkg_config_name", "xkbcomp")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # ------------------------------------------------------------------
    # OHOS autotools plumbing, reused from the CI-verified libxkbile recipe.
    # ------------------------------------------------------------------

    def _ohos_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/system/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _module_cflags(self):
        """All include dirs of the direct dependencies, as -I flags.

        Reads each dependency's declared includedirs rather than assuming
        <prefix>/include: libx11 keeps its headers under include/ and freetype
        (transitively pulled in by libxkbfile) under include/freetype2.
        """
        flags = []
        seen = set()
        for dependency in self.dependencies.host.values():
            for include_dir in (dependency.cpp_info.includedirs or ["include"]):
                path = os.path.join(dependency.package_folder, include_dir)
                if os.path.isdir(path) and path not in seen:
                    seen.add(path)
                    flags.append(f"-I{path}")
        return " ".join(flags)

    def _module_libs(self, *libs):
        flags = [f"-L{path}" for path in self._dependency_dirs("lib")]
        flags.extend(libs)
        return " ".join(flags)

    def _dependency_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            path = os.path.join(dependency.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _resolve_ohos_tool(self, tool):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in ("c", "cpp"):
            compiler_command = compilers.get(compiler)
            if not compiler_command:
                continue
            compiler_path = str(compiler_command).split()[0].strip("\"'")
            candidate = os.path.join(os.path.dirname(compiler_path), tool)
            if os.path.exists(candidate):
                return candidate
        return shutil.which(tool) or tool

    def _resolve_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            shutil.which("sh"),
            "/bin/sh",
            "/system/bin/sh",
        ):
            if not candidate:
                continue
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "sh"

    def _patch_conan_env_scripts(self, shell):
        generators_folder = self.generators_folder
        if not generators_folder or not os.path.isdir(generators_folder):
            return

        bootstrap_paths = self._ohos_tool_paths()
        if not bootstrap_paths:
            return
        bootstrap = ":".join(bootstrap_paths)
        marker = "# xkbcomp OHOS PATH bootstrap"
        for entry in os.listdir(generators_folder):
            if not entry.endswith(".sh") or entry.startswith("deactivate_"):
                continue
            script_path = os.path.join(generators_folder, entry)
            with open(script_path, "r", encoding="utf-8") as handle:
                content = handle.read()

            if marker not in content:
                content = f'{marker}\nexport PATH="{bootstrap}:${{PATH}}"\n' + content
            if shell:
                content = re.sub(
                    r'^export SHELL="[^"]*"$',
                    f'export SHELL="{shell}"',
                    content,
                    flags=re.MULTILINE,
                )
                content = re.sub(
                    r'^export CONFIG_SHELL="[^"]*"$',
                    f'export CONFIG_SHELL="{shell}"',
                    content,
                    flags=re.MULTILINE,
                )
            content = self._patch_missing_compiler_exports(content)

            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _patch_missing_compiler_exports(self, content):
        for variable, replacement in {
            "CC": self._fallback_compiler("c", "clang"),
            "CXX": self._fallback_compiler("cpp", "clang++"),
        }.items():
            if replacement:
                content = re.sub(
                    rf'^export {variable}="[^"]*"$',
                    f'export {variable}="{replacement}"',
                    content,
                    flags=re.MULTILINE,
                )
        return content

    def _fallback_compiler(self, compiler_key, fallback_name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compilers.get(compiler_key)
        if configured:
            configured_path = str(configured).split()[0].strip("\"'")
            if os.path.exists(configured_path) and os.access(configured_path, os.X_OK):
                return None
        fallback = shutil.which(fallback_name)
        if fallback and os.path.exists(fallback) and os.access(fallback, os.X_OK):
            return fallback
        return None

    def _add_runtime_library_paths(self, build_env):
        for dependency in self.dependencies.host.values():
            lib_dir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(lib_dir):
                build_env.prepend_path("LD_LIBRARY_PATH", lib_dir)

    def _add_dependency_flags(self, toolchain):
        for dependency in self.dependencies.host.values():
            include_dir = os.path.join(dependency.package_folder, "include")
            lib_dir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(include_dir):
                toolchain.extra_cflags.append(f"-I{include_dir}")
            if os.path.isdir(lib_dir):
                toolchain.extra_ldflags.append(f"-L{lib_dir}")

    def _prepend_ohos_tool_paths(self):
        tool_paths = self._ohos_tool_paths()
        existing = os.environ.get("PATH", "")
        for path in reversed(tool_paths):
            if os.path.isdir(path):
                if path not in existing.split(os.pathsep):
                    existing = path + (os.pathsep + existing if existing else "")
        os.environ["PATH"] = existing

    def _ohos_tool_paths(self):
        return [
            path
            for path in (
                "/data/service/hnp/bin",
                os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
                "/bin",
                "/usr/bin",
            )
            if os.path.isdir(path)
        ]

    def _patch_configure_runtime_shell(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        replace_in_file(
            self,
            configure_path,
            "umask 077",
            "umask 022",
            strict=False,
        )
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(
                self,
                configure_path,
                pattern,
                f"#!{shell}",
                strict=False,
            )
