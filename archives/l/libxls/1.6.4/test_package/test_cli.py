import csv
import io
from pathlib import Path
import shutil
import subprocess
import sys

binary, fixture, work = map(Path, sys.argv[1:])
if not binary.is_file() or not fixture.is_file():
    raise RuntimeError("Installed CLI/fixture missing")
work.mkdir(exist_ok=False)
named = work / "鸿蒙 工作簿.xls"
shutil.copyfile(fixture, named)
listing = subprocess.run([str(binary), str(fixture), "-l"], capture_output=True, timeout=30, check=True).stdout.decode("utf-8").splitlines()
if len(listing) != 4 or listing[0] != "FILE: " + str(fixture):
    raise RuntimeError("Expected three named worksheets")
def convert(path):
    output = subprocess.run([str(binary), str(path), "-t", listing[1]], capture_output=True, timeout=30, check=True).stdout
    header, separator, content = output.partition(b"\n")
    if not separator or header != ("FILE: " + str(path)).encode("utf-8"):
        raise RuntimeError("CLI filename banner mismatch")
    return content
reference = convert(fixture)
actual = convert(named)
if not actual or actual != reference:
    raise RuntimeError("UTF-8 path conversion output differs")
rows = list(csv.reader(io.StringIO(actual.decode("utf-8")), delimiter=";"))
if len(rows) != 24 or max(map(len, rows)) != 11:
    raise RuntimeError(f"XLS conversion geometry mismatch: rows={len(rows)}, max_columns={max(map(len, rows), default=0)}")
missing = subprocess.run([str(binary), str(work / "不存在.xls")], capture_output=True, timeout=30)
if missing.returncode == 0:
    raise RuntimeError("Missing workbook unexpectedly accepted")
print("LIBXLS_HARMONY_E2E_PASS=1/1 installed-cli utf8-space-path 24x11 missing-file-rejection")
