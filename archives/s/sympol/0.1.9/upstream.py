"""Execute original upstream entries, retaining the complete leaf-test count."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

source, build = map(Path, sys.argv[1:3])
binary = build / "sympol" / "sympol"
# A real target computation precedes the longer regression suite.
probe = subprocess.run([str(binary), "-d", "-i", str(source / "data/cyclic/cyclic4-5.ext")],
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
print(probe.stdout, flush=True)
if probe.returncode or not re.search(r"(?m)^\s*1\s+\d+\s+rational\s*$", probe.stdout):
    raise RuntimeError("target symmetry computation failed")
print("SYMPOL_TARGET_RUNTIME_PASS cyclic4-5 rays=1", flush=True)
perl = (source / "contrib/test-sympol.pl").read_text()
rank = (source / "test/test-rank.cpp").read_text()
cli_count = len(re.findall(r"^\$success\s*&=\s*test_polyhedron\(", perl, re.M))
rank_count = len(re.findall(r"^BOOST_AUTO_TEST_CASE\s*\(", rank, re.M))
if (cli_count, rank_count) != (28, 2):
    raise RuntimeError("upstream test inventory drift")
perl = shutil.which("perl")
if not perl:
    sibling = Path(sys.executable).with_name("perl")
    if not sibling.is_file():
        raise RuntimeError("Perl executable unavailable in PATH or interpreter prefix")
    perl = str(sibling)
cli = subprocess.run([perl, str(source / "contrib" / "test-sympol.pl"), str(build)],
                     text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
print(cli.stdout, flush=True)
if cli.returncode:
    sys.exit(cli.returncode)
cli_passes = len(re.findall(r"\bPASS\s+", cli.stdout))
if cli_passes != cli_count:
    raise RuntimeError("Perl upstream suite completed without all original leaf-test evidence")
rank = subprocess.run([str(build / "test" / "test-rank")],
                      text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
print(rank.stdout, flush=True)
if rank.returncode or not re.search(r"No errors detected", rank.stdout):
    raise RuntimeError("Boost.Test rank entry did not complete")
print(f"SYMPOL_UPSTREAM_RESULT={cli_count+rank_count}/{cli_count+rank_count} PASS "
      f"({cli_count} original CLI cases; {rank_count} Boost.Test cases; 2 CTest entries)", flush=True)
