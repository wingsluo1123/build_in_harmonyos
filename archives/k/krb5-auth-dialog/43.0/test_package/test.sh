#!/bin/sh
# L0c test source — CLI contract for krb5-auth-dialog 43.0.
# Invoked by test_package/conanfile.py via self.run() (R34 evidence);
# LD_LIBRARY_PATH (staged runtime closure) is injected by the caller.
STAGED="$1"
OUT="$("$STAGED" --version 2>&1)" || { echo "version run failed: $OUT" >&2; exit 1; }
echo "version output: $OUT"
case "$OUT" in
  *"krb5-auth-dialog 43.0"*) exit 0 ;;
  *) echo "version contract failed: $OUT" >&2; exit 1 ;;
esac
