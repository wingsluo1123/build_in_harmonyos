#!/usr/bin/env python3
"""Conan recipe — Crypt::OpenSSL::RSA Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module with C extension code that links against OpenSSL
libssl and libcrypto. The .so is loaded by Perl's XSLoader/DynaLoader at runtime.

Adaptations for OHOS:
- OPENSSL_PREFIX set to system OpenSSL installation path
- R32: settings.os check uses `in ("Linux", "OHOS")`
- R26: Not applicable (Perl XS .so is not a system same-name library)
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlcryptopensslrsaConan(ConanFile):
    name = "perl-crypt-openssl-rsa"
    version = "0.37"
    description = "RSA encoding and decoding using the openSSL libraries (Perl XS module)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/Crypt-OpenSSL-RSA"
    url = ""  # CI fills this

    # Custom files from recipe folder needed at build/package time
    exports = ["rsa_helper.c", "RSA_wrapper.pm"]

    # XS module compiles C code — needs compiler/build_type
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # OpenSSL (libssl, libcrypto) is a system-level dependency, not a Conan package
        # The Makefile.PL finds it via OPENSSL_PREFIX or Crypt::OpenSSL::Guess
        # Perl module dependencies (Crypt::OpenSSL::Random, Crypt::OpenSSL::Bignum)
        # are also system-level Perl modules, not Conan packages
        pass

    def source(self):
        # Ensure Python's ssl module can find libssl for HTTPS downloads
        _home = os.path.expanduser("~")
        _ld = os.environ.get("LD_LIBRARY_PATH", "")
        for _d in ["/usr/lib", f"{_home}/usr/local/lib"]:
            if os.path.isdir(_d) and _d not in _ld.split(":"):
                _ld = f"{_d}:{_ld}"
        os.environ["LD_LIBRARY_PATH"] = _ld
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_openssl_prefix(self):
        """Resolve OpenSSL installation prefix without hardcoding user paths.

        Tries in order:
        1. pkg-config --variable=prefix openssl
        2. Derive from openssl binary location in PATH
        3. Common system paths /usr, /usr/local
        4. Raises ConanException if nothing found
        """
        import shutil
        import subprocess

        # 1. Try pkg-config
        try:
            result = subprocess.run(
                ["pkg-config", "--variable=prefix", "openssl"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                prefix = result.stdout.strip()
                if os.path.isfile(os.path.join(prefix, "include", "openssl", "ssl.h")):
                    return prefix
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # 2. Derive from openssl binary location in PATH
        openssl_bin = shutil.which("openssl")
        if openssl_bin:
            # e.g. /usr/local/bin/openssl -> /usr/local
            prefix = os.path.dirname(os.path.dirname(openssl_bin))
            if os.path.isfile(os.path.join(prefix, "include", "openssl", "ssl.h")):
                return prefix

        # 3. Try common system paths (including user-installed via cmd-pkgs)
        _home = os.path.expanduser("~")
        for candidate in (os.path.join(_home, "usr", "local"), "/usr", "/usr/local"):
            if os.path.isfile(os.path.join(candidate, "include", "openssl", "ssl.h")):
                return candidate

        raise ConanException(
            "Cannot find OpenSSL prefix. Please set OPENSSL_PREFIX environment variable "
            "to the OpenSSL installation directory (e.g. /usr/local)."
        )

    def _resolve_perl_extra_libs(self):
        """Resolve extra Perl library paths where prerequisite modules
        (Crypt::OpenSSL::Guess, Crypt::OpenSSL::Random) are installed.

        On OHOS, Perl's @INC only includes system paths under /data/service/hnp.
        User-installed Perl modules go to $PREFIX/lib/perl5/ which is not in @INC.
        We derive the prefix from the perl binary location and check for the
        required module (Crypt::OpenSSL::Guess) to confirm the path is correct.
        """
        import shutil

        perl_bin = shutil.which("perl")
        if not perl_bin:
            return []

        # Derive prefix from perl binary: /usr/local/bin/perl -> /usr/local
        prefix = os.path.dirname(os.path.dirname(perl_bin))
        perl_lib_base = os.path.join(prefix, "lib", "perl5")

        extra_paths = []
        # Pure-Perl module path (e.g. Crypt::OpenSSL::Guess)
        if os.path.isfile(os.path.join(perl_lib_base, "Crypt", "OpenSSL", "Guess.pm")):
            extra_paths.append(perl_lib_base)

        # Architecture-specific path (e.g. Crypt::OpenSSL::Random .so)
        arch_dir = os.path.join(perl_lib_base, "aarch64-linux")
        if os.path.isdir(arch_dir):
            extra_paths.append(arch_dir)

        # Site-specific path
        import subprocess
        try:
            result = subprocess.run(
                ["perl", "-V:version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                # Parse version='5.42.0' from output
                ver_line = result.stdout.strip()
                ver = ver_line.split("='")[1].rstrip("'") if "='" in ver_line else ""
                if ver:
                    site_path = os.path.join(prefix, "lib", "site_perl", ver, "aarch64-linux")
                    if os.path.isdir(site_path):
                        extra_paths.append(site_path)
        except (subprocess.SubprocessError, IndexError, FileNotFoundError):
            pass

        return extra_paths

    def generate(self):
        # Ensure system tools (perl, clang, curl, etc.) are in PATH
        _home = os.path.expanduser("~")
        _path = os.environ.get("PATH", "")
        for _d in ["/data/service/hnp/bin", f"{_home}/usr/local/bin", "/usr/bin", "/bin"]:
            if os.path.isdir(_d) and _d not in _path.split(":"):
                _path = f"{_d}:{_path}"
        os.environ["PATH"] = _path

        # Set OPENSSL_PREFIX so Makefile.PL can find OpenSSL headers and libs
        # On CI workers, OpenSSL may not be installed yet — build() will handle it
        try:
            openssl_prefix = os.environ.get("OPENSSL_PREFIX") or self._resolve_openssl_prefix()
        except ConanException:
            openssl_prefix = os.environ.get("OPENSSL_PREFIX", "")
        if openssl_prefix:
            os.environ["OPENSSL_PREFIX"] = openssl_prefix
            self.buildenv_info.define("OPENSSL_PREFIX", openssl_prefix)
            self.buildenv_info.append_path("LD_LIBRARY_PATH", os.path.join(openssl_prefix, "lib"))

        # Set PERL5LIB to include paths where prerequisite Perl modules are installed
        perl_extra = self._resolve_perl_extra_libs()
        for p in perl_extra:
            os.environ["PERL5LIB"] = p if not os.environ.get("PERL5LIB") else os.environ["PERL5LIB"] + ":" + p
            self.buildenv_info.append_path("PERL5LIB", p)

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Resolve OpenSSL prefix (may auto-install via cmd-pkgs if headers missing)
        try:
            openssl_prefix = os.environ.get("OPENSSL_PREFIX") or self._resolve_openssl_prefix()
        except ConanException:
            openssl_prefix = ""
        if not openssl_prefix or not os.path.isfile(os.path.join(openssl_prefix, "include", "openssl", "ssl.h")):
            self.output.info("OpenSSL headers not found, installing via cmd-pkgs...")
            _home = os.path.expanduser("~")
            _tmp = os.path.join(_home, "tmp")
            os.makedirs(_tmp, exist_ok=True)
            _script = os.path.join(_tmp, "cmd-pkgs-install.sh")
            self.run(f'curl -fsSL -o "{_script}" '
                     'https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh')
            self.run(f'sh "{_script}" openssl 3.5.6')
            openssl_prefix = self._resolve_openssl_prefix()
        os.environ["OPENSSL_PREFIX"] = openssl_prefix

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        # Pass INC/LIBS explicitly so Makefile.PL doesn't need Crypt::OpenSSL::Guess
        inc = f"-I{openssl_prefix}/include"
        libs = f"-L{openssl_prefix}/lib -lssl -lcrypto"
        self.run(f'perl Makefile.PL INC="{inc}" LIBS="{libs}"', cwd=self.source_folder)

        # Step 2: Build XS module (for non-OHOS platforms where dlopen works)
        self.run("make -j1", cwd=self.source_folder)

        # Step 3: Build rsa_helper (SELinux workaround for OHOS)
        # On OHOS, dlopen() is blocked by SELinux; this C helper links
        # libssl/libcrypto at startup (bypassing dlopen) and provides
        # RSA operations via CLI for the Perl wrapper module.
        rsa_helper_src = os.path.join(self.recipe_folder, "rsa_helper.c")
        self.run(f"clang -o rsa_helper \"{rsa_helper_src}\""
                 f" -I{openssl_prefix}/include"
                 f" -L{openssl_prefix}/lib -lssl -lcrypto"
                 f" -DOPENSSL_API_COMPAT=0x30000000L"
                 f" -Wno-deprecated-declarations",
                 cwd=self.source_folder)

    def package(self):
        # Copy built artifacts from blib to package folder in standard layout
        # .so goes to lib/auto/Crypt/OpenSSL/RSA/ (Perl auto path)
        # .pm goes to lib/Crypt/OpenSSL/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        # Original XS module (for non-OHOS platforms)
        copy(self, "RSA.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "RSA"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "RSA"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "Crypt", "OpenSSL", "RSA"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Crypt", "OpenSSL", "RSA"))
        copy(self, "RSA.pm",
             src=os.path.join(blib_lib, "Crypt", "OpenSSL"),
             dst=os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL"))

        # SELinux workaround: C helper binary + wrapper Perl module (for OHOS)
        copy(self, "rsa_helper",
             src=src,
             dst=os.path.join(self.package_folder, "bin"))
        # Wrapper RSA.pm replaces the XS .pm on OHOS (falls back to XS if dlopen works)
        copy(self, "RSA_wrapper.pm",
             src=self.recipe_folder,
             dst=os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL"))
        # Rename RSA_wrapper.pm to RSA.pm in a separate step
        import shutil
        wrapper_dst = os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL", "RSA_wrapper.pm")
        final_dst = os.path.join(self.package_folder, "lib", "Crypt", "OpenSSL", "RSA.pm")
        if os.path.isfile(wrapper_dst):
            os.replace(wrapper_dst, final_dst)

    def package_info(self):
        # The shared library is RSA.so (Perl XS extension)
        self.cpp_info.libs = ["RSA"]
        self.cpp_info.libdirs = ["lib/auto/Crypt/OpenSSL/RSA"]
        self.cpp_info.includedirs = []
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
        # rsa_helper binary (SELinux workaround for OHOS)
        self.cpp_info.bindirs = ["bin"]
        # Explicitly set RSA_HELPER so the Perl wrapper can find the binary
        # without relying on -x checks (OHOS SELinux may not set execute bit)
        rsa_helper_path = os.path.join(self.package_folder, "bin", "rsa_helper")
        self.runenv_info.define("RSA_HELPER", rsa_helper_path)
        self.buildenv_info.define("RSA_HELPER", rsa_helper_path)
