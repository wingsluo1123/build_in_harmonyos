#!/usr/bin/env python3
"""Conan recipe — CVM 0.97 (SPAC/Makefile with Libtool)."""

import glob
import os
import shlex
import shutil
import socket
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"


class CvmConan(ConanFile):
    name = "cvm"
    version = "0.97"
    description = "Credential Validation Modules and client/module libraries"
    license = "GPL-2.0-or-later"
    homepage = "https://untroubled.org/cvm"
    url = "https://github.com/bruceg/cvm"
    # CVM exposes nine public libraries; the command suite is an additional
    # runtime surface.  Publish the shared libraries only so Conan propagates
    # headers and libraries to ordinary consumers without ambiguous static /
    # shared metadata.
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True]}
    default_options = {"shared": True}
    exports_sources = "tests/*"

    _libraries = (
        "cvm-v2client",
        "cvm-v1client",
        "cvm-module",
        "cvm-command",
        "cvm-local",
        "cvm-udp",
        "cvm-sql",
        "cvm-sasl",
        "cvm-qmail",
    )
    _programs = (
        "cvm-benchclient",
        "cvm-chain",
        "cvm-checkpassword",
        "cvm-pwfile",
        "cvm-qmail",
        "cvm-testclient",
        "cvm-unix",
        "cvm-v1benchclient",
        "cvm-v1checkpassword",
        "cvm-v1testclient",
        "cvm-vmailmgr",
        "cvm-vmailmgr-local",
        "cvm-vmailmgr-udp",
    )
    _test_programs = ("sasl-auth-test", "sql-query-test", "cvm-sqlite")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Public CVM headers expose bglibs types (for example bglibs/str.h),
        # and every component links bglibs.  Keep both traits visible to
        # downstream consumers instead of relying on Conan's transitive
        # defaults for a shared library.
        self.requires(
            "bglibs/2.04",
            transitive_headers=True,
            transitive_libs=True,
        )
        # These are upstream-test fixtures, not public CVM dependencies.
        # sqlite3 supplies both the cvm-sqlite link input and its fixture CLI;
        # cdb supplies cdbmake/cdbget for the self-contained Qmail/vmailmgr
        # databases created by tests.sh.
        self.test_requires("sqlite3/3.49.1")
        self.test_requires("cdb/20251021")

    def build_requirements(self):
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _write_spac_configuration(self, source):
        variables = AutotoolsToolchain(self).vars()
        cc = variables.get("CC", "clang")
        cflags = variables.get("CFLAGS", "")
        ldflags = variables.get("LDFLAGS", "")
        bglibs = self.dependencies["bglibs"].package_folder
        sqlite = self.dependencies["sqlite3"].package_folder
        include_dir = os.path.join(bglibs, "include")
        lib_dir = os.path.join(bglibs, "lib")
        sqlite_include_dir = os.path.join(sqlite, "include")
        sqlite_lib_dir = os.path.join(sqlite, "lib")

        compile_command = " ".join(
            value for value in (
                cc,
                cflags,
                "-g0",
                "-I" + shlex.quote(include_dir),
                "-I" + shlex.quote(sqlite_include_dir),
            ) if value
        )
        link_command = " ".join(
            value for value in (
                cc,
                ldflags,
                "-L" + shlex.quote(lib_dir),
            ) if value
        )
        save(self, os.path.join(source, "conf-cc"), compile_command + "\n")
        save(self, os.path.join(source, "conf-ld"), link_command + "\n")
        save(
            self,
            os.path.join(source, "sqlite.lib"),
            "-L{} -lsqlite3 -ldl -lpthread -lm\n".format(
                shlex.quote(sqlite_lib_dir)
            ),
        )
        save(
            self,
            os.path.join(source, "conf-lib"),
            "/usr/lib\n",
        )

    def _run_failure_atomicity_test(self, source):
        variables = AutotoolsToolchain(self).vars()
        cc = variables.get("CC", "clang")
        cflags = variables.get("CFLAGS", "")
        bglibs = self.dependencies["bglibs"].package_folder
        executable = os.path.join(source, "test-pipe-failure-atomic")
        command = " ".join(
            value for value in (
                cc,
                cflags,
                "-I" + shlex.quote(source),
                "-I" + shlex.quote(os.path.join(bglibs, "include")),
                shlex.quote(os.path.join(source, "tests", "pipe_failure_atomic.c")),
                "-o",
                shlex.quote(executable),
            ) if value
        )
        self.run(command, cwd=source)
        if can_run(self):
            self.run(shlex.quote(executable), cwd=source)

    def _run_upstream_tests(self, source):
        if not can_run(self):
            self.output.info("Cross-building: upstream runtime tests are deferred")
            return
        test_tmp = self._select_test_tmpdir(source)
        environment = Environment()
        environment.define("CVM_TEST_SOURCE", os.path.join(source, ".libs"))
        environment.define("CVM_TEST_TMPDIR", test_tmp)
        environment.define("CVM_TEST_UID", str(os.getuid()))
        environment.define("CVM_TEST_GID", str(os.getgid()))
        fixture_bins = [
            os.path.join(self.dependencies[dependency].package_folder, "bin")
            for dependency in ("sqlite3", "cdb")
        ]
        environment.define("CVM_TEST_TOOLS_PATH", os.pathsep.join(fixture_bins))
        environment.prepend_path(
            "LD_LIBRARY_PATH",
            os.path.join(source, ".libs"),
        )
        environment.prepend_path(
            "LD_LIBRARY_PATH",
            os.path.join(
                self.dependencies["bglibs"].package_folder,
                "lib",
            ),
        )
        with environment.vars(self).apply():
            self.run(
                "bash " + shlex.quote(os.path.join(source, "tests.sh")) + " -v",
                cwd=os.sep,
            )

    def _select_test_tmpdir(self, source):
        """Choose a writable mount that really supports pathname AF_UNIX."""
        candidates = [os.environ.get("TMPDIR")]
        if str(self.settings.os) == "OHOS":
            candidates.append("/data/storage/el2/base/cache")
        candidates.append(source)
        failures = []
        for base in dict.fromkeys(path for path in candidates if path):
            test_tmp = os.path.join(base, "cvm-0.97-tests-{}".format(os.getpid()))
            probe_path = os.path.join(test_tmp, "pathname.sock")
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                os.makedirs(test_tmp, mode=0o755, exist_ok=True)
                os.chmod(test_tmp, 0o755)
                probe.bind(probe_path)
            except OSError as exc:
                failures.append("{}: errno {} ({})".format(
                    base, exc.errno, exc.strerror
                ))
                shutil.rmtree(test_tmp, ignore_errors=True)
            else:
                self.output.info(
                    "pathname AF_UNIX fixture directory: " + test_tmp
                )
                return test_tmp
            finally:
                probe.close()
                if os.path.lexists(probe_path):
                    os.unlink(probe_path)
        raise RuntimeError(
            "No writable pathname AF_UNIX fixture directory: "
            + "; ".join(failures)
        )

    def build(self):
        apply_conandata_patches(self)
        source = self.source_folder
        self._write_spac_configuration(source)
        self.run(
            "rm -f compile load ltcompile ltload makeshlib "
            "crypt.lib s.lib shadow.lib socket.lib",
            cwd=source,
        )
        targets = "libraries " + " ".join(self._programs + self._test_programs)
        self.run("make -j1 " + targets, cwd=source)
        # The upstream harness expects all runnable helpers below one source
        # root.  Libtool programs live in .libs, while this non-Libtool helper
        # is emitted at the top level.
        shutil.copy2(
            os.path.join(source, "sql-query-test"),
            os.path.join(source, ".libs", "sql-query-test"),
        )
        self._run_failure_atomicity_test(source)
        self._run_upstream_tests(source)

    def package(self):
        source = self.source_folder
        include_dir = os.path.join(self.package_folder, "include", "cvm")
        for header in (
            "credentials.h",
            "errors.h",
            "facts.h",
            "module.h",
            "protocol.h",
            "sasl.h",
            "v1client.h",
            "v2client.h",
        ):
            copy(self, header, source, include_dir, keep_path=False)
        save(
            self,
            os.path.join(include_dir, "client.h"),
            load(self, os.path.join(source, "v2client.h")),
        )
        save(
            self,
            os.path.join(self.package_folder, "include", "cvm-sasl.h"),
            load(self, os.path.join(source, "sasl.h")),
        )

        lib_dir = os.path.join(self.package_folder, "lib")
        for library in self._libraries:
            for artifact in glob.glob(
                os.path.join(source, ".libs", "lib" + library + ".so*")
            ):
                copy(
                    self,
                    os.path.basename(artifact),
                    os.path.dirname(artifact),
                    lib_dir,
                    keep_path=False,
                )
        bin_dir = os.path.join(self.package_folder, "bin")
        for program in self._programs:
            copy(
                self,
                program,
                os.path.join(source, ".libs"),
                bin_dir,
                keep_path=False,
            )
        if self.settings.os == "OHOS":
            self._sanitize_package_elfs(bin_dir, lib_dir)
        copy(self, "COPYING", source, os.path.join(self.package_folder, "licenses"))

    def _sanitize_package_elfs(self, bin_dir, lib_dir):
        """Remove private paths and stale signatures from all shipped ELFs."""
        tools = {
            "patchelf": shutil.which("patchelf") or "/data/service/hnp/bin/patchelf",
            "objcopy": (shutil.which("llvm-objcopy")
                        or "/data/service/hnp/bin/llvm-objcopy"),
            "readelf": (shutil.which("llvm-readelf")
                        or "/data/service/hnp/bin/llvm-readelf"),
            "strip": (shutil.which("llvm-strip")
                      or "/data/service/hnp/bin/llvm-strip"),
            "signer": (shutil.which("binary-sign-tool")
                       or "/data/service/hnp/bin/binary-sign-tool"),
        }
        missing = [name for name, path in tools.items() if not os.path.isfile(path)]
        if missing:
            raise RuntimeError(
                "Required OHOS ELF tools are missing: " + ", ".join(missing)
            )
        paths = [os.path.join(bin_dir, program) for program in self._programs]
        for library in self._libraries:
            stem = "lib" + library + ".so"
            candidates = glob.glob(os.path.join(lib_dir, stem + ".*"))
            if not candidates:
                raise RuntimeError(
                    "No versioned shared library found for " + library
                )
            # Some OHOS storage/build combinations flatten Libtool symlinks
            # into byte-for-byte copies.  Select the fully versioned payload
            # and rebuild the linker-name and SONAME links deterministically.
            real = max(
                candidates,
                key=lambda item: (
                    os.path.basename(item).count("."),
                    len(os.path.basename(item)),
                ),
            )
            soname = subprocess.run(
                [tools["patchelf"], "--print-soname", real],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout.strip()
            if not soname.startswith(stem + "."):
                raise RuntimeError("Unexpected SONAME for " + real + ": " + soname)
            for link_name in (stem, soname):
                link_path = os.path.join(lib_dir, link_name)
                if os.path.abspath(link_path) == os.path.abspath(real):
                    continue
                if os.path.lexists(link_path):
                    os.unlink(link_path)
                os.symlink(os.path.basename(real), link_path)
            paths.append(real)
        for path in paths:
            signed = path + ".signed"
            subprocess.run(
                [tools["patchelf"], "--remove-rpath", path],
                check=True,
            )
            subprocess.run(
                [tools["strip"], "--strip-debug", path],
                check=True,
            )
            subprocess.run(
                [tools["objcopy"], "--remove-section", ".codesign", path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                [
                    tools["signer"], "sign",
                    "-inFile", path,
                    "-outFile", signed,
                    "-selfSign", "1",
                ],
                check=True,
            )
            os.replace(signed, path)
            os.chmod(path, 0o755)
            sections = subprocess.run(
                [tools["readelf"], "--sections", "--wide", path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout
            if sections.count(".codesign") != 1:
                raise RuntimeError(
                    "Signed ELF must have exactly one .codesign section: "
                    + path
                )

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        component_deps = {
            "v2client": ["bglibs::bglibs"],
            "v1client": ["bglibs::bglibs"],
            "module": ["bglibs::bglibs"],
            "command": ["bglibs::bglibs"],
            "local": ["bglibs::bglibs"],
            "udp": ["bglibs::bglibs"],
            "sql": ["bglibs::bglibs"],
            "sasl": ["bglibs::bglibs"],
            "qmail": ["bglibs::bglibs"],
        }
        for component, requires in component_deps.items():
            info = self.cpp_info.components[component]
            info.includedirs = ["include"]
            info.libs = ["cvm-" + component]
            info.requires = requires
            info.set_property("cmake_target_name", "cvm::" + component)
