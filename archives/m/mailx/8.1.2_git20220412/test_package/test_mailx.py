#!/usr/bin/env python3
"""Functional tests for the mailx command line tool.

Exercises the installed mailx binary end-to-end (9 checks, each counted
explicitly — no stdout string counting):
  1-2. usage text is printed for an unknown option
  3.   reading an empty mailbox prints "No mail for ..."
  4-9. reading a crafted mailbox file lists/prints messages + version banner

Machine evidence markers (HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT)
are printed with the real check counts produced below.
"""
import json
import os
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) < 2:
        print("usage: test_mailx.py <mailx_binary>", file=sys.stderr)
        return 2
    executable = sys.argv[1]

    def run(args, input_text=None, env_extra=None):
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [executable] + args,
            input=input_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    discovered = 0
    passed = 0
    failures = []

    def check(name, cond, detail=""):
        nonlocal discovered, passed
        discovered += 1
        if cond:
            passed += 1
            print("ok: %s" % name)
        else:
            failures.append(name)
            print("FAIL: %s %s" % (name, detail))

    # --- test 1-2: usage text on unknown option ------------------------------
    r = run(["--help"])
    usage = r.stderr + r.stdout
    check("usage-text", "usage:" in usage, "got: %r" % usage[:500])
    check("usage-send-options", "-s subject" in usage, "got: %r" % usage[:500])

    # --- test 3: empty mailbox ------------------------------------------------
    r = run(["-n"], env_extra={"MAIL": "/dev/null"})
    check("empty-mailbox", "No mail for" in (r.stdout + r.stderr),
          "got: %r%r" % (r.stdout[:300], r.stderr[:300]))

    # --- test 4-9: crafted mailbox read/list/print ---------------------------
    with tempfile.TemporaryDirectory() as td:
        mbox = os.path.join(td, "inbox")
        with open(mbox, "w") as f:
            f.write(
                "From alice@example.com Thu Jan  1 00:00:00 2026\n"
                "Subject: Hello World\n"
                "Date: Thu, 1 Jan 2026 00:00:00 +0000\n"
                "From: Alice <alice@example.com>\n"
                "To: bob@example.com\n"
                "\n"
                "This is the message body.\n"
                "Line two.\n"
            )
        # The mbox fixture must be non-empty, otherwise the harness would
        # compare empty output against empty expectations (toybox tar lesson).
        assert os.path.getsize(mbox) > 0, "mbox fixture is empty"
        r = run(["-n", "-f", mbox], input_text="h\np\nq\n")
        out = r.stdout + r.stderr
        check("read-rc", r.returncode == 0, "rc=%r out=%r" % (r.returncode, out[:500]))
        check("version-banner", "Mail version 8.1.2" in out, "got: %r" % out[:500])
        check("message-count", "1 message" in out, "got: %r" % out[:500])
        check("subject-listed", "Hello World" in out, "got: %r" % out[:500])
        check("body-printed", "This is the message body." in out, "got: %r" % out[:500])
        check("clean-exit", "complete" in out, "got: %r" % out[:500])

    print("test_package: %d/%d checks passed" % (passed, discovered))

    ok = (passed == discovered)
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
        "executed": True,
        "passed": ok,
        "command": "python3 test_mailx.py <bin>/mailx",
        "discovered": discovered,
        "passedCount": passed,
    }))
    # Upstream ships no test suite (audited tarball: OpenBSD bsd.prog.mk with
    # only all/clean/install/distribution targets, no tests/ dir, no check
    # target) — same conclusion as the merged bsd-mailx adaptation.
    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
        "status": "no_tests",
        "command": "",
        "discovered": 0,
        "executed": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "reason": "audited upstream tarball (53 files, OpenBSD bsd.prog.mk, "
                  "no check/test target, no tests dir): no upstream tests",
    }))

    if failures:
        print("failures: %s" % ", ".join(failures), file=sys.stderr)
        return 1
    print("mailx functional tests passed (%d assertions)" % passed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
