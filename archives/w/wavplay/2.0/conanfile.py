#!/usr/bin/env python3
"""Conan recipe for wavplay: WAV file player/recorder with an OHOS native
audio backend (OH_AudioRenderer / OH_AudioCapturer).

The upstream audio backend uses the legacy OSS /dev/dsp interface, which does
not exist on OpenHarmony. This recipe applies portability patches that rewrite
the backend to the OHOS native audio API (see patches/0002-src-file.c.patch)
and select it with the HAVE_OHOS_AUDIO capability macro. The X11 GUI clients are disabled (--enable-nox);
only the wavplay / wavrec CLI tools are built.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# On OpenHarmony PC (HMDFS) the native `mktemp -d` creates directories that the
# owner cannot write into (file creation inside returns "Permission denied"),
# which breaks autoconf's config.status temp-dir setup. This shim replaces it
# with a plain-`mkdir` implementation that yields a writable directory, honoring
# the `mktemp -d <template>` contract used by config.status.
_MKTEMP_SHIM = """#!/bin/sh
# HMDFS mktemp shim (mkdir-based). See the recipe docstring for the rationale.
d=0; tpl=""
for a in "$@"; do
  case "$a" in
    -d|-D|--dir) d=1 ;;
    -*) : ;;
    *) [ -n "$tpl" ] || tpl="$a" ;;
  esac
done
if [ "$d" = 1 ]; then
  [ -n "$tpl" ] || tpl="./tmp.XXXXXX"
  r=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom 2>/dev/null | head -c 6)
  [ -n "$r" ] || r=a1b2c3
  n=$(printf '%s' "$tpl" | sed 's/X\\{1,\\}$//')"$r"
  if mkdir "$n" 2>/dev/null; then printf '%s\\n' "$n"; exit 0; fi
  exit 1
fi
exit 1
"""


class WavplayConan(ConanFile):
    name = "wavplay"
    version = "2.0"
    description = ("WAV file player and recorder (OHOS native audio backend via "
                   "OH_AudioRenderer / OH_AudioCapturer)")
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/wavplay/"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("wavplay is supported only on Linux/OHOS")
        if str(self.settings.os) == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # wavplay's 2009 autotools build uses -I.. -I../include, which only
        # covers the build tree. In conan's default out-of-source (VPATH)
        # layout the generated wavplay.h (in the build include dir) cannot find
        # the source header wavfile.h (in the source include dir). Force an
        # in-source build to match the project's assumption (and the working
        # local build).
        self.folders.build = ""

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Build only the CLI tools (OHOS has no X11 for the GUI clients).
        tc.configure_args.append("--enable-nox")
        if str(self.settings.os) == "OHOS":
            # Explicit build/host triplets: the 2009 config.guess bundled with
            # wavplay cannot recognize the HarmonyOS build machine, so pass the
            # triplets directly (config.sub accepts aarch64-unknown-linux-gnu).
            # The OHOS SDK clang already targets aarch64-unknown-linux-ohos with
            # the OHOS sysroot baked in, so no --target/--sysroot is required.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
            # Select the OHOS native audio backend (patched) via the
            # HAVE_OHOS_AUDIO capability macro (not a platform macro, per
            # R8) and link the system audio library.
            tc.extra_cflags.append("-DHAVE_OHOS_AUDIO")
            tc.extra_ldflags.append("-lohaudio")
            # HMDFS mktemp fix: put a mkdir-based mktemp shim first on PATH so
            # config.status gets a writable temp dir.
            shim_dir = os.path.join(self.build_folder, "mktemp-shim")
            os.makedirs(shim_dir, exist_ok=True)
            shim = os.path.join(shim_dir, "mktemp")
            with open(shim, "w") as f:
                f.write(_MKTEMP_SHIM)
            os.chmod(shim, 0o755)
            env = Environment()
            env.prepend_path("PATH", shim_dir)
            env.vars(self).save_script("hmfs_mktemp_shim")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI tool: only executables are produced (no library, no installed
        # headers — include/Makefile.am uses noinst_HEADERS).
        self.cpp_info.bindirs = ["bin"]
        # No cpp_info.libs and no system_libs on purpose: this is an
        # application package (CLI tools only), and the packaged binaries
        # carry their own DT_NEEDED entry for libohaudio.so (a system OHOS
        # library). Exporting system_libs here would leak -lohaudio into
        # downstream consumers that never call the audio API.
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
