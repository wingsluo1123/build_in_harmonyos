"""Run the CUnit executables built by SPDK's test/unit Makefiles.

The upstream shell driver also initializes Linux hardware test infrastructure.
These unit executables use SPDK mocks and can be run directly on OHOS.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    root = Path(sys.argv[1]).resolve()
    output = root / "unit-test-results"
    output.mkdir(exist_ok=True)
    executables = sorted(p for p in (root / "test/unit").rglob("*_ut")
                         if p.is_file() and os.access(p, os.X_OK))
    # histogram_data.h has a different basename but the same _ut suffix.
    if not executables:
        raise RuntimeError("No upstream CUnit executables were built")
    inventory = []
    for source in sorted((root / "test/unit").rglob("*_ut.c")):
        if not source.is_file():
            continue
        sites = len(re.findall(r"\b(?:CU_ADD_TEST|CU_add_test)\s*\(",
                               source.read_text(encoding="utf-8")))
        inventory.append({"source": source.relative_to(root).as_posix(),
                          "registration_sites": sites,
                          "built": source.with_suffix("") in executables})
    (output / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    summary = re.compile(r"^\s*tests\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", re.M)
    results = []
    for exe in executables:
        relative = exe.relative_to(root).as_posix()
        log = output / (relative.replace("/", "__") + ".log")
        workdir = output / "work" / relative.replace("/", "__")
        workdir.mkdir(parents=True, exist_ok=True)
        timed_out = False
        with log.open("wb") as stream:
            try:
                process = subprocess.run([str(exe)], cwd=workdir, stdout=stream,
                                         stderr=subprocess.STDOUT, timeout=600)
                rc = process.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                rc = 124
        text = log.read_text(encoding="utf-8", errors="replace")
        rows = [tuple(map(int, row)) for row in summary.findall(text)]
        item = {"executable": relative, "returncode": rc, "timeout": timed_out,
                "discovered": sum(row[0] for row in rows),
                "executed": sum(row[1] for row in rows),
                "passed": sum(row[2] for row in rows),
                "failed": sum(row[3] for row in rows),
                "skipped": sum(row[4] for row in rows)}
        item["success"] = (rc == 0 and bool(rows) and item["failed"] == 0
                           and item["skipped"] == 0
                           and item["executed"] == item["discovered"])
        results.append(item)
        print("SPDK_UNIT_PROGRAM=" + json.dumps(item), flush=True)
        if not item["success"]:
            print(text[-6000:], flush=True)
        # Preserve partial results if a later executable crashes or times out.
        (output / "programs.json").write_text(json.dumps(results, indent=2) + "\n")
    totals = {key: sum(r[key] for r in results)
              for key in ("discovered", "executed", "passed", "failed", "skipped")}
    totals.update(status="passed" if all(r["success"] for r in results) else "failed",
                  programs=len(results), failed_programs=sum(not r["success"] for r in results),
                  command="run_unit_tests.py (upstream CUnit assertions; unit environment mocks)")
    totals["source_registration_sites"] = sum(r["registration_sites"] for r in inventory)
    totals["unbuilt_programs"] = [r for r in inventory if not r["built"]]
    config = (root / "include/spdk/config.h").read_text(encoding="utf-8")
    totals["conditional_exclusions"] = []
    if not re.search(r"^#define\s+SPDK_CONFIG_ISAL_CRYPTO\b", config, re.M):
        totals["conditional_exclusions"].append({
            "program": "test/unit/lib/accel/accel.c/accel_ut",
            "case": "test_sequence_dix",
            "reason": "ISA-L crypto disabled; software AES-XTS key creation returns ENOTSUP",
        })
    totals["baseline_registered_cases"] = totals["discovered"] + len(totals["conditional_exclusions"])
    (output / "summary.json").write_text(json.dumps(totals, indent=2) + "\n")
    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(totals), flush=True)
    return 0 if totals["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
