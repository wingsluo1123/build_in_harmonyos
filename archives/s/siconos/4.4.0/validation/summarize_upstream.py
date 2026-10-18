#!/usr/bin/env python3
"""Preserve real CTest outcomes and reject failures beyond the recorded baseline.

Two unchanged Lsodar reference comparisons also fail on the pinned upstream
Linux/GCC/GFortran build. They remain FAIL in every report. This package's
build policy permits only those exact methods, with their expected case counts
and zero exceptions; it does not turn their results into PASS or XFAIL.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def summarize(raw, inventory, policy, exit_code, processes):
    root = ET.fromstring(raw)
    cases = root.findall(".//testcase")
    names = [case.attrib["name"] for case in cases]
    registered = [test["name"] for test in inventory["tests"]]
    if len(names) != len(set(names)) or set(names) != set(registered):
        raise ValueError("JUnit cases do not match the actual CTest inventory")
    if len(cases) != policy["expected_ctest_groups"]:
        raise ValueError("Changed CTest inventory requires a new audit")
    if set(names) != set(policy["ctest_groups"]) or set(processes) != set(names):
        raise ValueError("Changed group identities or missing process outcomes")
    groups, solver_totals = [], Counter()
    cpp_groups = cpp_executed = cpp_failed = skipped = 0
    baseline_failures = []
    for case in cases:
        name = case.attrib["name"]
        output = case.findtext("system-out", "")
        skip = case.find("skipped") is not None
        failed = case.find("failure") is not None or case.find("error") is not None
        process = processes[name]
        if process["completion"] != "Completed":
            raise ValueError(f"Incomplete/abnormal child process: {name}: {process}")
        if failed:
            failure = case.find("failure")
            if (case.find("error") is not None or failure is None or
                    failure.attrib.get("message", "") not in ("", "Failed") or failure.attrib.get("type", "") or
                    process["status"] != "failed" or process["exit_code"] != "Failed" or
                    process["exit_value"] != "1"):
                raise ValueError(f"Nonordinary child failure: {name}: {process}")
        elif process["status"] != "passed" or process["exit_value"] not in (None, "0"):
            raise ValueError(f"Nonzero/abnormal supposedly passed process: {name}: {process}")
        skipped += int(skip)
        result = re.search(r"Run:\s+(\d+)\s+Failures:\s+(\d+)\s+Errors:\s+(\d+)", output)
        if result:
            cpp = dict(zip(("executed", "failures", "errors"), map(int, result.groups())))
        else:
            result = re.search(r"OK\s*\(\s*(\d+)\s+tests?\s*\)", output)
            cpp = {"executed": int(result[1]), "failures": 0, "errors": 0} if result else None
        methods = re.findall(r"\d+\) test: ([\w:]+) \(([FE])\)", output)
        expected_cpp = policy["cppunit_cases"].get(name)
        if (cpp is None) != (expected_cpp is None) or (cpp and cpp["executed"] != expected_cpp):
            raise ValueError(f"Missing/changed CppUnit group cases: {name}")
        if cpp:
            if not cpp["executed"]:
                raise ValueError(f"Empty CppUnit group: {name}")
            cpp_groups += 1
            cpp_executed += cpp["executed"]
            cpp_failed += cpp["failures"] + cpp["errors"]
            if bool(cpp["failures"] + cpp["errors"]) != failed:
                raise ValueError(f"CppUnit/CTest result mismatch: {name}")
        known = policy["baseline_reference_failures"].get(name)
        reference_observations = []
        if known and (not cpp or cpp["executed"] != known["executed"]):
            raise ValueError(f"Missing/changed CppUnit case summary: {name}")
        if known:
            blocks = re.findall(r"Comparison with reference file (\S+)\n(.*?)"
                                r"------- Integration done -------([01])", output, re.S)
            expected = known["reference_comparisons"]
            if len(blocks) != len(expected):
                raise ValueError(f"Missing/repeated reference comparisons: {name}")
            reference_failures = []
            for (filename, block, flag), check in zip(blocks, expected):
                if filename != check["file"]:
                    raise ValueError(f"Changed reference comparison order: {name}")
                lines = re.findall(r"^Error =\s*(.*?)\s*$", block, re.M)
                errors = [float(value) for value in lines]
                expected_lines = 1 if flag == "1" else 2
                if (len(errors) != expected_lines or len(set(errors)) != 1 or
                        any(not math.isfinite(value) or value < 0 for value in errors) or
                        max(errors) > known["max_reported_reference_difference"] or
                        (flag == "0") != (errors[0] > known["original_tolerance"])):
                    raise ValueError(f"Invalid/nonfinite reference result: {name}/{check['method']}")
                if flag == "0":
                    reference_failures.append(check["method"])
                reference_observations.append({"method": check["method"], "file": filename,
                                               "difference": errors[0], "tolerance": known["original_tolerance"],
                                               "original_reference_pass": flag == "1"})
            if sorted(reference_failures) != sorted(method for method, _ in methods):
                raise ValueError(f"Reference/C++ assertion result mismatch: {name}")
        if failed:
            if (not known or not cpp or cpp["errors"] or
                    cpp["failures"] != len(known["methods"]) or
                    sorted(methods) != sorted((method, "F") for method in known["methods"])):
                raise ValueError(f"New, exceptional, or changed upstream failure: {name}: {methods}")
            baseline_failures.extend(method for method, _ in methods)
        entries = re.findall(r"SICONOS_NUMERICS_RESULT id=(\d+) status=(\w+)", output)
        statuses = Counter(status for _, status in entries)
        if len(entries) != policy["solver_collection_cases"].get(name, 0):
            raise ValueError(f"Missing/changed solver collection count: {name}")
        if entries:
            ids = [int(index) for index, _ in entries]
            if sorted(ids) != list(range(len(ids))):
                raise ValueError(f"Missing or repeated solver collection cases: {name}")
            if set(statuses) - {"PASS", "FAIL", "XFAIL", "XPASS", "UNSTABLE_PASS", "UNSTABLE_FAIL"}:
                raise ValueError(f"Unknown solver result: {name}")
            if statuses["FAIL"]:
                raise ValueError(f"Unexpected solver collection failure: {name}")
        elif "_COLLECTION" in name:
            raise ValueError(f"Missing solver collection diagnostics: {name}")
        solver_totals.update(statuses)
        groups.append({"name": name, "status": "skipped" if skip else "fail" if failed else "pass",
                       "cppunit": cpp, "solver_collection_cases": dict(statuses),
                       "failed_methods": methods,
                       "reference_comparisons": reference_observations,
                       "process": process,
                       "output_sha256": hashlib.sha256(output.encode()).hexdigest()})
    failed = sum(group["status"] == "fail" for group in groups)
    if skipped or (exit_code != (8 if failed else 0)):
        raise ValueError(f"Skipped/abnormal CTest execution: {exit_code=}, {skipped=}")
    if (cpp_groups, cpp_executed) != (policy["expected_cppunit_groups"], policy["expected_cppunit_cases"]):
        raise ValueError(f"Missing CppUnit executions: {cpp_groups=}, {cpp_executed=}")
    result = {"framework": "CTest", "unit": "registered nonempty test group",
              "status": "partial" if failed else "pass", "discovered": len(cases),
              "executed": len(cases)-skipped, "passed": len(cases)-skipped-failed,
              "failed": failed, "skipped": skipped, "ctest_exit_code": exit_code,
              "baseline_reproduced_failed_methods": baseline_failures,
              "cppunit": {"groups": cpp_groups, "executed": cpp_executed,
                          "passed": cpp_executed-cpp_failed, "failed": cpp_failed},
              "solver_collections": dict(solver_totals),
              "raw_junit_sha256": hashlib.sha256(raw).hexdigest(), "groups": groups}
    # Compact public JUnit: preserve each original failure/skip/status; bind the
    # omitted verbose output by digest. The complete raw file remains in build/.
    for case, group in zip(cases, groups):
        for element in list(case):
            if element.tag == "system-out":
                case.remove(element)
        properties = ET.SubElement(case, "properties")
        ET.SubElement(properties, "property", name="original_output_sha256", value=group["output_sha256"])
        if group["failed_methods"]:
            ET.SubElement(case, "system-out").text = "\n".join(method for method, _ in group["failed_methods"])
    return result, ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--ctest-exit-code", type=int, required=True)
    args = parser.parse_args()
    policy = json.loads((Path(__file__).parent / "reference-policy.json").read_text())
    tag = (args.build / "Testing/TAG").read_text().splitlines()[0]
    dashboard_bytes = (args.build / "Testing" / tag / "Test.xml").read_bytes()
    processes = {}
    for test in ET.fromstring(dashboard_bytes).findall(".//Testing/Test"):
        values = {measurement.attrib["name"]: measurement.findtext("Value")
                  for measurement in test.findall("Results/NamedMeasurement")}
        name = test.findtext("Name")
        if name in processes:
            raise ValueError(f"Repeated dashboard process: {name}")
        processes[name] = {"status": test.attrib["Status"], "exit_code": values.get("Exit Code"),
                           "exit_value": values.get("Exit Value"), "completion": values.get("Completion Status")}
    result, compact = summarize((args.build / "upstream-raw.xml").read_bytes(),
                                json.loads((args.build / "upstream-inventory.json").read_text()),
                                policy, args.ctest_exit_code, processes)
    result["dashboard_sha256"] = hashlib.sha256(dashboard_bytes).hexdigest()
    (args.build / "upstream-results.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.build / "upstream-results.xml").write_bytes(compact)
    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({key: value for key, value in result.items() if key != "groups"}))
    if result["failed"]:
        print("UPSTREAM_REFERENCE_FAILURES_RETAINED_AS_FAIL=" + json.dumps(result["baseline_reproduced_failed_methods"]))


if __name__ == "__main__":
    main()
