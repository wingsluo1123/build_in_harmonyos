#!/usr/bin/env python3
"""Local dynamics checks of actual Twisting/explicit-SMC outputs; no golden replacement.

For A=[[0,1],[19,-2]], held input c, the equilibrium is (-c/19,0).
Writing M=A+I gives M*M=20*I and hence
exp(A*h)=exp(-h)*(cosh(sqrt(20)*h)*I+sinh(sqrt(20)*h)/sqrt(20)*M).
The original long-trajectory reference comparisons still run and still FAIL.
"""
import argparse
import json
import math
from pathlib import Path


def validate(path, twisting=True):
    rows = [[float(value) for value in line.split()]
            for line in path.read_text().splitlines() if line.strip()]
    if len(rows) != 2001 or any(len(row) != (5 if twisting else 4) for row in rows):
        raise ValueError(f"Unexpected output shape: {path}")
    if not all(math.isfinite(value) for row in rows for value in row):
        raise ValueError(f"Nonfinite trajectory: {path}")
    if rows[0][:3] != [0.0, -15.0, 20.0] or (twisting and rows[0][3:] != [1.0, -1.0]):
        raise ValueError(f"Unexpected initial state: {path}")
    bad_controls = sum(row[3] != math.copysign(1.0, -row[1]) or
                       row[4] != math.copysign(1.0, -row[2]) for row in rows) if twisting else 0
    max_defect = 0.0
    for left, right in zip(rows, rows[1:]):
        h = right[0] - left[0]
        if not .04999999999 < h < .05000000001:
            raise ValueError(f"Unexpected sample interval: {path}")
        force = 300 * left[3] + 60 * left[4] if twisting else left[3]
        equilibrium = -force / 19
        x, v = left[1] - equilibrium, left[2]
        k = math.sqrt(20)
        decay, ch, sh = math.exp(-h), math.cosh(k*h), math.sinh(k*h)/k
        expected_x = equilibrium + decay * (ch*x + sh*(x+v))
        expected_v = decay * (ch*v + sh*(19*x-v))
        max_defect = max(max_defect, abs(right[1]-expected_x), abs(right[2]-expected_v))
    # A local equation check, distinct from the unchanged upstream golden tolerance.
    if bad_controls or max_defect > 2e-10:
        raise ValueError(f"Invalid control/dynamics: {path}: {bad_controls=}, {max_defect=}")
    return {"file": path.name, "rows": len(rows),
            "control_sign_mismatches": bad_controls if twisting else None,
            "control_sign_check_applies": twisting,
            "max_local_dynamics_defect": max_defect, "local_defect_limit": 2e-10,
            "status": "pass", "counts_as_upstream_reference_pass": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    directory = args.build / "control/src/tests"
    result = {"validation": "independent-local-dynamics-and-twisting-control-law",
              "trajectories": [validate(directory / name) for name in
                               ("explicitTwisting_ZOH.dat", "explicitTwisting_Lsodar.dat")] +
                              [validate(directory / name, twisting=False) for name in
                               ("eSMC_ZOH.dat", "eSMC_Lsodar.dat")]}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("SICONOS_LOCAL_TRAJECTORY_VALIDATION=" + json.dumps(result))


if __name__ == "__main__":
    main()
