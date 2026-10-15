"""One installed-package CLI consumer; four saved Unicode/escape scenarios."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-folder", required=True, type=Path)
    options = parser.parse_args()
    if sys.flags.optimize:
        raise RuntimeError("Consumer assertions require optimization disabled")
    package = options.package_folder.resolve()
    site = package / "lib/python3.12/site-packages"
    sys.path.insert(0, str(site))
    import pawk
    module_file = Path(pawk.__file__).resolve()
    assert module_file == site / "pawk.py", (module_file, site)
    assert pawk.__version__ == "0.8.0", pawk.__version__
    wrapper = package / "bin/pawk"
    env = dict(os.environ, PYTHONPATH=str(site), PYTHONDONTWRITEBYTECODE="1",
               PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    cases = (
        ("unicode-F", ["-F", "汉", "repr(f)"], "a汉b\n", "['a', 'b']\n"),
        ("escaped-tab-F", ["-F", r"\t", "repr(f)"], "a\tb\n", "['a', 'b']\n"),
        ("unicode-O", ["-O", "é", "f"], "a b\n", "aéb\n"),
        ("unicode-L", ["-L", "汉", "l"], "a\nb\n", "a汉b汉"),
    )
    results = []
    for name, args, input_text, expected in cases:
        argv = [sys.executable, "-B", str(wrapper), "--strict"] + args
        result = subprocess.run(argv, input=input_text, text=True, encoding="utf-8",
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, check=False, timeout=30)
        item = {"name": name, "argv": argv, "stdin": input_text,
                "rc": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
                "expected": expected}
        print(json.dumps(item, ensure_ascii=False), flush=True)
        assert result.returncode == 0, item
        if result.stdout != expected:
            print("PAWK_UNICODE_DELIMITER_MISMATCH: " + json.dumps(item, ensure_ascii=False),
                  file=sys.stderr, flush=True)
        assert result.stdout == expected, item
        assert result.stderr == "", item
        results.append(name)
    print(json.dumps({"consumer_programs": 1, "scenarios": len(results),
                      "cli_calls": len(results), "functional_assertions": 3 * len(results),
                      "identity_assertions": 2, "module": str(module_file),
                      "module_sha256": hashlib.sha256(module_file.read_bytes()).hexdigest(),
                      "python": sys.version, "wrapper": str(wrapper),
                      "outcome": "PASS", "cases": results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
