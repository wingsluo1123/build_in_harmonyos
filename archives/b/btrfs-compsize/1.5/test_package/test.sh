#!/bin/sh
# test_package consumer test for btrfs-compsize 1.5.
# Invokes the installed `compsize` binary the way a user would, over two
# host-independent paths that need neither a btrfs filesystem nor root.
export PATH="$PATH:/system/bin"

echo "--- btrfs-compsize consumer verification ---"

# 1. --help → 用法文本, exit 0
out1=$(compsize --help 2>&1); rc1=$?
[ "$rc1" = "0" ] || { echo "FAIL: --help exit=$rc1 (want 0)"; exit 1; }
echo "$out1" | grep -q "Usage: compsize" || { echo "FAIL: usage text missing in [$out1]"; exit 1; }
echo "PASS 1: --help -> usage (exit 0)"

# 2. 空目录 → "No files.", exit 1（不触发需 root 的 btrfs ioctl）
mkdir -p emptydir
out2=$(compsize ./emptydir 2>&1); rc2=$?
[ "$rc2" = "1" ] || { echo "FAIL: empty-dir exit=$rc2 (want 1)"; exit 1; }
echo "$out2" | grep -q "No files." || { echo "FAIL: expected 'No files.' got [$out2]"; exit 1; }
echo "PASS 2: empty dir -> 'No files.' (exit 1)"

echo "test btrfs-compsize 1.5: 2/2 checks PASS"
exit 0
