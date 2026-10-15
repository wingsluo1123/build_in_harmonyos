import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class TlsrptConan(ConanFile):
    name = "tlsrpt"
    version = "0.5.0"
    description = "Low-level C library for TLS reporting (RFC 8460)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/sys4/libtlsrpt"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conanfile.py", "patches/*"

    def validate(self):
        if str(self.settings.os) not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration("tlsrpt requires POSIX Unix-domain datagram sockets")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or shutil.which("clang") or "cc"
        shell = next((path for path in (
            os.environ.get("CONFIG_SHELL"), shutil.which("bash"), "/bin/sh"
        ) if path and os.path.isfile(path) and os.access(path, os.X_OK)), "/bin/sh")
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        # Release configure uses umask 077 for probe directories, which HMDFS
        # does not implement correctly. Keep probe directories readable.
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, encoding="utf-8") as handle:
            content = handle.read()
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(content.replace("umask 077", "umask 022"))
        env = {
            "CC": cc, "AR": shutil.which("llvm-ar") or "ar",
            "RANLIB": shutil.which("llvm-ranlib") or "ranlib",
            "CFLAGS": "-O2 -fPIC" if self.settings.build_type == "Release" else "-g -fPIC",
            "CONFIG_SHELL": shell, "SHELL": shell,
            "TMPDIR": tmp, "TMP": tmp, "TEMP": tmp,
        }
        prefix = " ".join(key + "=" + shlex.quote(value) for key, value in env.items())
        args = "--enable-static --disable-shared --with-pic --prefix=/"
        if self.settings.os == "OHOS":
            # configure's bundled config.sub predates OHOS. Compilation still
            # uses the actual OHOS SDK compiler supplied by the Conan profile.
            args += " --host=aarch64-unknown-linux-gnu --build=aarch64-unknown-linux-gnu"
        self.run(f"{prefix} {shlex.quote(shell)} {shlex.quote(configure)} {args}", env="conanbuild")
        self.run(f"{prefix} make -j1 SHELL={shlex.quote(shell)}", env="conanbuild")
        self.run(f"{prefix} make -j1 check SHELL={shlex.quote(shell)}", env="conanbuild")
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests", "framework": "autotools", "command": "make check",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
            "reason": "v0.5.0 Makefile.am has no TESTS/check_PROGRAMS; make check is an empty target",
        }), flush=True)

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "tlsrpt.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "tlsrpt_version.h", src=self.build_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libtlsrpt.a", src=os.path.join(self.build_folder, ".libs"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["tlsrpt"]
        self.cpp_info.set_property("cmake_file_name", "tlsrpt")
        self.cpp_info.set_property("cmake_target_name", "tlsrpt::tlsrpt")
        self.cpp_info.set_property("pkg_config_name", "libtlsrpt")
