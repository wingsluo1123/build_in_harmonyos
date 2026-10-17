"""Consume this Conan package, including its three actual upstream distributions."""
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import sys
import termios

python_home = Path(os.environ["TRZSZ_PYTHON_HOME"]).resolve()
assert python_home in Path(sys.executable).resolve().parents, sys.executable
assert Path(sys.prefix).resolve() == python_home, sys.prefix
assert sys.version_info[:3] == (3, 12, 9), sys.version
assert callable(signal.alarm) and signal.SIGALRM
assert callable(termios.tcgetattr)
assert python_home in Path(termios.__file__).resolve().parents, termios.__file__

from trzsz.libs import transfer, utils
from trzsz.svr import recv, send

package = Path(os.environ["TRZSZ_PACKAGE_FOLDER"]).resolve()
for module in (utils, transfer, recv, send):
    assert package in Path(module.__file__).resolve().parents, module.__file__
for name in ("trzsz", "trzsz-libs", "trzsz-svr"):
    distribution = importlib.metadata.distribution(name)
    assert distribution.version == "1.1.5", (name, distribution.version)
    assert package in Path(distribution.locate_file("")).resolve().parents
root_requires = importlib.metadata.requires("trzsz")
assert "trzsz-libs==1.1.5" in root_requires
assert "trzsz-svr==1.1.5" in root_requires
assert importlib.metadata.requires("trzsz-svr") == ["trzsz-libs==1.1.5"]
assert not importlib.metadata.requires("trzsz-libs")
entries = {e.name: e.value for e in importlib.metadata.distribution("trzsz-svr").entry_points}
assert entries["trz"] == "trzsz.svr.recv:main"
assert entries["tsz"] == "trzsz.svr.send:main"
assert send.parse_args(["sample"]).file == ["sample"]
assert recv.parse_args([]).path == "."
print(json.dumps({"consumer": "functional.py", "python": sys.executable, "prefix": sys.prefix,
    "python_version": sys.version, "termios": termios.__file__,
    "distributions": ["trzsz==1.1.5", "trzsz-libs==1.1.5", "trzsz-svr==1.1.5"],
    "result": "PASS", "modules": [m.__file__ for m in (utils, transfer, recv, send)]}))
