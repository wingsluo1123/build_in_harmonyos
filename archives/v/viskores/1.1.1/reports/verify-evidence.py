#!/usr/bin/env python3
"""Verify original Git evidence and its binding to the current recipe."""
import argparse
import csv
import functools
import hashlib
import json
import pathlib
import subprocess
import xml.etree.ElementTree as ET

COMMIT = "e65190186b41e1b21e069649144a1078d8eb3208"
PREFIX = "archives/v/viskores/1.1.1"
root = pathlib.Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--extract", type=pathlib.Path, help="Export checked originals to a NEW directory")
args = parser.parse_args()
repo = pathlib.Path(subprocess.check_output(
    ["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip())
subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", COMMIT, "HEAD"], check=True)


@functools.lru_cache(maxsize=None)
def original(name):
    return subprocess.check_output([
        "git", "-C", str(repo), "cat-file", "blob", f"{COMMIT}:{PREFIX}/reports/{name}"])


with (root/"evidence-index.tsv").open(encoding="utf-8", newline="") as stream:
    rows = list(csv.DictReader(stream, delimiter="\t"))
assert len(rows) == 84 and len({row["path"] for row in rows}) == 84
for row in rows:
    data = original(row["path"])
    assert len(data) == int(row["bytes"]), row["path"]
    assert hashlib.sha256(data).hexdigest() == row["sha256"], row["path"]

expected = (("baseline/upstream-tests.xml", (366, 5, 0)),
            ("independent-native-upstream-tests.xml", (371, 0, 0)),
            ("independent-native-consumer-tests.xml", (1, 0, 0)),
            ("upstream-tests.xml", (371, 0, 0)),
            ("consumer-tests.xml", (1, 0, 0)),
            ("relocation-consumer-tests.xml", (1, 0, 0)))
for name, counts in expected:
    cases = list(ET.fromstring(original(name)).iter("testcase"))
    failed = sum(case.find("failure") is not None or case.find("error") is not None for case in cases)
    skipped = sum(case.find("skipped") is not None for case in cases)
    assert (len(cases)-failed-skipped, failed, skipped) == counts, name
    assert len({case.get("name") for case in cases}) == len(cases), name
    print(name, "PASS/FAIL/SKIP", counts)
inventory = json.loads(original("upstream-inventory.json"))
actual = {case.get("name") for case in ET.fromstring(original("upstream-tests.xml")).iter("testcase")}
assert {case["name"] for case in inventory["tests"]} == actual
for name in ("native-create-output.txt", "relocation-output.txt"):
    assert "CONSUMER_RESULT=13/13" in original(name).decode()
binding = json.loads(original("native-result.json"))["input_sha256"]
assert len(binding) == 7
for name, digest in binding.items():
    assert hashlib.sha256((repo/PREFIX/name).read_bytes()).hexdigest() == digest, name
assert (root/"native-result.json").read_bytes() == original("native-result.json")

if args.extract:
    target = args.extract.resolve()
    target.mkdir(parents=True, exist_ok=False)
    for row in rows:
        destination = target/row["path"]
        assert destination.resolve().is_relative_to(target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(original(row["path"]))
    print("Exported original evidence:", target)
print("Verified 84 original hashes, six XML outcomes, registration identity and seven current inputs")
