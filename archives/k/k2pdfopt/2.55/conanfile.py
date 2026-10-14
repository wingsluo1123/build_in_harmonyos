#!/usr/bin/env python3
"""Conan recipe — k2pdfopt 2.55 (custom Makefile-driven build, C application).

k2pdfopt optimizes PDF/text files for e-readers and small screens.
Upstream: https://willus.com/k2pdfopt/

Build notes:
- Upstream ships no working build system (its CMakeLists.txt is mostly
  commented out and relies on system pkg-config mupdf). This recipe drives
  the plain compilation model documented in readme_k2src.txt:
  willuslib -> libwillus.a, k2pdfoptlib -> libk2pdfopt.a, plus k2pdfopt.c.
- Upstream pins MuPDF 1.23.7. The artifact registry only has mupdf/1.25.1.
  k2pdfopt overrides only two MuPDF internals:
    * mupdf_mod/font-win32.c   (1.23.7 file; compiles unchanged against
      1.25.1 headers and provides the non-Windows no-op
      pdf_install_load_system_font_funcs)
    * mupdf-1.25.1/source/fitz/stext-device.c, patched to re-apply the
      upstream "willus mod" (`else dev->flags = 0;`) at the 1.25.1 call site
      (patch 0003; the other mupdf_mod files are either unmodified copies of
      1.23.7 sources or not needed with HAVE_MUPDF only, so they are skipped).
- OCR stack (GOCR/Leptonica/Tesseract) and DjVuLibre are disabled
  (patch 0001: willus.h defaults) — none of them exist in the artifact
  registry; k2pdfopt remains fully functional for PDF/text conversion.
- k2pdfopt's include_mod/ ships self-contained shim headers for
  jpeg/png/zlib; the JPEG symbols come from mupdf's statically bundled
  libjpeg (libmupdf-third.a). PNG/ZLIB are linked from the Conan packages.
- Single static executable; no shared libraries are produced (R26).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class K2pdfoptConan(ConanFile):
    name = "k2pdfopt"
    version = "2.55"
    license = "GPL-3.0-or-later"
    author = "Willus"
    url = "https://willus.com/k2pdfopt/"
    homepage = "https://willus.com/k2pdfopt/"
    description = "k2pdfopt — optimizes PDF/text files for e-readers and small-screen devices"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mupdf/1.25.1")
        self.requires("libpng/1.6.58")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # First entry: k2pdfopt itself (strip the zip root dir); second entry:
        # mupdf 1.25.1 source tree (kept in mupdf-1.25.1/ for the override).
        for i, src in enumerate(self.conan_data["sources"]):
            get(self, **src, strip_root=(i == 0))

    def _source_list(self, src):
        """C files to compile, mirroring readme_k2src.txt sections 2-4."""
        files = []
        # willuslib: skip DjVu / OCR backends (disabled in this build)
        for name in sorted(os.listdir(os.path.join(src, "willuslib"))):
            if not name.endswith(".c"):
                continue
            if name in ("bmpdjvu.c", "ocrgocr.c", "ocrtess.c"):
                continue
            files.append(f"willuslib/{name}")
        # k2pdfoptlib: skip the Windows GUI sources (HAVE_K2GUI off)
        for name in sorted(os.listdir(os.path.join(src, "k2pdfoptlib"))):
            if name.endswith(".c") and not name.startswith("k2gui"):
                files.append(f"k2pdfoptlib/{name}")
        files.append("k2pdfopt.c")
        # MuPDF overrides
        files.append("mupdf_mod/font-win32.c")
        files.append("mupdf-1.25.1/source/fitz/stext-device.c")
        return files

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # R33: compiler comes from the Conan profile conf, never from shell env
        comp_exe = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = comp_exe.get("c")
        if not cc:
            cc = {"clang": "clang", "gcc": "gcc", "apple-clang": "clang"}.get(
                str(self.settings.compiler), "cc")

        mupdf_src = os.path.join(src, "mupdf-1.25.1")
        deps = self.dependencies
        inc = [
            src, os.path.join(src, "include_mod"),
            os.path.join(src, "willuslib"), os.path.join(src, "k2pdfoptlib"),
            os.path.join(mupdf_src, "include"), os.path.join(mupdf_src, "source"),
            os.path.join(mupdf_src, "source", "fitz"),
            os.path.join(mupdf_src, "generated"),
            os.path.join(src, "mupdf_mod", "mupdf"),
        ]
        for dep in deps.values():
            inc.extend(dep.cpp_info.includedirs)
        inc = [p for p in inc if p and os.path.isdir(p)]

        objs = []
        for i, f in enumerate(self._source_list(src)):
            obj = os.path.join(self.build_folder, f"obj{i}.o")
            rel_obj = os.path.relpath(obj, src)
            self.run(f'{cc} -O2 -w -DNDEBUG -DHAVE_MUPDF -DHAVE_MUPDF_LIB '
                     f'{" ".join("-I" + p for p in inc)} '
                     f'-c {f} -o {rel_obj}',
                     cwd=src, env="conanbuild")
            objs.append(rel_obj)

        mupdf = deps["mupdf"]
        link_dirs = [f"-L{p}" for p in mupdf.cpp_info.libdirs]
        libpng = deps["libpng"]
        zlib = deps["zlib"]
        link_dirs += [f"-L{p}" for p in libpng.cpp_info.libdirs]
        link_dirs += [f"-L{p}" for p in zlib.cpp_info.libdirs]
        # Link order matters for static archives:
        # k2 objects -> libmupdf -> bundled third-party (jpeg etc.) -> png -> z
        cmd = (f'{cc} -O2 {" ".join(objs)} -o k2pdfopt '
               f'{" ".join(link_dirs)} '
               f'{" ".join("-l" + l for l in mupdf.cpp_info.libs)} '
               f'{" ".join("-l" + l for l in libpng.cpp_info.libs)} '
               f'{" ".join("-l" + l for l in zlib.cpp_info.libs)} -lm')
        ret = self.run(cmd, cwd=src, env="conanbuild")
        if ret != 0:
            raise ConanException(f"link failed with exit code {ret}")

    def package(self):
        copy(self, "k2pdfopt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
