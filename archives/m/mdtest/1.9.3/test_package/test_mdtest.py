#!/usr/bin/env python3
"""Run upstream scenarios and critical-path checks against installed mdtest."""

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import tempfile


def run(command, cwd, env=None, timeout=90, expect=0):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    process = subprocess.run(
        command, cwd=cwd, env=merged, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, timeout=timeout
    )
    if process.returncode != expect:
        raise AssertionError(
            "command returned {} (expected {}): {}\n{}".format(
                process.returncode, expect, command, process.stdout[-4000:]
            )
        )
    return process.stdout


def upstream_scenarios(root):
    one = str(root / "one")
    paths = "@".join(str(root / name) for name in ("one", "two", "three"))
    base = [
        [], ["-d", one], ["-d", one, "-n", "3"],
        ["-d", one, "-n", "3", "-i", "2"],
        ["-d", one, "-n", "3", "-i", "2", "-c"],
        ["-d", one, "-n", "3", "-i", "2", "-p", "1"],
        ["-d", one, "-n", "3", "-i", "2", "-v"],
        ["-d", one, "-n", "3", "-i", "2", "-v", "-v"],
        ["-d", one, "-n", "3", "-i", "2", "-V", "3"],
        ["-d", one, "-n", "3", "-i", "2", "-S"],
        ["-d", one, "-n", "3", "-i", "2", "-S", "-N", "4"],
        ["-d", one, "-n", "3", "-i", "2", "-u"],
        ["-d", one, "-n", "3", "-i", "2", "-u", "-t"],
        ["-d", one, "-n", "3", "-i", "2", "-u", "-t", "-D"],
        ["-d", one, "-n", "3", "-i", "2", "-u", "-t", "-F"],
        ["-d", one, "-n", "3", "-i", "2", "-u", "-t", "-F", "-w", "0"],
        ["-d", one, "-n", "3", "-i", "2", "-u", "-t", "-F", "-w", "1"],
        ["-d", one, "-n", "3", "-i", "2", "-u", "-t", "-F", "-w", "0", "-y"],
        ["-d", one, "-n", "3", "-i", "2", "-u", "-t", "-F", "-w", "1", "-y"],
        ["-d", one, "-n", "3", "-i", "2", "-u", "-t", "-N", "4"],
        ["-d", one, "-n", "3", "-i", "2", "-N", "4", "-f", "1", "-l", "3", "-s", "1"],
        ["-d", one, "-n", "3", "-i", "2", "-N", "4", "-f", "1", "-l", "3", "-s", "1", "-r"],
    ]
    multi = [
        ["-d", paths], ["-d", paths, "-n", "3"],
        ["-d", paths, "-n", "3", "-i", "2"],
        ["-d", paths, "-n", "3", "-i", "2", "-p", "1"],
        ["-d", paths, "-n", "3", "-i", "2", "-v"],
        ["-d", paths, "-n", "3", "-i", "2", "-v", "-v"],
        ["-d", paths, "-n", "3", "-i", "2", "-V", "3"],
        ["-d", paths, "-n", "3", "-i", "2", "-S"],
        ["-d", paths, "-n", "3", "-i", "2", "-u"],
        ["-d", paths, "-n", "3", "-i", "2", "-u", "-t"],
        ["-d", paths, "-n", "3", "-i", "2", "-u", "-t", "-D"],
        ["-d", paths, "-n", "3", "-i", "2", "-u", "-t", "-F"],
        ["-d", paths, "-n", "3", "-i", "2", "-u", "-t", "-F", "-w", "0"],
        ["-d", paths, "-n", "3", "-i", "2", "-u", "-t", "-F", "-w", "1"],
        ["-d", paths, "-n", "3", "-i", "2", "-u", "-t", "-F", "-w", "0", "-y"],
        ["-d", paths, "-n", "3", "-i", "2", "-u", "-t", "-F", "-w", "1", "-y"],
        ["-d", one, "-n", "3", "-i", "2", "-f", "1", "-l", "3", "-s", "1"],
    ]
    return base + multi


def summary_rate(output, operation):
    match = re.search(r"^\s*{}\s*:\s*([0-9.]+)".format(re.escape(operation)),
                      output, re.MULTILINE)
    if not match:
        raise AssertionError("missing summary row {}\n{}".format(operation, output[-3000:]))
    return float(match.group(1))


def run_negative(command, cwd, diagnostic, scenario, timeout=120):
    """Require the negative exit and observe its category despite MPI abort races."""
    outputs = []
    for _ in range(3):
        output = run(command, cwd, timeout=timeout, expect=1)
        outputs.append(output)
        if diagnostic in output:
            return output
    raise AssertionError(
        "upstream scenario {} returned the expected nonzero status but its "
        "diagnostic was lost in three MPI_Abort attempts:\n{}".format(
            scenario, "\n--- retry ---\n".join(text[-2000:] for text in outputs)
        )
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mdtest", required=True)
    parser.add_argument("--mpiexec", required=True)
    parser.add_argument("--interposer", required=True)
    parser.add_argument("--readelf", required=True)
    args = parser.parse_args()

    root = pathlib.Path(tempfile.mkdtemp(prefix="mdtest-consumer-"))
    try:
        for name in ("one", "two", "three"):
            (root / name).mkdir()

        help_text = run([args.mpiexec, "-n", "1", args.mdtest, "-h"], root)
        assert "Usage: mdtest" in help_text

        scenarios = upstream_scenarios(root)
        assert len(scenarios) == 39
        for index, options in enumerate(scenarios, 1):
            # Upstream describes -r as cleanup for objects left by a previous
            # interrupted run, but its Python-2 driver neither creates that
            # prerequisite nor checks child status.  On a clean directory the
            # published invocation deterministically takes its documented
            # missing-object path; assert that exact result instead of hiding
            # it or fabricating a pass fixture.
            if "-r" in options:
                output = run_negative(
                    [args.mpiexec, "-n", "4", args.mdtest] + options,
                    root,
                    "FAILED in create_remove_items_helper, unable to remove",
                    index,
                )
                assert "No such file or directory" in output
                continue
            directory = options[options.index("-d") + 1] if "-d" in options else ""
            if "@" in directory and "-u" not in options:
                run_negative(
                    [args.mpiexec, "-n", "4", args.mdtest] + options,
                    root,
                    "FAILED in valid_tests, shared directory mode is not compatible "
                    "with multiple directory paths",
                    index,
                )
                continue
            output = run([args.mpiexec, "-n", "4", args.mdtest] + options,
                         root, timeout=120)
            assert "-- finished at" in output, "upstream scenario {} incomplete".format(index)
            assert "SUMMARY: (of" in output, "upstream scenario {} missing summary".format(index)
        print("UPSTREAM_SCENARIOS_OBSERVED=40/40")
        print("UPSTREAM_POSITIVE_PASS=31 UPSTREAM_NEGATIVE_CLASSIFIED=9")

        skew_dir = root / "critical-path"
        skew_dir.mkdir()
        skew_env = {
            "LD_PRELOAD": args.interposer,
            "MDTEST_DELAY_RANK": "1",
            # For -F -C, call 3 is file_test()'s start timestamp: it occurs
            # after the opening barrier and immediately before rank-local
            # production work.  Delaying this sample models post-barrier
            # scheduler skew instead of adding time after the closing barrier.
            "MDTEST_DELAY_WTIME_CALL": "3",
            "MDTEST_DELAY_USEC": "1000000",
        }
        skew = run([
            args.mpiexec, "-n", "2", args.mdtest, "-d", str(skew_dir),
            "-n", "4", "-i", "1", "-F", "-C"
        ], root, env=skew_env)
        assert "MDTEST_DELAY_APPLIED rank=1 wtime_call=3 usec=1000000" in skew, (
            "the controlled start-sampling skew was not applied:\n{}".format(
                skew[-3000:]
            )
        )
        rate = summary_rate(skew, "File creation")
        assert 0.0 < rate < 12.0, (
            "rate did not cover the barrier-adjacent start skew: {}".format(rate)
        )
        print("CRITICAL_PATH_RATE={:.3f}".format(rate))
        print("HARMONYOS_CONSUMER_SCENARIO_PASS=1/1")

        local_dir = root / "no-barrier"
        local_dir.mkdir()
        no_barrier = run([
            args.mpiexec, "-n", "2", args.mdtest, "-d", str(local_dir),
            "-n", "4", "-i", "1", "-F", "-C", "-B"
        ], root)
        assert summary_rate(no_barrier, "File creation") > 0.0

        binary = pathlib.Path(args.mdtest).read_bytes()
        assert binary[:4] == b"\x7fELF"
        assert binary[18:20] == b"\xb7\x00", "not an AArch64 ELF"
        inspection = run([args.readelf, "-S", "-d", args.mdtest], root)
        assert inspection.count(".codesign") == 1, "expected one signing section"
        needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", inspection)
        assert needed == ["libmpi.so.12", "libc.so"], (
            "unexpected dynamic dependency closure: {}".format(needed)
        )
        assert "(RPATH)" not in inspection and "(RUNPATH)" not in inspection and (
            b".conan2/" not in binary
        ), "binary retained a build-cache path or runtime search path"
        print("HARMONYOS_ELF_ASSERTIONS_PASS=5/5")
        print("CONSUMER_ASSERTIONS_PASS=7/7")
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
