#!/usr/bin/env python3
"""Conan recipe for mtink 1.0.16 — EPSON inkjet status monitor (C + Motif/X11,
hand-written `Configure` + `Makefile.ORG`).

Upstream mtink ships four front ends: the Motif GUI `mtink`, the printer chooser
`mtinkc`, the console status monitor `ttink` and the sharing daemon `mtinkd`,
plus the parport device-query helper `detect/askPrinter`.

OHOS PC adaptation notes (all readings in notes.md):

* The recipe deliberately builds upstream's **console configuration**
  (`Configure -x`, "If you want only the tty based version use the -x option").
  In that mode the upstream script emits a Makefile whose `PRG` contains no
  GUI target, so all GUI compile/link rules (and therefore the whole
  Motif/X11/libXp/libXpm include and library set) drop out of the build face.
  No source patch is needed for this: `-x` is an upstream-supported switch.
* The GUI face was measured, not assumed: with `--build=never` the published
  Motif closure cannot resolve for the OHOS profile
  (`conan install --requires=motif/2.3.8 ... --build=never` ->
  `ERROR: Missing prebuilt package for 'libxext/6.4.0.1'`), so a Motif-linked
  `mtink` cannot be built from published binaries here.  See notes.md.
* libusb is NOT a dependency of the Linux/OHOS build face: `mainSrc/usbHlp.c`
  is entirely inside `#ifdef MACOS`, and the `Configure -m` "libusb under
  Linux" mode is self-contradictory upstream (it defines MACOS, which compiles
  `rw.c` down to nothing while `d4lib.c` still calls `devRead`/`devWrite`).
  Consequently `usbHlp.o` is an empty translation unit and no `usb_*` symbol is
  referenced (verified with llvm-nm on the linked binaries).
* The 2007 Makefile has no `CFLAGS`; every compile line is
  `$(CFLAGS) $(MTINK_CFLAGS)`.  The recipe pins `CC` and `CFLAGS` on the make
  command line from the Conan configuration (R33) instead of relying on the
  worker environment.
* `make install` is unusable here: every `install-*` target is wrapped in
  `if id | grep '=0(root)'` and writes to `/etc/init.d`, `/etc/rc.d` and
  `/usr/lib/cups/backend`.  Packaging is therefore done by `copy()`.
* OHOS ELF self-signing is required (loader EPERM otherwise).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# Upstream `Configure -x` (console configuration) builds these three programs.
# `ttink` comes from the default `all` target, the other two are named
# explicitly because upstream's Linux branch of `Configure` keys off
# `uname = Linux`, which is `HarmonyOS` on this platform.
_CONSOLE_BINS = (
    ("ttink", "bin/ttink"),
    ("mtinkd", "bin/mtinkd"),
    (os.path.join("detect", "askPrinter"), "bin/askPrinter"),
)

class MtinkConan(ConanFile):
    name = "mtink"
    version = "1.0.16"
    description = ("mtink 1.0.16 — EPSON inkjet printer status monitor: console "
                   "status monitor (ttink), sharing daemon (mtinkd) and the "
                   "parallel-port device query helper (askPrinter)")
    license = "GPL-2.0-or-later"
    homepage = "http://xwtools.automatix.de/mtink/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("epson", "printer", "status-monitor", "parallel-port", "ohos")

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # mtink 1.0.16 needs zero source patches (`Configure -x` is upstream's
        # own switch for the console build), so this is a no-op maintained for
        # the CI G1 contract and for any future patch.
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mtink supports Linux and OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        """R33: toolchain values come from the Conan configuration only."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables['c'] is not configured")
        jobs = self.conf.get("tools.build:jobs", default=1, check_type=int)
        return cc, max(1, jobs)

    def build(self):
        cc, jobs = self._toolchain()
        apply_conandata_patches(self)  # zero patches for 1.0.16: no-op

        # Upstream hand-written Configure (POSIX sh, not autoconf).  -x selects
        # the tty-only build: no Motif/X11 probe, no GUI target in PRG.
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        configure = os.path.join(self.source_folder, "Configure")
        if not os.path.isfile(configure):
            raise ConanException(f"upstream Configure script missing: {configure}")
        self.run(f'"{shell}" ./Configure -x -p /', cwd=self.source_folder)

        makefile = os.path.join(self.source_folder, "Makefile")
        if not os.path.isfile(makefile):
            raise ConanException("Configure did not generate a Makefile")
        text = open(makefile, "r", encoding="utf-8", errors="replace").read()
        if "MTINK_CFLAGS" not in text:
            # sanity: the Makefile.ORG template really was expanded
            raise ConanException("generated Makefile looks unexpanded")
        prg_line = _prg_line(text)
        if not prg_line:
            raise ConanException("generated Makefile has no PRG line")
        self.output.info("generated Makefile " + prg_line)
        # `Configure -x` must leave the Motif front ends out of the build face.
        tokens = prg_line.split("=", 1)[1].split()
        for gui_target in ("mtink", "mtinkc", "gimp-mtink"):
            if gui_target in tokens:
                raise ConanException(
                    f"Configure -x left the GUI target {gui_target!r} in PRG: "
                    + prg_line)
        if "ttink" not in tokens:
            raise ConanException("Configure -x did not select ttink: " + prg_line)

        flags = "-O2 -fPIC -fcommon"
        make_vars = f'CC={cc} CFLAGS="{flags}"'
        # Only the three runtime programs are built.  Upstream's default `all`
        # target also builds the developer utilities (utils/bldRes,
        # utils/rdPrtDesc, utils/chckRes); utils/chckRes compiles rdRes.c with
        # -DRESCHECK=1 and does not survive clang 15
        # ("non-void function 'searchCmp' should return a value" - inside the
        # #if RESCHECK block only).  The utilities are not part of the
        # delivered package, so they are not built instead of patching 2007
        # code that we do not ship.
        #
        # `mtinkd` and `detect/askPrinter` are named explicitly because
        # upstream's Configure keys that branch off `uname = Linux`, which is
        # `HarmonyOS` here.
        targets = " ".join(target for target, _ in _CONSOLE_BINS)
        self.run(f"make -j{jobs} {targets} {make_vars}", cwd=self.source_folder)

        for target, _ in _CONSOLE_BINS:
            product = os.path.join(self.source_folder, target)
            if not os.path.isfile(product) or os.path.getsize(product) == 0:
                raise ConanException(f"expected build product missing: {target}")
        self.output.info("build products verified: "
                         + ", ".join(t for t, _ in _CONSOLE_BINS))

    def package(self):
        for target, destination in _CONSOLE_BINS:
            copy(self, target, src=self.source_folder,
                 dst=os.path.join(self.package_folder, os.path.dirname(destination)),
                 keep_path=False)
            self._sign_ohos_elf(os.path.join(self.package_folder, destination))

        # Runtime data set shipped by upstream's install-desc target.  NOTE:
        # 1.0.16 already compiles the very same 91 printer records into
        # mainSrc/model.c (utils/printer.desc.bldin has 91 `.PRINTER` blocks);
        # the external file is read only from the fixed paths
        # /usr/lib/mtink|/usr/local/lib/mtink|/opt/mtink, so inside a
        # relocatable Conan package the built-in table is authoritative.
        copy(self, "utils/printer.desc.bldin", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "mtink"),
             keep_path=False)
        copy(self, "*.align", src=os.path.join(self.source_folder, "utils"),
             dst=os.path.join(self.package_folder, "share", "mtink"),
             keep_path=False)
        copy(self, "*.html", src=os.path.join(self.source_folder, "html"),
             dst=os.path.join(self.package_folder, "share", "doc", "mtink"),
             keep_path=False)
        copy(self, "*.gif", src=os.path.join(self.source_folder, "html"),
             dst=os.path.join(self.package_folder, "share", "doc", "mtink"),
             keep_path=False)
        copy(self, "LICENCE", src=os.path.join(self.source_folder, "html"),
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "CHANGE.LOG", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        self._verify_installed_tree()

    def _verify_installed_tree(self):
        """Installed-layout contract: fail loudly instead of shipping a stub."""
        expected = ["bin/ttink", "bin/mtinkd", "bin/askPrinter",
                    "share/mtink/printer.desc.bldin",
                    "licenses/LICENCE", "licenses/CHANGE.LOG"]
        missing = [p for p in expected
                   if not os.path.isfile(os.path.join(self.package_folder, p))]
        if missing:
            raise ConanException("installed tree is incomplete: "
                                 + ", ".join(missing))
        self.output.info("installed tree verified: " + ", ".join(expected))

    @staticmethod
    def _sign_ohos_elf(path):
        """OHOS refuses to execute unsigned ELFs (loader EPERM)."""
        signer = shutil.which("binary-sign-tool") \
            or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") \
            or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"missing executable to sign: {path}")
        if not (os.path.isfile(signer) and os.path.isfile(readelf)):
            raise ConanException("required OHOS signing tools are missing")
        output = path + ".signed"
        if os.path.lexists(output):
            os.unlink(output)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", output,
                        "-selfSign", "1"], check=True, timeout=120)
        sections = subprocess.run([readelf, "-SW", output], check=True,
                                  capture_output=True, text=True,
                                  timeout=60).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(
                f"signed executable does not carry exactly one .codesign "
                f"section: {path}")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))


def _prg_line(makefile_text):
    """Return the generated `PRG = ...` line, or an empty string."""
    for line in makefile_text.splitlines():
        if line.startswith("PRG"):
            return line
    return ""
