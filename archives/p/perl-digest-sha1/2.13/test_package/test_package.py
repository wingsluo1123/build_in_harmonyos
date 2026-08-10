#!/usr/bin/env python3
"""Test script for Digest::SHA1 package verification.
Verifies that the package contains valid ELF .so and the Perl module loads.

Usage: python3 test_package.py <pkg_folder>
"""
import sys
import os
import subprocess

MODULE = "Digest::SHA1"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_package.py <pkg_folder>", file=sys.stderr)
        sys.exit(1)

    pkg_folder = sys.argv[1]
    errors = []

    # Find .so file by walking the package folder
    so_path = None
    for root, dirs, files in os.walk(pkg_folder):
        for fn in files:
            if fn.endswith(".so"):
                so_path = os.path.join(root, fn)
                break
        if so_path:
            break

    if not so_path:
        errors.append("No .so file found in package")
    else:
        with open(so_path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                errors.append(f"{so_path} is not valid ELF (magic: {magic})")

    # Find .pm file matching the module name and determine PERL5LIB
    pm_path = None
    perl5lib = None
    module_rel = MODULE.replace("::", "/") + ".pm"
    for root, dirs, files in os.walk(pkg_folder):
        for fn in files:
            full_path = os.path.join(root, fn)
            if full_path.endswith("/" + module_rel):
                pm_path = full_path
                idx = full_path.rfind("/" + module_rel)
                perl5lib = full_path[:idx]
                break
    # Also check if .pm is directly in a directory (e.g., DBI.pm)
    if not pm_path:
        for root, dirs, files in os.walk(pkg_folder):
            for fn in files:
                if fn == module_rel:
                    pm_path = os.path.join(root, fn)
                    perl5lib = root
                    break
            if pm_path:
                break
    # Fallback: find any .pm file
    if not pm_path:
        for root, dirs, files in os.walk(pkg_folder):
            for fn in files:
                if fn.endswith(".pm"):
                    pm_path = os.path.join(root, fn)
                    break
            if pm_path:
                break

    if not pm_path:
        errors.append("No .pm file found in package")
    elif perl5lib:
        # Actually load the Perl module (R34: not just file existence check)
        env = dict(os.environ)
        env["PERL5LIB"] = perl5lib
        result = subprocess.run(
            ["perl", "-e", "use " + MODULE + "; print 'loaded'"],
            capture_output=True, text=True, env=env, timeout=10
        )
        if result.returncode != 0:
            errors.append(f"Failed to load Perl module {MODULE}: {result.stderr.strip()}")
    else:
        errors.append(f"Found .pm file but could not determine PERL5LIB: {pm_path}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: {MODULE} package verified - .so (ELF valid), .pm found, module loads")
    sys.exit(0)


if __name__ == "__main__":
    main()
