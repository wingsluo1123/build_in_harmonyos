#!/usr/bin/env python3
"""Conan recipe — chezscheme 10.4.1 for HarmonyOS PC (aarch64).

Chez Scheme is a self-bootstrapping Scheme compiler/interpreter.
It uses a custom build system (zuo), not standard autotools.
Build uses --pbarch (portable bytecode petit bootstrap) to avoid
platform-specific assembly, producing a tpb64l (threaded pb 64-bit LE)
binary that runs on unknown OS (including OHOS).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment


class ChezschemeConan(ConanFile):
    name = "chezscheme"
    version = "10.4.1"
    description = "Chez Scheme is a compiler and runtime for the Scheme programming language"
    license = "Apache-2.0"
    homepage = "https://github.com/cisco/ChezScheme"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No external dependencies (bundles zlib, lz4, zuo, nanopass, stex)

    def layout(self):
        # Simple layout: source folder = build folder = root
        # Avoids basic_layout()'s "src" subfolder which causes path issues
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan"
        self.folders.build_folder_vars = []

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: compiler/flags come from Conan Environment, not bare env vars
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("CFLAGS", "-fPIC -O2 -DDISABLE_CURSES -DDISABLE_X11 -DDISABLE_ICONV")
        env.define("LDFLAGS", "-fPIC")
        env.define("CPPFLAGS", "")  # Avoid system config.h shadowing Chez Scheme's config.h
        env.define("AR", "llvm-ar")
        env.define("RANLIB", "llvm-ranlib")
        env.vars(self, scope="build").save_script("chezscheme_build_env")
        env.vars(self, scope="run").save_script("chezscheme_run_env")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Fallback: ensure HMDFS patch applied (ln -f/ln -s → cp)
        from conan.tools.files import replace_in_file
        install_zuo = os.path.join(src, "makefiles", "install.zuo")
        if os.path.exists(install_zuo):
            try:
                replace_in_file(self, install_zuo,
                    '(shell/wait* "ln" "-f" from to)',
                    '(shell/wait* "cp" from to)')
            except Exception:
                pass
            try:
                replace_in_file(self, install_zuo,
                    '(shell/wait* "ln" "-s" from to)',
                    '(shell/wait* "cp" from to)')
            except Exception:
                pass
            # Fix ln-s/rel: use absolute path instead of relative
            try:
                replace_in_file(self, install_zuo,
                    '(find-relative-path to-dir from)',
                    'from')
            except Exception:
                pass
        # Chez Scheme custom configure: --pbarch for portable bytecode
        self.run(
            f'./configure --pbarch --disable-curses --disable-x11 --disable-iconv --as-is '
            f'--installprefix={self.package_folder}',
            cwd=src,
            env="conanbuild",
        )
        self.run("make -j4", cwd=src, env="conanbuild")

    def package(self):
        src = self.source_folder
        self.run("make install", cwd=src, env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
