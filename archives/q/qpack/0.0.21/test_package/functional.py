"""Run the original nine methods and a narrow consumer against the real C package."""
import hashlib
import importlib.machinery
import json
from pathlib import Path
import sys
import sysconfig
import unittest


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    package = Path(sys.argv[1]).resolve()
    upstream = Path(sys.argv[2]).resolve()
    report = Path(sys.argv[3]).resolve()
    # The Conan package is selected before import; no source-tree or fallback substitution.
    sys.path.insert(0, str(package / "lib/python"))
    import qpack
    import qpack._qpack as native
    from qpack import fallback

    native_path = Path(native.__file__).resolve()
    assert native_path.is_relative_to(package)
    assert isinstance(native.__loader__, importlib.machinery.ExtensionFileLoader)
    assert qpack.unpackb is native._unpackb and qpack.packb is native._packb
    assert qpack.__version__ == "0.0.21"
    assert sys.version_info[:3] == (3, 12, 9), sys.version
    assert sys.flags.optimize == 0
    original_sha = "209a077bfbdf4f152ad7dca05cfcf643167d2c1f111bf91189a127f75c309f6a"
    assert sha256(upstream / "qpack_test.py") == original_sha
    data = {
        "python": sys.version, "executable": sys.executable,
        "prefix": sys.prefix, "soabi": sysconfig.get_config_var("SOABI"),
        "extension": str(native_path), "extension_sha256": sha256(native_path),
        "public_unpackb_module": qpack.unpackb.__module__,
        "upstream_test_sha256": original_sha,
        "count_unit": "upstream unittest methods and added consumer groups; alias observations are not test methods",
        "added_consumer_programs": 1, "groups": [],
    }
    report.parent.mkdir(parents=True, exist_ok=True)

    def save():
        report.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    suite = unittest.defaultTestLoader.discover(str(upstream), pattern="qpack_test.py")
    assert suite.countTestCases() == 9, suite.countTestCases()
    with report.with_suffix(".upstream.txt").open("w", encoding="utf-8") as output:
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    data["upstream"] = {
        "discovered": 9, "run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skipped": len(result.skipped),
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
    }
    save()

    def group(name, operation):
        row = {"name": name, "observations": []}
        try:
            operation(row["observations"])
        except Exception as exc:
            row.update(passed=False, error_type=type(exc).__name__, error=str(exc))
        else:
            row["passed"] = True
        data["groups"].append(row)
        save()

    def aliases(observations, names, payload):
        for name in names:
            actual = qpack.unpackb(payload, decode=name)
            reference = fallback.unpackb(payload, decode=name)
            observations.append({"alias": name, "payload_hex": payload.hex(),
                                 "c_value": actual, "fallback_value": reference})
            assert type(actual) is str and actual == reference == "\u00ff"

    group("utf8_aliases_non_ascii", lambda rows: aliases(
        rows, ("utf-8", "UTF-8", "Utf-8", "utf8", "UTF8", "Utf8"), b"\x82\xc3\xbf"))
    group("latin1_aliases_non_ascii", lambda rows: aliases(
        rows, ("latin-1", "LATIN-1", "Latin-1", "latin1", "LATIN1", "Latin1"), b"\x81\xff"))

    def default_bytes(rows):
        for payload, expected in ((b"\x81\xff", b"\xff"), (b"\x82\xc3\xbf", b"\xc3\xbf")):
            actual, reference = qpack.unpackb(payload), fallback.unpackb(payload)
            rows.append({"payload_hex": payload.hex(), "c_hex": actual.hex(), "fallback_hex": reference.hex()})
            assert type(actual) is bytes and actual == reference == expected
    group("default_bytes", default_bytes)

    def ignore_errors(rows):
        payload = b"\x81\xff"
        errors = []
        for backend in (qpack, fallback):
            try:
                backend.unpackb(payload, decode="utf8")
            except ValueError as exc:
                errors.append(type(exc).__name__)
            else:
                raise AssertionError("invalid UTF8 unexpectedly decoded")
            actual = backend.unpackb(payload, decode="utf8", ignore_decode_errors=True)
            valid = backend.unpackb(b"\x82\xc3\xbf", decode="utf8", ignore_decode_errors=True)
            rows.append({"backend": backend.__name__, "strict_error": errors[-1],
                         "ignored_hex": actual.hex(), "valid_value": valid})
            assert type(actual) is bytes and actual == b"\xff" and valid == "\u00ff"
        assert errors[0] == errors[1]
    group("utf8_strict_and_ignore_errors", ignore_errors)
    data["added_groups"] = {"run": len(data["groups"]),
                             "passed": sum(row["passed"] for row in data["groups"]),
                             "failed": sum(not row["passed"] for row in data["groups"])}
    save()
    print(json.dumps({"upstream": data["upstream"], "added_groups": data["added_groups"],
                      "extension": str(native_path), "report": str(report)}))
    return 0 if result.wasSuccessful() and not result.skipped and all(row["passed"] for row in data["groups"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
