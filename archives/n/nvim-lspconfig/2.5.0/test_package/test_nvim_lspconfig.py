import os
import sys


root = sys.argv[1]
required = [
    os.path.join(root, "lua", "lspconfig.lua"),
    os.path.join(root, "lua", "lspconfig", "configs", "lua_ls.lua"),
    os.path.join(root, "plugin", "lspconfig.lua"),
    os.path.join(root, "doc", "lspconfig.txt"),
    os.path.join(root, "LICENSE.md"),
]

missing = [path for path in required if not os.path.isfile(path)]
if missing:
    raise SystemExit("missing packaged plugin files: " + ", ".join(missing))

with open(required[0], encoding="utf-8") as handle:
    if "configs" not in handle.read():
        raise SystemExit("lua/lspconfig.lua does not contain expected config loader content")

print("nvim-lspconfig plugin files are packaged")
