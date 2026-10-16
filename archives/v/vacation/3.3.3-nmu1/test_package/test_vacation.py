#!/usr/bin/env python3
"""End-to-end vacation consumer scenarios on HarmonyOS PC."""

import os
import pathlib
import subprocess
import sys
import tempfile
import time


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def wait_for(path, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def run_message(vacation, helper, root, name, headers, *, jflag=True,
                database=None, sender=None, expect_send=False):
    database = database or root / f"{name}.db"
    capture = root / f"{name}.mail"
    message_file = root / "vacation.msg"
    envelope = sender or f"sender-{name}@example.test"
    content = (
        f"From {envelope} Sat Jan 1 00:00:00 2000\n"
        + headers
        + "\nmessage body\n"
    )
    command = [vacation]
    if jflag:
        command.append("-j")
    command += ["-f", str(database), "-m", str(message_file),
                "vacation-user"]
    env = os.environ.copy()
    env["VACATION_SENDMAIL"] = str(helper)
    env["VACATION_CAPTURE"] = str(capture)
    result = subprocess.run(
        command,
        input=content,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=10,
        check=False,
    )
    require(result.returncode == 0,
            f"{name}: vacation failed: {result.stderr}")
    appeared = wait_for(capture) if expect_send else wait_for(capture, 0.35)
    require(appeared == expect_send,
            f"{name}: expected send={expect_send}, observed {appeared}")
    return database, capture, envelope


def main():
    require(len(sys.argv) == 2, "usage: test_vacation.py <installed-vacation>")
    vacation = os.path.realpath(sys.argv[1])
    require(os.path.isfile(vacation) and os.access(vacation, os.X_OK),
            "installed vacation command is unavailable")

    root = pathlib.Path(tempfile.mkdtemp(prefix="vacation-ohos-"))
    helper = pathlib.Path(__file__).with_name("capture_sendmail.py")
    helper.chmod(0o755)
    (root / "vacation.msg").write_text(
        "Subject: away: $SUBJECT\n\nI am away.\n", encoding="utf-8"
    )

    database, capture, envelope = run_message(
        vacation, helper, root, "ordinary",
        "To: user@example.test\nSubject: planned leave\n",
        expect_send=True,
    )
    reply = capture.read_text(encoding="utf-8")
    args_path = pathlib.Path(str(capture) + ".args")
    require(wait_for(args_path), "sendmail argument capture was not written")
    args = args_path.read_text(encoding="utf-8")
    require(f"To: {envelope}\n" in reply, "reply targets envelope sender")
    require("Auto-Submitted: auto-replied\n" in reply,
            "reply declares automatic submission")
    require("Subject: away: planned leave\n" in reply,
            "subject substitution survives the complete flow")
    require(envelope in args and "--" in args,
            "sendmail-compatible recipient arguments are preserved")
    print("PASS ordinary installed-command reply flow")

    capture.unlink()
    pathlib.Path(str(capture) + ".args").unlink()
    run_message(
        vacation, helper, root, "ordinary-repeat",
        "To: user@example.test\nSubject: repeated\n",
        database=database,
        sender=envelope,
        expect_send=False,
    )
    print("PASS Berkeley DB repeat-sender throttling")

    suppressed = [
        ("auto-inline", "Auto-Submitted: auto-replied\n"),
        ("auto-folded", "Auto-Submitted:\n auto-replied\n"),
        ("precedence-folded", "Precedence:\n bulk\n"),
        ("auto-nobody", "Auto-Submitted: nobody\n"),
    ]
    for name, policy in suppressed:
        run_message(
            vacation, helper, root, name,
            "To: user@example.test\nSubject: policy\n" + policy,
            expect_send=False,
        )
        print(f"PASS suppress {name}")

    run_message(
        vacation, helper, root, "crlf-folded",
        "To: user@example.test\r\nSubject: policy\r\n"
        "Auto-Submitted:\r\n\tauto-replied\r\n",
        expect_send=False,
    )
    print("PASS CRLF folded policy suppression")

    _, no_capture, _ = run_message(
        vacation, helper, root, "auto-no",
        "To: user@example.test\nSubject: human\nAuto-Submitted:\n no\n",
        expect_send=True,
    )
    require("away: human" in no_capture.read_text(encoding="utf-8"),
            "exact Auto-Submitted no remains eligible")
    print("PASS exact Auto-Submitted no")

    _, recipient_capture, _ = run_message(
        vacation, helper, root, "folded-recipient",
        "To:\n vacation-user" +
        "@example.test\nSubject: recipient\n",
        jflag=False,
        expect_send=True,
    )
    require(recipient_capture.exists(), "folded recipient reaches user")
    print("PASS folded recipient matching")

    _, subject_capture, _ = run_message(
        vacation, helper, root, "folded-subject",
        "To: user@example.test\nSubject: hello\n world\n",
        expect_send=True,
    )
    require("away: hello world" in subject_capture.read_text(encoding="utf-8"),
            "folded subject is unfolded once")
    print("PASS folded subject propagation")

    _, return_capture, _ = run_message(
        vacation, helper, root, "folded-return-path",
        "To: user@example.test\nReturn-Path:\n <bounce@example.test>\n"
        "Subject: return path\n",
        expect_send=True,
    )
    require("To: bounce@example.test\n" in
            return_capture.read_text(encoding="utf-8"),
            "folded Return-Path controls the reply recipient")
    print("PASS folded Return-Path")

    oversized = "Auto-Submitted:\n" + "".join(
        " " + ("x" * 950) + "\n" for _ in range(9)
    )
    run_message(
        vacation, helper, root, "oversized-policy",
        "To: user@example.test\nSubject: oversized\n" + oversized,
        expect_send=False,
    )
    print("PASS oversized logical policy header fails closed")

    print("HarmonyOS vacation consumer flow passed (12 scenarios)")


if __name__ == "__main__":
    main()
