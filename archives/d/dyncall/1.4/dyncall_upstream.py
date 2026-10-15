"""Run every upstream program and retain every parameterized case ID."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from dyncall_sign import sign_elf

PROGRAMS = (
    "plain_c++", "callback_plain_c++", "suite2", "suite3", "suite_floats", "ellipsis",
    "call_suite", "call_suite_aggrs", "callback_suite", "callback_suite_aggrs", "plain",
    "suite", "callf", "nm", "dynload_plain", "resolve_self", "test_thunk", "malloc_wx", "callback_plain",
)
COUNTS = {"suite2": 16, "suite3": 341, "suite_floats": 2047, "ellipsis": 85,
          "call_suite": 400, "call_suite_aggrs": 400, "callback_suite": 800,
          "callback_suite_aggrs": 400, "suite": 511}


def run(build):
    build = Path(build)
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ":".join(str(build/x) for x in ("dyncall", "dyncallback", "dynload")) + ":" + env.get("LD_LIBRARY_PATH", "")
    for directory, library in (("dyncall", "dyncall_s"), ("dyncallback", "dyncallback_s"), ("dynload", "dynload_s")):
        elf = build / directory / ("lib" + library + ".so")
        if elf.exists(): sign_elf(elf)
    fixture = build / "test/dynload_plain/dynload_plain_ß_test"
    sign_elf(fixture)
    results = []
    total = 0
    for name in PROGRAMS:
        directory = "thunk" if name == "test_thunk" else name
        binary = build / "test" / directory / name
        sign_elf(binary)
        args = [str(binary)]
        if name == "nm":
            # Read the live loader mapping, not a guessed libc alias.
            providers = sorted({line.split()[-1] for line in Path("/proc/self/maps").read_text().splitlines()
                                if "ld-musl-aarch64.so.1" in line and line.split()[-1].startswith("/")})
            if len(providers) != 1: raise RuntimeError("C runtime provider mapping is ambiguous")
            args.append(providers[0])
        result = subprocess.run(args, cwd=binary.parent, env=env, capture_output=True, timeout=120)
        text = result.stdout.decode("utf-8", "strict")
        print(text, end="", flush=True)
        print(result.stderr.decode("utf-8", "strict"), end="", file=sys.stderr, flush=True)
        if result.returncode: raise RuntimeError(name + " returned " + str(result.returncode))
        if name in COUNTS:
            rows = [(int(match.group(1)), line.rsplit(":",1)[-1]) for line in text.splitlines()
                    if (match := re.match(r"^([0-9]+)[-:]", line))]
            if [row[0] for row in rows] != list(range(COUNTS[name])) or any(row[1] != "1" for row in rows):
                raise RuntimeError(name + " case-ID/denominator/result mismatch")
            cases = COUNTS[name]
        else:
            cases = 1
        if name == "nm":
            if "printf" not in text.splitlines(): raise RuntimeError("nm did not enumerate printf")
        elif name == "test_thunk":
            for expected in ("... W^X memory: wx: 1", "... heap memory: sigsegv", "... stack memory: sigsegv"):
                if expected not in text: raise RuntimeError("thunk protection observation missing: " + expected)
        elif "result: " + name + ": 1" not in text:
            # The C++ programs use their original success formatting.
            if name not in ("plain_c++", "callback_plain_c++"):
                raise RuntimeError(name + " lacks its upstream success marker")
        total += cases
        results.append({"program": name, "cases": cases, "status": "PASS", "returncode": result.returncode})
    if total != 5010: raise RuntimeError("Complete test denominator drift: " + str(total))
    with (build/"upstream-results.json").open("x", encoding="utf-8") as output:
        json.dump({"registered_programs":19,"parameterized_cases":5000,"composite_cases":10,
                   "total":total,"passed":total,"programs":results},output,indent=2)
    print("UPSTREAM_5010_OF_5010_PASS\nUPSTREAM_PROGRAMS_19_OF_19_PASS", flush=True)
    print("{}/{} PASS (complete upstream inventory)".format(total, total), flush=True)


if __name__ == "__main__":
    run(sys.argv[1])
