#!/usr/bin/env python3
"""Consumer verification for pd-jmmmp 0.61.

pd-jmmmp is pure Pure Data data: 72 abstractions, 68 help patches, the
``jmmmp-meta.pd`` libdir marker, twelve ``*.txt`` data files and the example
images the GUI abstractions display.  There is no C/C++ source and no upstream
test suite, so this verifier is the whole quality gate.  It has two layers:

  data layer (always):
    * the packaged libdir holds exactly the upstream file set;
    * every shipped ``.pd`` file is a structurally valid Pd patch (``#N canvas``
      header, balanced subpatches, in-range ``#X connect`` indices);
    * ``jmmmp-meta.pd`` declares the libdir name and the upstream license;
    * every object class referenced by an abstraction is Pd vanilla, another
      shipped abstraction (plain or ``jmmmp/<name>``) or one of the documented
      external Pd-library classes - so a new dependency or a typo fails here;
    * the libraries named in the upstream ``[declare]`` lines are exactly the
      documented set;
    * the set of abstractions instantiated by ``jmmmp_instantiate.pd`` equals
      the set computed here from the static class closure, which keeps that
      patch a maintained artifact instead of a hand-kept list.

  runtime layer (only where --pd is given):
    * ``jmmmp_instantiate.pd`` creates one instance of every abstraction whose
      class closure needs nothing but Pd vanilla, with no creation error;
    * ``jmmmp_smoke.pd`` drives nine deterministic abstractions and the captured
      output must carry the exact expected values;
    * the ``jmmmp/<name>`` namespace form used by upstream patches resolves;
    * negative control: both patches are run again without the package on Pd's
      search path; every library object must fail to resolve and no expected
      value may appear, which proves the positive run cannot pass vacuously.

Two upstream patches (``multiarray.pd``, ``jp.garble.pd``) store whole child
patches inside message boxes and Pd wraps long records over several physical
lines, so the reader here rebuilds logical ``#X`` records before parsing;
a line-oriented reader reports bogus errors on those two files.

Exit status 0 = every assertion passed, 1 = at least one assertion failed.
"""

import argparse
import os
import re
import subprocess
import sys

PD_TIMEOUT = 120

# Object classes that Pd 0.56.5 (the version puredata/0.56.5 builds) provides
# itself, as referenced by this release.  Derived by running every class
# referenced by the shipped abstractions through `pd -verbose` and keeping the
# ones that resolve without any extra library - see notes.md.
VANILLA_CLASSES = frozenset({
    "-", "-~", "*", "*~", "/", "==", ">", ">=", "abs", "abs~",
    "append", "array", "bang", "biquad~", "block~", "bng", "catch~", "change",
    "clip", "clip~", "cnv", "cos", "ctlin", "ctlout", "dac~", "dbtorms",
    "declare", "del", "delread~", "delwrite~", "div", "drawcurve", "drawnumber",
    "drawpolygon", "drawsymbol", "drawtext", "element", "env~", "exp", "expr",
    "expr~", "f", "filledpolygon", "ftom", "fudiformat", "fudiparse", "get",
    "getsize", "hip~", "hradio", "hsl", "i", "inlet", "inlet~", "int", "key",
    "line", "line~", "list", "loadbang", "log", "makefilename", "makenote",
    "max", "max~", "metro", "min", "mod", "moses", "mtof", "mtof~",
    "namecanvas", "nbx", "netreceive", "netsend", "noise~", "notein",
    "openpanel", "oscformat", "oscparse", "outlet", "outlet~", "pack",
    "pdcontrol", "phasor~", "pipe", "plot", "pointer", "poly", "pow", "pow~",
    "print", "r", "random", "realtime", "receive", "receive~", "rfft~",
    "route", "s", "samplerate~", "savepanel", "sel", "select", "send", "send~",
    "set", "setsize", "sig~", "snapshot~", "soundfiler", "spigot", "sqrt",
    "sqrt~", "struct", "swap", "switch~", "symbol", "t", "table", "tabplay~",
    "tabread", "tabwrite", "tabwrite~", "text", "textfile", "tgl", "throw~",
    "timer", "unpack", "until", "v", "value", "vline~", "vradio", "vsl", "vu",
    "wrap",
})

# Classes provided by other Pd libraries.  Each is a runtime prerequisite of a
# Pd installation, documented per abstraction in notes.md; none of them is a
# Conan dependency of this data-only package.
EXTERNAL_CLASSES = frozenset({
    "abl_link~", "coll", "cyclone/click~", "cyclone/cycle~", "cyclone/dbtoa",
    "cyclone/delay~", "cyclone/delta~", "cyclone/gate", "cyclone/lessthan~",
    "cyclone/modulo~", "cyclone/play~", "cyclone/rand~", "cyclone/rminus",
    "cyclone/round~", "cyclone/sah~", "cyclone/snapshot~", "cyclone/speedlim",
    "date", "dbtoa", "demux", "drip", "else/dir", "else/openfile", "gate",
    "gemhead", "gemwin", "getdir", "iem_blocksize~", "iemmatrix", "image",
    "inv", "l2s", "last-x", "list-add", "list-apply", "list-drip", "list-mult",
    "list-rev", "list-rot", "list2symbol", "listfunnel", "makesymbol",
    "maxlib/pitch", "minmax", "mrpeach/packOSC", "mrpeach/udpsend", "msgfile",
    "mtx_mul~", "mtx_transpose", "oscx/dumpOSC", "oscx/sendOSC", "pix_data",
    "pix_draw", "pix_image", "pix_info", "rminus", "rminus~", "routeOSC",
    "s2l", "selector~", "send13", "serialize", "shell", "speedlim", "split",
    "splitfilename", "symbol2list", "system.hostname", "tab_sum", "time",
    "udpreceive", "unpackOSC", "unsymbol", "uzi", "zl",
})

# Libraries named by the upstream [declare] lines of this release.
DECLARED_LIBRARIES = frozenset({
    "Gem", "abl_link~", "ceammc", "cyclone", "ext13", "ggee", "iem_tab",
    "iemlib", "iemmatrix", "jmmmp", "list-abs", "maxlib", "mrpeach", "zexy",
})

# Upstream 0.61 ships a jmmmp-meta.pd that still declares VERSION 0.48.  The
# file is shipped unchanged (it is upstream data, not a packaging defect we may
# silently edit); the value is asserted so a future upstream fix is noticed and
# notes.md records the mismatch.
META_NAME = "NAME jmmmp;"
META_VERSION = "VERSION 0.48;"
META_LICENSE = "LICENSE BSD;"

# label -> ordered values printed for that label by jmmmp_smoke.pd, captured
# from Pd 0.56.5 (the interpreter puredata/0.56.5 builds) and derived from the
# abstraction sources:
#   appent/prepent        list append/prepend, [list trim] drops the selector
#   f+ 10 2               counter: first bang 10, then +2 each
#   change-symbol         forwards a symbol only when it changed
#   jp.symbol-expand      one symbol -> one list element per character
#   expr_scale 0 9 100 255  (in-0)*(100-255)/(0-9)+100
#   jmmmp/scale -1 1 0 127  (in+1)*(127-0)/(1+1)
#   lbang                 loadbang + one bang = two bangs
#   sguigot 1             toggle on, so the bang passes
EXPECTED_SMOKE = (
    ("APPENT", ["1 2 3 7", "5 7"]),
    ("PREPENT", ["0 1 2 3"]),
    ("FPLUS", ["10", "12", "14"]),
    ("CHANGESYMBOL", ["symbol alpha", "symbol beta", "symbol gamma"]),
    ("SYMBOL_EXPAND", ["list a b c"]),
    ("EXPR_SCALE", ["100", "255", "177.5"]),
    ("SCALE", ["0", "127", "63.5"]),
    ("LBANG", ["bang", "bang"]),
    ("SGUIGOT", ["bang"]),
)

EXPECTED_SENTINELS = ("JMMMP_INSTANTIATE_DONE: bang", "JMMMP_SMOKE_DONE: bang")
CREATION_ERRORS = ("couldn't create", "no such object")
LABEL_LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$")
CLASS_TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.~+*/<>=!&|^-]*$")
OBJECT_KEYWORDS = frozenset({
    "obj", "msg", "text", "floatatom", "symbolatom", "listbox", "bng", "tgl",
    "nbx", "vslider", "hslider", "vradio", "hradio", "vu", "cnv", "graph",
    "array", "restore",
})


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
        return self.check(actual == expected,
                          "%s (expected %r, got %r)" % (message, expected, actual))


def read_text(path):
    """Decode a Pd file.  120 of the 141 upstream patches are Latin-1, not UTF-8."""
    with open(path, "rb") as handle:
        return handle.read().decode("latin-1")


def _ends_record(line):
    """True when a physical line ends with an unescaped ';' (record terminator)."""
    stripped = line.rstrip()
    if not stripped.endswith(";"):
        return False
    backslashes = 0
    index = len(stripped) - 2
    while index >= 0 and stripped[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 0


def records(text):
    """Yield logical '#X' records, rejoining the physical lines Pd wrapped."""
    buffer = []
    for line in text.splitlines():
        buffer.append(line.rstrip())
        if _ends_record(line):
            yield " ".join(part.strip() for part in buffer if part.strip())
            buffer = []
    leftover = " ".join(part.strip() for part in buffer if part.strip())
    if leftover:
        yield leftover


def parse_patch(path):
    """Structurally validate one Pd patch; return (root object count, errors)."""
    errors = []
    stack = []
    root_objects = 0
    canvases = 0
    restores = 0
    for number, record in enumerate(records(read_text(path)), start=1):
        if record.startswith("#N canvas"):
            canvases += 1
            stack.append([])
            continue
        match = re.match(r"^#X (\S+)\s*(.*)$", record)
        if not match:
            continue
        keyword, body = match.group(1), match.group(2)
        if keyword == "connect":
            indices = re.findall(r"-?\d+", body)
            if len(indices) != 4:
                errors.append("record %d: malformed connect line: %s"
                              % (number, record[:80]))
                continue
            source, _outlet, target, _inlet = (int(value) for value in indices)
            current = stack[-1] if stack else None
            if current is None:
                errors.append("record %d: connect outside of a canvas" % number)
                continue
            for index in (source, target):
                if not 0 <= index < len(current):
                    errors.append(
                        "record %d: connect references object %d of a canvas with %d objects"
                        % (number, index, len(current)))
        elif keyword in OBJECT_KEYWORDS:
            if not stack:
                errors.append("record %d: object outside of a canvas" % number)
                continue
            if keyword == "restore":
                finished = stack.pop()
                restores += 1
                if stack:
                    stack[-1].append(finished)
                    root_objects = len(stack[0])
                    continue
                errors.append("record %d: restore without matching canvas" % number)
                continue
            if len(stack) == 1:
                root_objects = len(stack[-1]) + 1
            stack[-1].append(keyword)
    if len(stack) > 1:
        errors.append("%d canvas block(s) never restored" % (len(stack) - 1))
    if canvases != restores + 1:
        errors.append("unbalanced subpatches: %d '#N canvas' vs %d '#X restore'"
                      % (canvases, restores))
    if canvases == 0:
        errors.append("no '#N canvas' header")
    return root_objects, errors


def object_classes(path):
    """Class name of every real '#X obj' box (message-box text is not inspected)."""
    classes = []
    for record in records(read_text(path)):
        if not record.startswith("#X obj "):
            continue
        parts = record[len("#X obj "):].rstrip(";").split(None, 2)
        if len(parts) < 3 or not parts[2].strip():
            continue
        token = parts[2].split()[0]
        if not CLASS_TOKEN.match(token) or token.isdigit():
            continue
        classes.append(token)
    return classes


def declared_libraries(path):
    """(libs, paths) named by the [declare] records of one patch."""
    libs, paths = [], []
    for record in records(read_text(path)):
        if not record.startswith("#X declare"):
            continue
        mode = None
        for token in record[len("#X declare"):].replace(";", " ").split():
            if token in ("-lib", "-path"):
                mode = token
            elif mode == "-lib":
                libs.append(token)
            elif mode == "-path":
                paths.append(token)
    return libs, paths


def split_namespaced(class_name):
    """'jmmmp/scale' -> ('jmmmp', 'scale'); plain names -> (None, name)."""
    if "/" in class_name:
        namespace, rest = class_name.split("/", 1)
        return namespace, rest
    return None, class_name


def library_classes(path, abstractions):
    """The library's own classes used by one patch (used for the negative control)."""
    used = set()
    for class_name in object_classes(path):
        namespace, bare = split_namespaced(class_name)
        if namespace == "jmmmp" and bare in abstractions:
            used.add(bare)
        elif namespace is None and class_name in abstractions:
            used.add(class_name)
    return used


def verify_data(verifier, jmmmp_dir, patches_dir):
    inventory_path = os.path.join(patches_dir, "jmmmp_inventory.txt")
    if not verifier.check(os.path.isfile(inventory_path),
                          "inventory %s is missing" % inventory_path):
        return set()
    expected = {line.strip() for line in read_text(inventory_path).splitlines()
                if line.strip() and not line.startswith("#")}

    if not verifier.check(os.path.isdir(jmmmp_dir), "libdir %s is missing" % jmmmp_dir):
        return set()
    present = set()
    for dirpath, _dirnames, filenames in os.walk(jmmmp_dir):
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), jmmmp_dir)
            present.add(rel.replace(os.sep, "/"))
    verifier.equal(sorted(present - expected), [], "unexpected files in the packaged libdir")
    verifier.equal(sorted(expected - present), [], "missing files in the packaged libdir")

    abstractions = sorted(
        name[:-3] for name in expected
        if name.endswith(".pd") and not name.endswith("-help.pd")
        and "/" not in name and name != "jmmmp-meta.pd")

    # ---- every shipped patch must be structurally valid -------------------
    for name in sorted(expected):
        if not name.endswith(".pd"):
            continue
        _objects, errors = parse_patch(os.path.join(jmmmp_dir, name.replace("/", os.sep)))
        verifier.equal(errors, [], "%s is not a valid Pd patch" % name)

    # ---- libdir meta file -------------------------------------------------
    meta = os.path.join(jmmmp_dir, "jmmmp-meta.pd")
    if verifier.check(os.path.isfile(meta), "jmmmp-meta.pd is missing"):
        meta_text = read_text(meta)
        verifier.check(META_NAME in meta_text, "meta file does not declare %s" % META_NAME)
        verifier.check(META_VERSION in meta_text,
                       "meta file does not declare %s (upstream 0.61 ships the stale "
                       "0.48 value; see notes.md)" % META_VERSION)
        verifier.check(META_LICENSE in meta_text, "meta file does not declare %s" % META_LICENSE)

    # ---- class dependency map --------------------------------------------
    referenced = {name: sorted(set(object_classes(os.path.join(jmmmp_dir, "%s.pd" % name))))
                  for name in abstractions}
    unknown = []
    external_used = set()
    for name, classes in referenced.items():
        for class_name in classes:
            namespace, bare = split_namespaced(class_name)
            if namespace == "jmmmp":
                if bare in abstractions:
                    continue          # namespaced reference to a shipped abstraction
            elif class_name in abstractions:
                continue              # plain reference to a shipped abstraction
            if class_name in EXTERNAL_CLASSES:
                external_used.add(class_name)
                continue
            if class_name in VANILLA_CLASSES:
                continue
            unknown.append("%s: %s" % (name, class_name))
    verifier.equal(sorted(unknown), [],
                   "abstractions reference classes that are neither Pd vanilla, nor "
                   "shipped by this package, nor documented external classes")
    verifier.equal(sorted(EXTERNAL_CLASSES - external_used), [],
                   "documented external class is not used by this release any more")

    libraries = set()
    for name in abstractions:
        libs, paths = declared_libraries(os.path.join(jmmmp_dir, "%s.pd" % name))
        libraries.update(libs)
        libraries.update(paths)
    verifier.equal(sorted(libraries - DECLARED_LIBRARIES), [],
                   "abstraction declares a Pd library that is not documented")
    verifier.equal(sorted(DECLARED_LIBRARIES - libraries), [],
                   "documented Pd library is no longer declared by any abstraction")

    # ---- static closure: which abstractions need no external library? -----
    needs_external = {}

    def needs(name, stack=()):
        if name in needs_external:
            return needs_external[name]
        result = False
        children = []
        for class_name in referenced[name]:
            namespace, bare = split_namespaced(class_name)
            if class_name in EXTERNAL_CLASSES:
                result = True
            elif namespace == "jmmmp" and bare in abstractions:
                children.append(bare)
            elif namespace is None and class_name in abstractions:
                children.append(class_name)
        if not result:
            for child in children:
                if child not in stack and needs(child, stack + (name,)):
                    result = True
                    break
        needs_external[name] = result
        return result

    clean = sorted(name for name in abstractions if not needs(name))

    # ---- the instantiate patch must match that closure -------------------
    instantiate = os.path.join(patches_dir, "jmmmp_instantiate.pd")
    if verifier.check(os.path.isfile(instantiate),
                      "%s is missing" % os.path.basename(instantiate)):
        instantiated = library_classes(instantiate, set(abstractions))
        verifier.equal(sorted(instantiated - set(clean)), [],
                       "jmmmp_instantiate.pd instantiates an abstraction that needs an "
                       "external Pd library")
        verifier.equal(sorted(set(clean) - instantiated), [],
                       "jmmmp_instantiate.pd does not instantiate every vanilla-only "
                       "abstraction")

    print("data layer: %d files, %d abstractions, %d vanilla-only, %d external-dependent, "
          "%d external classes"
          % (len(expected), len(abstractions), len(clean), len(abstractions) - len(clean),
             len(external_used)))
    return set(abstractions)


def run_pd(pd_binary, patch, libdir=None, parent=None):
    """Run one headless Pd pass and return (status, combined output).

    -batch turns off GUI/audio/MIDI, -noprefs keeps user preferences out,
    -nostdpath keeps the standard search path away so that only the package can
    provide the abstractions, and -send "; pd quit" terminates Pd after every
    -open patch was loaded (loadbangs run synchronously inside -open, so the
    patch has already executed when the quit arrives).
    """
    command = [pd_binary, "-batch", "-nogui", "-noaudio", "-noprefs", "-nostdpath"]
    if libdir:
        command += ["-path", libdir]
    if parent:
        command += ["-path", parent]
    command += ["-open", patch, "-send", "; pd quit"]
    try:
        completed = subprocess.run(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=PD_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, "pd did not terminate within %d s: %s" % (PD_TIMEOUT, " ".join(command))
    except OSError as error:
        return None, "could not execute %s: %s" % (pd_binary, error)
    return completed.returncode, completed.stdout.decode("utf-8", "replace")


def dump(title, text):
    print("--- %s ---" % title)
    for line in text.splitlines():
        if line.rstrip():
            print("    %s" % line.rstrip())
    print("--- end of %s ---" % title)


def parse_run_log(text):
    results = {}
    for line in text.splitlines():
        match = LABEL_LINE.match(line)
        if match:
            results.setdefault(match.group(1), []).append(match.group(2))
    return results


def verify_runtime(verifier, jmmmp_dir, parent, patches_dir, pd_binary, abstractions):
    instantiate = os.path.join(patches_dir, "jmmmp_instantiate.pd")
    smoke = os.path.join(patches_dir, "jmmmp_smoke.pd")
    for patch in (instantiate, smoke):
        if not verifier.check(os.path.isfile(patch), "test patch %s is missing" % patch):
            return

    positive = ""
    for patch in (instantiate, smoke):
        status, output = run_pd(pd_binary, patch, libdir=jmmmp_dir, parent=parent)
        if status is None:
            verifier.check(False, output)
            return
        positive += output
    dump("pd run with the package on the search path", positive)

    negative = ""
    for patch in (instantiate, smoke):
        status, output = run_pd(pd_binary, patch)
        if status is None:
            verifier.check(False, output)
            return
        negative += output
    dump("pd run without the package on the search path (negative control)", negative)

    for sentinel in EXPECTED_SENTINELS:
        verifier.check(sentinel in positive,
                       "runtime log misses the loadbang sentinel %r" % sentinel)
    results = parse_run_log(positive)
    for label, values in EXPECTED_SMOKE:
        verifier.equal(results.get(label, []), values, "unexpected results for %s" % label)
    for marker in CREATION_ERRORS:
        verifier.check(marker not in positive,
                       "runtime log reports %r although the library was loaded" % marker)

    # Negative control: every library box must be unresolvable without the
    # package, and nothing the positive run asserts may appear.
    expected_errors = len(library_classes(instantiate, abstractions)) + \
        len(library_classes(smoke, abstractions))
    observed_errors = sum(negative.count(marker) for marker in CREATION_ERRORS)
    verifier.equal(observed_errors, expected_errors,
                   "negative control did not fail to resolve exactly the library objects "
                   "(a class name may be shadowed by Pd vanilla)")
    leaked = sorted(set(parse_run_log(negative)) & {label for label, _ in EXPECTED_SMOKE})
    verifier.equal(leaked, [],
                   "negative control produced results without the package on the search path")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jmmmp-dir", required=True,
                        help="packaged lib/pd-externals/jmmmp")
    parser.add_argument("--patches", default=os.path.dirname(os.path.abspath(__file__)),
                        help="directory holding the test patches and the inventory")
    parser.add_argument("--pd", help="Pd interpreter used for the runtime layer")
    parser.add_argument("--pd-externals",
                        help="parent of the jmmmp directory, so that the 'jmmmp/<name>' "
                             "namespace resolves (default: parent of --jmmmp-dir)")
    args = parser.parse_args()

    parent = args.pd_externals or os.path.dirname(os.path.abspath(args.jmmmp_dir.rstrip(os.sep)))
    verifier = Verifier()
    abstractions = verify_data(verifier, args.jmmmp_dir, args.patches)
    if args.pd:
        verify_runtime(verifier, args.jmmmp_dir, parent, args.patches, args.pd, abstractions)

    print("jmmmp checks: %d assertions, %d failed"
          % (verifier.assertions, len(verifier.failures)))
    for failure in verifier.failures:
        print("FAIL: %s" % failure)
    return 1 if verifier.failures else 0


if __name__ == "__main__":
    sys.exit(main())
