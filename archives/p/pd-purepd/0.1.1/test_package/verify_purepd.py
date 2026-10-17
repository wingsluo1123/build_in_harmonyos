#!/usr/bin/env python3
"""Test-package verification for pd-purepd (pure-Pd library, no compiled code).

pd-purepd ships no C/C++ sources: upstream's Makefile has an empty SOURCES list
and the whole library is a set of 26 Pure Data abstractions ("objects written
purely in Pd").  The consumer test therefore verifies the *data* that the
package installs, plus the behaviour of those abstractions inside a real Pd
interpreter:

  layer 1 (always): the packaged libdir is complete, every file is a
      structurally valid Pd patch, every #X connect references an existing
      object of its canvas, and every object class referenced by an abstraction
      is either a Pd vanilla class or another shipped purepd abstraction.
      That last check is the defining property of this library: it must not
      pull in any external/binary Pd library.

  layer 2 (only where --pd is given): purepd_instantiate.pd creates one
      instance of every shipped abstraction and purepd_smoke.pd feeds known
      inputs through the deterministic control objects; the Pd output must
      carry the expected results and no object-creation error.

  layer 3 (only where --pd is given): the smoke patch is run again without the
      package on Pd's search path.  It must then fail to resolve the
      abstractions, which proves layer 2 can detect a broken library instead of
      passing vacuously.

Usage:
    verify_purepd.py --purepd-dir DIR
    verify_purepd.py --purepd-dir DIR --patches DIR --pd /path/to/pd

Exit status 0 = every assertion passed, 1 = at least one assertion failed.
"""

import argparse
import os
import re
import subprocess
import sys

PD_TIMEOUT = 60

# Upstream Makefile (0.1.1) PDOBJECTS: the abstraction set of this release.
ABSTRACTIONS = (
    "^",
    "alternate",
    "any_argument",
    "clip",
    "cosh",
    "delta",
    "delta~",
    "fifo",
    "float_argument",
    "for++",
    "gt2~",
    "gt~",
    "inv",
    "log10",
    "lt2~",
    "lt~",
    "moses",
    "once",
    "oneshot",
    "purepd_error",
    "sgn~",
    "sinh",
    "symbol_argument",
    "tanh",
    "uzi",
    "velocity",
)

# Pd vanilla classes referenced by those 26 abstractions (plus the usual
# aliases) -- anything outside this set and ABSTRACTIONS would be an external
# library dependency, which purepd must not have.
VANILLA_CLASSES = frozenset(
    {
        "-",
        "-~",
        "*",
        "*~",
        "/",
        "&",
        "|",
        "+",
        "+~",
        "<",
        "==",
        ">=",
        "b",
        "bang",
        "dac~",
        "exp",
        "f",
        "float",
        "i",
        "inlet",
        "inlet~",
        "int",
        "line",
        "list",
        "loadbang",
        "log",
        "max",
        "min",
        "outlet",
        "outlet~",
        "pipe",
        "pow",
        "print",
        "route",
        "rzero~",
        "s",
        "sel",
        "select",
        "sig~",
        "spigot",
        "swap",
        "symbol",
        "t",
        "table",
        "tabread~",
        "timer",
        "trigger",
        "until",
    }
)

# Line keywords that create one connectable object inside a canvas.  Pd counts
# comments (#X text) and restored subpatches (#X restore) in the same per-canvas
# index space that #X connect uses, so they must be counted here as well.
OBJECT_KEYWORDS = frozenset(
    {
        "obj",
        "msg",
        "text",
        "floatatom",
        "symbolatom",
        "listbox",
        "bng",
        "tgl",
        "nbx",
        "vslider",
        "hslider",
        "vradio",
        "hradio",
        "vu",
        "cnv",
        "graph",
        "array",
        "restore",
    }
)

# Expected runtime output of purepd_smoke.pd, captured from the upstream Pd
# 0.56-5 interpreter (the version puredata/0.56.5 builds):
# label -> ordered list of the values printed for that label.
EXPECTED_SMOKE = (
    ("PUREPD_INV", ["0.25"]),
    ("PUREPD_LOG10", ["1"]),
    ("PUREPD_COSH", ["1"]),
    ("PUREPD_SINH", ["0"]),
    ("PUREPD_TANH", ["0"]),
    # [^] prints once per operand: 5 xor 0, then 5 xor 5.
    ("PUREPD_XOR", ["5", "0"]),
    # [delta] passes the first input through, then reports the difference.
    ("PUREPD_DELTA", ["3", "7"]),
    # [fifo] pops the oldest pushed element.
    ("PUREPD_FIFO", ["1"]),
    ("PUREPD_ONCE", ["1"]),
    ("PUREPD_ONESHOT", ["bang"]),
    ("PUREPD_ALTERNATE_A", ["11", "33"]),
    ("PUREPD_ALTERNATE_B", ["22"]),
    ("PUREPD_UZI_NUM", ["1", "2", "3"]),
    ("PUREPD_UZI_LAST", ["bang"]),
)

# Both patches print a sentinel as their last loadbang action, which proves the
# patch was fully loaded and its loadbangs executed.
EXPECTED_SENTINELS = ("PUREPD_INSTANTIATE: bang", "PUREPD_SMOKE_DONE: bang")

CREATION_ERRORS = ("couldn't create", "no such object")


class Verifier:
    def __init__(self):
        self.assertions = 0
        self.failures = []

    def check(self, condition, message):
        self.assertions += 1
        if not condition:
            self.failures.append(message)
        return bool(condition)

    def equal(self, actual, expected, message):
        return self.check(
            actual == expected, "%s (expected %r, got %r)" % (message, expected, actual)
        )


def parse_patch(path):
    """Structurally validate one Pd patch file.

    Returns (object_count_root, errors).  Object counts are tracked per canvas
    so that #X connect indices can be range-checked.
    """
    errors = []
    stack = []
    root_objects = 0
    canvases = 0
    restores = 0
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    if not lines or not lines[0].startswith("#N canvas "):
        errors.append("does not start with a '#N canvas' header")
        return 0, errors
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#N canvas"):
            canvases += 1
            stack.append([])
            continue
        match = re.match(r"^#X (\S+)\s*(.*)$", line)
        if not match:
            continue
        keyword, body = match.group(1), match.group(2)
        if keyword == "connect":
            indices = re.findall(r"-?\d+", body)
            if len(indices) != 4:
                errors.append("line %d: malformed connect line" % number)
                continue
            src, _outlet, dst, _inlet = (int(value) for value in indices)
            current = stack[-1] if stack else None
            if current is None:
                errors.append("line %d: connect outside of a canvas" % number)
                continue
            for index in (src, dst):
                if not 0 <= index < len(current):
                    errors.append(
                        "line %d: connect references object %d of a canvas with %d objects"
                        % (number, index, len(current))
                    )
        elif keyword in OBJECT_KEYWORDS:
            if not stack:
                errors.append("line %d: object outside of a canvas" % number)
                continue
            if keyword == "restore":
                finished = stack.pop()
                restores += 1
                if stack:
                    stack[-1].append(finished)
                    if len(stack) == 1:
                        root_objects = len(stack[0])
                    continue
                errors.append("line %d: restore without matching canvas" % number)
                continue
            if len(stack) == 1:
                root_objects = len(stack[0]) + 1
            stack[-1].append(keyword)
    if len(stack) > 1:
        errors.append("%d canvas block(s) never restored" % (len(stack) - 1))
    if canvases != restores + 1:
        errors.append(
            "unbalanced subpatches: %d '#N canvas' vs %d '#X restore'"
            % (canvases, restores)
        )
    return root_objects, errors


def object_classes(path):
    """Class names of the object boxes of one abstraction file."""
    classes = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("#X obj "):
                body = line[len("#X obj ") :].rstrip(";")
                parts = body.split(None, 2)
                if len(parts) == 3 and parts[2].strip():
                    classes.append(parts[2].split()[0])
    return classes


def run_pd(pd_binary, purepd_dir, patch, search_path):
    """Run one headless Pd pass and return its combined output.

    `-batch` turns off GUI/audio/MIDI, `-noprefs` keeps the run free of user
    preferences, `-nostdpath` keeps the standard search path out of the way and
    `-send "; pd quit"` terminates Pd after the patch was opened (loadbangs run
    during -open, so the whole patch has already executed at that point).
    """
    command = [pd_binary, "-batch", "-nogui", "-noaudio", "-noprefs", "-nostdpath"]
    if search_path:
        command += ["-path", purepd_dir]
    command += ["-open", patch, "-send", "; pd quit"]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=PD_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "pd did not terminate within %d s: %s" % (PD_TIMEOUT, " ".join(command))
    except OSError as error:
        return None, "could not execute %s: %s" % (pd_binary, error)
    output = completed.stdout.decode("utf-8", "replace")
    return completed.returncode, output


def dump(title, text):
    """Print one captured Pd run so the CI log carries the raw evidence."""
    print("--- %s ---" % title)
    for line in text.splitlines():
        print("    %s" % line)
    print("--- end of %s ---" % title)


def verify_data(verifier, purepd_dir):
    expected_files = {"purepd-meta.pd", "README.txt", "LICENSE.txt"}
    for name in ABSTRACTIONS:
        expected_files.add("%s.pd" % name)
        expected_files.add("%s-help.pd" % name)

    if not verifier.check(os.path.isdir(purepd_dir), "libdir %s is missing" % purepd_dir):
        return
    present = set(os.listdir(purepd_dir))
    verifier.equal(
        sorted(present - expected_files),
        [],
        "unexpected files in the packaged libdir",
    )
    missing = sorted(expected_files - present)
    verifier.equal(missing, [], "missing files in the packaged libdir")

    meta = os.path.join(purepd_dir, "purepd-meta.pd")
    if verifier.check(os.path.isfile(meta), "purepd-meta.pd is missing"):
        with open(meta, "r", encoding="utf-8", errors="replace") as handle:
            meta_text = handle.read()
        verifier.check("NAME purepd;" in meta_text, "meta file does not declare NAME purepd")
        verifier.check(
            "VERSION 0.1.1;" in meta_text, "meta file does not declare VERSION 0.1.1"
        )

    referenced = set()
    for name in ABSTRACTIONS:
        path = os.path.join(purepd_dir, "%s.pd" % name)
        if not os.path.isfile(path):
            continue
        _objects, errors = parse_patch(path)
        verifier.equal(errors, [], "%s.pd is not a valid Pd patch" % name)
        referenced.update(object_classes(path))

    unresolved = sorted(referenced - VANILLA_CLASSES - set(ABSTRACTIONS))
    verifier.equal(
        unresolved,
        [],
        "abstractions reference classes outside Pd vanilla / this library",
    )

    # The help patches and the meta file are shipped documentation; still check
    # that they parse as Pd patches.
    for name in sorted(expected_files):
        if name.endswith("-help.pd") or name == "purepd-meta.pd":
            _objects, errors = parse_patch(os.path.join(purepd_dir, name))
            verifier.equal(errors, [], "%s is not a valid Pd patch" % name)


def parse_run_log(text):
    """Collect 'LABEL: value' lines of a Pd run, in order."""
    results = {}
    for line in text.splitlines():
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$", line)
        if match:
            results.setdefault(match.group(1), []).append(match.group(2))
    return results


def verify_runtime(verifier, purepd_dir, patches_dir, pd_binary):
    instantiate = os.path.join(patches_dir, "purepd_instantiate.pd")
    smoke = os.path.join(patches_dir, "purepd_smoke.pd")
    for patch in (instantiate, smoke):
        if not verifier.check(os.path.isfile(patch), "test patch %s is missing" % patch):
            return

    positive = ""
    for patch in (instantiate, smoke):
        status, output = run_pd(pd_binary, purepd_dir, patch, search_path=True)
        if status is None:
            verifier.check(False, output)
            return
        positive += output
    dump("pd run with the package on the search path", positive)

    status, negative = run_pd(pd_binary, purepd_dir, smoke, search_path=False)
    if status is None:
        verifier.check(False, negative)
        return
    dump("pd run without the package on the search path (negative control)", negative)

    for sentinel in EXPECTED_SENTINELS:
        verifier.check(
            sentinel in positive,
            "runtime log misses the loadbang sentinel %r" % sentinel,
        )
    results = parse_run_log(positive)
    for label, values in EXPECTED_SMOKE:
        verifier.equal(results.get(label, []), values, "unexpected results for %s" % label)
    for marker in CREATION_ERRORS:
        verifier.check(
            marker not in positive,
            "runtime log reports %r although the library was loaded" % marker,
        )

    verifier.check(
        any(marker in negative for marker in CREATION_ERRORS),
        "negative control did not report a missing-abstraction error",
    )
    leaked = sorted(set(parse_run_log(negative)) & {label for label, _ in EXPECTED_SMOKE})
    verifier.equal(
        leaked,
        [],
        "negative control produced results without the package on Pd's search path",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purepd-dir", required=True, help="packaged lib/pd-externals/purepd")
    parser.add_argument("--patches", help="directory holding purepd_*.pd")
    parser.add_argument("--pd", help="Pd interpreter to run the abstractions with")
    args = parser.parse_args()

    verifier = Verifier()
    verify_data(verifier, args.purepd_dir)
    if args.pd:
        if not args.patches:
            parser.error("--pd requires --patches")
        verify_runtime(verifier, args.purepd_dir, args.patches, args.pd)

    print(
        "purepd checks: %d assertions, %d failed"
        % (verifier.assertions, len(verifier.failures))
    )
    for failure in verifier.failures:
        print("FAIL: %s" % failure)
    return 1 if verifier.failures else 0


if __name__ == "__main__":
    sys.exit(main())
