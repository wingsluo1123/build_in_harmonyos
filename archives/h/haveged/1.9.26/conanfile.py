"""haveged 1.9.26: entropy generator and libhavege for HarmonyOS PC."""

import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HavegedConan(ConanFile):
    name = "haveged"
    version = "1.9.26"
    description = "HAVEGE entropy generator and libhavege"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jirka-h/haveged"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self, **self.conan_data["sources"],
            filename="haveged-1.9.26.tar.gz", strip_root=True,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(("--enable-shared", "--disable-static"))
        else:
            tc.configure_args.extend(("--enable-static", "--disable-shared"))
        if str(self.settings.os) == "OHOS":
            # The device allows RNDGETENTCNT but rejects even a zero length
            # RNDADDENTROPY request with ENOTSUP. Ship the file/stream generator,
            # not a daemon that cannot inject entropy into the kernel pool.
            tc.configure_args.extend((
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
                "--disable-daemon",
            ))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            configure = os.path.join(self.source_folder, "configure")
            # E114: HMDFS maps mode 0700 temporary directories to a foreign
            # owner, so config.status cannot write conf*/subs1.awk.
            replace_in_file(
                self, configure,
                '(umask 077 && mktemp -d "./confXXXXXX")',
                'mktemp -d "./confXXXXXX"',
            )
            replace_in_file(
                self, configure,
                '(umask 077 && mkdir "$tmp")',
                'mkdir "$tmp"',
            )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

        # Run the script through bash: /bin/bash is absent on HarmonyOS and
        # CI disallows direct execution of scripts from this volume.
        ent_makefile = Path(self.build_folder) / "ent" / "Makefile"
        data = ent_makefile.read_text()
        needle = "\t./test.sh"
        if data.count(needle) != 1:
            raise RuntimeError("upstream ent check-local command changed")
        ent_makefile.write_text(data.replace(needle, "\tbash $(srcdir)/test.sh", 1))
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        libdir = Path(self.package_folder) / "lib"
        patterns = ("*.la", "*.a") if self.options.shared else ("*.la", "*.so", "*.so.*")
        for pattern in patterns:
            for artifact in libdir.glob(pattern):
                artifact.unlink()
        copy_license = Path(self.source_folder) / "COPYING"
        dst = Path(self.package_folder) / "licenses" / "COPYING"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(copy_license.read_bytes())

    def package_info(self):
        self.cpp_info.libs = ["havege"]
