#!/usr/bin/env python3
"""Conan recipe for libvisio 0.1.11 — Visio file format parser library.

Adapted for HarmonyOS PC (arm64) platform.
License: MPL-2.0
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.gnu import AutotoolsDeps


class LibvisioConan(ConanFile):
    name = "libvisio"
    version = "0.1.11"
    description = "Library for parsing the Microsoft Visio file format structure"
    license = "MPL-2.0"
    homepage = "https://github.com/LibreOffice/libvisio"
    url = "https://github.com/LibreOffice/libvisio"  # Package repository URL

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "AutotoolsDeps", "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0@ohpcd/stable")
        self.requires("librevenge/0.0.5@ohpcd/stable")
        self.requires("icu4c/78@ohpcd/stable")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Static build by default
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Disable tests and tools (avoids cppunit dependency)
        tc.configure_args.append("--disable-tests")
        tc.configure_args.append("--disable-tools")

        # Add -rpath flags so configure test programs can find shared libs
        # (avoid LD_LIBRARY_PATH which breaks lld linked against libxml2)
        for dep_name in ["librevenge", "icu4c", "libxml2", "zlib"]:
            dep = self.dependencies.get(dep_name)
            if dep:
                for libdir in dep.cpp_info.libdirs:
                    tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")

        tc.generate()

        # E002: Set TMPDIR to build folder to avoid HMDFS mktemp issues
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        # Add a mktemp wrapper to PATH that uses TMPDIR
        wrapper_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(wrapper_dir, exist_ok=True)
        mktemp_wrapper = os.path.join(wrapper_dir, "mktemp")
        with open(mktemp_wrapper, "w") as f:
            f.write("""#!/system/bin/sh
TMPDIR="${TMPDIR:-/storage/Users/currentUser/tmp}"
if [ "$1" = "-d" ]; then
    shift
    DIR="$TMPDIR/mktemp_$$"
    mkdir -p "$DIR"
    echo "$DIR"
else
    FILE="$TMPDIR/mktemp_file_$$_$(date +%s%N 2>/dev/null || echo $$)"
    touch "$FILE"
    echo "$FILE"
fi
""")
        os.chmod(mktemp_wrapper, 0o755)
        env.define("PATH", wrapper_dir + ":" + os.environ.get("PATH", ""))
        env.vars(self, scope="build").save_script("libvisio_env")

    def _fix_shebang(self, script_path):
        """Fix shebang for HarmonyOS: /bin/sh -> /system/bin/sh"""
        if not os.path.exists(script_path):
            return
        # Use strict=False to avoid exceptions when pattern not found
        replace_in_file(self, script_path, "#!/bin/sh", "#!/system/bin/sh", strict=False)
        replace_in_file(self, script_path, "#! /bin/sh", "#!/system/bin/sh", strict=False)

    def _patch_config_guess(self):
        """E007: Patch config.guess/config.sub for HarmonyOS detection"""
        candidates = [
            os.environ.get("OHC_SKILL_ROOT", ""),
            os.path.expanduser("~/.opendesk/apps/skills/resources/openharmony-compile-agent"),
        ]
        patch_script = None
        for root in candidates:
            if root:
                p = os.path.join(root, "scripts", "patch-autotools-ohos.pl")
                if os.path.exists(p):
                    patch_script = p
                    break
        if not patch_script:
            return

        # Script expects both config.guess AND config.sub as arguments
        src = self.source_folder
        config_guess = os.path.join(src, "config.guess")
        config_sub = os.path.join(src, "config.sub")
        if os.path.exists(config_guess) and os.path.exists(config_sub):
            self.run(f'perl "{patch_script}" "{config_guess}" "{config_sub}"', env="conanbuild")

    def _fix_la_files(self):
        """Fix broken libdir in .la files from conan dependencies"""
        for dep_name in ["librevenge", "icu4c", "libxml2", "zlib"]:
            dep = self.dependencies.get(dep_name)
            if not dep:
                continue
            for libdir in dep.cpp_info.libdirs:
                la_files = glob.glob(os.path.join(libdir, "*.la"))
                for la_file in la_files:
                    try:
                        with open(la_file, "r") as f:
                            content = f.read()
                        # Fix broken libdir (e.g., '//lib')
                        if "//lib" in content or "libdir=''" in content:
                            content = content.replace(f"libdir='//lib'", f"libdir='{libdir}'")
                            content = content.replace(f"libdir=''", f"libdir='{libdir}'")
                            # Fix broken dependency paths
                            content = content.replace("//lib/", f"{libdir}/")
                            with open(la_file, "w") as f:
                                f.write(content)
                    except Exception:
                        pass

    def build(self):
        apply_conandata_patches(self)

        # E165: Fix shebang in autogen.sh first
        autogen_path = os.path.join(self.source_folder, "autogen.sh")
        self._fix_shebang(autogen_path)

        # Set up AUTOM4TE for aclocal (autoconf workaround)
        autom4te = shutil.which("autom4te")
        if autom4te:
            os.environ["AUTOM4TE"] = autom4te

        # Run autogen.sh to generate configure (if not already generated)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(autogen_path) and not os.path.exists(configure_path):
            self.run(f'cd "{self.source_folder}" && /system/bin/sh autogen.sh',
                     env="conanbuild")

        # E165: Fix shebang in configure (generated by autogen.sh)
        self._fix_shebang(configure_path)

        # E007: Patch config.guess/config.sub for HarmonyOS
        self._patch_config_guess()

        # Fix broken .la files in conan cache
        self._fix_la_files()

        # Set PKG_CONFIG_PATH to include the Conan generators folder
        # where PkgConfigDeps generated .pc files
        gen_folder = self.generators_folder
        os.environ["PKG_CONFIG_PATH"] = gen_folder + ":" + os.environ.get("PKG_CONFIG_PATH", "")

        # Create symlinks for .pc files that need alternate names
        # e.g., librevenge.pc -> librevenge-0.0.pc
        pc_aliases = {
            "librevenge": "librevenge-0.0",
            "libxml2": "libxml-2.0",
            "icu4c": "icu-uc",
        }
        for src_name, alias_name in pc_aliases.items():
            src_pc = os.path.join(gen_folder, f"{src_name}.pc")
            alias_pc = os.path.join(gen_folder, f"{alias_name}.pc")
            if os.path.exists(src_pc) and not os.path.exists(alias_pc):
                shutil.copy(src_pc, alias_pc)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["visio-0.1"]
        self.cpp_info.includedirs = ["include/libvisio-0.1"]
        # Propagate transitive dependencies so test_package can find headers
        self.cpp_info.requires = ["librevenge::librevenge", "boost::boost",
                                   "icu4c::icu4c", "libxml2::libxml2", "zlib::zlib"]
