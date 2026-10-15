import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from dyncall_sign import sign_elf

binary = Path(sys.argv[1])
sign_elf(binary)
result = subprocess.run([str(binary)], capture_output=True, env=os.environ.copy(), timeout=30)
print(result.stdout.decode("utf-8", "strict"), end="")
print(result.stderr.decode("utf-8", "strict"), end="", file=sys.stderr)
if result.returncode or b"CONSUMER_1_OF_1_PASS" not in result.stdout:
    raise RuntimeError("Installed-package consumer failed: " + str(result.returncode))
