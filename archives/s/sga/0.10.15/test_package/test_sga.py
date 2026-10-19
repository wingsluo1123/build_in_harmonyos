"""Verify the installed executable, including actual BWT data production."""
import collections
import subprocess
import sys
from pathlib import Path

binary, work = map(Path, sys.argv[1:3])
if not binary.is_file():
    raise RuntimeError("installed executable missing")
work.mkdir(parents=True, exist_ok=False)
sequences = ["AGTCAGTACCGGTTACGATTCGAGCTAGTCGA", "GTCAGTACCGGTTACGATTCGAGCTAGTCGAA",
             "AGTCAGTACCGGTTACGATTCGAGCTAGTCGA"]
reads = work / "输入序列.fa"
reads.write_text("".join(f">seq{i}\n{s}\n" for i, s in enumerate(sequences)), encoding="utf-8")
prefix = work / "index"
subprocess.run([str(binary), "index", "-a", "ropebwt", "--no-reverse", "-t", "1",
                "-p", str(prefix), str(reads)], check=True, cwd=work, timeout=90)
out = work / "恢复序列.fa"
subprocess.run([str(binary), "bwt2fa", "-o", str(out), str(prefix)+".bwt"],
               check=True, cwd=work, timeout=90)
actual = [s for s in out.read_text().splitlines() if not s.startswith(">")]
if collections.Counter(actual) != collections.Counter(sequences):
    raise RuntimeError("installed CLI roundtrip changed sequence contents or multiplicity")
if not Path(str(prefix)+".bwt").is_file():
    raise RuntimeError("installed CLI did not create its index")
print("SGA_CONSUMER_PASS=2/2 installed-index utf8-path-exact-roundtrip", flush=True)
