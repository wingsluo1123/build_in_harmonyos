#!/usr/bin/env python3
"""Conan recipe for Berkeley DB 5.3.28.

Berkeley DB uses autotools but requires running configure from the
build_unix/ subdirectory: cd build_unix && ../dist/configure --prefix=...
The source tarball contains a src/ directory with the actual source code.

R26: Not a system-name library, so shared builds are fine.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class Berkeleydb5Conan(ConanFile):
    name = "berkeley-db5"
    version = "5.3.28"
    description = "Berkeley DB 5.3.28 — embedded key/value database library"
    license = "Sleepycat"  # Berkeley DB Sleepycat Public License
    homepage = "https://www.oracle.com/database/technologies/related/berkeleydb.html"
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
        tc = AutotoolsToolchain(self)
        # Berkeley DB needs to run configure from build_unix/, not from source root.
        # The autotools.configure() helper runs ./configure at source root, which
        # doesn't work for this project. We pass args via configure_args for
        # consistency, then run configure manually in build().
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--with-repmgr-ssl=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        build_dir = os.path.join(src_dir, "build_unix")
        os.makedirs(build_dir, exist_ok=True)

        # Configure from build_unix/ using ../dist/configure
        # Conan's AutotoolsToolchain sets --prefix=/ for library packages,
        # and DESTDIR handles the actual install path.
        self.run(
            f"cd {build_dir} && ../dist/configure "
            f"--prefix=/ "
            f"--enable-static --enable-shared --with-repmgr-ssl=no",
            env="conanbuild"
        )
        # Patch config.status for OHOS/HarmonyOS (HMDFS) compatibility.
        # Two issues:
        #   (1) `print -r` is a ksh/zsh builtin not available in HMDFS /bin/sh
        #       → replace with POSIX `printf '%s\n'`.
        #   (2) config.status creates temp awk scripts in ./confXXXX/ then
        #       executes them directly (`./subs1.awk`). HMDFS denies execute
        #       permission on newly-created scripts → Permission denied.
        #       → rewrite the invocation to `awk -f <script>` so the script
        #         only needs read permission, not execute.
        config_status = os.path.join(build_dir, "config.status")
        if os.path.isfile(config_status):
            with open(config_status) as f:
                content = f.read()
            # (1) print -r -- "..."  →  printf '%s\n' "..."
            content = content.replace('print -r --', "printf '%s\\n'")
            # (1b) any bare `print -r ` fallback
            content = content.replace('print -r ', "printf '%s\\n' ")
            # (2) Direct awk script execution:  "$ac_tmp/subs1.awk"  →  awk -f "$ac_tmp/subs1.awk"
            #     config.status invokes awk scripts via:  . "$tmp/subs1.awk"  OR  "$tmp/subs1.awk"
            #     We wrap every `subs*.awk` direct invocation with `awk -f`.
            import re
            # Match:  "$ac_tmp/subsN.awk"   or   $ac_tmp/subsN.awk   (no leading awk -f)
            content = re.sub(
                r'(?<!awk -f )(\$ac_tmp/subs\d+\.awk)',
                r'awk -f \1',
                content,
            )
            # Also handle the "./confXXX/subsN.awk" form used by older autotools
            content = re.sub(
                r'(?<!awk -f )(\./conf\S+/subs\d+\.awk)',
                r'awk -f \1',
                content,
            )
            # (3) mktemp temp dir: umask 077 → umask 022, use $TMPDIR
            content = content.replace(
                '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                '  tmp="${TMPDIR:-/tmp}"/conf$$  &&',
            )
            content = content.replace(
                '  (umask 077 && mkdir "$tmp")',
                '  (umask 022 && mkdir -p "$tmp")',
            )
            with open(config_status, "w") as f:
                f.write(content)

        self.run(f"cd {build_dir} && make -j1", env="conanbuild")
        self.run(
            f"cd {build_dir} && make install DESTDIR={self.package_folder}",
            env="conanbuild"
        )

    def package(self):
        # build() already handles install via DESTDIR
        pass

    def package_info(self):
        self.cpp_info.libs = ["db-5.3"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
