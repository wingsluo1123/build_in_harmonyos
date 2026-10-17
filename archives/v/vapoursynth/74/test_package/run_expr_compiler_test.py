#!/usr/bin/env python3
"""Run VapourSynth's ExprDebugger harness on non-Windows targets."""

import importlib.util
import os
import subprocess
import sys


def _load_module(path):
    spec = importlib.util.spec_from_file_location("vapoursynth_expr_compiler_test", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load test module from {}".format(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_expr_compiler_test.py COMPILER_TEST EXPR_DEBUGGER")

    test_path = os.path.realpath(sys.argv[1])
    expr_debugger = os.path.realpath(sys.argv[2])
    test_dir = os.path.dirname(test_path)
    module = _load_module(test_path)
    module.EXPR_DEBUGGER_PATH = expr_debugger

    original_check_output = subprocess.check_output

    def check_output_without_creationflags(*args, **kwargs):
        kwargs.pop("creationflags", None)
        return original_check_output(*args, **kwargs)

    subprocess.check_output = check_output_without_creationflags
    old_cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(expr_debugger))
        module.main()
    finally:
        os.chdir(old_cwd)
        subprocess.check_output = original_check_output

    total = 0
    for filename in module.TEST_CASES:
        with open(os.path.join(test_dir, filename), encoding="utf-8") as handle:
            total += sum(1 for line in handle if line.strip())
    print("expr_compiler compiler_test.py passed: {} expressions".format(total))


if __name__ == "__main__":
    main()
