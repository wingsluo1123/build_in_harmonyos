#!/usr/bin/env python3
"""Conan recipe — pam_script 1.1.9 (PAM module that runs scripts per PAM phase).

pam_script is a loadable PAM module: for every module type it forks and execs
one administrator supplied script (pam_script_auth, pam_script_acct,
pam_script_passwd, pam_script_ses_open, pam_script_ses_close) and maps the
script exit status onto the PAM return code.  Its only hard dependency is a
PAM implementation, which the already published linux-pam/1.7.2 package
provides on OpenHarmony (<security/pam_appl.h>, <security/pam_modules.h>,
libpam.so).

Build system
------------
Upstream only ships autotools files and the tag archive has no generated
``configure``.  Bootstrapping it on OHOS means running ``autoreconf`` with the
``automake`` tool_requires package, whose ``bin/.aclocal-real`` starts with
``#!/data/service/hnp/bin/perl`` — a path that does not exist on the device —
so ``autoreconf`` aborts with exit status 126 before the first line of the
upstream source is compiled.  The whole upstream build is a single
translation unit linked as a version-less libtool module, so the recipe
reproduces exactly that artifact with CMake, which both the OHOS toolchain and
the repository CI already provide:

    libtool -module -avoid-version pam_script.la
        ->  lib/security/pam_script.so

No upstream source file is modified; the CMake glue only feeds the feature
macros that ``configure`` would otherwise generate into ``config.h``
(PACKAGE, HAVE_SETENV, HAVE_VSYSLOG) and the ``PAM_SCRIPT_DIR`` default that
``Makefile.am`` derives from ``$(sysconfdir)``.

``make install`` is not reproduced either: upstream's install hooks create
symlinks under ``${sysconfdir}`` and run the ``etc/pam_script`` helper, which
is a system administration step rather than a package artifact.  The packaged
payload is the module, its man page, the upstream documentation and the
licence.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save

# Default directory the module looks its scripts up in.  Upstream bakes
# $(sysconfdir) into -DPAM_SCRIPT_DIR, and a distribution build uses /etc.
PAM_SCRIPT_DIR = "/etc"

CMAKE_LISTS = """\
cmake_minimum_required(VERSION 3.20)
project(pam_script C)

if(NOT PAM_INCLUDE_DIR)
    message(FATAL_ERROR "PAM_INCLUDE_DIR must point at the linux-pam headers")
endif()
if(NOT PAM_LIBRARY)
    message(FATAL_ERROR "PAM_LIBRARY must point at libpam.so")
endif()

# One translation unit, built as a loadable PAM module: this is what
# `libtool -module -avoid-version` produces for the upstream autotools build.
add_library(pam_script MODULE pam_script.c)
set_target_properties(pam_script PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pam_script"
    SUFFIX ".so"
)
target_include_directories(pam_script PRIVATE ${PAM_INCLUDE_DIR})
# On OHOS the loader resolves a dlopen()ed module only inside its own
# dependency closure, so the module has to record libpam.so.0 as DT_NEEDED
# instead of leaving pam_* undefined for the host process to provide.  The
# host PAM stack has the same DSO loaded, so no second copy appears.
target_link_libraries(pam_script PRIVATE ${PAM_LIBRARY})

# Feature macros that upstream's configure would write into config.h.
# HAVE_CONFIG_H stays undefined, so pam_script.c does not include config.h.
target_compile_definitions(pam_script PRIVATE
    PACKAGE="pam-script"
    PAM_SCRIPT_DIR="@PAM_SCRIPT_DIR@"
    HAVE_SETENV=1
    HAVE_VSYSLOG=1
)

install(TARGETS pam_script LIBRARY DESTINATION lib/security)
"""


class PamScriptConan(ConanFile):
    name = "pam_script"
    version = "1.1.9"
    description = ("PAM module that executes scripts during the authentication, "
                   "account, password and session phases")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/jeroennijhof/pam_script"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pam_script is a loadable PAM module and needs a POSIX PAM host")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "pam_script is dlopen()ed by a PAM stack; a static build is unusable")

    def requirements(self):
        self.requires("linux-pam/1.7.2")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        pam = self.dependencies["linux-pam"]
        include = pam.cpp_info.includedirs[0]
        if not os.path.isabs(include):
            include = os.path.join(pam.package_folder, include)
        libdir = pam.cpp_info.libdirs[0]
        if not os.path.isabs(libdir):
            libdir = os.path.join(pam.package_folder, libdir)
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.cache_variables["PAM_INCLUDE_DIR"] = include
        tc.cache_variables["PAM_LIBRARY"] = os.path.join(libdir, "libpam.so")
        tc.cache_variables["PAM_SCRIPT_DIR"] = PAM_SCRIPT_DIR
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"),
             CMAKE_LISTS.replace("@PAM_SCRIPT_DIR@", PAM_SCRIPT_DIR))
        cmake = CMake(self)
        cmake.configure()
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
        cmake.build(build_tool_args=["-j{}".format(jobs)])

    def package(self):
        cmake = CMake(self)
        cmake.install()

        module = os.path.join(self.package_folder, "lib", "security", "pam_script.so")
        if not os.path.isfile(module):
            raise ConanException("pam_script.so was not installed into lib/security")

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README*", src=os.path.join(self.source_folder, "etc"),
             dst=os.path.join(self.package_folder, "share", "doc", "pam_script"))
        self._install_man_page()
        if str(self.settings.os) == "OHOS":
            self._sign_shared_objects()

    def _install_man_page(self):
        template = os.path.join(self.source_folder, "pam-script.7.in")
        if not os.path.isfile(template):
            return
        with open(template, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        text = text.replace("@sysconfdir@", PAM_SCRIPT_DIR)
        text = text.replace("@libdir@", "lib/security")
        # configure.ac still declares 1.1.8 inside the 1.1.9 tag; the package
        # version is the tag version.
        text = text.replace("@PACKAGE_STRING@", "pam-script 1.1.9")
        save(self, os.path.join(self.package_folder, "share", "man", "man7", "pam-script.7"), text)

    def _sign_shared_objects(self):
        paths = [
            path
            for path in glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True)
            if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path)
        ]
        if not paths:
            return
        objcopy = self._find_ohos_tool("OHOS_LLVM_OBJCOPY", "llvm-objcopy")
        signer = self._find_ohos_tool("OHOS_BINARY_SIGN_TOOL", "binary-sign-tool")
        missing = [
            name for name, path in (("llvm-objcopy", objcopy), ("binary-sign-tool", signer))
            if not path
        ]
        if missing:
            raise ConanException("OHOS signing tools unavailable: %s" % ", ".join(missing))
        for path in paths:
            strip_result = self.run(
                f'{objcopy} --remove-section .codesign "{path}"', ignore_errors=True)
            if strip_result != 0:
                raise ConanException("llvm-objcopy could not remove .codesign from %s" % path)
            sign_result = self.run(
                f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1',
                ignore_errors=True)
            if sign_result != 0:
                raise ConanException("binary-sign-tool failed for %s" % path)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, env_name, command):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.isfile(configured):
                return configured
        tool_dir = os.environ.get("SIGN_TOOL_PATH")
        if tool_dir:
            candidate = os.path.join(tool_dir, command)
            if os.path.isfile(candidate):
                return candidate
        candidates = [os.path.join("/data/service/hnp/bin", command)]
        # The OHOS SDK that ships the compiler also ships binary-sign-tool.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("c") or compilers.get("cpp") or "")
        if compiler_dir:
            candidates.append(os.path.join(compiler_dir, command))
        sdk_root = os.path.join(os.path.expanduser("~"), ".harmonybrew", "opt")
        candidates.extend(sorted(
            glob.glob(os.path.join(sdk_root, "ohos-sdk*", "bin", command)), reverse=True))
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(command)

    def package_info(self):
        moduledir = os.path.join(self.package_folder, "lib", "security")
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib/security"]
        self.cpp_info.set_property("cmake_file_name", "pam_script")
        self.cpp_info.set_property("cmake_target_name", "pam_script::pam_script")
        self.cpp_info.requires = ["linux-pam::pam"]
        # A PAM module is never linked, it is dlopen()ed by the PAM stack.
        self.runenv_info.define_path(
            "PAM_SCRIPT_MODULE", os.path.join(moduledir, "pam_script.so"))
        self.runenv_info.append_path("LD_LIBRARY_PATH", moduledir)
