#!/usr/bin/env python3
"""Conan recipe — libqalculate 5.11.0 (Autotools).

A multi-purpose desktop calculator library.
Provides arbitrary precision arithmetic, symbolic calculation,
unit conversion, and plotting support.
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibqalculateConan(ConanFile):
    name = "libqalculate"
    version = "5.11.0"
    description = "A multi-purpose desktop calculator library with arbitrary precision"
    license = "GPL-2.0-or-later"
    homepage = "https://qalculate.github.io/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # System dependencies: gmp 6.3.0, mpfr 4.2.1, readline 8.2, libxml2 2.15.3
    # These are not Conan packages — built from source if missing on the worker.

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # System dependencies (gmp, mpfr, readline, libxml2) are pre-installed
        # in ~/usr/local. CPPFLAGS is needed for AC_CHECK_HEADER (gmp.h),
        # CFLAGS/CXXFLAGS for compilation, LDFLAGS for linking.
        sys_prefix = os.path.expanduser("~/usr/local")

        env = Environment()
        env.define("PKG_CONFIG_PATH", f"{sys_prefix}/lib/pkgconfig")
        env.define("LD_LIBRARY_PATH", f"{sys_prefix}/lib")
        env.define("CPPFLAGS", f"-I{sys_prefix}/include")
        env.vars(self).save_script("sysdeps_env")

        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append(f"-I{sys_prefix}/include")
        tc.extra_cxxflags.append(f"-I{sys_prefix}/include")
        tc.extra_ldflags.append(f"-L{sys_prefix}/lib")
        tc.configure_args.append("--without-libcurl")
        tc.configure_args.append("--without-icu")
        tc.configure_args.append(f"CPPFLAGS=-I{sys_prefix}/include")
        tc.generate()

    def _ensure_system_dep(self, name, version, url, header, configure_extra="", fallback_url=None):
        """Build and install a system dependency from source if not present.

        GMP and MPFR are not Conan packages in the ohpcd registry and may not
        be pre-installed on CI workers. This method downloads the upstream
        source tarball, applies minimal HarmonyOS portability fixes (config.guess
        platform detection + umask 077 removal for HMDFS), then builds and
        installs to ~/usr/local.
        """
        sys_prefix = os.path.expanduser("~/usr/local")
        header_path = os.path.join(sys_prefix, "include", header)

        if os.path.exists(header_path):
            self.output.info(f"{name} already installed at {sys_prefix}")
            return

        self.output.info(f"{name} not found, building {name} {version} from source...")

        tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        build_dir = tempfile.mkdtemp(prefix=f"{name}-build-", dir=tmpdir)

        # Download and extract — try multiple sources with fallback
        # Primary URL first, then GitHub mirrors (if fallback_url is set)
        urls_to_try = [url]
        if fallback_url and "github.com" in fallback_url:
            urls_to_try.extend([
                f"https://gh-proxy.com/{fallback_url}",
                f"https://mirror.ghproxy.com/{fallback_url}",
                f"https://ghproxy.com/{fallback_url}",
                fallback_url.replace("https://github.com", "https://kkgithub.com"),
                fallback_url,
            ])
        elif "github.com" in url:
            urls_to_try = [
                f"https://gh-proxy.com/{url}",
                f"https://mirror.ghproxy.com/{url}",
                f"https://ghproxy.com/{url}",
                url.replace("https://github.com", "https://kkgithub.com"),
                url,
            ]

        downloaded = False
        for mirror_url in urls_to_try:
            # Try curl first (better SSL/header support on OHOS),
            # fall back to wget if curl is unavailable
            for cmd in (
                f'curl -fsSL "{mirror_url}" | tar xJ -C "{build_dir}"',
                f'wget -O - "{mirror_url}" | tar xJ -C "{build_dir}"',
            ):
                try:
                    self.run(cmd, env="conanbuild")
                    downloaded = True
                    self.output.info(f"Downloaded {name} from {mirror_url}")
                    break
                except Exception:
                    continue
            if downloaded:
                break
            self.output.info(f"Download failed from {mirror_url}, trying next...")
        if not downloaded:
            raise Exception(f"Failed to download {name} from all sources")

        src_dir = os.path.join(build_dir, f"{name}-{version}")

        # Patch config.guess / configfsf.guess for HarmonyOS platform detection
        for guess_name in ("configfsf.guess", "config.guess"):
            guess_path = os.path.join(src_dir, guess_name)
            if not os.path.exists(guess_path):
                continue
            with open(guess_path, "r") as f:
                content = f.read()
            # Add HarmonyOS to the Linux case pattern
            content = content.replace(
                "Linux|GNU|GNU/*)", "Linux|GNU|GNU/*|HarmonyOS)"
            )
            # Add aarch64:HarmonyOS case before aarch64_be:Linux
            harmonyos_case = (
                "    aarch64:HarmonyOS:*:*)\n"
                "\tGUESS=$UNAME_MACHINE-unknown-linux-gnu\n"
                "\t;;\n"
            )
            if "aarch64:HarmonyOS" not in content:
                content = content.replace(
                    "    aarch64_be:Linux:*:*)",
                    harmonyos_case + "    aarch64_be:Linux:*:*)",
                )
            with open(guess_path, "w") as f:
                f.write(content)
            self.output.info(f"Patched {guess_name} for HarmonyOS")
            break

        # Patch configure: remove umask 077 for HMDFS compatibility
        configure_path = os.path.join(src_dir, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077 && ", "")
            with open(configure_path, "w") as f:
                f.write(content)
            self.output.info("Patched configure: removed umask 077 for HMDFS")

        # Ensure config.h.in exists (some tarballs ship without it)
        config_h_in = os.path.join(src_dir, "config.h.in")
        if not os.path.exists(config_h_in):
            open(config_h_in, "w").close()
            self.output.info("Created empty config.h.in")

        # Configure, build, install (static only to avoid polluting /lib)
        self.run(
            f'cd "{src_dir}" && '
            f"./configure --prefix={sys_prefix} --disable-shared "
            f"--enable-static {configure_extra} && "
            f"make -j2 && make install",
            env="conanbuild",
        )
        self.output.info(f"{name} {version} built and installed to {sys_prefix}")

    def build(self):
        # Ensure GMP and MPFR are available (not Conan packages — built from
        # source if missing on the CI worker).
        self._ensure_system_dep(
            "gmp", "6.3.0",
            "https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz",
            "gmp.h", "ABI=64",
        )
        self._ensure_system_dep(
            "mpfr", "4.2.1",
            "https://ftp.gnu.org/gnu/mpfr/mpfr-4.2.1.tar.xz",
            "mpfr.h",
        )
        self._ensure_system_dep(
            "libxml2", "2.15.3",
            "https://download.gnome.org/sources/libxml2/2.15/libxml2-2.15.3.tar.xz",
            "libxml/libxml.h",
            "--without-python --without-lzma --without-zlib --without-icu",
            fallback_url="https://github.com/GNOME/libxml2/releases/download/v2.15.3/libxml2-2.15.3.tar.xz",
        )

        apply_conandata_patches(self)

        # Fix: patch 0003 doesn't cover all pthread_cancel call sites in
        # util.cc. Wrap remaining unguarded calls with HAVE_PTHREAD_* macros
        # so they compile on platforms lacking these functions (e.g., OHOS).
        util_cc = os.path.join(self.source_folder, "libqalculate", "util.cc")
        if os.path.exists(util_cc):
            with open(util_cc, "r") as f:
                lines = f.readlines()
            new_lines = []
            in_pthread_guard = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#ifdef HAVE_PTHREAD"):
                    in_pthread_guard = True
                if in_pthread_guard and stripped == "#endif":
                    in_pthread_guard = False
                    new_lines.append(line)
                    continue
                if not in_pthread_guard:
                    if "pthread_setcancelstate(" in line and not stripped.startswith("#"):
                        new_lines.append("#ifdef HAVE_PTHREAD_SETCANCELSTATE\n")
                        new_lines.append(line)
                        new_lines.append("#endif\n")
                        continue
                    if "pthread_setcanceltype(" in line and not stripped.startswith("#"):
                        new_lines.append("#ifdef HAVE_PTHREAD_SETCANCELTYPE\n")
                        new_lines.append(line)
                        new_lines.append("#endif\n")
                        continue
                    if "pthread_cancel(" in line and not stripped.startswith("#"):
                        new_lines.append("#ifdef HAVE_PTHREAD_CANCEL\n")
                        new_lines.append(line)
                        new_lines.append("#endif\n")
                        continue
                new_lines.append(line)
            with open(util_cc, "w") as f:
                f.writelines(new_lines)
            self.output.info("Patched util.cc: guarded remaining pthread_cancel calls")

        # Feature detection: check pthread_cancel availability (R8 compliance).
        # Uses Conan build env (not bare shell vars) to compile a test program.
        # If functions are unavailable (e.g., OHOS), generates an empty header
        # so #ifdef HAVE_PTHREAD_* guards resolve to false.
        test_c = (
            '#include <pthread.h>\n'
            'int main(){pthread_cancel(0);'
            'pthread_setcancelstate(0,0);'
            'pthread_setcanceltype(0,0);return 0;}\n'
        )
        test_file = os.path.join(self.source_folder, "_pthread_test.c")
        header_path = os.path.join(self.source_folder, "libqalculate",
                                   "pthread_compat.h")
        with open(test_file, "w") as f:
            f.write(test_c)

        try:
            self.run(f"$CC -c {test_file} -o /dev/null 2>/dev/null",
                     env="conanbuild")
            with open(header_path, "w") as f:
                f.write("#pragma once\n")
                f.write("#define HAVE_PTHREAD_CANCEL 1\n")
                f.write("#define HAVE_PTHREAD_SETCANCELSTATE 1\n")
                f.write("#define HAVE_PTHREAD_SETCANCELTYPE 1\n")
        except Exception:
            with open(header_path, "w") as f:
                f.write("#pragma once\n")
                f.write("/* pthread_cancel not available on this platform */\n")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["qalculate"]
        self.cpp_info.system_libs = ["gmp", "mpfr", "readline", "xml2"]
