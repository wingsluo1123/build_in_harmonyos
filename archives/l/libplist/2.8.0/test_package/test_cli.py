import json
from pathlib import Path
import subprocess
import sys

binary, work = map(Path, sys.argv[1:])
if not binary.is_file():
    raise RuntimeError("Installed plistutil missing")
work.mkdir(exist_ok=False)
expected = {"鸿蒙 中文": "保留字符 & < >", "count": 1234567890123, "array": [True, 42, "测试"]}
source = work / "原始 输入.json"
source.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
previous = source
for format_, filename in (("bin", "二进制 输出.plist"), ("xml", "XML 输出.plist"), ("json", "最终 输出.json")):
    output = work / filename
    subprocess.run([str(binary), "-i", str(previous), "-o", str(output), "-f", format_],
                   capture_output=True, check=True, timeout=30)
    if not output.is_file() or not output.stat().st_size:
        raise RuntimeError("Empty conversion output")
    if format_ == "bin" and not output.read_bytes().startswith(b"bplist00"):
        raise RuntimeError("Expected binary plist header")
    previous = output
if json.loads(previous.read_text(encoding="utf-8")) != expected:
    raise RuntimeError("JSON/binary/XML/JSON roundtrip changed values")
invalid = work / "无效 文件.plist"
invalid.write_bytes(b"not-a-plist")
result = subprocess.run([str(binary), "-i", str(invalid), "-f", "json"], capture_output=True, timeout=30)
if result.returncode == 0:
    raise RuntimeError("Invalid input unexpectedly accepted")
print("LIBPLIST_HARMONY_E2E_PASS=1/1 installed-cli utf8-space-path json-bin-xml-json exact-values invalid-input")
