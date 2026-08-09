#!/usr/bin/env python3
"""Conan recipe for zathura-pdf-mupdf 2026.05.10 — PDF plugin for zathura using MuPDF.

This plugin is a shared module (.so) loaded by zathura at runtime.
It links statically against mupdf (libmupdf.a ~50MB) for PDF rendering.

Build approach (self-contained, no external conan deps for mupdf/girara/zathura):
  1. Download zathura-pdf-mupdf source (meson project)
  2. Download mupdf 1.27.2 source + thirdparty submodules (bundled build)
  3. Apply mupdf mujs patches (fill thirdparty/mujs/ with regexp/utf source)
  4. Build mupdf libs (libmupdf.a, libmupdf-third.a) with bundled deps
  5. Download girara 2026.02.04 source (headers only, stub lib for linking)
  6. Download zathura 2026.05.20 source (headers only, stub lib for linking)
  7. Create .pc files for girara, zathura, mupdf
  8. Create stub gtk/gtk.h (zathura's links.h includes <gtk/gtk.h> but
     the plugin doesn't use GTK directly — symbols resolved at runtime)
  9. Build zathura-pdf-mupdf plugin with meson (-Dc_std=c17, clang15 no C23)

Conan deps: glib/2.84.0.1, cairo/1.18.4 (from ohpcd artifact repo)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


# Mupdf thirdparty submodule commits (same as mupdf-tools recipe)
SUBMODULES = {
    "freetype": ("thirdparty-freetype2", "42608f77f20749dd6ddc9e0536788eaad70ea4b5"),
    "harfbuzz": ("thirdparty-harfbuzz", "ff8031d14b30d7c1b10fa3466d5f7c458837647b"),
    "libjpeg": ("thirdparty-libjpeg", "7fe42a89507fac623fadf0c68fd1b10ebef66a23"),
    "lcms2": ("thirdparty-lcms2", "f75fad71d53efd58d7312bea21c2bedca0b9e6da"),
    "openjpeg": ("thirdparty-openjpeg", "5781f7478694c78e7a245dc21fe7fa6f65bf3b96"),
    "zlib": ("thirdparty-zlib", "51b7f2abdade71cd9bb0e7a373ef2610ec6f9daf"),
    "brotli": ("thirdparty-brotli", "6e092ab79683949f432d1c0cab88effa683c90d7"),
    "jbig2dec": ("jbig2dec", "d915733ec69260c1fd2c458b06835cb57bb85ac7"),
    "mujs": ("mujs", "33c83d8553048fd7710a518821cdefa5818e1559"),
}

GIRARA_URL = "https://pwmt.org/projects/girara/download/girara-2026.02.04.tar.xz"
ZATHURA_URL = "https://pwmt.org/projects/zathura/download/zathura-2026.05.20.tar.xz"
MUPDF_URL = "https://codeload.github.com/ArtifexSoftware/mupdf/tar.gz/refs/tags/1.27.2"


class ZathuraPdfMupdfConan(ConanFile):
    name = "zathura-pdf-mupdf"
    version = "2026.05.10"
    description = "PDF plugin for zathura using MuPDF renderer"
    license = "MIT"
    homepage = "https://github.com/pwmt/zathura-pdf-mupdf"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        # Export mupdf patches (applied to mupdf source, not in conandata.yml)
        patches_dir = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(patches_dir):
            copy(self, "*", patches_dir, self.export_folder)

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("cairo/1.18.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # 1. Main source: zathura-pdf-mupdf
        get(self, **self.conan_data["sources"], strip_root=True)

        # 2. Download girara source (headers only)
        girara_dest = os.path.join(self.source_folder, "girara-src")
        get(self, url=GIRARA_URL, strip_root=True, destination=girara_dest)

        # 3. Download zathura source (headers only)
        zathura_dest = os.path.join(self.source_folder, "zathura-src")
        get(self, url=ZATHURA_URL, strip_root=True, destination=zathura_dest)

        # 4. Download mupdf source (use curl+tar due to URL without .tar.gz extension)
        mupdf_dest = os.path.join(self.source_folder, "mupdf-src")
        os.makedirs(mupdf_dest, exist_ok=True)
        tmpfile = os.path.join(self.source_folder, ".mupdf.tar.gz")
        self.run(f'curl -L -o "{tmpfile}" "{MUPDF_URL}" --connect-timeout 30 --max-time 300 -k -s')
        self.run(f'tar xzf "{tmpfile}" -C "{mupdf_dest}" --strip-components=1')
        os.remove(tmpfile)

        # 5. Download mupdf thirdparty submodules
        for dir_name, (repo, commit) in SUBMODULES.items():
            url = f"https://codeload.github.com/ArtifexSoftware/{repo}/tar.gz/{commit}"
            dest = os.path.join(mupdf_dest, "thirdparty", dir_name)
            shutil.rmtree(dest, ignore_errors=True)
            os.makedirs(dest, exist_ok=True)
            tmpfile = os.path.join(self.source_folder, f".{dir_name}.tar.gz")
            self.run(f'curl -L -o "{tmpfile}" "{url}" --connect-timeout 30 --max-time 120 -k -s')
            self.run(f'tar xzf "{tmpfile}" -C "{dest}" --strip-components=1')
            os.remove(tmpfile)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["c_std"] = "c17"
        tc.project_options["tests"] = "disabled"
        tc.project_options["pdf"] = "enabled"
        tc.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # Fix native file: ensure ar points to full path of llvm-ar
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.isfile(native_file):
            with open(native_file, "r") as f:
                content = f.read()
            if "ar =" not in content and "[binaries]" in content:
                content = content.replace(
                    "[binaries]\n",
                    "[binaries]\nar = '/data/service/hnp/bin/llvm-ar'\n",
                )
            elif "ar =" not in content:
                content += "\n[binaries]\nar = '/data/service/hnp/bin/llvm-ar'\n"
            else:
                import re
                content = re.sub(r"ar\s*=.*", "ar = '/data/service/hnp/bin/llvm-ar'", content)
            with open(native_file, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        mupdf_dir = os.path.join(src, "mupdf-src")
        girara_dir = os.path.join(src, "girara-src")
        zathura_dir = os.path.join(src, "zathura-src")

        # Local prefix for dependency staging
        local_prefix = os.path.join(self.build_folder, "local_prefix")
        for d in ["lib/pkgconfig", "include", "lib"]:
            os.makedirs(os.path.join(local_prefix, d), exist_ok=True)

        # Set up environment for build (os.environ used by self.run())
        old_env = dict(os.environ)
        env_path = os.environ.get("PATH", "")
        if "/data/service/hnp/bin" not in env_path:
            os.environ["PATH"] = f"/data/service/hnp/bin:{env_path}"
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # 1. Build mupdf (libraries only)
        # Use persistent cache to avoid rebuilding mupdf on every conan create
        # (mupdf build takes ~20 min; cache makes subsequent runs <30s)
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "mupdf-build-1.27.2")
        mupdf_build = os.path.join(mupdf_dir, "build", "release")

        if os.path.isdir(os.path.join(cache_dir, "lib")) and \
           os.path.isfile(os.path.join(cache_dir, "lib", "libmupdf.a")):
            # Use cached mupdf build (fast path)
            self.output.info("Using cached mupdf build from %s" % cache_dir)
            copy(self, "*.a", os.path.join(cache_dir, "lib"),
                 os.path.join(local_prefix, "lib"))
            copy(self, "*.h", os.path.join(cache_dir, "include"),
                 os.path.join(local_prefix, "include"))
        else:
            # Build mupdf from source (slow path, first run only)
            import multiprocessing
            nproc = multiprocessing.cpu_count() or 1
            nproc = min(nproc, 4)  # cap at 4 for memory safety

            make_cmd = (
                "make CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib "
                "HAVE_X11=no HAVE_GLUT=no HAVE_OBJCOPY=no "
                "shared=no build=release extract=no html=no mujs=no "
                f"-j{nproc} libs"
            )
            self.run(make_cmd, cwd=mupdf_dir)

            # Install mupdf headers and libs
            copy(self, "*.a", mupdf_build, os.path.join(local_prefix, "lib"))
            copy(self, "*.h", os.path.join(mupdf_dir, "include"),
                 os.path.join(local_prefix, "include"))

            # Cache the build artifacts for future runs
            os.makedirs(os.path.join(cache_dir, "lib"), exist_ok=True)
            os.makedirs(os.path.join(cache_dir, "include"), exist_ok=True)
            copy(self, "*.a", mupdf_build, os.path.join(cache_dir, "lib"))
            copy(self, "*.h", os.path.join(mupdf_dir, "include"),
                 os.path.join(cache_dir, "include"))
            self.output.info("Cached mupdf build to %s" % cache_dir)

        with open(os.path.join(local_prefix, "lib", "pkgconfig", "mupdf.pc"), "w") as f:
            f.write(
                f"prefix={local_prefix}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: mupdf\n"
                f"Description: MuPDF PDF rendering library\n"
                f"Version: 1.27.2\n"
                f"Libs: -L${{libdir}} -lmupdf -lmupdf-third\n"
                f"Libs.private: -lm -lpthread -ldl\n"
                f"Cflags: -I${{includedir}}\n"
            )

        # 4. Install girara headers + stub lib + .pc
        girara_inc = os.path.join(local_prefix, "include", "girara")
        os.makedirs(girara_inc, exist_ok=True)
        girara_src_hdrs = os.path.join(girara_dir, "girara")
        for hf in os.listdir(girara_src_hdrs):
            if hf.endswith(".h") and hf != "version.h.in":
                shutil.copy2(os.path.join(girara_src_hdrs, hf), girara_inc)

        with open(os.path.join(girara_inc, "girara-version.h"), "w") as f:
            f.write(
                "#ifndef GIRARA_VERSION_H\n"
                "#define GIRARA_VERSION_H\n"
                "#define GIRARA_VERSION_MAJOR 2026\n"
                "#define GIRARA_VERSION_MINOR 02\n"
                "#define GIRARA_VERSION_REV 04\n"
                '#define GIRARA_VERSION "2026.02.04"\n'
                "#endif\n"
            )

        self.run("llvm-ar rcs libgirara.a", cwd=os.path.join(local_prefix, "lib"))

        with open(os.path.join(local_prefix, "lib", "pkgconfig", "girara.pc"), "w") as f:
            f.write(
                f"prefix={local_prefix}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: girara\n"
                f"Description: girara library (headers for plugin build)\n"
                f"Version: 2026.02.04\n"
                f"Libs: -L${{libdir}} -lgirara\n"
                f"Cflags: -I${{includedir}}\n"
            )

        # 5. Install zathura headers + stub lib + .pc (with plugindir)
        zathura_inc = os.path.join(local_prefix, "include", "zathura")
        os.makedirs(zathura_inc, exist_ok=True)
        zathura_src_hdrs = os.path.join(zathura_dir, "zathura")
        for hf in os.listdir(zathura_src_hdrs):
            if hf.endswith(".h") and hf != "version.h.in":
                shutil.copy2(os.path.join(zathura_src_hdrs, hf), zathura_inc)

        with open(os.path.join(zathura_inc, "zathura-version.h"), "w") as f:
            f.write(
                "#ifndef ZATHURA_VERSION_H\n"
                "#define ZATHURA_VERSION_H\n"
                "#define ZATHURA_VERSION_MAJOR 2026\n"
                "#define ZATHURA_VERSION_MINOR 05\n"
                "#define ZATHURA_VERSION_REV 20\n"
                '#define ZATHURA_VERSION "2026.05.20"\n'
                "#define ZATHURA_API_VERSION 6\n"
                "#define ZATHURA_ABI_VERSION 7\n"
                "#endif\n"
            )

        self.run("llvm-ar rcs libzathura.a", cwd=os.path.join(local_prefix, "lib"))

        with open(os.path.join(local_prefix, "lib", "pkgconfig", "zathura.pc"), "w") as f:
            f.write(
                f"prefix={local_prefix}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n"
                f"plugindir=${{libdir}}/zathura\n\n"
                f"Name: zathura\n"
                f"Description: zathura document viewer (headers for plugin build)\n"
                f"Version: 2026.05.20\n"
                f"Requires: girara\n"
                f"Libs: -L${{libdir}} -lzathura\n"
                f"Cflags: -I${{includedir}}\n"
            )

        # 6. Create stub gtk/gtk.h (zathura links.h includes <gtk/gtk.h>)
        gtk_dir = os.path.join(local_prefix, "include", "gtk")
        os.makedirs(gtk_dir, exist_ok=True)
        with open(os.path.join(gtk_dir, "gtk.h"), "w") as f:
            f.write(
                "#ifndef __GTK_STUB_H__\n"
                "#define __GTK_STUB_H__\n"
                "#include <glib.h>\n"
                "typedef void* GdkAtom;\n"
                "#endif\n"
            )

        # 7. Build zathura-pdf-mupdf with meson
        pkg_config_path = os.path.join(local_prefix, "lib", "pkgconfig")
        # Copy custom .pc files to conan generators folder so meson finds them
        # (conan's run() may source conanbuild.sh which resets PKG_CONFIG_PATH)
        for pc_file in ["zathura.pc", "girara.pc", "mupdf.pc"]:
            src_pc = os.path.join(pkg_config_path, pc_file)
            if os.path.isfile(src_pc):
                shutil.copy2(src_pc, self.generators_folder)
        # Set environment for meson
        os.environ["PKG_CONFIG_PATH"] = self.generators_folder
        os.environ["LD_LIBRARY_PATH"] = os.path.join(local_prefix, "lib")
        os.environ.setdefault("AR", "/data/service/hnp/bin/llvm-ar")
        os.environ.setdefault("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        # Also copy include dirs by setting CFLAGS
        os.environ.setdefault("CFLAGS", "-fPIC -O2")
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Restore environment
        os.environ.clear()
        os.environ.update(old_env)

    def package(self):
        # Copy the plugin .so (main artifact)
        copy(self, "libpdf-mupdf.so", self.build_folder,
             os.path.join(self.package_folder, "lib", "zathura"))
        # Copy mupdf static libs (consumers linking the plugin need them)
        local_lib = os.path.join(self.build_folder, "local_prefix", "lib")
        copy(self, "libmupdf*.a", local_lib, os.path.join(self.package_folder, "lib"))
        # Copy mupdf headers
        local_inc = os.path.join(self.build_folder, "local_prefix", "include", "mupdf")
        copy(self, "*.h", local_inc, os.path.join(self.package_folder, "include", "mupdf"))

    def package_info(self):
        self.cpp_info.libs = ["pdf-mupdf"]
        self.cpp_info.libdirs = ["lib/zathura", "lib"]
        self.cpp_info.includedirs = ["include"]
