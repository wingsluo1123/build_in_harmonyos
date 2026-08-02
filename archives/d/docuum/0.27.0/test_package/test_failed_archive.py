import pathlib
import sys


if len(sys.argv) != 2:
    raise SystemExit("usage: test_failed_archive.py <package_folder>")

package_folder = pathlib.Path(sys.argv[1])
record_folder = package_folder / "share" / "docuum"
manifest = (record_folder / "manifest.yaml").read_text(encoding="utf-8")
notes = (record_folder / "notes.md").read_text(encoding="utf-8")

assert "status: failed" in manifest
assert "failure_reason:" in manifest
assert "Rust" in manifest or "Cargo" in manifest or "cargo" in manifest
assert "Rust" in notes or "Cargo" in notes or "cargo" in notes
assert "OHOS" in notes

print("PASS: docuum failed adaptation record is complete")
