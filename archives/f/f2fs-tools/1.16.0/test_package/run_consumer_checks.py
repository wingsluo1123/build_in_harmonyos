import argparse
import os
import shutil
import subprocess
import tempfile


EXPECTED_VERSION = "1.16.0"
VERSION_TOOLS = (
    "mkfs.f2fs", "fsck.f2fs", "dump.f2fs", "defrag.f2fs",
    "resize.f2fs", "sload.f2fs", "f2fslabel",
)
CONSUMER_CASES = [f"{name}-version" for name in VERSION_TOOLS] + [
    "f2fs_io-command-table",
    "f2fscrypt-command-table",
    "parse.f2fs-missing-argument-diagnostic",
    "mkfs-regular-image",
    "fsck-regular-image",
]


class TestNotRun(Exception):
    """A case could not be attempted because its required environment is absent."""


def locate(name):
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"required package executable not found on PATH: {name}")
    return path


def command_case(argv, expected_text, expected_rc=0):
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    output = result.stdout + result.stderr
    if result.returncode != expected_rc:
        raise AssertionError(
            f"command={argv!r} rc={result.returncode} expected={expected_rc}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if expected_text not in output:
        raise AssertionError(
            f"command={argv!r} did not print {expected_text!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return output.strip()


def report_runtime_unavailable(target, build):
    reason = (
        "not executed: Conan can_run() returned false for target "
        f"{target} from build context {build}; no compatible native or emulated "
        "runtime is configured."
    )
    for name in CONSUMER_CASES:
        print(f"TEST_PACKAGE-CASE {name} SKIP")
        print(f"TEST_PACKAGE-RAW-OUTPUT {name}: {reason}")
    print(
        f"TEST_PACKAGE-SUMMARY total={len(CONSUMER_CASES)} pass=0 "
        f"fail=0 notrun={len(CONSUMER_CASES)}"
    )
    print("TEST_PACKAGE-EXIT code=0")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-unavailable", nargs=2, metavar=("TARGET", "BUILD"))
    args = parser.parse_args()
    if args.runtime_unavailable:
        return report_runtime_unavailable(*args.runtime_unavailable)

    results = []

    def run_case(name, function):
        try:
            detail = function()
        except TestNotRun as exc:
            results.append((name, "SKIP", str(exc)))
            print(f"TEST_PACKAGE-CASE {name} SKIP")
            print(f"TEST_PACKAGE-RAW-OUTPUT {name}: {exc}")
        except Exception as exc:
            results.append((name, "FAIL", str(exc)))
            print(f"TEST_PACKAGE-CASE {name} FAIL")
            print(f"TEST_PACKAGE-RAW-OUTPUT {name}: {exc}")
        else:
            results.append((name, "PASS", ""))
            print(f"TEST_PACKAGE-CASE {name} PASS")
            if detail:
                print(f"TEST_PACKAGE-DETAIL {name}: {detail.splitlines()[0]}")

    for tool_name in VERSION_TOOLS:
        run_case(
            f"{tool_name}-version",
            lambda name=tool_name: command_case(
                [locate(name), "-V"], EXPECTED_VERSION
            ),
        )

    run_case(
        "f2fs_io-command-table",
        lambda: command_case([locate("f2fs_io"), "help"], "fsync"),
    )
    run_case(
        "f2fscrypt-command-table",
        lambda: command_case([locate("f2fscrypt"), "help"], "Available commands"),
    )
    run_case(
        "parse.f2fs-missing-argument-diagnostic",
        lambda: command_case([locate("parse.f2fs")], "Usage: parse.f2fs", expected_rc=1),
    )

    temp_parent = os.environ.get("TMPDIR")
    if temp_parent and not os.path.isdir(temp_parent):
        temp_parent = None
    try:
        temporary = tempfile.TemporaryDirectory(prefix="f2fs-tools-test-", dir=temp_parent)
    except OSError as error:
        for name in ("mkfs-regular-image", "fsck-regular-image"):
            reason = f"not executed: no writable temporary workspace: {error}"
            results.append((name, "SKIP", reason))
            print(f"TEST_PACKAGE-CASE {name} SKIP")
            print(f"TEST_PACKAGE-RAW-OUTPUT {name}: {reason}")
    else:
        tmp = temporary.name
        image = os.path.join(tmp, "consumer-smoke.img")
        image_ready = False

        def make_image():
            nonlocal image_ready
            try:
                with open(image, "wb") as stream:
                    stream.truncate(128 * 1024 * 1024)
            except OSError as error:
                raise TestNotRun(
                    f"not executed: cannot create disposable image in {tmp}: {error}"
                ) from error
            detail = command_case(
                [locate("mkfs.f2fs"), "-f", image], "F2FS-tools"
            )
            image_ready = True
            return detail

        run_case("mkfs-regular-image", make_image)

        def check_image():
            if not image_ready:
                raise TestNotRun(
                    "not executed: mkfs-regular-image did not produce a validated input image"
                )
            return command_case(
                [locate("fsck.f2fs"), "-f", image], "FSCK"
            )

        run_case("fsck-regular-image", check_image)
        try:
            temporary.cleanup()
        except OSError as error:
            # Cleanup is diagnostic only; never suppress the per-case summary.
            print(f"TEST_PACKAGE-CLEANUP not-run: {error}")

    passed = sum(status == "PASS" for _, status, _ in results)
    failed = sum(status == "FAIL" for _, status, _ in results)
    notrun = sum(status == "SKIP" for _, status, _ in results)
    print(
        f"TEST_PACKAGE-SUMMARY total={len(results)} pass={passed} "
        f"fail={failed} notrun={notrun}"
    )
    exit_code = 1 if failed else 0
    print(f"TEST_PACKAGE-EXIT code={exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
