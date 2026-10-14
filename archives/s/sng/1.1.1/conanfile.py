#!/usr/bin/env python3
"""Conan recipe — sng 1.1.1

sng ("Scriptable Network Graphics") is a PNG <-> editable-text converter:
``sng < image.png`` prints the chunks as text, ``sng < image.sng`` compiles
the text back into a PNG.  Three C files, plain Makefile, depends on libpng
(-> zlib).

Adaptation notes
----------------
* Build system: hand-written GNU-make Makefile (no configure).  We build the
  ``sng`` target only; the default ``all`` also runs asciidoctor for the man
  page/HTML, which is not available on the build machines.  The pre-rendered
  ``sng.1`` shipped in the tarball is installed instead.
* LDFLAGS: the Makefile hard-sets ``LDFLAGS=-lpng``, which would drop the
  ``-L`` paths of the Conan dependencies, so the Conan-generated LDFLAGS is
  passed on the ``make`` command line (CC/CFLAGS/CPPFLAGS/LIBS come from the
  environment as usual).
* rgb.txt: sng loads the X11 colour-name table from ``RGBTXT`` (default
  ``/usr/share/X11/rgb.txt``) the first time a colour name is resolved, and
  aborts with "RGB database ... is missing" otherwise.  The table comes from
  the already published ``rgb`` package; it is copied into this package as
  ``share/X11/rgb.txt`` and ``RGBTXT`` is baked to that file.
* Upstream test: ``make check`` = shellcheck + ``sng_regress`` over a PNG
  suite that is not part of the tarball.  We run ``sng_regress`` on the
  shipped ``test.sng`` and ``snglogo.png`` (patched to honour $TMPDIR and use
  ``diff -u``; /tmp is read-only and toybox ``diff`` has no ``-c`` on OHOS).
* OHOS kernel refuses unsigned ELF: the binary is self-signed.
"""
import os
import shlex
import shutil
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SngConan(ConanFile):
    name = "sng"
    version = "1.1.1"
    description = "Scriptable Network Graphics: PNG <-> editable text converter"
    license = "BSD-2-Clause"
    homepage = "https://gitlab.com/esr/sng"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("png", "image", "converter", "command-line")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58.3")
        self.requires("rgb/1.1.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()
        VirtualRunEnv(self).generate()

    # ------------------------------------------------------------------ #
    def _rgb_txt_src(self):
        pkg = self.dependencies["rgb"].package_folder
        path = os.path.join(pkg, "share", "X11", "rgb.txt")
        if not os.path.isfile(path):
            raise ConanException(f"rgb.txt not found in the rgb package: {path}")
        return path

    def _rgb_txt_dst(self):
        return os.path.join(self.package_folder, "share", "X11", "rgb.txt")

    def _sign_elf(self, path):
        """OHOS kernel refuses to execute unsigned ELF files."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # HMFS may ignore chmod

    def build(self):
        apply_conandata_patches(self)
        # RGBTXT is baked into the binary; the file itself is installed by
        # package(), but the upstream test below runs before that, so place
        # it now as well (same destination, same content).
        dst = self._rgb_txt_dst()
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(self._rgb_txt_src(), dst)
        # The Makefile hard-sets LDFLAGS=-lpng, which would drop the -L/rpath
        # flags of the Conan dependencies: hand the generated value over on
        # the command line (CC/CFLAGS/CPPFLAGS/LIBS flow in via the env).
        ldflags = " ".join(
            v for v in (AutotoolsToolchain(self).vars().get("LDFLAGS"),
                        AutotoolsDeps(self).vars().get("LDFLAGS")) if v)
        self.run(
            f'make sng VERSION={self.version} RGBTXT="{dst}" LDFLAGS={shlex.quote(ldflags)}',
            cwd=self.source_folder,
        )
        self._sign_elf(os.path.join(self.source_folder, "sng"))
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run upstream's regression harness (``make check`` minus shellcheck).

        ``sng_regress`` round-trips every argument (decompile / recompile /
        canonicalise) and only *prints* a line on failure, so the run is
        green iff it prints nothing.  If the build machine cannot execute the
        target binary at all (e.g. an x86_64 runner with the aarch64 OHOS
        profile) the run is skipped with a warning; on a native machine a
        binary that does not run is a build failure.
        """
        import platform

        sng = os.path.join(self.source_folder, "sng")
        probe_in = os.path.join(self.source_folder, "test.sng")
        try:
            self.run(f'"{sng}" < "{probe_in}" > "{os.devnull}"',
                     cwd=self.source_folder, env="conanrun")
        except ConanException:
            machine = platform.machine().lower()
            native = {"armv8": ("aarch64", "arm64"),
                      "x86_64": ("x86_64", "amd64")}.get(str(self.settings.arch), ())
            if machine in native:
                raise
            self.output.warning(
                f"Upstream sng_regress skipped: this {machine} build machine "
                f"cannot execute the {self.settings.arch} target binary.")
            return

        shell = "/data/service/hnp/bin/bash"
        if not os.path.exists(shell):
            shell = "bash"
        tmpdir = os.path.join(self.build_folder, "regress-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        out = StringIO()
        self.run(
            f'TMPDIR="{tmpdir}" {shell} ./sng_regress test.sng snglogo.png',
            cwd=self.source_folder, env="conanrun", stdout=out,
        )
        text = out.getvalue().strip()
        if text:
            raise ConanException(f"upstream sng_regress reported failures:\n{text}")
        self.output.info("upstream sng_regress: test.sng + snglogo.png round-trip clean")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "sng", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "sng.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        dst = self._rgb_txt_dst()
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(self._rgb_txt_src(), dst)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
