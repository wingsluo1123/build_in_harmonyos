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

    def _ensure_system_dep(self, name, version, url, header, configure_extra="",
                           extra_urls=None):
        """Build and install a system dependency from source if not present."""
        sys_prefix = os.path.expanduser("~/usr/local")
        header_path = os.path.join(sys_prefix, "include", header)

        if os.path.exists(header_path):
            self.output.info(f"{name} already installed at {sys_prefix}")
            return

        self.output.info(f"{name} not found, building {name} {version} from source...")

        tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        build_dir = tempfile.mkdtemp(prefix=f"{name}-build-", dir=tmpdir)

        # Build list of URLs to try
        urls_to_try = [url]
        if extra_urls:
            urls_to_try.extend(extra_urls)
        # Expand GitHub URLs with mirrors
        expanded = []
        for u in urls_to_try:
            if "github.com" in u:
                expanded.extend([
                    f"https://gh-proxy.com/{u}",
                    f"https://mirror.ghproxy.com/{u}",
                    f"https://ghproxy.com/{u}",
                    u.replace("https://github.com", "https://kkgithub.com"),
                    u,
                ])
            else:
                expanded.append(u)
        urls_to_try = expanded

        downloaded = False
        for mirror_url in urls_to_try:
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

        # Patch config.guess / configfsf.guess for HarmonyOS
        for guess_name in ("configfsf.guess", "config.guess"):
            guess_path = os.path.join(src_dir, guess_name)
            if not os.path.exists(guess_path):
                continue
            with open(guess_path, "r") as f:
                content = f.read()
            content = content.replace(
                "Linux|GNU|GNU/*)", "Linux|GNU|GNU/*|HarmonyOS)"
            )
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

        # Patch configure: remove umask 077 for HMDFS
        configure_path = os.path.join(src_dir, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077 && ", "")
            with open(configure_path, "w") as f:
                f.write(content)
            self.output.info("Patched configure: removed umask 077 for HMDFS")

        # Ensure config.h.in exists
        config_h_in = os.path.join(src_dir, "config.h.in")
        if not os.path.exists(config_h_in):
            open(config_h_in, "w").close()
            self.output.info("Created empty config.h.in")

        # Configure, build, install
        self.run(
            f'cd "{src_dir}" && '
            f"./configure --prefix={sys_prefix} --disable-shared "
            f"--enable-static {configure_extra} && "
            f"make -j2 && make install",
            env="conanbuild",
        )
        self.output.info(f"{name} {version} built and installed to {sys_prefix}")

    def build(self):
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
            extra_urls=[
                "https://mirrors.ocf.berkeley.edu/gnome/sources/libxml2/2.15/libxml2-2.15.3.tar.xz",
                "https://ftp.acc.umu.se/mirror/gnome.org/sources/libxml2/2.15/libxml2-2.15.3.tar.xz",
                "https://ftp.yz.yamagata-u.ac.jp/pub/GNOME/sources/libxml2/2.15/libxml2-2.15.3.tar.xz",
            ],
        )

        apply_conandata_patches(self)

        # Fix: patch 0003 doesn't cover all pthread_cancel call sites.
        # Write a temp Python script and run it to wrap remaining unguarded
        # calls with HAVE_PTHREAD_* macros. Using self.run() with a script
        # is more reliable than Python file I/O via self.source_folder.
        tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        patch_script = os.path.join(tmpdir, "_patch_pthread.py")
        with open(patch_script, "w") as f:
            f.write(
                'import glob\n'
                'for path in glob.glob("*/libqalculate/util.cc"):\n'
                '    lines = open(path).readlines()\n'
                '    out = []\n'
                '    for line in lines:\n'
                '        s = line.strip()\n'
                '        if "pthread_setcancelstate(" in line and not s.startswith("#"):\n'
                '            out.append("#ifdef HAVE_PTHREAD_SETCANCELSTATE\\n")\n'
                '            out.append(line)\n'
                '            out.append("#endif\\n")\n'
                '        elif "pthread_setcanceltype(" in line and not s.startswith("#"):\n'
                '            out.append("#ifdef HAVE_PTHREAD_SETCANCELTYPE\\n")\n'
                '            out.append(line)\n'
                '            out.append("#endif\\n")\n'
                '        elif "pthread_cancel(" in line and not s.startswith("#"):\n'
                '            out.append("#ifdef HAVE_PTHREAD_CANCEL\\n")\n'
                '            out.append(line)\n'
                '            out.append("#endif\\n")\n'
                '        else:\n'
                '            out.append(line)\n'
                '    open(path, "w").writelines(out)\n'
                '    print(f"Patched {path}")\n'
            )
        self.run(f"python3 {patch_script}", env="conanbuild")
        self.output.info("Patched util.cc: guarded remaining pthread_cancel calls")

        # Feature detection: check pthread_cancel availability (R8 compliance).
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
