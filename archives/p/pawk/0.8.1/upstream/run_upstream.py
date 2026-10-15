"""Invoke the nine untouched upstream assertions, never the benchmark __main__."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

TEST_NAMES = (
    "test_action_parse", "test_action_match", "test_action_match_negate",
    "test_integration_sum", "test_integration_match", "test_integration_negate_match",
    "test_integration_truth", "test_integration_multiple_actions",
    "test_integration_csv_empty_fields",
)
TEST_SHA256 = "6948770f9e70bd5641791decf3b387722639f6d7e6a1b243103c5ef8013fe49a"


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--module-folder", required=True, type=Path)
    args.add_argument("--tests-file", required=True, type=Path)
    options = args.parse_args()
    if sys.flags.optimize:
        raise RuntimeError("Upstream assert statements require optimization disabled")
    test_file = options.tests_file.resolve()
    source = test_file.read_bytes()
    if hashlib.sha256(source).hexdigest() != TEST_SHA256:
        raise RuntimeError("Pinned upstream test bytes changed")
    names = tuple(n.name for n in ast.parse(source).body
                  if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"))
    if names != TEST_NAMES:
        raise RuntimeError("Upstream test inventory changed")
    module_file = options.module_folder.resolve() / "pawk.py"
    sys.path.insert(0, str(module_file.parent))
    import pawk
    if Path(pawk.__file__).resolve() != module_file:
        raise RuntimeError("Tests imported a different pawk module")
    spec = importlib.util.spec_from_file_location("pawk_upstream_tests", test_file)
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    results = []
    for name in TEST_NAMES:
        try:
            getattr(tests, name)()
        except Exception as error:
            results.append({"name": name, "outcome": "FAIL",
                            "error": f"{type(error).__name__}: {error}"})
        else:
            results.append({"name": name, "outcome": "PASS"})
    failed = sum(result["outcome"] == "FAIL" for result in results)
    print(json.dumps({"runner": "direct invocation of original test functions; not pytest",
                      "python": sys.version, "module": str(module_file),
                      "module_sha256": hashlib.sha256(module_file.read_bytes()).hexdigest(),
                      "upstream_test_sha256": TEST_SHA256, "discovered": len(TEST_NAMES),
                      "executed": len(results), "passed": len(results) - failed,
                      "failed": failed, "skipped": 0, "results": results}, ensure_ascii=False))
    return int(failed != 0)


if __name__ == "__main__":
    sys.exit(main())
