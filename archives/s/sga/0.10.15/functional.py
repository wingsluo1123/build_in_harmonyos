"""Small deterministic functional checks; no external sequence downloads."""
import collections
import subprocess
import sys
from pathlib import Path

binary, root = map(Path, sys.argv[1:3])
print("SGA_UPSTREAM_TESTS=0/0 (no registered upstream TESTS/check_PROGRAMS)", flush=True)
if not binary.is_file():
    raise RuntimeError("selected package executable is absent")
root.mkdir(parents=True, exist_ok=False)
reads = ["ACGTGACTGACCTAGGCTAACCGTACGATGCA", "TTGACTGACCTAGGCTAACCGTACGATGCATT",
         "GACTGACCTAGGCTAACCGTACGATGCATTGG", "ACGTGACTGACCTAGGCTAACCGTACGATGCA"]
input_file = root / "reads.fa"
input_file.write_text("".join(f">read{i}\n{s}\n" for i, s in enumerate(reads)))

def run(*args):
    p = subprocess.run([str(binary), *map(str, args)], cwd=root, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    print(p.stdout, flush=True)
    if p.returncode:
        raise RuntimeError(f"SGA command failed rc={p.returncode}: {args}")
    return p.stdout

assert "0.10.15" in run("--version")
checks = 1
for algorithm in ("sais", "ropebwt"):
    prefix = root / algorithm
    run("index", "-a", algorithm, "--no-reverse", "-t", "1", "-p", prefix, input_file)
    bwt = Path(str(prefix) + ".bwt")
    if not bwt.is_file() or bwt.stat().st_size == 0:
        raise RuntimeError("index command did not create a BWT")
    checks += 1
    output = root / (algorithm + "-roundtrip.fa")
    run("bwt2fa", "-o", output, bwt)
    actual = [s for s in output.read_text().splitlines() if not s.startswith(">")]
    if collections.Counter(actual) != collections.Counter(reads):
        raise RuntimeError("index/inverse-BWT roundtrip changed reads or multiplicity")
    checks += 1
bad = subprocess.run([str(binary), "nonexistent-sga-command"], cwd=root,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)
if bad.returncode == 0:
    raise RuntimeError("invalid command unexpectedly succeeded")
checks += 1
if checks != 6:
    raise RuntimeError("functional check count drift")
print("SGA_FUNCTIONAL_PASS=6/6 version two-indexes two-exact-roundtrips invalid-command", flush=True)
