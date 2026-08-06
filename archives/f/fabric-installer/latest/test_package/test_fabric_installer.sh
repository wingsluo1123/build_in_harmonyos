#!/usr/bin/env bash
# Smoke test for fabric-installer conan package.
# Verifies that install-fabric.sh exists, has a valid shebang,
# passes bash -n syntax check, and responds to --help.

set -e

BIN_DIR="$1"

if [ -z "$BIN_DIR" ]; then
    echo "Usage: $0 <bin_dir>"
    exit 1
fi

# 1. Script exists
if [ ! -f "${BIN_DIR}/install-fabric.sh" ]; then
    echo "ERROR: install-fabric.sh not found in ${BIN_DIR}"
    exit 1
fi
echo "✓ install-fabric.sh exists"

# 2. Shebang check
if ! head -1 "${BIN_DIR}/install-fabric.sh" | grep -q '#!'; then
    echo "ERROR: install-fabric.sh has no shebang"
    exit 1
fi
echo "✓ shebang present"

# 3. Bash syntax check
bash -n "${BIN_DIR}/install-fabric.sh"
echo "✓ bash -n syntax check passed"

# 4. --help responds with expected options
bash "${BIN_DIR}/install-fabric.sh" --help 2>&1 | grep -q "fabric-version" || {
    echo "ERROR: --help does not show fabric-version option"
    exit 1
}
echo "✓ --help output verified"

echo ""
echo "fabric-installer: all tests passed"
