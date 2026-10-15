#!/usr/bin/env python3
"""Conan recipe for vtgamma 0.5 — gamma correction for virtual terminals (pure Perl).

Upstream (kilobyte/vtgamma) ships a single Perl script plus a man page; the
release tarball contains no build system at all (LICENSE, README, vtgamma,
vtgamma.1).

OHOS adaptation (script-package paradigm, cf. cgvg / check-jsonschema):
- the script is installed as-is except for its shebang, which upstream hard-codes
  to `#!/usr/bin/perl -w`. HarmonyOS PC ships perl at a non-standard location
  (/data/service/hnp/bin/perl), so an absolute interpreter path is not valid on
  the target. It is rewritten to `#!/usr/bin/env perl` so the interpreter is
  resolved from PATH; the Conan runtime dependency perl/5.42.2 provides it via
  VirtualRunEnv.
- build() asserts the upstream shebang before rewriting it, so an upstream
  change fails loudly instead of silently shipping an unpatched script.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, load, save
from conan.tools.layout import basic_layout


class VtgammaConan(ConanFile):
    name = "vtgamma"
    version = "0.5"
    description = "Gamma correction for Linux virtual terminals and many graphical terminal emulators"
    license = "Public-Domain"
    homepage = "https://github.com/kilobyte/vtgamma"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"vtgamma only supports Linux/OHOS, got {self.settings.os}")

    def requirements(self):
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, filename="vtgamma-0.5.tar.gz", **self.conan_data["sources"], strip_root=True)

    def build(self):
        src = self.source_folder
        install_dir = os.path.join(self.build_folder, "install")
        script = os.path.join(src, "vtgamma")
        content = load(self, script)
        shebang = "#!/usr/bin/perl -w"
        if not content.startswith(shebang):
            raise ConanException("upstream vtgamma shebang drifted: expected %r" % shebang)
        content = content.replace(shebang, "#!/usr/bin/env perl", 1)
        bin_dir = os.path.join(install_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        out_script = os.path.join(bin_dir, "vtgamma")
        save(self, out_script, content)
        os.chmod(out_script, 0o755)
        man_dir = os.path.join(install_dir, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        shutil.copy2(os.path.join(src, "vtgamma.1"), os.path.join(man_dir, "vtgamma.1"))

    def package(self):
        install_dir = os.path.join(self.build_folder, "install")
        copy(self, "*", src=os.path.join(install_dir, "bin"), dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*", src=os.path.join(install_dir, "share"), dst=os.path.join(self.package_folder, "share"), keep_path=True)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
