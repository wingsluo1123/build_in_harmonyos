"""Run the unchanged upstream summary consumer on all 12 fixed sample files."""

import argparse
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("module_root", type=pathlib.Path)
parser.add_argument("report", type=pathlib.Path)
parser.add_argument("--record-baseline", action="store_true")
args = parser.parse_args()
root = args.module_root.resolve()
sys.path.insert(0, str(root))
sys.dont_write_bytecode = True
import mrtparse

assert pathlib.Path(mrtparse.__file__).resolve().parent == root / "mrtparse"
samples = root / "mrtparse" / "samples"
examples = root / "mrtparse" / "examples"
if not samples.is_dir():
    samples, examples = root / "samples", root / "examples"
names = ("bird_bgp", "bird6_bgp", "bird-mrtdump_bgp", "bird-mrtdump_rib",
         "bird6-mrtdump_bgp", "bird6-mrtdump_rib", "openbgpd_bgp",
         "openbgpd_rib_table", "openbgpd_rib_table-mp", "openbgpd_rib_table-v2",
         "quagga_bgp", "quagga_rib")
environment = os.environ.copy()
environment.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1", TZ="UTC")
results = {}
for name in names:
    sample = samples / name
    command = [sys.executable, "-B", str(examples / "summary.py"), str(sample)]
    process = subprocess.run(command, env=environment, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, check=False)
    count = 0
    errors = []
    reader = mrtparse.Reader(str(sample))
    try:
        for entry in reader:
            count += 1
            if entry.mrt.err is not None:
                errors.append({"record": count, "code": entry.mrt.err, "message": entry.mrt.err_msg})
    finally:
        reader.f.close()
    results[name] = {
        "sample_sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
        "records": count, "decoder_errors": errors,
        "summary_exit_code": process.returncode,
        "summary_stdout_sha256": hashlib.sha256(process.stdout).hexdigest(),
        "summary_stderr_sha256": hashlib.sha256(process.stderr).hexdigest(),
        "summary_stdout": process.stdout.decode("utf-8"),
        "summary_stderr": process.stderr.decode("utf-8"),
    }
    if process.returncode:
        raise RuntimeError("Upstream summary failed for " + name)

if args.record_baseline:
    successful = True
    mismatches = []
else:
    expected = json.loads(pathlib.Path(__file__).with_name("samples-expected.json").read_text())
    mismatches = [name for name in names if results[name] != expected["samples"][name]]
    successful = not mismatches
report = {
    "mode": "original-source-baseline" if args.record_baseline else "sample-validation",
    "platform": platform.platform(), "python": sys.version,
    "module_sha256": hashlib.sha256(pathlib.Path(mrtparse.__file__).read_bytes()).hexdigest(),
    "sample_count": len(results), "mismatches": mismatches, "successful": successful,
    "counting": "12 unmodified upstream sample inputs with summary.py; no upstream automated suite claimed",
    "samples": results,
}
args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))
for name, result in results.items():
    print("%s: records=%d decoder_errors=%d summary_rc=%d" % (
        name, result["records"], len(result["decoder_errors"]), result["summary_exit_code"]))
sys.exit(0 if successful else 1)
