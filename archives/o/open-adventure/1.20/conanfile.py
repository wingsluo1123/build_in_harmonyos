import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OpenAdventureConan(ConanFile):
    name = "open-adventure"
    version = "1.20"
    description = "Colossal Cave Adventure, the 1995 430-point version"
    license = "BSD-2-Clause"
    homepage = "https://gitlab.com/esr/open-adventure"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        cc = "clang"
        try:
            comp_exe = self.conf.get("tools.build:compiler_executables", check_type=dict)
            if comp_exe and "c" in comp_exe:
                cc = comp_exe["c"]
        except Exception:
            pass

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        build_dir = os.path.join(self.build_folder, "dep_build")
        os.makedirs(build_dir, exist_ok=True)
        local_prefix = os.path.join(self.build_folder, "local_prefix")
        for sub in ("bin", "lib", "lib/pkgconfig", "include"):
            os.makedirs(os.path.join(local_prefix, sub), exist_ok=True)

        self._build_ncurses(build_dir, local_prefix, cc)
        self._build_libedit(build_dir, local_prefix, cc)
        self._build_open_adventure(local_prefix, cc)

    def _fix_scripts(self, src_dir):
        """Fix umask 077 and shebang in ALL scripts for HMDFS/OHOS."""
        import re
        for root, dirs, files in os.walk(src_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                if "umask 077" not in content and "#!/bin/bash" not in content and "#!/bin/sh" not in content and "#! /bin/bash" not in content and "#! /bin/sh" not in content:
                    continue
                content = content.replace("umask 077", "umask 022")
                content = content.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
                content = content.replace("#!/bin/sh", "#!/system/bin/sh")
                content = content.replace("#! /bin/bash", "#! /data/service/hnp/bin/bash")
                content = content.replace("#! /bin/sh", "#! /system/bin/sh")
                try:
                    with open(fpath, "w") as f:
                        f.write(content)
                except Exception:
                    pass

    def _build_ncurses(self, build_dir, prefix, cc):
        ncurses_src = os.path.join(build_dir, "ncurses-6.4")
        get(self, url="https://ftp.gnu.org/pub/gnu/ncurses/ncurses-6.4.tar.gz",
            sha256="6931283d9ac87c5073f30b6290c4c75f21632bb4fc3603ac8100812bed248159",
            destination=build_dir, strip_root=False)

        self._fix_scripts(ncurses_src)

        arch = str(self.settings.arch)
        build_type = "aarch64-unknown-linux-gnu" if arch in ("armv8", "aarch64") else "x86_64-unknown-linux-gnu"

        self.run(
            f"cd {ncurses_src} && ./configure"
            f" --prefix={prefix}"
            f" --build={build_type} --host={build_type}"
            " --without-shared --without-debug --without-ada"
            " --without-manpages --without-tests --without-cxx-binding"
            " --enable-overwrite"
            f" CC={cc} CFLAGS='-fPIC -O2'"
        )

        for subdir in ("ncurses", "progs", "panel", "menu", "form", "misc", "include"):
            mkpath = os.path.join(ncurses_src, subdir, "Makefile")
            if os.path.exists(mkpath):
                with open(mkpath, "rb") as f:
                    data = f.read()
                data = re.sub(rb"top_srcdir\t= [^\n]*", b"top_srcdir\t= ..", data)
                with open(mkpath, "wb") as f:
                    f.write(data)

        ncurses_cflags = "-fPIC -O2 -Wno-implicit-function-declaration -Wno-int-conversion"
        self.run(f"cd {ncurses_src}/include && make CC={cc} CFLAGS='{ncurses_cflags}'")
        self.run(f"cd {ncurses_src}/ncurses && make CC={cc} CFLAGS='{ncurses_cflags}'")

        import shutil as shutil_mod
        lib_dir = os.path.join(prefix, "lib")
        inc_dir = os.path.join(prefix, "include")
        src_lib = os.path.join(ncurses_src, "lib", "libncurses.a")
        if os.path.exists(src_lib):
            shutil_mod.copy2(src_lib, os.path.join(lib_dir, "libncurses.a"))
        ncurses_a = os.path.join(lib_dir, "libncurses.a")
        if os.path.exists(ncurses_a):
            for name in ("libncursesw.a", "libtinfo.a", "libcurses.a"):
                link_path = os.path.join(lib_dir, name)
                if not os.path.exists(link_path):
                    os.symlink("libncurses.a", link_path)

        for hdr in os.listdir(os.path.join(ncurses_src, "include")):
            if hdr.endswith(".h"):
                shutil_mod.copy2(os.path.join(ncurses_src, "include", hdr), os.path.join(inc_dir, hdr))
        for hdr in ("curses.h", "term.h", "ncurses_def.h", "hashsize.h", "parametrized.h"):
            src_hdr = os.path.join(ncurses_src, "ncurses", hdr)
            if os.path.exists(src_hdr):
                shutil_mod.copy2(src_hdr, os.path.join(inc_dir, hdr))

    def _build_libedit(self, build_dir, prefix, cc):
        libedit_src = os.path.join(build_dir, "libedit-20240808-3.1")
        get(self, url="https://thrysoee.dk/editline/libedit-20240808-3.1.tar.gz",
            sha256="5f0573349d77c4a48967191cdd6634dd7aa5f6398c6a57fe037cc02696d6099f",
            destination=build_dir, strip_root=False)

        self._fix_scripts(libedit_src)

        arch = str(self.settings.arch)
        build_type = "aarch64-unknown-linux-gnu" if arch in ("armv8", "aarch64") else "x86_64-unknown-linux-gnu"

        self.run(
            f"cd {libedit_src} && ./configure"
            f" --prefix={prefix}"
            f" --build={build_type} --host={build_type}"
            " --disable-shared --enable-static"
            f" CC={cc} CFLAGS='-fPIC -O2 -D__STDC_ISO_10646__'"
            f" LDFLAGS='-L{prefix}/lib'"
        )

        self.run(
            f"cd {libedit_src} && make -j1"
            f" CC={cc} CFLAGS='-fPIC -O2 -D__STDC_ISO_10646__'"
            f" AUTOMAKE=true AUTOCONF=true ACLOCAL=true"
        )
        self.run(
            f"cd {libedit_src} && make install"
            f" CC={cc} CFLAGS='-fPIC -O2 -D__STDC_ISO_10646__'"
            f" AUTOMAKE=true AUTOCONF=true ACLOCAL=true"
        )

    def _build_open_adventure(self, prefix, cc):
        src = self.source_folder
        old_pkg = os.environ.get("PKG_CONFIG_PATH", "")
        old_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = os.path.join(prefix, "lib", "pkgconfig")
        os.environ["LD_LIBRARY_PATH"] = os.path.join(prefix, "lib") + ":" + old_ld

        self.run(f"make CC={cc} CFLAGS='-fPIC -O2' LIBS='-ledit -lncurses' -j1", cwd=src)
        self.run(f"make cheat CC={cc} CFLAGS='-fPIC -O2' LIBS='-ledit -lncurses'", cwd=src)

        for binary in ("advent", "cheat"):
            src_bin = os.path.join(src, binary)
            dst_bin = os.path.join(self.build_folder, binary)
            if os.path.exists(src_bin) and not os.path.exists(dst_bin):
                copy(self, binary, src, self.build_folder)

        os.environ["PKG_CONFIG_PATH"] = old_pkg
        os.environ["LD_LIBRARY_PATH"] = old_ld

    def package(self):
        copy(self, "advent", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cheat", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
