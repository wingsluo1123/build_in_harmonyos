#!/usr/bin/env python3
"""Run adns make check and emit auditable per-case status records."""

import argparse
import csv
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def has_token(text, token):
    pattern = r"(?<!\S)" + re.escape(token) + r"(?!\S)"
    return re.search(pattern, text) is not None


def get_case_names(regress_source):
    return sorted(
        os.path.basename(path)[5:-4]
        for path in glob.glob(os.path.join(regress_source, "case-*.sys"))
    )


def classify(names, output, returncode, regress_source, build_dir):
    rows = []
    lines = output.splitlines()
    for name in names:
        skip_marker = "SKIPPED-" + name
        failure = next(
            (line.strip() for line in lines if "FAILED" in line and f"case-{name} -" in line),
            None,
        )
        if has_token(output, skip_marker):
            case_file = Path(regress_source) / ("case-" + name + ".sys")
            try:
                program = case_file.read_text(encoding="utf-8").split()[0]
            except (OSError, IndexError):
                program = "unknown"
            playback = Path(build_dir) / "regress" / (program + "_playback")
            if not playback.is_file():
                reason = f"regress/r1test 找不到回放程序 {program}_playback"
            else:
                reason = "上游 regress/r1test 将回放程序退出码 5 归为跳过；原始 SKIPPED 标记保留"
            rows.append((name, "SKIP", skip_marker, reason))
        elif failure:
            rows.append((name, "FAIL", failure, "上游 regress/r1test 输出 FAILED，原始行保留"))
        elif has_token(output, name):
            rows.append((name, "PASS", name, "上游 regress/r1test 输出用例名"))
        elif returncode != 0:
            tail = next((line.strip() for line in reversed(lines) if line.strip()), "make check failed")
            rows.append((name, "NOTRUN", tail, "make check 在该用例状态可见前退出"))
        else:
            rows.append((name, "NOTRUN", "no per-case marker", "make check 成功但未观察到该用例的上游状态标记"))
    return rows


def run_checkall(args):
    script = Path(args.regress_source) / "checkall"
    shell = shutil.which("sh")
    if not script.is_file() or not shell:
        return None
    env = os.environ.copy()
    env["srcdir"] = args.regress_source
    return subprocess.run(
        [shell, str(script)],
        cwd=Path(args.build_dir) / "regress",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", required=True)
    parser.add_argument("--build-dir", required=True)
    parser.add_argument("--regress-source", required=True)
    args = parser.parse_args()

    names = get_case_names(args.regress_source)
    if not names:
        print("UPSTREAM-SUMMARY total=0 pass=0 fail=0 notrun=0")
        return 2

    print("UPSTREAM-COMMAND=make check", flush=True)
    primary = subprocess.run(
        [args.make, "check"],
        cwd=args.build_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    all_output = primary.stdout
    rows = classify(names, all_output, primary.returncode, args.regress_source, args.build_dir)
    fallback = None
    if primary.returncode != 0 and any(row[1] == "NOTRUN" for row in rows):
        fallback = run_checkall(args)
        if fallback is not None:
            all_output += "\n=== upstream regress/checkall fallback after make check failure ===\n"
            all_output += fallback.stdout
            rows = classify(
                names, fallback.stdout, fallback.returncode, args.regress_source, args.build_dir
            )

    report_dir = Path(os.environ.get("ADNS15060_REPORT_DIR", args.build_dir))
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "adns15060-upstream-make-check.log").write_text(
        all_output, encoding="utf-8"
    )
    with (report_dir / "adns15060-upstream-results.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("case", "status", "raw_output", "reason"))
        writer.writerows(rows)

    sys.stdout.write(primary.stdout)
    if fallback is not None:
        print("\n=== upstream regress/checkall fallback after make check failure ===")
        sys.stdout.write(fallback.stdout)
    if all_output and not all_output.endswith("\n"):
        sys.stdout.write("\n")

    for name, status, raw, reason in rows:
        print(f"UPSTREAM-{status} {name} raw={raw} reason={reason}")
    passed = sum(status == "PASS" for _, status, _, _ in rows)
    failed = sum(status == "FAIL" for _, status, _, _ in rows)
    notrun = sum(status in ("SKIP", "NOTRUN") for _, status, _, _ in rows)
    print(f"UPSTREAM-SUMMARY total={len(rows)} pass={passed} fail={failed} notrun={notrun}")

    return 1 if primary.returncode != 0 or failed or any(status == "NOTRUN" for _, status, _, _ in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
