#!/usr/bin/env python3
"""Consumer end-to-end test for the konclude Conan package on HarmonyOS PC.

Rule 12 requires at least one *complete consumer end-to-end case* that really
runs on the HarmonyOS PC target and checks a real business result.  This script
is that consumer: it drives the ``Konclude`` executable that was **installed by
the recipe under test** (never a source-tree build, never a system binary) with
real OWL 2 inputs, and asserts on the *derived* reasoning results.

Two cases are executed (one end-to-end flow each, several assertions per case):

  CONSUMER-E2E-01  Reasoning pipeline (classification / satisfiability /
                   consistency) on real OWL 2 XML knowledge bases.
  CONSUMER-E2E-02  OWLlink server over TCP loopback: an OWLlink XML request is
                   POSTed to the installed ``owllinkserver`` and the business
                   answer (``BooleanResponse result="false"`` for a class that
                   is unsatisfiable by definition+disjointness) is checked.

Usage:
  python3 test_consumer.py --konclude <pkg>/bin/Konclude \
      --fixtures <test_package>/fixtures --tmpdir <writable-dir>

Exit code 0 = every assertion of every case passed; 1 = at least one failed.
"""

import argparse
import http.client
import os
import socket
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

OWL_NS = "http://www.w3.org/2002/07/owl#"
FAMILY_NS = "http://example.org/konclude-ohos/family#"
OWL_NOTHING = OWL_NS + "Nothing"
OWL_THING = OWL_NS + "Thing"

results = []


def check(case, ok, message):
    results.append((case, bool(ok), message))
    print(("  [PASS] " if ok else "  [FAIL] ") + message, flush=True)
    return bool(ok)


def run_konclude(konclude, args, timeout=600):
    """Run the installed Konclude binary and return (rc, combined output)."""
    proc = subprocess.run([konclude] + args, capture_output=True, text=True,
                          timeout=timeout)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def owl_xml_facts(path):
    """Return (direct_subclass_pairs, transitive_closure, equivalent_sets).

    Konclude's ``classification`` writes the *direct* class hierarchy (each
    named class linked to its immediate subsumers only), so transitively
    entailed subsumptions have to be derived by closure — exactly how a consumer
    of the OWL/XML hierarchy file has to interpret it.
    """
    root = ET.parse(path).getroot()
    subs, equivs = set(), []
    for node in root:
        if node.tag.endswith("SubClassOf"):
            kids = list(node)
            if len(kids) == 2:
                subs.add((kids[0].get("IRI"), kids[1].get("IRI")))
        elif node.tag.endswith("EquivalentClasses"):
            equivs.append(frozenset(k.get("IRI") for k in node))

    closure = set(subs)
    changed = True
    while changed:
        changed = False
        for sub, sup in list(closure):
            for sub2, sup2 in list(closure):
                if sup == sub2 and (sub, sup2) not in closure:
                    closure.add((sub, sup2))
                    changed = True
    return subs, closure, equivs


def case_consumer_e2e_01(konclude, fixtures, workdir):
    """CONSUMER-E2E-01 — reasoning pipeline on real OWL 2 inputs."""
    case = "CONSUMER-E2E-01"
    print(f"[{case}] reasoning pipeline "
          "(classification -> satisfiability -> consistency) on real OWL 2 XML", flush=True)

    family = os.path.join(fixtures, "family-reasoning.owl.xml")
    inconsistent = os.path.join(fixtures, "inconsistent-family.owl.xml")
    hierarchy = os.path.join(workdir, "family-class-hierarchy.owl.xml")

    # --- step 1: classification (produces a new file with the inferred hierarchy)
    rc, out = run_konclude(konclude, ["classification", "-w", "2", "-i", family,
                                      "-o", hierarchy])
    if not check(case, rc == 0, f"classification exit code == 0 (got {rc})"):
        print(out[-2000:])
        return
    if not check(case, os.path.isfile(hierarchy) and os.path.getsize(hierarchy) > 0,
                 "classification wrote a non-empty OWL/XML hierarchy file"):
        return

    subs, closure, equivs = owl_xml_facts(hierarchy)
    # Entailed by the definition Father = Man and (hasChild some Person)
    check(case, (FAMILY_NS + "Father", FAMILY_NS + "Man") in subs,
          "inferred  Father subClassOf Man    (direct edge, only via the definition)")
    # Entailed transitively through Man -> Person
    check(case, (FAMILY_NS + "Father", FAMILY_NS + "Person") in closure,
          "inferred  Father subClassOf Person (transitive closure of the hierarchy)")
    # Entailed from the disjointness of Male and Female
    check(case, frozenset([OWL_NOTHING, FAMILY_NS + "Contradiction"]) in equivs,
          "inferred  Contradiction equivalentTo owl:Nothing (Male and Female disjoint)")
    # Negative control: must NOT be inferred any more (guards against a degenerate
    # "everything subsumes everything" output)
    check(case, (FAMILY_NS + "Woman", FAMILY_NS + "Man") not in closure,
          "control    Woman subClassOf Man is NOT inferred (direct edges or closure)")

    # --- step 2: class satisfiability (business answer on stdout)
    rc, out = run_konclude(konclude, ["satisfiability", "-w", "1", "-i", family,
                                      "-x", FAMILY_NS + "Father"])
    check(case, rc == 0 and "answered with 'Yes'" in out
          and "is satisfiable." in out and "is not satisfiable." not in out,
          "satisfiability of #Father answered 'Yes' (is satisfiable)")

    rc, out = run_konclude(konclude, ["satisfiability", "-w", "1", "-i", family,
                                      "-x", FAMILY_NS + "Contradiction"])
    check(case, rc == 0 and "answered with 'No'" in out
          and "is not satisfiable." in out,
          "satisfiability of #Contradiction answered 'No' (is not satisfiable)")

    # --- step 3: consistency of two different real inputs
    rc, out = run_konclude(konclude, ["consistency", "-w", "1", "-i", inconsistent])
    check(case, rc == 0 and "is inconsistent." in out,
          "consistency of the overlapping-assertions KB reports 'is inconsistent'")

    rc, out = run_konclude(konclude, ["consistency", "-w", "1", "-i", family])
    check(case, rc == 0 and "is consistent." in out and "is inconsistent" not in out,
          "consistency of the consistent KB reports 'is consistent'")


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def case_consumer_e2e_02(konclude, fixtures, workdir):
    """CONSUMER-E2E-02 — OWLlink server over TCP loopback."""
    case = "CONSUMER-E2E-02"
    print(f"[{case}] OWLlink server over TCP loopback "
          "(installed owllinkserver + real OWLlink request/response)", flush=True)

    request_path = os.path.join(fixtures, "owllink-satisfiability-request.xml")
    body = open(request_path, "rb").read()
    port = _free_port()

    log_path = os.path.join(workdir, "owllinkserver.log")
    log = open(log_path, "w")
    server = subprocess.Popen([konclude, "owllinkserver", "-w", "2", "-p", str(port)],
                              stdout=log, stderr=subprocess.STDOUT)
    try:
        # wait until the listening socket accepts connections
        deadline = time.time() + 60
        ready = False
        while time.time() < deadline:
            if server.poll() is not None:
                break
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=2):
                    ready = True
                    break
            except OSError:
                time.sleep(1)
        if not check(case, ready, f"owllinkserver accepted connections on 127.0.0.1:{port}"):
            return

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=120)
        conn.request("POST", "/", body=body,
                     headers={"Content-Type": "text/xml;charset=UTF-8"})
        resp = conn.getresponse()
        payload = resp.read().decode("utf-8", "replace")
        conn.close()

        check(case, resp.status == 200, f"OWLlink request answered with HTTP 200 (got {resp.status})")
        check(case, "ResponseMessage" in payload,
              "response body is an OWLlink <ResponseMessage>")
        check(case, "<OK" in payload, "response contains the <OK/> acknowledgement")

        booleans = [e.get("result") for e in ET.fromstring(payload).iter()
                    if e.tag.endswith("BooleanResponse")]
        # Robust against a server that also echoes the request's ExpectedResult:
        # every BooleanResponse in the answer must be the business answer "false"
        # (at least one must be present).
        check(case, booleans and all(b == "false" for b in booleans),
              "IsClassSatisfiable(#Contradiction) answered false "
              f"(BooleanResponse results={booleans})")
    finally:
        server.terminate()
        try:
            server.wait(timeout=30)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()
        with open(log_path, "r", errors="replace") as fh:
            logtail = fh.read()
        check(case, "HTTP request successfully processed" in logtail,
              "owllinkserver log records the processed HTTP request")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--konclude", required=True,
                        help="path to the installed bin/Konclude")
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--tmpdir", default="")
    args = parser.parse_args()

    if not os.path.isfile(args.konclude) or not os.access(args.konclude, os.X_OK):
        print(f"installed Konclude binary not executable: {args.konclude}", file=sys.stderr)
        return 1

    workdir = args.tmpdir or tempfile.mkdtemp(prefix="konclude-consumer-")
    os.makedirs(workdir, exist_ok=True)
    print(f"consumer under test : {args.konclude}")
    print(f"fixtures            : {args.fixtures}")
    print(f"scratch dir         : {workdir}")

    started = time.time()
    case_consumer_e2e_01(args.konclude, args.fixtures, workdir)
    case_consumer_e2e_02(args.konclude, args.fixtures, workdir)

    cases_run = sorted({c for c, _, _ in results})
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print("\n================ consumer end-to-end summary ================")
    for case in cases_run:
        per_case = [(ok, msg) for c, ok, msg in results if c == case]
        ok_all = all(ok for ok, _ in per_case)
        print(f"{case}: {'PASS' if ok_all else 'FAIL'} "
              f"({sum(1 for ok, _ in per_case if ok)}/{len(per_case)} assertions)")
    print(f"cases executed: {len(cases_run)}/{len(cases_run)}  "
          f"assertions: {passed}/{len(results)} passed, {failed} failed  "
          f"elapsed {time.time() - started:.1f}s")
    print("=============================================================")
    return 0 if failed == 0 and cases_run else 1


if __name__ == "__main__":
    sys.exit(main())
