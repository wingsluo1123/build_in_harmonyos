#!/usr/bin/env python3
"""Conan recipe — mdfried 0.22.4 (Rust/cargo project).

mdfried is a markdown viewer for the terminal that renders images and big headers.
Built with cargo. chafa is an optional feature (chafa-dyn) — not enabled by default
because OHOS musl dynamic linker does not search LD_LIBRARY_PATH for transitive
dependencies (libchafa.so → libglib-2.0.so loading fails).

Adaptations for OpenHarmony:
- rust-toolchain.toml channel line commented out via conandata patch
  (system has rustc 1.96.1, project requests 1.92.0)
- Build with --no-default-features to avoid chafa dynamic linking issues on musl
- cargo configured to use rsproxy.cn mirror (SSL issues with crates.io on OHOS)
- chafa/glib/pcre2/libintl are optional system packages (R18), only needed if
  building with chafa-dyn or chafa-static features
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

try:
    from conan.tools.env import Environment
except ImportError:
    Environment = None


class MdfriedConan(ConanFile):
    name = "mdfried"
    version = "0.22.4"
    description = "A markdown viewer for the terminal that renders images and big headers"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/benjajaja/mdfried"
    url = ""  # CI fills this

    # R32: settings.os must use in ("Linux", "OHOS"), not == "Linux"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    # ------------------------------------------------------------------
    # System dependencies (R18/R21)
    # ------------------------------------------------------------------
    # chafa, glib, pcre2, libintl are pre-installed musl-compatible system
    # libraries — NOT conan packages. They are installed via cmd-pkgs and
    # Alpine Linux musl packages at $HOME/usr/local/lib/.
    # Using system_requirements() instead of self.requires() avoids conan
    # remote lookup failures (chafa/1.18.2@ohpcd/stable is not published).
    # ------------------------------------------------------------------

    def system_requirements(self):
        """Declare system-level dependencies (R18/R21).

        Pre-installed musl-compatible system libraries (NOT conan packages):
        - chafa 1.18.2: pre-compiled system package (via cmd-pkgs)
        - glib 2.78.6, pcre2 10.42, libintl 0.22.3: Alpine Linux musl packages
          (transitive runtime deps of chafa)

        CI environment must have these pre-installed at $HOME/usr/local/lib/.
        Install chafa via:
          curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- chafa 1.18.2
        Install glib/pcre2/libintl from Alpine Linux musl packages.
        """
        # Non-blocking check: warn if chafa pkg-config file is missing
        home = os.path.expanduser("~")
        chafa_pc = os.path.join(home, "usr", "local", "lib", "pkgconfig", "chafa.pc")
        if not os.path.exists(chafa_pc):
            self.output.warning(
                "chafa.pc not found at %s. Ensure chafa and its transitive "
                "deps (glib, pcre2, libintl) are pre-installed." % chafa_pc
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        """Generate environment for cargo build using Conan's Environment class (R21).

        Uses dynamic paths (os.path.expanduser) instead of hardcoded absolute paths.
        System libraries are expected at $HOME/usr/local/lib/.
        """
        # Build dynamic paths — no hardcoding (R21)
        home = os.path.expanduser("~")
        sys_lib_dir = os.path.join(home, "usr", "local", "lib")
        sys_pkgconfig_dir = os.path.join(sys_lib_dir, "pkgconfig")

        if Environment is not None:
            # Use Conan 2 Environment class — no direct os.environ modification (R21)
            # Note: use a unique script name to avoid collision with Conan's
            # aggregated "conanbuild.sh" which sources all sub-scripts.
            env = Environment()

            # PKG_CONFIG_PATH for chafa and glib
            existing_pkgconfig = os.environ.get("PKG_CONFIG_PATH", "")
            if existing_pkgconfig:
                pkg_config_value = f"{sys_pkgconfig_dir}:{existing_pkgconfig}"
            else:
                pkg_config_value = sys_pkgconfig_dir
            env.define_path("PKG_CONFIG_PATH", pkg_config_value)

            # LD_LIBRARY_PATH for runtime library resolution
            existing_ld = os.environ.get("LD_LIBRARY_PATH", "")
            if existing_ld:
                ld_lib_value = f"{sys_lib_dir}:{existing_ld}"
            else:
                ld_lib_value = sys_lib_dir
            env.define_path("LD_LIBRARY_PATH", ld_lib_value)

            # Proxy for cargo/crates.io access (OHOS SSL workaround)
            env.define("HTTPS_PROXY", "http://127.0.0.1:7890")
            env.define("HTTP_PROXY", "http://127.0.0.1:7890")

            # TMPDIR for cargo temp files (R10: use $HOME/tmp)
            env.define_path("TMPDIR", os.path.join(home, "tmp"))

            # Save with unique name — aggregated conanbuild.sh will source this
            envvars = env.vars(self)
            envvars.save_script("mdfried_buildenv")
        else:
            # Fallback for older conan versions
            self.output.warning(
                "conan.tools.env.Environment not available, using os.environ fallback"
            )
            os.environ["PKG_CONFIG_PATH"] = (
                f"{sys_pkgconfig_dir}:{os.environ.get('PKG_CONFIG_PATH', '')}"
            )
            os.environ["LD_LIBRARY_PATH"] = (
                f"{sys_lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
            )

    def build(self):
        # Apply patches declared in conandata.yml (R3)
        # Patch 0001-rust-toolchain.toml.patch comments out channel = "1.92.0"
        # because system has rustc 1.96.1
        apply_conandata_patches(self)

        home = os.path.expanduser("~")

        # Configure cargo mirror — OHOS SSL issues with crates.io (R21)
        cargo_config_dir = os.path.join(home, ".cargo")
        cargo_config = os.path.join(cargo_config_dir, "config.toml")
        os.makedirs(cargo_config_dir, exist_ok=True)

        cargo_mirror_config = (
            '[source.crates-io]\n'
            'replace-with = "rsproxy-sparse"\n'
            '\n'
            '[source.rsproxy-sparse]\n'
            'url = "sparse+https://rsproxy.cn/index/"\n'
            '\n'
            '[source.rsproxy]\n'
            'registry = "https://rsproxy.cn/crates.io-index"\n'
            '\n'
            '[registries.rsproxy]\n'
            'index = "https://rsproxy.cn/crates.io-index"\n'
            '\n'
            '[net]\n'
            'git-fetch-with-cli = true\n'
        )

        # Write cargo mirror config if not already present
        need_write = True
        if os.path.exists(cargo_config):
            with open(cargo_config, "r") as f:
                existing = f.read()
            if "rsproxy" in existing:
                need_write = False
        if need_write:
            with open(cargo_config, "w") as f:
                f.write(cargo_mirror_config)
            self.output.info("Cargo mirror configured (rsproxy.cn)")

        # Ensure TMPDIR directory exists (R10: temp files in $HOME/tmp)
        # TMPDIR, HTTPS_PROXY, HTTP_PROXY are set via generate() Environment
        # class and applied by self.run(..., env="conanbuild") (R21)
        tmpdir = os.path.join(home, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # Build with cargo --no-default-features
        # Reason: musl dynamic linker does not search LD_LIBRARY_PATH for
        # transitive dependencies. chafa-dyn feature requires libchafa.so →
        # libglib-2.0.so chain, which fails on OHOS musl. --no-default-features
        # skips chafa, producing a binary that only needs system libc.
        # chafa is optional — mdfried falls back to other rendering methods.
        # env="conanbuild" loads the Environment script from generate()
        self.run("cargo build --release --no-default-features", env="conanbuild")

    def package(self):
        # Copy the binary to the package
        # Note: cargo builds in source_folder, not build_folder
        copy(self, "mdfried", src=os.path.join(self.source_folder, "target", "release"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # mdfried is a command-line executable, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # Conan 2: VirtualRunEnv uses runenv_info to set PATH at runtime
        # Without this, test_package can't find mdfried in PATH
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
