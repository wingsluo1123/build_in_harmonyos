#!/usr/bin/env python3
"""Conan recipe — libu2f-host 1.1.10

Yubico Universal 2nd Factor (U2F) host-side C library (libu2f-host) plus the
`u2f-host` command line utility.

Build system: GNU Autotools.  The official Yubico release tarball already ships
a generated `configure`, `Makefile.in` and a pre-built man page, so no
autoreconf/bootstrap step is required.

OHOS specifics
--------------
* `config.guess`/`config.sub` (2019) do not recognise HarmonyOS; `configure` is
  driven with an explicit aarch64-unknown-linux-gnu --build/--host triplet.
* Dependencies come from Conan (json-c, hidapi).  configure.ac probes
  `json-c`/`json` and `hidapi`/`hidapi-hidraw` through pkg-config, while the
  Conan packages ship json-c.pc and hidapi-libusb.pc.  The LIBJSON_* / HIDAPI_*
  override variables are injected so PKG_CHECK_MODULES succeeds without
  patching upstream sources.
* Installed header layout places hidapi.h under include/hidapi and json.h under
  include/json-c, whereas the sources include <hidapi.h> and <json.h>; those
  sub-directories are therefore added to the respective *_CFLAGS.
* help2man/gengetopt are unavailable on OHOS.  The tarball ships pre-generated
  src/u2f-host.1 and src/cmdline.{c,h}; their timestamps are refreshed so the
  corresponding make (re)generation rules are treated as up to date.
* musl libc lacks a few symbols referenced by the shared json-c/libusb
  libraries; the linker is relaxed with -Wl,--allow-shlib-undefined.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches, copy, load, save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# HMDFS marks directories created under `umask 077` with the setgid bit
# (drwx--S---), which blocks even the owner from writing files inside them.
# config.status creates its temporary archive dir that way and then fails with
# "…/subs1.awk: Permission denied" / "could not setup config files machinery".
# Relaxing the umask to 022 keeps temp dirs writable (knowledge base E129).
_UMASK_FIX_FILES = ("configure", "build-aux/ltmain.sh", "build-aux/install-sh")


class Libu2fHostConan(ConanFile):
    name = "libu2f-host"
    version = "1.1.10"
    description = "Yubico Universal 2nd Factor (U2F) host-side C library and u2f-host CLI"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/Yubico/libu2f-host"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("json-c/0.17")
        self.requires("hidapi/0.14.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _refresh_generated_sources(self):
        """help2man/gengetopt are absent on OHOS: keep the pre-generated
        man page and gengetopt outputs newer than their inputs so the
        matching make rules are skipped."""
        for rel in ("src/u2f-host.1", "src/cmdline.c", "src/cmdline.h"):
            path = os.path.join(self.source_folder, rel)
            if os.path.exists(path):
                os.utime(path, None)

    def _relax_umask_for_hmdfs(self):
        """Relax autoconf's `umask 077` temp-dir guard (E129).

        On HMDFS a directory created under `umask 077` ends up with the setgid
        bit set and is not writable by its own owner, so config.status fails
        when it tries to create its `confXXXXXX/subs1.awk` helper.
        Rewriting the umask to 022 keeps the temp directory writable.
        """
        for rel in _UMASK_FIX_FILES:
            path = os.path.join(self.source_folder, rel)
            if not os.path.exists(path):
                continue
            content = load(self, path)
            if "umask 077" in content:
                save(self, path, content.replace("umask 077", "umask 022"))

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_ldflags.append("-Wl,--allow-shlib-undefined")

        if not self.options.shared:
            tc.configure_args.append("--disable-shared")

        # config.guess/config.sub from 2019 cannot canonicalise HarmonyOS.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])

        env = tc.environment()

        jsonc = self.dependencies["json-c"]
        jinc = os.path.join(jsonc.package_folder, "include")
        jlib = os.path.join(jsonc.package_folder, "lib")
        env.define("LIBJSON_CFLAGS", f"-I{jinc} -I{jinc}/json-c")
        env.define("LIBJSON_LIBS", f"-L{jlib} -ljson-c")

        hidapi = self.dependencies["hidapi"]
        libusb = self.dependencies["libusb"]
        hinc = os.path.join(hidapi.package_folder, "include", "hidapi")
        hlib = os.path.join(hidapi.package_folder, "lib")
        ulib = os.path.join(libusb.package_folder, "lib")
        env.define("HIDAPI_CFLAGS", f"-I{hinc}")
        env.define("HIDAPI_LIBS", f"-L{hlib} -lhidapi-libusb -L{ulib} -lusb-1.0")

        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        self._refresh_generated_sources()
        self._relax_umask_for_hmdfs()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["u2f-host"]
        self.cpp_info.set_property("pkg_config_name", "u2f-host")
        self.cpp_info.set_property("cmake_file_name", "libu2f-host")
        self.cpp_info.set_property("cmake_target_name", "libu2f-host::libu2f-host")
        self.cpp_info.requires = ["json-c::json-c", "hidapi::hidapi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
