#!/bin/sh
set -eu

package_folder="$1"

for utility in mkfs.erofs fsck.erofs dump.erofs mount.erofs; do
    executable="$package_folder/bin/$utility"
    test -x "$executable"
    "$executable" --help >/dev/null
done
