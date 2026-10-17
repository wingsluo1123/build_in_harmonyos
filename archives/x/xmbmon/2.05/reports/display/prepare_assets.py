#!/usr/bin/env python3
"""下载已实测版本的显示依赖并验证哈希，不安装到全局目录。"""
import hashlib
import json
from pathlib import Path
import urllib.request

root = Path(__file__).resolve().parent
records = json.loads((root / "downloads.json").read_text())
for record in records:
    target = root / record["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with urllib.request.urlopen(record["url"], timeout=60) as response:
            target.write_bytes(response.read())
    if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
        raise RuntimeError("SHA256 不一致：" + record["path"])
    print("已验证", record["path"])
files = [{"path": r["path"], "sha256": r["sha256"]} for r in records]
for name in ("install_runtime.py", "local_viewer.py", "xvfb_local_paths.c"):
    files.append({"path": name, "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()})
(root / "MANIFEST.json").write_text(json.dumps({"files": files}, indent=2) + "\n")
