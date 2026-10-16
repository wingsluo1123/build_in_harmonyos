#!/usr/bin/env python3
"""Conan test_package — rpcgen/2.6.4 (rule-12 consumer end-to-end test).

Drives the *installed* rpcgen CLI and then compiles and runs what it produced:

  1. The packaged bin/rpcgen is invoked from its package folder (not by PATH
     lookup) four times, once per generation mode, on a real interface
     definition: calc.h (-h), calc_xdr.c (-c), calc_clnt.c (-l), calc_svc.c (-m).
  2. calc_consumer.c + the generated client stub and XDR routines are compiled
     against the packaged libtirpc; the generated dispatcher is reused through
     the unity-style include inside calc_consumer.c.
  3. The resulting program forks a server on 127.0.0.1:<ephemeral port> and
     performs two real RPC calls over TCP loopback with the generated stubs,
     asserting the business results (struct sum/product, scalar square).

rpcgen needs an external C preprocessor; HarmonyOS provides it as clang-cpp and
has no command named `cpp`, so this test supplies the traditional name (see
_cpp_shim_dir).  No rpcbind is required: the service is registered locally.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

GENERATED = ("calc.h", "calc_xdr.c", "calc_clnt.c", "calc_svc.c")


class RpcgenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The generated stubs are compiled and run against TI-RPC.
        self.requires("libtirpc/1.3.7")

    def layout(self):
        basic_layout(self)

    def _cc(self):
        """C compiler of the active profile (falls back to PATH lookup)."""
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        return compilers.get("c") or "clang"

    def _cpp_shim_dir(self):
        """Directory providing the `cpp` entry rpcgen looks for.

        rpcgen always pipes the .x through an external preprocessor; upstream
        resolves it as -Y <dir>/cpp, then /lib/cpp, then plain `cpp` from PATH.
        HarmonyOS ships that preprocessor as clang-cpp under the toolchain
        prefix, so the traditional name is provided here.  `-x c` is required
        because clang would otherwise consider the .x extension a linker input.
        """
        shim_dir = os.path.join(self.build_folder, "cpp-shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "cpp")
        with open(shim, "w", encoding="utf-8") as handle:
            handle.write('#!/bin/sh\nexec "%s" -E -x c "$@"\n' % self._cc())
        os.chmod(shim, 0o755)
        return shim_dir

    def _tirpc_flags(self):
        dep = self.dependencies["libtirpc"]
        components = dep.cpp_info.aggregated_components()
        includes = ["-I" + inc for inc in components.includedirs]
        tirpc_inc = os.path.join(dep.package_folder, "include", "tirpc")
        if os.path.isdir(tirpc_inc) and ("-I" + tirpc_inc) not in includes:
            includes.append("-I" + tirpc_inc)
        libs = ["-L" + lib for lib in components.libdirs]
        return includes, libs

    def _generate(self, rpcgen, gen_dir, shim_dir):
        """Run the packaged rpcgen once per generation mode.

        rpcgen derives the ``#include`` it writes into the generated sources
        from the path of the input file, so the interface definition is copied
        next to the generated files and named relatively - otherwise the
        generated code would embed this machine's absolute paths.
        """
        shutil.copyfile(os.path.join(self.source_folder, "calc.x"),
                        os.path.join(gen_dir, "calc.x"))
        modes = (("-h", "calc.h"), ("-c", "calc_xdr.c"),
                 ("-l", "calc_clnt.c"), ("-m", "calc_svc.c"))
        for flag, filename in modes:
            # -Y <dir>: upstream's documented way of pointing rpcgen at a
            # preprocessor; the value is a *directory* to which rpcgen appends
            # "/cpp" (see README "运行说明").
            self.run(f'"{rpcgen}" -Y "{shim_dir}" {flag} -o {filename} calc.x',
                     cwd=gen_dir)
        for filename in GENERATED:
            path = os.path.join(gen_dir, filename)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise ConanException(
                    "rpcgen did not produce a usable " + filename)
            self.output.info(f"rpcgen generated {filename} "
                             f"({os.path.getsize(path)} bytes)")

    def test(self):
        if not can_run(self):
            return

        package_folder = self.dependencies[self.tested_reference_str].package_folder
        rpcgen = os.path.join(package_folder, "bin", "rpcgen")
        if not os.path.isfile(rpcgen):
            raise ConanException("packaged rpcgen not found at " + rpcgen)

        gen_dir = os.path.join(self.build_folder, "gen")
        os.makedirs(gen_dir, exist_ok=True)
        shim_dir = self._cpp_shim_dir()
        self._generate(rpcgen, gen_dir, shim_dir)

        includes, libs = self._tirpc_flags()
        exe = os.path.join(self.build_folder, "calc_consumer")
        self.run(" ".join(
            [self._cc(), "-I" + gen_dir] + includes +
            ["-o", f'"{exe}"',
             f'"{os.path.join(self.source_folder, "calc_consumer.c")}"',
             f'"{os.path.join(gen_dir, "calc_clnt.c")}"',
             f'"{os.path.join(gen_dir, "calc_xdr.c")}"'] + libs + ["-ltirpc"]))

        self.run(f'"{exe}"', env="conanrun")
