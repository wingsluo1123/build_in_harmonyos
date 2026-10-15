#!/usr/bin/env python3
"""Install and verify the WQY Native Drawing probe on one HarmonyOS HDC device."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path


PASS_MARKER = "WQY_HARMONY_TEST_PASS=1/1"
FAIL_PREFIX = "WQY_HARMONY_TEST_FAIL="
RUN_ID_PREFIX = "WQY_HARMONY_TEST_RUN_ID="
RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class DeviceTestError(RuntimeError):
    """Raised when device discovery, installation, launch, or result parsing fails."""


@dataclass(frozen=True)
class DeviceResult:
    pass_markers: int
    fail_markers: int


def select_single_hdc_target(target_output: str) -> str:
    """Select the only connected USB or TCP HDC target, ignoring UART targets."""
    targets: list[str] = []
    for line in target_output.splitlines():
        columns = line.split()
        if (
            len(columns) >= 3
            and columns[1].upper() in {"USB", "TCP"}
            and columns[2].lower() == "connected"
        ):
            targets.append(columns[0])
    if len(targets) != 1:
        raise DeviceTestError(
            f"expected exactly one connected HDC target (USB or TCP), found {len(targets)}: {targets}"
        )
    return targets[0]


def parse_device_result(log_text: str, expected_run_id: str) -> DeviceResult:
    """Accept exactly one success record emitted by this HAP build's run ID."""
    if not RUN_ID_RE.fullmatch(expected_run_id):
        raise DeviceTestError("expected run ID must be a 32-character lowercase hex value")

    lines = log_text.splitlines()
    starts = [index for index, line in enumerate(lines) if f"{RUN_ID_PREFIX}{expected_run_id}" in line]
    if not starts:
        raise DeviceTestError(f"expected run ID {expected_run_id} was not found in device logs")
    if len(starts) != 1:
        raise DeviceTestError(f"expected one run ID marker, found {len(starts)}")

    run_lines = lines[starts[0] + 1 :]
    failures = [line for line in run_lines if FAIL_PREFIX in line]
    if failures:
        raise DeviceTestError("device reported a failure marker: " + " | ".join(failures))
    passes = sum(PASS_MARKER in line for line in run_lines)
    if passes != 1:
        raise DeviceTestError(f"expected one pass marker for this run, found {passes}")
    return DeviceResult(pass_markers=passes, fail_markers=0)


def bundle_dump_matches(bundle_dump: str, expected_bundle: str) -> bool:
    """Check bm dump output without depending on whitespace or JSON punctuation."""
    match = re.search(
        r"(?m)^\s*[\"']?bundleName[\"']?\s*[:=]\s*[\"']?([^\"',\s}]+)",
        bundle_dump,
    )
    return match is not None and match.group(1) == expected_bundle


def run_command(command: list[str], *, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeviceTestError(f"command failed to run: {command!r}: {exc}") from exc


def run_checked(command: list[str], *, timeout: float = 30.0) -> str:
    result = run_command(command, timeout=timeout)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise DeviceTestError(
            f"command returned {result.returncode}: {command!r}\n{output}"
        )
    return output


def read_run_id_from_hap(hap_path: Path) -> str:
    suffix = "resources/rawfile/wqy-test-run-id.txt"
    try:
        with zipfile.ZipFile(hap_path) as archive:
            matches = [name for name in archive.namelist() if name.endswith(suffix)]
            if len(matches) != 1:
                raise DeviceTestError(
                    f"expected one staged run ID in HAP, found {len(matches)}"
                )
            run_id = archive.read(matches[0]).decode("ascii").strip()
    except (OSError, zipfile.BadZipFile, UnicodeError) as exc:
        raise DeviceTestError(f"cannot read test run ID from HAP {hap_path}: {exc}") from exc
    if not RUN_ID_RE.fullmatch(run_id):
        raise DeviceTestError("HAP contains an invalid test run ID")
    return run_id


def read_bundle_name_from_hap(hap_path: Path) -> str:
    try:
        with zipfile.ZipFile(hap_path) as archive:
            module = json.loads(archive.read("module.json"))
            bundle = module["app"]["bundleName"]
    except (OSError, KeyError, TypeError, ValueError, zipfile.BadZipFile) as exc:
        raise DeviceTestError(f"cannot read app bundle name from HAP {hap_path}: {exc}") from exc
    if not isinstance(bundle, str) or not bundle:
        raise DeviceTestError("HAP module.json contains an invalid app bundle name")
    return bundle


def find_hdc(explicit_path: str | None) -> str:
    if explicit_path:
        candidate = Path(explicit_path)
        if candidate.is_file():
            return str(candidate)
        located = shutil.which(explicit_path)
        if located:
            return located
        raise DeviceTestError(f"HDC executable does not exist: {explicit_path}")
    located = shutil.which("hdc")
    if located:
        return located
    raise DeviceTestError("HDC was not found; pass its path with --hdc")


def execute_device_test(
    hap: Path,
    bundle: str,
    ability: str,
    hdc: str,
    timeout_seconds: float,
    poll_interval: float,
) -> tuple[str, DeviceResult, str]:
    if not hap.is_file():
        raise DeviceTestError(f"signed HAP does not exist: {hap}")
    hap_bundle = read_bundle_name_from_hap(hap)
    if hap_bundle != bundle:
        raise DeviceTestError(
            f"HAP bundle is {hap_bundle!r}, but the runner was asked to launch {bundle!r}"
        )
    run_id = read_run_id_from_hap(hap)

    target = select_single_hdc_target(run_checked([hdc, "list", "targets", "-v"]))
    selector = [hdc, "-t", target]
    install_output = run_checked(selector + ["install", "-r", str(hap)], timeout=120.0)
    print(f"Installed {hap.name} on HDC target {target}: {install_output}")

    dump = run_checked(selector + ["shell", "bm", "dump", "-n", bundle])
    if not bundle_dump_matches(dump, bundle):
        raise DeviceTestError(
            f"installed bundle dump did not confirm {bundle!r}:\n{dump}"
        )

    launch_output = run_checked(
        selector + ["shell", "aa", "start", "-a", ability, "-b", bundle],
        timeout=60.0,
    )
    print(f"Launched {bundle}/{ability}: {launch_output}")

    deadline = time.monotonic() + timeout_seconds
    last_log = ""
    while time.monotonic() < deadline:
        query = run_command(
            selector + ["shell", "hilog", "-x", "-T", "WQYFontProbe"], timeout=15.0
        )
        last_log = query.stdout + query.stderr
        if query.returncode != 0:
            raise DeviceTestError(f"failed to read device hilog:\n{last_log.strip()}")

        if f"{RUN_ID_PREFIX}{run_id}" in last_log:
            try:
                result = parse_device_result(last_log, expected_run_id=run_id)
                return target, result, last_log
            except DeviceTestError as exc:
                if "failure marker" in str(exc):
                    raise
                if "expected one pass marker" not in str(exc):
                    raise
        time.sleep(poll_interval)

    raise DeviceTestError(
        f"timed out after {timeout_seconds:g}s waiting for HAP result; last hilog:\n"
        f"{last_log.strip()}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hap", type=Path, required=True, help="signed arm64 HarmonyOS HAP")
    parser.add_argument("--bundle", required=True, help="HarmonyOS bundle name")
    parser.add_argument("--ability", required=True, help="entry ability name")
    parser.add_argument("--hdc", help="path to the HDC executable")
    parser.add_argument("--timeout", type=float, default=120.0, help="device result timeout")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="hilog poll interval")
    args = parser.parse_args(argv)

    try:
        hdc = find_hdc(args.hdc)
        target, result, device_log = execute_device_test(
            args.hap,
            args.bundle,
            args.ability,
            hdc,
            args.timeout,
            args.poll_interval,
        )
    except DeviceTestError as exc:
        print(f"WQY HarmonyOS device test failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"WQY_HARMONY_TEST_PASS=1/1 target={target} "
        f"run_id={read_run_id_from_hap(args.hap)} markers={result.pass_markers}"
    )
    print(device_log.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
