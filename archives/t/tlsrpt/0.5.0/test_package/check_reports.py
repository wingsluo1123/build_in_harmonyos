"""Run 14 functional cases; validate received datagrams as exact JSON objects."""
import json
import subprocess
import sys

CASES = ("version", "errors", "allocator", "no_connection", "long_path",
         "connection", "success", "failure", "multiple", "cancel",
         "no_policies", "nested", "unfinished", "missing_receiver")


def expected_report(mode):
    policy = {"policy-type": 2, "policy-domain": "example.org",
              "policy-string": ["version: STSv1", "mode: enforce"],
              "mx-host": ["*.example.org"], "t": 0, "f": 0}
    if mode == "failure":
        policy.update(t=1, f=1)
        policy["failure-details"] = [{"c": 204, "s": "192.0.2.1", "n": "mx.example.org",
            "h": "mail.example.org", "r": "192.0.2.2",
            "a": 'quote" slash\\ line\n tab\t', "f": "certificate-expired"}]
    policies = [policy]
    if mode == "multiple":
        policies += [{"policy-type": 1, "failure-details": [{"c": 305}], "t": 1, "f": 1},
                     {"policy-type": 9, "t": 0, "f": 0}]
    return {"dpv": "1", "d": "example.org",
            "pr": "v=TLSRPTv1; rua=mailto:r@example.org", "policies": policies}


for case in CASES:
    result = subprocess.run([sys.argv[1], case], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(f"{case}: rc={result.returncode}\n{result.stdout}\n{result.stderr}")
    if case in ("success", "failure", "multiple"):
        actual = json.loads(result.stdout)
        expected = expected_report(case)
        if actual != expected:
            raise AssertionError(f"{case}: {actual!r} != {expected!r}")
    elif result.stdout.strip():
        raise AssertionError(f"{case}: unexpected report: {result.stdout}")
    print(f"PASS {case}", flush=True)
print(f"tlsrpt 0.5.0: {len(CASES)}/{len(CASES)} functional cases passed", flush=True)
