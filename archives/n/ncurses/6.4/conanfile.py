import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.4"
    description = "Terminal display library"
    license = "MIT"
    homepage = "https://invisible-island.net/ncurses/"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-shared", "--without-debug", "--without-ada",
            "--without-manpages", "--without-tests", "--without-cxx-binding",
            "--enable-widec", "--enable-overwrite",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Fix garbled variables in all Makefiles (OHOS autoconf incompatibility)
        src = self.source_folder
        bld = self.source_folder
        for root, dirs, files in os.walk(bld):
            for fname in files:
                if fname == "Makefile":
                    fpath = os.path.join(root, fname)
                    with open(fpath, "rb") as f:
                        content = f.read()
                    # Compute correct srcdir for this subdirectory
                    rel = os.path.relpath(root, bld)
                    if rel == ".":
                        subdir = ""
                    else:
                        subdir = rel
                    srcdir_val = os.path.join(src, subdir) if subdir else src
                    lines = content.split(b"\n")
                    fixed = []
                    for line in lines:
                        try:
                            line.decode("ascii")
                        except UnicodeDecodeError:
                            line = bytes(b for b in line if b < 128)
                        if line.startswith(b"top_srcdir"):
                            line = b"top_srcdir\t= " + src.encode()
                        elif line.startswith(b"top_builddir"):
                            line = b"top_builddir\t= " + bld.encode()
                        elif line.startswith(b"srcdir") and not line.startswith(b"srcdir_"):
                            line = b"srcdir\t= " + srcdir_val.encode()
                        fixed.append(line)
                    with open(fpath, "wb") as f:
                        f.write(b"\n".join(fixed))
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ncursesw", "formw", "menuw", "panelw"]
