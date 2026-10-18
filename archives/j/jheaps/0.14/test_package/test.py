#!/usr/bin/env python3
"""OpenHarmony consumer tests for the packaged jheaps 0.14 jar.

Verifies the exact packaged artifact (nonempty, ZIP CRC, Java 8 bytecode,
required entries, OSGi bundle manifest, class count), then compiles a real
consumer against the jar and runs one end-to-end scenario:

1. dijkstra: Dijkstra shortest paths over a deterministic strongly-connected
   digraph driven by three different jheaps heap families (pairing tree heap,
   binary array addressable heap, double radix monotone heap), each
   cross-checked against a Bellman-Ford reference computed inside the
   consumer (200 assertions).
2. os-name normalization: the consumer JVM runs with JAVA_TOOL_OPTIONS
   -Dos.name=Linux, the same normalization the build pins for Maven and
   Surefire on OpenHarmony, and must report os.name=Linux back to test.py.
"""

import argparse
import os
import re
import struct
import subprocess
import sys
import zipfile

DIJKSTRA_EXPECTED = "jheaps 0.14 ohos dijkstra tests passed: 209"

REQUIRED_ENTRIES = (
    "org/jheaps/AddressableHeap.class",
    "org/jheaps/Heap.class",
    "org/jheaps/MergeableHeap.class",
    "org/jheaps/array/BinaryArrayAddressableHeap.class",
    "org/jheaps/monotone/DoubleRadixAddressableHeap.class",
    "org/jheaps/tree/PairingHeap.class",
    "org/jheaps/tree/FibonacciHeap.class",
    "META-INF/MANIFEST.MF",
)

EXPECTED_CLASS_COUNT = 88


def fail(message):
    raise RuntimeError(message)


def class_major(data, entry, jar):
    if len(data) < 8 or data[:4] != b"\xca\xfe\xba\xbe":
        fail("{} in {} is not a valid Java class".format(entry, jar))
    return struct.unpack(">H", data[6:8])[0]


def verify_jar(jar):
    if not os.path.isfile(jar) or os.path.getsize(jar) <= 0:
        fail("Packaged jheaps JAR is missing or empty: {}".format(jar))
    with zipfile.ZipFile(jar) as archive:
        corrupt = archive.testzip()
        if corrupt:
            fail("{} has a corrupt ZIP entry: {}".format(jar, corrupt))
        entries = set(archive.namelist())
        class_entries = [e for e in entries if e.endswith(".class")]
        majors = set(
            class_major(archive.read(entry), entry, jar)
            for entry in class_entries
        )
        if majors != {52}:
            fail(
                "{} bytecode mismatch: majors={}".format(jar, sorted(majors))
            )
        missing = sorted(set(REQUIRED_ENTRIES) - entries)
        if missing:
            fail(
                "{} is missing required entries: {}".format(
                    jar, ", ".join(missing)
                )
            )
        if len(class_entries) != EXPECTED_CLASS_COUNT:
            fail(
                "Unexpected class count in {}: {} (expected {})".format(
                    jar, len(class_entries), EXPECTED_CLASS_COUNT
                )
            )
        manifest = archive.read("META-INF/MANIFEST.MF").decode(
            "utf-8", "replace"
        )
    if "Automatic-Module-Name: org.jheaps" not in manifest:
        fail(
            "{} lacks the OSGi Automatic-Module-Name org.jheaps generated "
            "by the maven-bundle-plugin".format(jar)
        )


def compile_consumer(javac, jar, work, source):
    classes = os.path.join(work, "consumer-classes")
    os.makedirs(classes, exist_ok=True)
    subprocess.run(
        [
            javac,
            "--release",
            "8",
            "-encoding",
            "UTF-8",
            "-cp",
            jar,
            "-d",
            classes,
            source,
        ],
        check=True,
    )
    return classes


def run_dijkstra(java, jar, classes, work):
    environment = dict(os.environ)
    # Same platform normalization the build pins for Maven and its forked
    # Surefire JVMs; the consumer must report it back (OpenHarmony JVMs
    # otherwise announce a non-Linux os.name that some tooling rejects).
    environment["JAVA_TOOL_OPTIONS"] = (
        environment.get("JAVA_TOOL_OPTIONS", "").strip()
        + " -Dos.name=Linux"
    ).strip()
    if not environment.get("HOME"):
        environment["HOME"] = work
    result = subprocess.run(
        [
            java,
            "-cp",
            os.pathsep.join([classes, jar]),
            "TestJHeaps",
            "dijkstra",
        ],
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
        env=environment,
    )
    lines = [
        ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()
    ]
    markers = dict(
        ln.split("=", 1) for ln in lines if "=" in ln and not ln.startswith("jheaps")
    )
    if markers.get("JHEAPS_OS") != "Linux":
        fail(
            "os.name normalization failed: expected Linux, saw {!r}".format(
                markers.get("JHEAPS_OS")
            )
        )
    final = [ln for ln in lines if ln.startswith("jheaps")]
    if not final:
        fail("dijkstra scenario produced no summary line")
    if final[-1] != DIJKSTRA_EXPECTED:
        fail(
            "Unexpected dijkstra scenario output: {!r}; expected {!r}".format(
                final[-1], DIJKSTRA_EXPECTED
            )
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lib", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--java", required=True)
    parser.add_argument("--javac", required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()

    jar = os.path.join(args.lib, "jheaps-{}.jar".format(args.version))
    verify_jar(jar)
    classes = compile_consumer(args.javac, jar, args.work, args.source)
    run_dijkstra(args.java, jar, classes, args.work)
    print("dijkstra scenario passed: 3 heap families, bellman-ford "
          "cross-check, os.name normalization")
    print("JAR verification passed: clean ZIP, Java 8 bytecode, required "
          "entries, OSGi bundle manifest, exact class count")
    print("jheaps {} OHOS consumer tests passed".format(args.version))


if __name__ == "__main__":
    main()
