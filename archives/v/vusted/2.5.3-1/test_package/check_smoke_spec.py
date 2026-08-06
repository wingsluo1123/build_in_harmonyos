#!/usr/bin/env python3
"""Static guard for the Vusted smoke spec used by test_package."""

import sys
from pathlib import Path


spec = Path(sys.argv[1])
text = spec.read_text(encoding="utf-8")
required = [
    'describe("vusted smoke"',
    'it("runs inside Neovim"',
    'vim.fn.has("nvim")',
    'require("vusted.helper")',
]
missing = [token for token in required if token not in text]
if missing:
    raise SystemExit("missing Vusted smoke spec token(s): " + ", ".join(missing))

print("vusted smoke spec is present")
