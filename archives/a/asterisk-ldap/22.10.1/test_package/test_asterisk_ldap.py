#!/usr/bin/env python3
"""Static verification of the packaged asterisk-ldap module (no external tools).

Checks the ELF dynamic information of lib/asterisk/modules/res_config_ldap.so:

  1. ELF64 LE, e_machine = AArch64, e_type = ET_DYN (shared object);
  2. DT_NEEDED contains libldap.so.2 and liblber.so.2 (OpenLDAP binding);
  3. undefined dynamic symbols contain the OpenLDAP API surface that
     res_config_ldap.c actually uses (ldap_*, ber_free);
  4. undefined dynamic symbols contain the Asterisk module ABI entry points
     ast_module_register / ast_module_unregister;
  5. DT_INIT_ARRAY is present and non-empty — the module self-registers through
     a constructor (this is how the Asterisk loader discovers it);
  6. no DT_RPATH / DT_RUNPATH — the build-machine private prefix must not leak
     into the shipped artifact;
  7. the OpenLDAP ABI version tag OPENLDAP_2.200 is bound (2.6.x soname ABI).

Usage: python3 test_asterisk_ldap.py <package_folder>
"""
import os
import sys

import elf_utils

MODULE_REL = os.path.join("lib", "asterisk", "modules", "res_config_ldap.so")

EXPECTED_NEEDED = {"libldap.so.2", "liblber.so.2"}
EXPECTED_LDAP_API = {
    "ldap_initialize",
    "ldap_set_option",
    "ldap_sasl_bind_s",
    "ldap_search_ext_s",
    "ldap_modify_ext_s",
    "ldap_unbind_ext_s",
    "ldap_msgfree",
    "ber_free",
}
EXPECTED_ASTERISK_ABI = {"ast_module_register", "ast_module_unregister"}

FAILURES = []
CHECKS = [0]


def check(name, ok, detail=""):
    CHECKS[0] += 1
    if ok:
        print(f"[ok]   {name}")
        return True
    print(f"[fail] {name}: {detail}")
    FAILURES.append(name)
    return False


def main():
    pkg = sys.argv[1]
    module = os.path.join(pkg, MODULE_REL)
    check("module packaged at lib/asterisk/modules/res_config_ldap.so",
          os.path.isfile(module), module)
    if not os.path.isfile(module):
        return 1

    info = elf_utils.parse(module)

    check("ELF header: AArch64 shared object (ET_DYN)",
          info["e_type"] == elf_utils.ET_DYN
          and info["e_machine"] == elf_utils.EM_AARCH64,
          f"e_type={info['e_type']} e_machine={info['e_machine']}")

    missing = EXPECTED_NEEDED - set(info["needed"])
    check("DT_NEEDED contains libldap.so.2 and liblber.so.2",
          not missing, f"missing {sorted(missing)}; have {info['needed']}")

    undef = set(info["undefined"])
    missing = EXPECTED_LDAP_API - undef
    check("binds the OpenLDAP API used by res_config_ldap (%d syms)"
          % len(EXPECTED_LDAP_API), not missing,
          f"missing {sorted(missing)}")

    missing = EXPECTED_ASTERISK_ABI - undef
    check("binds the Asterisk module ABI (ast_module_register/unregister)",
          not missing, f"missing {sorted(missing)}")

    check("DT_INIT_ARRAY present and non-empty (module self-registration)",
          bool(info["init_array"]) and info["init_array_sz"] > 0,
          f"init_array={info['init_array']} size={info['init_array_sz']}")

    check("no DT_RPATH/DT_RUNPATH (no build-machine path leakage)",
          not info["rpath"] and not info["runpath"],
          f"rpath={info['rpath']} runpath={info['runpath']}")

    check("OpenLDAP ABI version OPENLDAP_2.200 is bound",
          b"OPENLDAP_2.200" in info["blob"])

    print("-" * 64)
    print(f"static checks: {CHECKS[0]}")
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): " + ", ".join(FAILURES))
        return 1
    print("STATIC CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
