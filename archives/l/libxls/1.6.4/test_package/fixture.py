"""Restore the unchanged upstream XLS fixture from strict text transport."""
import base64
import hashlib
import json
from pathlib import Path
import sys


EXPECTED = {
    "schema": "libxls-upstream-fixture-v1",
    "upstream_path": "test/files/test2.xls",
    "encoded": "test2.xls.b64",
    "decoded": "test2.xls",
    "bytes": 35840,
    "sha256": "df7d4e07b72284c17ecca138412b48d4217041e5f81a7c297b331c546a20604a",
}


def restore(source, destination):
    source, destination = Path(source), Path(destination)
    manifest = source / "fixture-manifest.json"
    encoded = source / EXPECTED["encoded"]
    if any(p.is_symlink() for p in (manifest, encoded, destination)):
        raise RuntimeError("linked fixture path")
    if json.loads(manifest.read_text(encoding="utf-8")) != EXPECTED:
        raise RuntimeError("fixture manifest drift")
    text = encoded.read_bytes()
    raw = base64.b64decode(text.replace(b"\n", b""), validate=True)
    canonical = base64.b64encode(raw)
    canonical = b"\n".join(canonical[i:i+76] for i in range(0, len(canonical), 76)) + b"\n"
    if text != canonical or len(raw) != EXPECTED["bytes"] or hashlib.sha256(raw).hexdigest() != EXPECTED["sha256"]:
        raise RuntimeError("fixture canonical bytes/hash mismatch")
    for parent in (destination, *destination.parents):
        if parent.is_symlink():
            raise RuntimeError("redirected fixture output")
    destination.mkdir(exist_ok=True)
    output = destination / EXPECTED["decoded"]
    if any(p.name != EXPECTED["decoded"] or not p.is_file() or p.is_symlink() for p in destination.iterdir()):
        raise RuntimeError("foreign fixture output")
    if not output.exists():
        with output.open("xb") as stream:
            stream.write(raw)
    if output.is_symlink() or output.read_bytes() != raw:
        raise RuntimeError("decoded fixture drift")
    return output


if __name__ == "__main__":
    output = restore(sys.argv[1], sys.argv[2])
    print("FIXTURE_EXACT_BYTES_PASS", EXPECTED["bytes"], EXPECTED["sha256"])
