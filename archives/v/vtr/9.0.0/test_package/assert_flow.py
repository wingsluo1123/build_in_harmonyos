#!/usr/bin/env python3
"""Stage-level assertions over a completed VTR CAD run.

Invoked by test_package/conanfile.py with the flow's temp directory.  The point
is that a package which *builds* but whose flow is broken -- a missing ABC, a
VPR that skips packing, a routing stage that dies -- must fail here.  Each
stage is asserted on the artifact or the log line that only that stage emits.

Every marker below is taken from VTR 9.0.0's own parse configuration
(vtr_flow/parse/parse_config/...), so these are the strings upstream itself
relies on to measure each stage.  Nothing here is invented.

Exit code 0 only if every stage is proven to have run.
"""
import os
import sys

# stage -> (filename, marker, human description)
# markers verbatim from the upstream parse config:
#   common/vpr.pack.txt, timing/vpr.place.txt, common/vpr.route_min_chan_width.txt
STAGES = [
    # ABC's own marker, not a VPR one: common/abc.txt defines
    #   abc_synth_time;abc0.out;elapse: .* seconds, total: (.*) seconds
    # "Packing" belongs to vpr.out and was wrong here -- it made this stage
    # report FAIL on a run whose ABC had in fact completed.
    ("synthesis",   "abc0.out", "elapse:",                                  "synthesis"),
    ("packing",     "vpr.out",  "Packing took",                             "packing"),
    ("placement",   "vpr.out",  "Placement estimated critical path delay",  "placement"),
    ("routing",     "vpr.out",  "Successfully routed after",                "routing"),
    ("routing_wl",  "vpr.out",  "Total wirelength:",                        "routing"),
    ("timing",      "vpr.out",  "timing analysis took",                     "timing analysis"),
]

# Artifacts the flow must leave behind (kept by run_vtr_flow.py).
ARTIFACT_EXTS = (".net", ".place", ".route")


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        fail("usage: assert_flow.py <flow_temp_dir>")
    temp_dir = sys.argv[1]
    if not os.path.isdir(temp_dir):
        fail("flow temp dir does not exist: " + temp_dir)

    entries = sorted(os.listdir(temp_dir))
    print("flow produced %d entries: %s" % (len(entries), entries))

    # ---- 1. per-stage evidence in the logs ------------------------------
    checked = set()
    for _stage, filename, marker, label in STAGES:
        path = os.path.join(temp_dir, filename)
        if not os.path.isfile(path):
            fail("expected log %r was not produced" % filename)
        if os.path.getsize(path) == 0:
            fail("log %r is empty" % filename)
        with open(path, "r", errors="replace") as fh:
            text = fh.read()
        if marker not in text:
            fail("%s: marker %r not found in %s -- that stage did not run"
                 % (label or _stage, marker, filename))
        checked.add(label or _stage)
        print("  [ok] %-16s %s contains %r" % (label or _stage, filename, marker))

    # ---- 2. elaboration front end --------------------------------------
    # WITH_PARMYS is on, so parmys/yosys elaboration must have produced a log.
    # (odin.out only appears for the odin front end.)
    if os.path.isfile(os.path.join(temp_dir, "parmys.out")):
        print("  [ok] elaboration     parmys.out present")
    elif os.path.isfile(os.path.join(temp_dir, "odin.out")):
        print("  [ok] elaboration     odin.out present")
    else:
        fail("no elaboration log (parmys.out / odin.out) was produced")

    # ---- 3. result artifacts, non-empty ---------------------------------
    found = {}
    for name in entries:
        for ext in ARTIFACT_EXTS:
            if name.endswith(ext):
                p = os.path.join(temp_dir, name)
                size = os.path.getsize(p)
                if size == 0:
                    fail("artifact %r is empty" % name)
                found[ext] = (name, size)
    for ext in ARTIFACT_EXTS:
        if ext not in found:
            fail("no %s artifact was produced by the flow" % ext)
        name, size = found[ext]
        print("  [ok] artifact        %s (%d bytes)" % (name, size))

    # ---- 4. VPR's own verdict -------------------------------------------
    out_txt = os.path.join(temp_dir, "output.txt")
    if os.path.isfile(out_txt):
        with open(out_txt, "r", errors="replace") as fh:
            verdict = fh.read()
        for line in verdict.splitlines():
            if line.startswith("vpr_status="):
                status = line.split("=", 1)[1].strip()
                print("  [ok] vpr_status      %s" % status)
                if status.lower() not in ("success", "ok"):
                    fail("VPR reported status %r" % status)
                break
        else:
            fail("output.txt has no vpr_status line")
    else:
        print("  [warn] no output.txt; relying on log markers above")

    print("PASS: synthesis, packing, placement, routing and timing analysis "
          "all executed and produced artifacts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
