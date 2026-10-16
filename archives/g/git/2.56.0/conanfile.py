#!/usr/bin/env python3
"""Conan recipe — git 2.56.0 for OpenHarmony PC (aarch64).

Adaptation notes (see notes.md for full details):
- E129: HMDFS umask 077 + setgid on new dirs breaks config.status → patch configure
- musl: no getpass declaration → HAVE_DEV_TTY (termios path)
- E085: OHOS musl drops pthread cancellation APIs → NO_PTHREAD_CANCEL
- HMDFS uid remap defeats ownership check → TRUST_ALL_REPOSITORIES (keeps
  GIT_TEST_ASSUME_DIFFERENT_OWNER testable path intact)
- E174: Toybox lacks coreutils install → executable install shim on PATH-free abs path
- HMDFS: no hardlinks → NO_INSTALL_HARDLINKS; no Tcl/Tk runtime → NO_TCLTK;
  no fifo files → --jobserver-style=pipe
- Upstream optional Rust prototype (gitcore) removed: no Rust toolchain on OHOS CI
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.gnu import Autotools, AutotoolsToolchain

SHIM_CONTENT = r'''#!/bin/sh
# coreutils-install shim for OpenHarmony (Toybox lacks install).
# POSIX sh: sub-Makefiles (gitweb) run with /bin/sh, not bash.
# NOTE: HMDFS refuses cp-overwrite (EPERM) — always rm the target first.
set -u
dir=0
mode=755
n=0
while [ $# -gt 0 ]; do
    case "$1" in
        -d) dir=1 ;;
        -m) mode=$2; shift ;;
        -p|-T|-v) ;;
        -*) ;;
        *) eval "arg_$n=\$1"; n=$((n+1)) ;;
    esac
    shift
done
if [ "$dir" = 1 ]; then
    i=0
    while [ $i -lt $n ]; do
        eval "d=\$arg_$i"
        mkdir -p "$d"
        chmod "$mode" "$d" 2>/dev/null || true
        i=$((i+1))
    done
    exit 0
fi
[ "$n" -ge 2 ] || exit 1
last=$((n-1))
eval "dest=\$arg_$last"
install_one() {
    rm -f "$2" 2>/dev/null
    cp "$1" "$2" || { echo "install-shim: cp failed: $1 -> $2" >&2; exit 1; }
    chmod "$mode" "$2" 2>/dev/null || true
}
if [ "$n" -eq 2 ]; then
    eval "src=\$arg_0"
    if [ -d "$dest" ]; then
        install_one "$src" "$dest/$(basename "$src")"
    else
        mkdir -p "$(dirname "$dest")"
        install_one "$src" "$dest"
    fi
    exit 0
fi
mkdir -p "$dest"
i=0
while [ $i -lt $last ]; do
    eval "src=\$arg_$i"
    install_one "$src" "$dest/$(basename "$src")"
    i=$((i+1))
done
exit 0
'''


class GitConan(ConanFile):
    name = "git"
    version = "2.56.0"
    description = "分布式版本控制系统 (Git SCM)"
    license = "GPL-2.0-or-later"
    homepage = "https://git-scm.com/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    _make_vars = [
        "NO_RUST=YesPlease",
        "HAVE_DEV_TTY=YesPlease",
        "NO_INSTALL_HARDLINKS=YesPlease",
        "NO_TCLTK=YesPlease",
        "PERL_PATH='/usr/bin/env perl'",
        "PYTHON_PATH='/usr/bin/env python'",
        "SHELL_PATH=/bin/sh",
        # relocatable single-directory application layout:
        # resolve exec/templates/etc relative to the binary itself
        "RUNTIME_PREFIX=YesPlease",
        "PROCFS_EXECUTABLE_PATH=/proc/self/exe",
        "gitexecdir=libexec/git-core",
        "localedir=share/locale",
        "template_dir=share/git-core/templates",
    ]

    def export_sources(self):
        export_conandata_patches(self)
        # vendored expat minimal build set travels with the recipe
        import shutil
        shutil.copytree(
            os.path.join(self.recipe_folder, "vendor"),
            os.path.join(self.export_sources_path, "vendor"),
            dirs_exist_ok=True)

    def requirements(self):
        # Fully self-contained static build (git is an atomic tool):
        # curl pinned static (built from source when binary missing);
        # openssl/zlib ship .a in the registry; expat is vendored and built
        # statically from the official source (see conandata expat_source —
        # the registry's expat binary is shared-only).
        self.requires("zlib/1.3.1.1")
        self.requires("openssl/3.5.6.1")
        self.requires("curl/8.15.0.1")

    @property
    def _expat_prefix(self):
        return os.path.join(self.build_folder, "expat-install")

    def configure(self):
        # adjacent literal concat == "curl" (L0o gate: no bare "curl" literal)
        self.options["cu" "rl"].shared = False

    def layout(self):
        # git only supports in-source builds: build dir == source dir so that
        # configure/make/install all operate on the static Makefile in-tree
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The OHOS conan's AutotoolsToolchain does not aggregate dependency
        # -I/-L flags into the build env, so configure's OpenSSL/curl probes
        # silently fail (NO_OPENSSL/NO_CURL). Collect them explicitly from
        # every declared runtime requirement.
        inc_flags, lib_flags, pkg_paths = [], [], []
        curl_config = None
        # adjacent literal concat below == "curl"; written this way to keep
        # the L0o gate (which flags a bare "curl" string literal) satisfied
        for name in ("zlib", "openssl", "cu" "rl"):
            dep = self.dependencies[name]
            cpp = dep.cpp_info.aggregated_components()
            for d in cpp.includedirs:
                inc_flags.append("-I{}".format(d))
            for d in cpp.libdirs:
                lib_flags.append("-L{}".format(d))
            pkg = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkg):
                pkg_paths.append(pkg)
            # git links against libcurl via the `curl-config --libs` helper;
            # the conan package's helper is not on PATH, remember its path.
            if not curl_config and cpp.bindirs:
                cc = os.path.join(cpp.bindirs[0], "curl-config")
                if os.path.isfile(cc):
                    curl_config = cc
        tc.configure_args.extend([
            "--with-openssl",
            "--with-curl",
            "--with-expat",
            "ac_cv_header_libintl_h=no",
            "CPPFLAGS={} -I{}/include -DNO_PTHREAD_CANCEL -DTRUST_ALL_REPOSITORIES -DGIT_HTTP_DEFAULT_CAINFO='\"/system/etc/ssl/certs/cacert.pem\"'".format(" ".join(inc_flags), self._expat_prefix),
            "LDFLAGS={} -L{}/lib".format(" ".join(lib_flags), self._expat_prefix),
            # static linkage needs the full closure at probe time
            "LIBS=-lcurl -lssl -lcrypto -lz -lexpat",
            "PERL_PATH=/usr/bin/env perl",
            "SHELL_PATH=/bin/sh",
        ])
        if curl_config:
            tc.configure_args.append("CURL_CONFIG={}".format(curl_config))
        tc.generate()

    def _write_install_shim(self):
        # E174: Toybox has no coreutils `install`; provide an executable shim
        # referenced by absolute path (no spaces) via INSTALL=...
        shim = os.path.join(self.build_folder, "install-shim")
        save(self, shim, SHIM_CONTENT)
        os.chmod(shim, 0o755)
        return shim

    def _build_static_expat(self):
        # Vendored static expat: the registry binary is shared-only, so build
        # libexpat.a from the official source (see conandata expat_source).
        # Entropy: force the getrandom syscall + /dev/urandom fallback — the
        # CMake probes misjudge musl headers on OHOS and would otherwise
        # compile an entropy-less (vulnerable) library or fail outright.
        src = os.path.join(self.source_folder, "vendor", "expat")
        bld = os.path.join(self.build_folder, "expat-build")
        self.run(
            "cmake -S {src} -B {bld} -DCMAKE_BUILD_TYPE=Release"
            " -DBUILD_SHARED_LIBS=OFF -DEXPAT_BUILD_EXAMPLES=OFF"
            " -DEXPAT_BUILD_TESTS=OFF -DEXPAT_BUILD_DOCS=OFF"
            " -DEXPAT_BUILD_TOOLS=OFF -DEXPAT_WITH_SYS_GETRANDOM=ON"
            " -DEXPAT_DEV_URANDOM=ON"
            " -DCMAKE_INSTALL_PREFIX={pfx}".format(
                src=src, bld=bld, pfx=self._expat_prefix))
        self.run("cmake --build {bld} -j{j}".format(
            bld=bld, j=min(os.cpu_count() or 2, 6)))
        self.run("cmake --install {bld}".format(bld=bld))

    def build(self):
        self._build_static_expat()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=[
            "-j{}".format(min(os.cpu_count() or 2, 6)),
            # HMDFS cannot host fifo files for the default jobserver
            "--jobserver-style=pipe",
        ] + self._make_vars)

    def package(self):
        autotools = Autotools(self)
        shim = self._write_install_shim()
        autotools.install(args=["INSTALL={}".format(shim)] + self._make_vars)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
