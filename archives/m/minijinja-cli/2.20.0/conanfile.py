#!/usr/bin/env python3
"""Conan 2.x recipe — minijinja-cli 2.20.0

A command-line tool for the MiniJinja template engine.
Source: GitHub (mitsuhiko/minijinja)
Build system: cargo (Rust)
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MinijinjaCliConan(ConanFile):
    name = "minijinja-cli"
    version = "2.20.0"
    description = "Command Line Utility to render MiniJinja/Jinja2 templates"
    license = "Apache-2.0"
    homepage = "https://github.com/mitsuhiko/minijinja"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"minijinja-cli supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="minijinja-2.20.0.tar.gz")

    def generate(self):
        # Create .cargo/config.toml with linker and target settings
        cargo_dir = os.path.join(self.build_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        config_path = os.path.join(cargo_dir, "config.toml")
        with open(config_path, "w") as f:
            f.write('[build]\ntarget-dir = "target"\n')
            if str(self.settings.os) == "OHOS":
                f.write(
                    '\n[target.aarch64-unknown-linux-ohos]\n'
                    'linker = "clang"\n'
                )

    def build(self):
        apply_conandata_patches(self)

        # Set writable TMPDIR on OHOS (/tmp is read-only, E002)
        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/minijinja-cli")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        # Ensure Rust toolchain is available (CI workers may not have it)
        if not shutil.which("cargo"):
            self._ensure_rust_toolchain()

        # Ensure cc is available (Rust cc-rs crate requires it as C compiler)
        if not shutil.which("cc"):
            clang = shutil.which("clang")
            if clang:
                local_bin = os.path.expanduser("~/.local/bin")
                os.makedirs(local_bin, exist_ok=True)
                cc_link = os.path.join(local_bin, "cc")
                if not os.path.exists(cc_link):
                    os.symlink(clang, cc_link)
                os.environ["PATH"] = local_bin + ":" + os.environ.get("PATH", "")
            os.environ["CC"] = "clang"
            os.environ["CXX"] = "clang++"

        # Fetch dependencies first (so we can patch before building)
        self.run("cargo fetch", env="conanbuild")

        # Apply OHOS patch to rustyline: TIOCGWINSZ is u64 but ioctl expects c_int
        cargo_home = os.environ.get("CARGO_HOME", os.path.expanduser("~/.cargo"))
        rustyline_paths = glob.glob(
            os.path.join(cargo_home, "registry/src/*/rustyline-14.0.0")
        )
        if rustyline_paths:
            unix_rs = os.path.join(rustyline_paths[0], "src/tty/unix.rs")
            if os.path.isfile(unix_rs):
                # Only patch if not already patched
                with open(unix_rs, "r") as f:
                    content = f.read()
                if "nix::ioctl_read_bad!(win_size" in content:
                    replace_in_file(
                        self,
                        unix_rs,
                        "nix::ioctl_read_bad!(win_size, libc::TIOCGWINSZ, libc::winsize);",
                        (
                            "// Patched for OHOS: TIOCGWINSZ is u64 but ioctl expects c_int\n"
                            "unsafe fn win_size(fd: libc::c_int, data: &mut libc::winsize) -> nix::Result<libc::c_int> {\n"
                            "    let ret = libc::ioctl(fd, libc::TIOCGWINSZ as libc::c_int, data as *mut _ as *mut libc::c_void);\n"
                            "    nix::errno::Errno::result(ret)\n"
                            "}\n"
                        ),
                    )

        # Build release binary
        self.run("cargo build --release -p minijinja-cli", env="conanbuild")

    def _ensure_rust_toolchain(self):
        """Install Rust toolchain via Harmonybrew if cargo is not in PATH."""
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")

        # Check if Harmonybrew Rust is already installed
        if os.path.isfile(os.path.join(brew_bin, "cargo")):
            os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
            return

        # Install Harmonybrew if not present
        if not os.path.isfile(os.path.expanduser("~/.harmonybrew/bin/brew")):
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild",
            )

        # Install Rust via brew
        brew_path = os.path.expanduser("~/.harmonybrew/bin/brew")
        self.run(f'{brew_path} install rust', env="conanbuild")

        # Add to PATH
        os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")

    def package(self):
        # Copy the built binary to bin/
        target_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "minijinja-cli", target_dir,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
