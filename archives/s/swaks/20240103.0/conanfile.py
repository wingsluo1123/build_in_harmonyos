#!/usr/bin/env python3
"""Conan recipe for swaks 20240103.0 (Swiss Army Knife for SMTP).

swaks is a single self-contained Perl 5 script.  The upstream release asset
carries no build system and no compiled artifact, so the OHOS adaptation work
is not "make it compile" but:

  * declaring the Perl interpreter as a real runtime requirement
    (``run=True``) instead of relying on a system ``perl`` that OHOS does not
    provide, so that ``conan install`` wires an interpreter into the
    consumer's ``conanrun`` PATH;
  * staging the script as an executable entry point (R38: the package
    provides the ``swaks`` command);
  * proving with an executable consumer test that the staged CLI really
    speaks SMTP (test_package/test_swaks.sh drives a real transaction against
    a loopback SMTP sink).

No patches are needed: upstream already uses the portable
``#!/usr/bin/env perl`` shebang, which HarmonyOS >= HongMeng Kernel 1.12.0
supports because ``/usr/bin/env`` exists (knowledge base E037).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import copy, get, load


class SwaksConan(ConanFile):
    name = "swaks"
    version = "20240103.0"
    description = "Swiss Army Knife for SMTP - all-purpose, scriptable SMTP transaction tester"
    license = "GPL-2.0-or-later"
    homepage = "https://jetmore.org/john/code/swaks/"
    url = "https://github.com/jetmore/swaks"
    package_type = "application"

    # Nothing is compiled, but CI gate L0p requires the full OHOS setting set
    # (os/compiler/build_type/arch): a profile that carries more settings than
    # the recipe declares is rejected before conan create runs.
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def requirements(self):
        # swaks executes the Perl interpreter on the *host* (target) platform,
        # so perl is a runtime requirement, not a build tool.
        # run=True keeps perl out of the header/library interface while still
        # making Conan's VirtualRunEnv prepend its bin/ directory to PATH
        # (VirtualRunEnv only honours cpp_info.bindirs for requires with
        # run=True).
        self.requires("perl/5.42.2", run=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"swaks {self.version} only supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # There is nothing to compile, so build() guards the identity of the
        # artifact instead: the staged script must be the released version and
        # must keep the portable shebang this package relies on.
        content = load(self, os.path.join(self.source_folder, "swaks"))

        version_marker = f'build_version("{self.version}"'
        if version_marker not in content:
            raise ConanException(
                f"swaks source does not declare version {self.version} "
                f"(marker {version_marker!r} not found)"
            )
        if not content.startswith("#!/usr/bin/env perl"):
            first_line = content.splitlines()[0] if content else "<empty>"
            raise ConanException(
                "swaks source no longer starts with the portable "
                f"'#!/usr/bin/env perl' shebang: {first_line!r}"
            )
        self.output.info(
            f"swaks {self.version}: source script verified ({len(content)} bytes, upstream shebang kept)"
        )

    def package(self):
        copy(
            self,
            "swaks",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        os.chmod(os.path.join(self.package_folder, "bin", "swaks"), 0o755)

        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "doc", "swaks"),
            keep_path=False,
        )
        copy(
            self,
            "README.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "swaks"),
            keep_path=False,
        )

    def package_info(self):
        # Pure CLI package: expose bin/ only, so consumers neither link nor
        # include anything from it.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
