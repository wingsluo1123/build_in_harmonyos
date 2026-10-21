"""Execute the unchanged standalone Asio Automake test inventory without bootstrap tools."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def inventory(path, features):
    variables = {}
    stack = [True]
    logical = path.read_text(encoding="utf-8").replace("\\\n", " ")
    for raw in logical.splitlines():
        line = raw.strip()
        if line.startswith("if "):
            name = line[3:].strip()
            negate = name.startswith("!")
            key = name[1:] if negate else name
            if key not in features:
                raise RuntimeError("Unknown upstream condition: " + name)
            stack.append(stack[-1] and (not features[key] if negate else features[key]))
        elif line == "endif":
            if len(stack) == 1:
                raise RuntimeError("Unbalanced upstream condition")
            stack.pop()
        elif line == "else":
            if len(stack) < 2:
                raise RuntimeError("Unexpected upstream else")
            stack[-1] = stack[-2] and not stack[-1]
        elif stack[-1]:
            match = re.fullmatch(r"([A-Za-z0-9_]+)\s*(\+?=)\s*(.*)", line)
            if match:
                name, operator, value = match.groups()
                words = value.split()
                if operator == "=":
                    variables[name] = words
                else:
                    variables.setdefault(name, []).extend(words)
    if len(stack) != 1:
        raise RuntimeError("Unclosed upstream condition")
    tests = variables.get("TESTS", [])
    if tests == ["$(check_PROGRAMS)"]:
        tests = variables.get("check_PROGRAMS", [])
    programs = variables.get("check_PROGRAMS", [])
    if not tests or len(set(tests)) != len(tests) or not set(tests).issubset(programs):
        raise RuntimeError("Upstream test/build inventory mismatch")
    result = []
    for name in programs:
        key = re.sub(r"[^A-Za-z0-9_]", "_", name) + "_SOURCES"
        sources = variables.get(key)
        if not sources or any("$" in value or not value.endswith(".cpp") for value in sources):
            raise RuntimeError("Unsupported upstream source mapping: " + name)
        paths = [path.parent / value for value in sources]
        if any(not value.is_file() for value in paths):
            raise RuntimeError("Upstream source absent: " + name)
        result.append((name, paths, name in tests))
    return result


def main():
    source, build, launcher = map(Path, sys.argv[1:4])
    compiler = sys.argv[4]
    standard = int(sys.argv[5])
    if standard < 11:
        raise RuntimeError("Standalone upstream tests require C++11 or later")
    features = {"STANDALONE": True, "SEPARATE_COMPILATION": False,
                "HAVE_BOOST_COROUTINE": False, "HAVE_BOOST_SYSTEM": False,
                "HAVE_OPENSSL": False, "WINDOWS_TARGET": False,
                "HAVE_CXX11": standard >= 11, "HAVE_CXX14": standard >= 14,
                "HAVE_CXX17": standard >= 17, "HAVE_CXX20": standard >= 20,
                "HAVE_COROUTINES": False}
    if standard >= 20:
        raise RuntimeError("C++20 requires an explicit coroutine capability probe; not silently disabled")
    groups = [("unit", source / "src/tests/Makefile.am"),
              ("properties", source / "src/tests/properties/Makefile.am")]
    tests = [(group + "/" + name, paths, run) for group, makefile in groups
             for name, paths, run in inventory(makefile, features)]
    if len({name for name, _, _ in tests}) != len(tests):
        raise RuntimeError("Duplicate upstream test identity")
    build.mkdir(parents=True, exist_ok=True)
    identity = {"scope": "full upstream standalone C++17 configuration; Boost stackful and optional SSL not enabled",
                "features": features, "count": sum(run for _, _, run in tests), "compiled_programs": len(tests),
                "tests": [{"id": name, "sources": [p.relative_to(source).as_posix() for p in paths],
                           "source_sha256": [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
                           "runtime_registered": run}
                          for name, paths, run in tests]}
    with (build / "upstream-inventory.json").open("x") as stream:
        json.dump(identity, stream, indent=2)
    results = []
    for index, (name, paths, run) in enumerate(tests, 1):
        binary = build / "bin" / name
        binary.parent.mkdir(parents=True, exist_ok=True)
        args = [sys.executable, str(launcher), str(build), compiler,
                "-std=c++" + str(standard), "-stdlib=libc++", "-pthread", "-O0",
                "-DASIO_STANDALONE", "-DASIO_DISABLE_DEPRECATED_MSG", "-I" + str(source / "include"),
                *map(str, paths), "-o", str(binary)]
        log = build / ("test-" + str(index) + ".log")
        print(f"UPSTREAM_BEGIN {index}/{len(tests)} {name}", flush=True)
        with log.open("xb", buffering=0) as stream:
            stream.write(("COMPILE " + shlex.join(args) + "\n").encode())
            compiled = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
            if compiled.returncode:
                raise RuntimeError("Upstream compilation failed: " + name + "; " + log.read_text(errors="replace")[-8000:])
            stream.write(("BINARY_SHA256 " + hashlib.sha256(binary.read_bytes()).hexdigest() + "\n").encode())
            returncode = subprocess.run([str(binary)], stdout=stream, stderr=subprocess.STDOUT, timeout=90).returncode if run else 0
        record = {"id": name, "runtime_registered": run, "result": "PASS" if returncode == 0 else "FAIL",
                  "returncode": returncode, "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                  "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
        results.append(record)
        with (build / ("result-" + str(index) + ".json")).open("x") as stream:
            json.dump(record, stream, sort_keys=True)
        print("UPSTREAM_RESULT", name, record["result"], flush=True)
        if returncode:
            raise RuntimeError("Upstream test failed: " + name + "; " + log.read_text(errors="replace")[-8000:])
    with (build / "upstream-results.json").open("x") as stream:
        json.dump(results, stream, indent=2)
    count = sum(item["runtime_registered"] for item in results)
    print(f"UPSTREAM_N_OF_N_PASS {count} ({count}/{identity['count']} registered programs; {len(results)} compiled programs)", flush=True)


if __name__ == "__main__":
    main()
