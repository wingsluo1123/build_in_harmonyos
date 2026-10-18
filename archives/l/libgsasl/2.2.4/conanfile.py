"""GNU SASL C library, packaged separately from libgsasl-tools."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgsaslConan(ConanFile):
    name = "libgsasl"
    version = "2.2.4"
    description = "GNU Simple Authentication and Security Layer C library"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gnu.org/software/gsasl/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libgsasl requires Linux or OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-static", "--disable-shared", "--disable-nls",
            "--disable-gtk-doc", "--without-gnutls",
            "--without-stringprep", "--disable-gssapi", "--disable-gs2",
            "--disable-ntlm",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        configure_path = os.path.join(self.source_folder, "configure")
        # HMDFS may ignore the restrictive umask used by config.status.
        replace_in_file(
            self, configure_path,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp="${TMPDIR:-/tmp}/conf$$" && (umask 000 && mkdir -p "$tmp") &&',
        )
        replace_in_file(
            self, configure_path,
            '  tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            '  tmp=${TMPDIR:-/tmp}/conf$$-$RANDOM\n  (umask 000 && mkdir -p "$tmp")',
        )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        # The upstream lib/ install target delivers libgsasl, public headers,
        # and libgsasl.pc while leaving the GPL command-line program in src/.
        autotools = Autotools(self)
        autotools.make(
            args=["-C", "lib", f"DESTDIR={self.package_folder}"],
            target="install",
        )
        # AutotoolsToolchain configures prefix=/ for DESTDIR packaging. Make
        # the installed .pc usable by consumers outside the build root.
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "libgsasl.pc")
        replace_in_file(self, pc, "prefix=/\n", "prefix=${pcfiledir}/../..\n")
        # Libtool archives embed the build-time libdir and are not needed for
        # consumers of the installed static archive.
        os.remove(os.path.join(self.package_folder, "lib", "libgsasl.la"))
        copy(
            self, "COPYING.LESSER", src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["gsasl"]
        self.cpp_info.set_property("pkg_config_name", "libgsasl")
