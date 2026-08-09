#!/usr/bin/env python3
"""Conan recipe for gphoto2 2.5.32 — OHOS (OpenHarmony) aarch64 adaptation.

Build system: autotools (release tarball includes configure).
Portability patches: config.guess/config.sub for OHOS detection (E007),
main.c pthread_cancel replacement for musl/OHOS (E099).

Dependencies:
  - libgphoto2/2.5.31 (core camera access library)
  - libexif/0.6.26    (EXIF metadata support)
  - popt/1.16         (command-line option parsing)

OHOS adaptations:
  - pthread_cancel unavailable on musl/OHOS → flag-based cancellation (#ifdef __OHOS__)
  - config.guess/config.sub updated for OHOS platform detection
  - configure temp directory patched for HMDFS compatibility (E002)
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class Gphoto2Conan(ConanFile):
    name = "gphoto2"
    version = "2.5.32"
    description = "Command-line utility for accessing digital cameras via libgphoto2"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/gphoto/gphoto2"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gphoto2 is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libgphoto2/2.5.31")
        self.requires("libexif/0.6.26")
        self.requires("popt/1.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        cached_src = "/storage/Users/currentUser/tmp/gphoto2-2.5.32.tar.bz2"
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as e:
            self.output.warn(f"Download failed: {e}. Using cached source.")
            from conan.tools.files import unzip
            unzip(self, cached_src, self.source_folder, strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        # Ensure configure conftest programs can find shared libs at runtime
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
                # Set PKG_CONFIG_PATH for dependencies with .pc files
                pkgdir = os.path.join(libdir, "pkgconfig")
                if os.path.isdir(pkgdir):
                    env.prepend_path("PKG_CONFIG_PATH", pkgdir)
            # Also check builddirs for pkgconfig
            for bindir in dep.cpp_info.bindirs:
                pkgdir = os.path.join(os.path.dirname(bindir), "lib", "pkgconfig")
                if os.path.isdir(pkgdir):
                    env.prepend_path("PKG_CONFIG_PATH", pkgdir)
        # Set TMPDIR and AWK for config.status to avoid HMDFS exec issues
        env.define("TMPDIR", "/data/storage/el2/base/cache")
        env.define("AWK", "gawk")
        # Set LIBGPHOTO2_CFLAGS and LIBGPHOTO2_LIBS to bypass pkg-config .la path issues
        for dep in self.dependencies.values():
            if dep.ref.name == "libgphoto2":
                inc_flags = " ".join(f"-I{d}" for d in dep.cpp_info.includedirs)
                lib_flags = " ".join(f"-L{d}" for d in dep.cpp_info.libdirs)
                lib_names = " ".join(f"-l{l}" for l in dep.cpp_info.libs)
                env.define("LIBGPHOTO2_CFLAGS", inc_flags)
                env.define("LIBGPHOTO2_LIBS", f"{lib_flags} {lib_names}")
                self.output.info(f"Set LIBGPHOTO2_CFLAGS={inc_flags}")
                self.output.info(f"Set LIBGPHOTO2_LIBS={lib_flags} {lib_names}")
        env.vars(self, scope="build").save_script("conanbuild_env")

    def build(self):
        import shutil
        autotools = Autotools(self)
        src = self.source_folder
        # Remove .la files from dependencies (they have wrong paths from --prefix=/)
        # Without .la files, libtool falls back to direct -l linking which works with -L paths
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isdir(libdir):
                    continue
                for la_file in os.listdir(libdir):
                    if la_file.endswith(".la"):
                        la_path = os.path.join(libdir, la_file)
                        try:
                            os.remove(la_path)
                            self.output.info(f"Removed .la file: {la_file} from {dep.ref.name}")
                        except Exception:
                            pass
        ohos_config_guess = "/storage/Users/currentUser/.conan2/p/b/libgpfc36ae7e387d9/b/auto-aux/config.guess"
        ohos_config_sub = "/storage/Users/currentUser/.conan2/p/b/libgpfc36ae7e387d9/b/auto-aux/config.sub"
        target_aux = os.path.join(src, "auto-aux")
        os.makedirs(target_aux, exist_ok=True)
        if os.path.exists(ohos_config_guess):
            shutil.copy2(ohos_config_guess, os.path.join(target_aux, "config.guess"))
            self.output.info("Copied OHOS-aware config.guess from libgphoto2 cache")
        if os.path.exists(ohos_config_sub):
            shutil.copy2(ohos_config_sub, os.path.join(target_aux, "config.sub"))
            self.output.info("Copied OHOS-aware config.sub from libgphoto2 cache")
        # Apply the main.c patch (pthread_cancel fix) using git apply
        for p in self.conan_data.get("patches", []):
            if "main.c" in p.get("patch_file", ""):
                patch_file = os.path.join(src, p["patch_file"])
                self.run(f'cd "{src}" && git apply "{patch_file}"')
                self.output.info(f"Applied patch: {p['patch_file']}")
        # Patch configure to use writable temp directory for config.status (E002)
        configure = os.path.join(src, "configure")
        if os.path.isfile(configure):
            with open(configure, "r") as f:
                content = f.read()
            content = content.replace(
                'mktemp -d "./confXXXXXX"',
                'mktemp -d "/data/storage/el2/base/cache/confXXXXXX"'
            )
            content = content.replace(
                'tmp=./conf$$-$RANDOM',
                'tmp=/data/storage/el2/base/cache/conf$$-$RANDOM'
            )
            with open(configure, "w") as f:
                f.write(content)
            self.output.info("Patched configure for HMDFS temp directory (E002)")
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone binary, no C++/library info
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _apply_patch(self, src, patch_file):
        """Apply a diff -ruN patch. Handles file creation and modification."""
        with open(patch_file, "r") as f:
            content = f.read()
        # Parse diff -ruN format
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("--- "):
                old_file = line[4:].split("\t")[0].strip()
                i += 1
                if i < len(lines) and lines[i].startswith("+++ "):
                    new_file = lines[i][4:].split("\t")[0].strip()
                    i += 1
                    # Strip a/ or b/ prefix
                    if old_file.startswith("a/"):
                        old_file = old_file[2:]
                    if new_file.startswith("b/"):
                        new_file = new_file[2:]
                    # Find the hunk
                    if i < len(lines) and lines[i].startswith("@@"):
                        # Parse hunk header
                        hunk_info = lines[i][3:].split(" ")
                        old_start = int(hunk_info[0].split(",")[0])
                        old_count = int(hunk_info[0].split(",")[1]) if "," in hunk_info[0] else 1
                        new_count = int(hunk_info[1].split(",")[1]) if "," in hunk_info[1] else 1
                        i += 1
                        # Collect new file lines (lines starting with +)
                        new_lines = []
                        for j in range(i, min(i + old_count + new_count + 10, len(lines))):
                            if j >= len(lines):
                                break
                            hline = lines[j]
                            if hline.startswith("@@"):
                                break
                            if hline.startswith("+"):
                                new_lines.append(hline[1:])
                            elif hline.startswith(" "):
                                new_lines.append(hline[1:])
                            elif hline.startswith("-"):
                                pass  # Skip removed lines
                            else:
                                break
                        i = j
                        # Write the new file
                        target = os.path.join(src, new_file)
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        # Write the new file with execute permission for scripts
                        if new_file.endswith(("config.guess", "config.sub")):
                            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
                            with os.fdopen(fd, "w") as wf:
                                wf.write("\n".join(new_lines))
                        else:
                            with open(target, "w") as wf:
                                wf.write("\n".join(new_lines))
                        self.output.info(f"  Created/modified: {new_file}")
            else:
                i += 1
