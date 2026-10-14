#!/usr/bin/env python3
"""Conan test_package — asterisk-ldap 22.10.1 (R34 real artifact verification).

Two independent checks, both actually executed:

  1. static — `test_asterisk_ldap.py` parses the packaged module's ELF dynamic
     information with its own parser (program headers + PT_DYNAMIC + .dynsym,
     no binutils needed) and asserts it is an AArch64 shared object that binds
     OpenLDAP (DT_NEEDED libldap.so.2/liblber.so.2, the res_config_ldap LDAP API
     surface, OPENLDAP_2.200) and the Asterisk module ABI
     (ast_module_register/unregister, non-empty DT_INIT_ARRAY), with no
     build-machine RPATH leakage.

  2. dynamic (HarmonyOS) — `ldap_module_load.c` is linked against stubs for the
     Asterisk core API symbols (generated here from the module's own undefined
     symbol list) with -rdynamic, then dlopen()s the packaged module with
     RTLD_NOW. The module's constructor calls ast_module_register(), which the
     stub records; the test asserts one registration with a valid
     `struct ast_module_info` (name == res_config_ldap, load/unload present).
     RTLD_NOW makes success a proof that the OHOS loader resolves every
     dependency of the built module (libldap.so.2, liblber.so.2, libc).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run

# Symbols of the Asterisk core API that a loadable module resolves from the
# host process image (the asterisk binary is linked -rdynamic).
CORE_PREFIXES = ("ast_", "__ast_", "_ast_", "option_", "pbx_", "loader_", "engine_")


class AsteriskLdapTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return ccs.get("c") or "clang"

    def build(self):
        here = os.path.dirname(os.path.realpath(__file__))
        sys.path.insert(0, here)
        import elf_utils  # noqa: E402  (shipped next to this recipe)

        pkg = self.dependencies["asterisk-ldap"].package_folder
        module = os.path.join(pkg, "lib", "asterisk", "modules", "res_config_ldap.so")
        if not os.path.isfile(module):
            raise ConanInvalidConfiguration(f"module not found: {module}")

        info = elf_utils.parse(module)
        core_syms = sorted({
            name for name in info["undefined"]
            if name.startswith(CORE_PREFIXES)
        })

        stub = os.path.join(self.build_folder, "ldap_host_stub.c")
        with open(stub, "w", encoding="utf-8") as handle:
            handle.write("/* auto-generated: Asterisk core API stubs for the "
                         "module load test */\n#include <stddef.h>\n")
            handle.write("void *__ohos_test_module_info = 0;\n"
                         "int __ohos_test_register_calls = 0;\n")
            handle.write("void ast_module_register(const void *info)"
                         "{__ohos_test_module_info=(void*)info;"
                         "__ohos_test_register_calls++;}\n")
            handle.write("void ast_module_unregister(const void *info){(void)info;}\n")
            for name in core_syms:
                if name in ("ast_module_register", "ast_module_unregister"):
                    continue
                handle.write(f"void {name}(void) {{}}\n")

        cc = self._cc()
        driver = os.path.join(here, "ldap_module_load.c")
        out = os.path.join(self.build_folder, "ldap_module_load")
        self.run(f"{cc} -rdynamic -Wl,-E -o {out} {stub} {driver}")
        self._load_test = out
        self._module = module

    def test(self):
        if not can_run(self):
            return
        here = os.path.dirname(os.path.realpath(__file__))
        pkg = self.dependencies["asterisk-ldap"].package_folder
        self.run(f"{sys.executable} {os.path.join(here, 'test_asterisk_ldap.py')} {pkg}")
        self.run(f"{self._load_test} {self._module}", env="conanrun")
        self.output.info("asterisk-ldap consumer test passed")
