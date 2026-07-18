#!/system/bin/sh
# Test baresip binary installation
if [ -x "$1" ]; then
    echo "baresip binary exists and is executable"
    exit 0
else
    echo "baresip binary not found at $1"
    exit 1
fi