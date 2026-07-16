#!/usr/bin/env python3
"""Conan recipe — source-highlight 3.1.9 (GNU source-code syntax highlighter, autotools)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SourcehighlightConan(ConanFile):
    name = "source-highlight"
    version = "3.1.9"
    description = "Source-code syntax highlighter"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/src-highlite/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add stub boost_regex library path to LDFLAGS
        tc.extra_ldflags.append(f"-L{self.source_folder}/lib")
        tc.extra_ldflags.append("-lboost_regex")
        # C++17 compat: suppress warnings from old C++ code
        tc.extra_cxxflags.append("-Wno-dynamic-exception-spec")
        tc.extra_cxxflags.append("-Wno-register")
        tc.generate()
        # Write environment variables into conanbuild.sh so configure sees them
        gen_dir = os.path.join(self.source_folder, "build-release", "conan")
        os.makedirs(gen_dir, exist_ok=True)
        with open(os.path.join(gen_dir, "conanbuild.sh"), "a") as f:
            f.write('\nexport BOOST_REGEX_LIB="boost_regex"\n')
            # E061: gnulib stdbool module needs this env var
            f.write('export gl_cv_header_stdbool_h="yes"\n')

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebangs for HarmonyOS (bash at /data/service/hnp/bin/bash)
        scripts_to_fix = ["configure", "install-sh", "config.status", "config.sub", "config.guess"]
        for script in scripts_to_fix:
            sp = os.path.join(self.source_folder, script)
            if os.path.exists(sp):
                self.run(
                    f"sed -i '1s|#!/bin/bash|#!/data/service/hnp/bin/bash|' '{sp}'"
                )
                self.run(
                    f"sed -i '1s|#!/bin/sh|#!/system/bin/sh|' '{sp}'"
                )
        # E007/E160: Fix config.guess to recognize HarmonyOS as Linux+musl
        guess_paths = [
            os.path.join(self.source_folder, "build-aux", "config.guess"),
            os.path.join(self.source_folder, "utils", "config.guess"),
            os.path.join(self.source_folder, "config", "config.guess"),
            os.path.join(self.source_folder, "config.guess"),
        ]
        for guess in guess_paths:
            if os.path.exists(guess):
                self.run(
                    r"""sed -i '/case "${UNAME_SYSTEM}" in/a HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl; ;;' """ + f"'{guess}'"
                )
                break
        # E125: HMDFS blocks config.status mktemp -d "./confXXXXXX"
        # Create a mktemp wrapper that uses a fixed directory name instead
        wrapper_dir = os.path.join(self.source_folder, "bin")
        self.run(f"mkdir -p {wrapper_dir}")
        self.run(f"""cat > '{wrapper_dir}/mktemp' << 'WRAPPER'
#!/data/service/hnp/bin/bash
# HMDFS workaround: mktemp wrapper
# If called with -d pattern like "./confXXXXXX", use a fixed directory
if [[ "$*" == *"./conf"* ]]; then
  dirname=$(echo "$*" | sed 's/.*\\.\\/conf//' | sed 's/X*$//')
  echo "./confdir_$$"
  mkdir -p "./confdir_$$"
else
  exec /system/bin/mktemp "$@"
fi
WRAPPER""")
        self.run(f"chmod +x '{wrapper_dir}/mktemp'")
        # Prepend the wrapper to PATH
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{wrapper_dir}:{old_path}"
        # Also create confdir in case the wrapper doesn't work
        confdir = os.path.join(self.source_folder, "confdir")
        self.run(f"mkdir -p {confdir}$$")
        # Also add the wrapper path to the conan build environment
        self.output.info(f"HMDFS workaround: mktemp wrapper at {wrapper_dir}/mktemp")
        # Boost::Regex is header-only since 1.69, but configure still needs a library to link.
        # Create a stub libboost_regex.a to satisfy the link test, then add --with-boost-regex.
        boost_lib_dir = os.path.join(self.source_folder, "lib")
        self.run(f"mkdir -p {boost_lib_dir}")
        # Create an empty object file and archive it as libboost_regex.a
        self.run(f"cd '{boost_lib_dir}' && touch empty.c && clang -c empty.c -o empty.o && llvm-ar cr libboost_regex.a empty.o && rm -f empty.c empty.o")
        # Set BOOST_REGEX_LIB to skip the configure suffix check
        self.run(f"export BOOST_REGEX_LIB=boost_regex")
        # Skip the bootstrap configure check for boost regex library
        # Boost::Regex is header-only since 1.69, configure still tries to link against it.
        # Patch configure to skip the library link check.
        configure_script = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_script):
            # Set BOOST_REGEX_LIB before the suffix check to skip it
            self.run(
                r"""sed -i '/if test "$ax_cv_boost_regex" = "yes"; then/a BOOST_REGEX_LIB="boost_regex"; BOOST_REGEX_LDFLAGS=""' """
                + f"'{configure_script}'"
            )
            # Replace all boost regex as_fn_error calls with no-ops
            self.run(
                r"""sed -i 's|as_fn_error.*Could not find a version of the Boost::Regex|: # patch: skip boost regex|' """
                + f"'{configure_script}'"
            )
            self.run(
                r"""sed -i 's|as_fn_error.*Could not link against|: # patch: skip boost regex|' """
                + f"'{configure_script}'"
            )
            self.run(
                r"""sed -i 's|as_fn_error.*ERROR! Boost::regex|: # patch: skip boost regex|' """
                + f"'{configure_script}'"
            )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["source-highlight"]
