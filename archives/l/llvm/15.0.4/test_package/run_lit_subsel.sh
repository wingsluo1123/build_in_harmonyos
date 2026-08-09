#!/bin/sh
# LLVM 15.0.4 R3-A lit 入口封装 —— run_lit_subsel.sh（临时 worktree 实测版，不入库）
# 包装 llvm-lit：把源码 llvm/test 映射到本目录 lit.site.cfg.py，跑 R3 规定子集。
set -u
ENTRY="/storage/Users/currentUser/tmp/llvm-r3a-lit-entry"
SRC="/storage/Users/currentUser/tmp/adaptivecpp-r6-llvm15-source/llvm-project-15.0.4.src"
PY="${PYTHON:-python3}"

cat > "$ENTRY/llvm-lit-wrapper.py" <<'PYEOF'
import os, sys
SRC = "/storage/Users/currentUser/tmp/adaptivecpp-r6-llvm15-source/llvm-project-15.0.4.src"
ENTRY = "/storage/Users/currentUser/tmp/llvm-r3a-lit-entry"
sys.path.insert(0, os.path.join(SRC, "llvm", "utils", "lit"))
from lit.main import main
config_map = {}
config_map[os.path.normcase(os.path.realpath(os.path.join(SRC, "llvm", "test")))] = os.path.join(ENTRY, "lit.site.cfg.py")
builtin_parameters = {"build_mode": "Release"}
builtin_parameters["config_map"] = config_map
sys.exit(main(builtin_parameters))
PYEOF

"$PY" "$ENTRY/llvm-lit-wrapper.py" "$@"
