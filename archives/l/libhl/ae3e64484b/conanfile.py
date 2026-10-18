#!/usr/bin/env python3
"""libhl — thread-safe hash tables, linked lists, queues and other data structures for C.

Build layout note: upstream keeps its build system inside ``build/``. That directory
is an out-of-tree build directory holding the pre-generated ``configure``; the real
``Makefile.in`` / ``config.h.in`` / ``build-aux`` live at the repository root and the
copies inside ``build/`` are relative symlinks pointing back to the parent.
``configure`` derives ``srcdir`` from its own path relative to the working directory,
so the build must be driven from ``build/`` in order for ``srcdir`` to resolve to the
repository root (otherwise ``srcdir`` becomes ``.`` and VPATH lookups fail).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, chdir, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibhlConan(ConanFile):
    name = "libhl"
    version = "ae3e64484b"
    description = ("Thread-safe hash tables, linked lists, queues, red-black trees, tries "
                   "and graphs written in C")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/xant/libhl"
    url = "https://github.com/xant/libhl"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        with chdir(self, self.source_folder):
            apply_conandata_patches(self)

        # Upstream ships the build system under build/ (pre-generated configure). On
        # HarmonyOS (toybox mktemp + HMDFS), `umask 077 && mktemp -d` yields a 0700
        # directory the configure script cannot write into, so drop the explicit umask
        # from the temp-dir creation (same fix as the abook configure patch).
        cfg = os.path.join(self._build_dir, "configure")
        replace_in_file(self, cfg,
                        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                        'tmp=`(mktemp -d "./confXXXXXX") 2>/dev/null` &&')
        replace_in_file(self, cfg, '(umask 077 && mkdir "$tmp")', '(mkdir "$tmp")')

        autotools = Autotools(self)
        with chdir(self, self._build_dir):
            autotools.configure(build_script_folder=self._build_dir)
            # E074: HarmonyOS SELinux forbids user processes creating FIFOs, so GNU make's
            # jobserver cannot allocate its fifo ("jobserver mkfifo: ... Operation not
            # permitted") and parallel libtool invocations die with fork EAGAIN. Pin -j1;
            # Autotools.make detects the explicit -j in args and no longer appends -j<jobs>.
            autotools.make(target="shared" if self.options.shared else "static",
                           args=["-j1"])

    def package(self):
        copy(self, "*.a", src=self._build_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so*", src=self._build_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["hl"]

    @property
    def _build_dir(self):
        return os.path.join(self.source_folder, "build")
