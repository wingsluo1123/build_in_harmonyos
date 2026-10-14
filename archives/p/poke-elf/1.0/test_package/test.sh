#!/bin/sh
# test_package/test.sh -- consumer tests for poke-elf 1.0 (R34).
# Runs in the conanrun env. POKEDATADIR/POKE_LOAD_PATH are exported
# by test_package/conanfile.py before this script runs.
#
# NOTE: poke's `-L FILE` loads a Poke *file* and exits (shebang mode);
# it is NOT a load-path directory option (poke manual "Invoking poke":
# `-L FILE load the given pickle and exit`). Passing the pickles
# directory to -L makes poke compile the directory itself and fail with
# "input in flex scanner failed", while -c/-s are never processed.
# The documented way to expose out-of-prefix pickles is the
# POKE_LOAD_PATH env var (prepended to load_path at startup; see
# poke-elf manual "Installation"). All invocations below therefore rely
# on POKE_LOAD_PATH + `load elf;` and never pass -L.
set -u

PASS=0; FAIL=0

WORK="$PWD/.elf-work"
rm -rf "$WORK"; mkdir -p "$WORK"

ELFPK="${POKE_ELF_PICKLESDIR:-}"
if [ -z "$ELFPK" ]; then
  echo "FAIL: POKE_ELF_PICKLESDIR is empty"
  exit 1
fi
# Fallback if the conanrun env did not export POKE_LOAD_PATH (e.g. manual run).
if [ -z "${POKE_LOAD_PATH:-}" ]; then
  POKE_LOAD_PATH="$ELFPK"
  export POKE_LOAD_PATH
fi

# --- T1: poke binary works -------------------------------------------------
V=$(poke --version 2>/dev/null | head -1)
case "$V" in
  *"GNU poke"*) echo "PASS: T1 poke --version ($V)"; PASS=$((PASS+1));;
  *) echo "FAIL: T1 poke --version (got: $V)"; FAIL=$((FAIL+1));;
esac

# --- T2: load the elf pickle ----------------------------------------------
if poke --color=no -c 'load elf;' >/dev/null 2>&1; then
  echo "PASS: T2 load elf pickle"; PASS=$((PASS+1))
else
  echo "FAIL: T2 load elf pickle"; FAIL=$((FAIL+1))
fi

# --- T3: ELF file-type constants (ET_EXEC=2, ET_DYN=3) ----------------------
cat > "$WORK/t3.pk" <<'EOF'
load elf;
assert (ELF_ET_EXEC == 2);
assert (ELF_ET_DYN == 3);
print "T3-OK\n";
EOF
R=$(poke --color=no -s "$WORK/t3.pk" 2>/dev/null)
if [ "$R" = "T3-OK" ]; then
  echo "PASS: T3 ELF file-type constants"; PASS=$((PASS+1))
else
  echo "FAIL: T3 ELF file-type constants (got: $R)"; FAIL=$((FAIL+1))
fi

# --- T4: ELF class constants (CLASS32=1, CLASS64=2) -------------------------
cat > "$WORK/t4.pk" <<'EOF'
load elf;
assert (ELF_CLASS_32 == 1);
assert (ELF_CLASS_64 == 2);
print "T4-OK\n";
EOF
R=$(poke --color=no -s "$WORK/t4.pk" 2>/dev/null)
if [ "$R" = "T4-OK" ]; then
  echo "PASS: T4 ELF class constants"; PASS=$((PASS+1))
else
  echo "FAIL: T4 ELF class constants (got: $R)"; FAIL=$((FAIL+1))
fi

# --- T5: AArch64 machine constant (EM_AARCH64=183) ---------------------------
cat > "$WORK/t5.pk" <<'EOF'
load elf;
assert (ELF_EM_AARCH64 == 183);
print "T5-OK\n";
EOF
R=$(poke --color=no -s "$WORK/t5.pk" 2>/dev/null)
if [ "$R" = "T5-OK" ]; then
  echo "PASS: T5 ELF AArch64 machine constant"; PASS=$((PASS+1))
else
  echo "FAIL: T5 ELF AArch64 machine constant (got: $R)"; FAIL=$((FAIL+1))
fi

echo "===="
echo "TOTAL PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
