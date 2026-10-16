#!/usr/bin/env python3
"""Conan recipe for the Makefile-based tsdecrypt 10.0 on HarmonyOS PC."""

import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load
from conan.tools.layout import basic_layout


class TsdecryptConan(ConanFile):
    name = "tsdecrypt"
    version = "10.0"
    description = "MPEG transport stream decryptor and conditional access client"
    license = "GPL-2.0-only"
    homepage = "https://github.com/gfto/tsdecrypt"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.0.21")
        self.requires("libdvbcsa/1.1.0")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("tsdecrypt/10.0 is packaged for OHOS only")
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("tsdecrypt/10.0 requires OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(self, **sources["main"], strip_root=True)
        get(self, **sources["libfuncs"], destination=os.path.join(self.source_folder, "libfuncs"), strip_root=True)
        get(self, **sources["libtsfuncs"], destination=os.path.join(self.source_folder, "libtsfuncs"), strip_root=True)

    def _tool(self, language):
        configured = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        fallback = "clang++" if language == "cpp" else "clang"
        return configured.get(language) or shutil.which(fallback) or fallback

    def _make_variables(self):
        openssl = self.dependencies["openssl"].package_folder
        dvbcsa = self.dependencies["libdvbcsa"].package_folder
        include_flags = [
            "-I{}".format(os.path.join(openssl, "include")),
            "-I{}".format(os.path.join(dvbcsa, "include")),
        ]
        cflags = " ".join([
            "-O2", "-fPIC", "-D_GNU_SOURCE", "-DTSDECRYPT_NO_PTHREAD_CANCEL",
            "-Wall", "-Wextra", "-Wshadow",
            "-Wformat-security", "-Wstrict-prototypes",
            "-ffile-prefix-map={}=/usr/src/tsdecrypt-10.0".format(self.source_folder),
        ] + include_flags)
        libs = " ".join([
            "-L{}".format(os.path.join(openssl, "lib")),
            "-L{}".format(os.path.join(dvbcsa, "lib")),
            "-lcrypto", "-ldvbcsa", "-ldl", "-lpthread",
        ])
        linker = shutil.which("ld.lld") or "ld.lld"
        return self._tool("c"), self._tool("cpp"), linker, cflags, libs

    @staticmethod
    def _native_ohos():
        return os.path.isdir("/system/bin") and platform.machine() in ("aarch64", "arm64")

    def _sign_executable(self, binary):
        """Replace any stale signature with one valid for execution on HarmonyOS."""
        directory = os.path.dirname(binary)
        filename = os.path.basename(binary)
        signed = filename + ".signed"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, filename), cwd=directory)
        self.run(
            '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, filename, signed),
            cwd=directory,
        )
        os.replace(os.path.join(directory, signed), binary)
        os.chmod(binary, 0o755)

    @staticmethod
    def _tool_output(*args):
        output = subprocess.check_output(args)
        return output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output

    def build(self):
        apply_conandata_patches(self)
        cc, cxx, linker, cflags, libs = self._make_variables()

        if self._native_ohos():
            ff_log = os.path.join(self.build_folder, "upstream-ffdecsa.log")
            self.run(
                'make -C FFdecsa clean && make -C FFdecsa FFdecsa_test '
                'COMPILER="{}" PARALLEL_MODE=PARALLEL_32_INT FLAGS="{}"'.format(cxx, cflags),
                cwd=self.source_folder,
            )
            ff_runner = os.path.join(self.source_folder, "FFdecsa", "FFdecsa_test")
            self._sign_executable(ff_runner)
            self.run('"{}" > "{}" 2>&1'.format(ff_runner, ff_log))
            if load(self, ff_log).count("CORRECT!") < 10:
                raise ConanException("FFdecsa upstream runner did not complete all comparisons")

            ts_log = os.path.join(self.build_folder, "upstream-libtsfuncs.log")
            self.run(
                'make -C libtsfuncs clean && make -C libtsfuncs tstest '
                'CC="{}" LINK="{} -o" CFLAGS="{}"'.format(cc, linker, cflags),
                cwd=self.source_folder,
            )
            ts_runner = os.path.join(self.source_folder, "libtsfuncs", "tstest")
            self._sign_executable(ts_runner)
            self.run('TZ=UTC "{}" > "{}" 2>&1'.format(ts_runner, ts_log))
            ts_output = load(self, ts_log)
            if "ERROR" in ts_output or ts_output.count("generator is correct") < 32:
                raise ConanException("libtsfuncs upstream runner reported a mismatch")

        self.run("make distclean", cwd=self.source_folder)
        self.run("make -C FFdecsa clean", cwd=self.source_folder)
        self.run(
            'make -j1 dvbcsa CC="{}" LINK="{} -o" CFLAGS="{}" tsdecrypt_LIBS="{}"'.format(
                cc, linker, cflags, libs
            ),
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "tsdecrypt", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "tsdecrypt.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        binary = os.path.join(bindir, "tsdecrypt")
        os.chmod(binary, 0o755)
        self._sign_executable(binary)

        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        section_text = self._tool_output(readelf, "-S", binary)
        dynamic_text = self._tool_output(readelf, "-d", binary)
        if section_text.count(".codesign") != 1:
            raise ConanException("packaged ELF must contain exactly one .codesign section")
        if "RPATH" in dynamic_text or "RUNPATH" in dynamic_text:
            raise ConanException("packaged ELF contains a build-time runtime path")
        if ".conan2" in dynamic_text or self.package_folder in dynamic_text:
            raise ConanException("packaged ELF leaks a Conan cache path")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
