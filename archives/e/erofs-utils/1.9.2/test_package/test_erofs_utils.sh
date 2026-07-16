#!/bin/sh
set -eu

mkfs.erofs --help >/dev/null
fsck.erofs --help >/dev/null
dump.erofs --help >/dev/null
mount.erofs --help >/dev/null
