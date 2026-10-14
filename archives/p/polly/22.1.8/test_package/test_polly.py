#!/usr/bin/env python3
"""Polly packaged-consumer assertion.

Usage: test_polly.py <package_folder>

Loads the packaged LLVMPolly.so through the packaged opt and verifies that
Polly detects the SCoP in test_polly.ll. This covers:
  1. opt 22.1.8 loads LLVMPolly.so (plugin entry llvmGetPassPluginInfo resolves;
     no undefined symbol — the OHOS musl BIND_NOW/namespace risk E004/E088).
  2. print<polly-scops> reports a SCoP (core polyhedral functionality).
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: test_polly.py <package_folder>", file=sys.stderr)
        return 2

    pkg = sys.argv[1]
    opt = os.path.join(pkg, "bin", "opt")
    plugin = os.path.join(pkg, "lib", "LLVMPolly.so")
    here = os.path.dirname(os.path.abspath(__file__))
    test_ll = os.path.join(here, "test_polly.ll")

    for f, label in ((opt, "opt"), (plugin, "LLVMPolly.so"), (test_ll, "test_polly.ll")):
        if not os.path.isfile(f):
            print("missing consumer artifact: {} ({})".format(label, f), file=sys.stderr)
            return 1

    cmd = [
        opt,
        "-load-pass-plugin={}".format(plugin),
        "-passes=polly-custom<detect>",
        "-polly-print-detect",
        "-disable-output",
        test_ll,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out)

    if proc.returncode != 0:
        print("opt -load-pass-plugin failed rc={}".format(proc.returncode), file=sys.stderr)
        return proc.returncode or 1

    if "Scop" not in out and "scop" not in out:
        print("polly did not detect a Scop", file=sys.stderr)
        return 1

    print("POLLY SCOP DETECTION OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
