#!/usr/bin/env python3
"""Conan recipe — berkeley-db4 4.8.30 (autotools, special build dir).

Berkeley DB requires running configure from the build_unix subdirectory:
    cd build_unix && ../dist/configure && make && make install

Patches handle:
- config.guess/config.sub update for aarch64-unknown-linux-ohos (E007)
- HMDFS umask/setgid tmp directory fix
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class BerkeleyDb4Conan(ConanFile):
    name = "berkeley-db4"
    version = "4.8.30"
    description = "High-performance embedded key/value database with Btree, Hash, Queue, Recno access methods"
    license = "Sleepycat"
    homepage = "https://www.oracle.com/database/berkeley-db/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Set TMPDIR to avoid permission issues on HMDFS
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--disable-static")
            tc.configure_args.append("--enable-shared")
        # Berkeley DB specific options
        # Disable C++ support - old Berkeley DB C++ code is incompatible with modern libcxx
        tc.configure_args.append("--disable-cxx")
        # Set TMPDIR environment variable
        env = tc.environment()
        env.define("TMPDIR", tmpdir)
        env.define("TEMP", tmpdir)
        env.define("TMP", tmpdir)
        # Set umask globally so all generated scripts (including config.status) inherit it
        env.define("UMASK", "022")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        
        # Fix umask 077 in configure script - this affects both configure itself
        # and the config.status script that configure generates
        configure_path = os.path.join(self.source_folder, "dist", "configure")
        if os.path.exists(configure_path):
            with open(configure_path, 'r') as f:
                content = f.read()
            # Replace all umask 077 with umask 022
            content = content.replace('umask 077', 'umask 022')
            with open(configure_path, 'w') as f:
                f.write(content)
        
        # Berkeley DB must be configured/built from build_unix subdirectory
        build_unix = os.path.join(self.source_folder, "build_unix")
        if not os.path.isdir(build_unix):
            os.makedirs(build_unix, mode=0o755)
        
        # Create tmp directory for configure temp files
        tmpdir = os.path.join(build_unix, "tmp")
        if not os.path.isdir(tmpdir):
            os.makedirs(tmpdir, mode=0o755)
        
        # Set umask to avoid setgid issues on HMDFS
        old_umask = os.umask(0o022)
        try:
            autotools = Autotools(self)
            with chdir(self, build_unix):
                # Pass TMPDIR as environment variable
                env = os.environ.copy()
                env["TMPDIR"] = tmpdir
                env["TEMP"] = tmpdir
                env["TMP"] = tmpdir
                
                autotools.configure(
                    build_script_folder=os.path.join(self.source_folder, "dist")
                )
                autotools.make(args=["-j1"])
        finally:
            os.umask(old_umask)

    def package(self):
        build_unix = os.path.join(self.source_folder, "build_unix")
        autotools = Autotools(self)
        with chdir(self, build_unix):
            autotools.install()
        # Remove documentation files to reduce package size
        docs_dir = os.path.join(self.package_folder, "docs")
        if os.path.isdir(docs_dir):
            import shutil
            shutil.rmtree(docs_dir, ignore_errors=True)

    def package_info(self):
        self.cpp_info.libs = ["db-4.8", "db"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
