#!/bin/sh
# Standalone consumer test for lsh-utils 2.1 (same sequence as
# test_package/conanfile.py test()).  Used for the recorded on-device run.
#
# Usage:  sh test_lsh_utils.sh <bin-dir> [workdir]
#   <bin-dir>  directory containing lsh-keygen / lsh-writekey / lsh-decrypt-key
#              (the installed package's bin/)
#
# Exit status 0 = round trip succeeded, non-zero = failure.
set -u

BINDIR="${1:?usage: sh test_lsh_utils.sh <bin-dir> [workdir]}"
WORK="${2:-}"

if [ -z "$WORK" ]; then
    WORK=$(mktemp -d 2>/dev/null) || WORK="./lsh-utils-consumer-test.$$"
    mkdir -p "$WORK"
fi
mkdir -p "$WORK"

MAKESEED="$BINDIR/lsh-make-seed"
KEYGEN="$BINDIR/lsh-keygen"
WRITEKEY="$BINDIR/lsh-writekey"
DECRYPTKEY="$BINDIR/lsh-decrypt-key"

for tool in "$MAKESEED" "$KEYGEN" "$WRITEKEY" "$DECRYPTKEY"; do
    if [ ! -x "$tool" ]; then
        echo "FAIL: $tool is missing or not executable" >&2
        exit 1
    fi
done

# The askpass helper must print the passphrase without a trailing newline.
ASKPASS="$WORK/askpass"
printf '#!/bin/sh\nprintf bar\n' > "$ASKPASS"
chmod 755 "$ASKPASS"

PLAIN="$WORK/key.origkey"
ENCRYPTED="$WORK/key"
NEVER="$WORK/key.nevercrypted"
DECRYPTED="$WORK/key.decrypted"

# lsh keeps its yarrow seed file under $HOME/.lsh, so point HOME at the work dir.
echo "== 0. lsh-make-seed (seed the randomness generator)"
HOME="$WORK" "$MAKESEED" -q --sloppy || { echo "FAIL: lsh-make-seed" >&2; exit 1; }

echo "== 1. lsh-keygen (RSA key generation, libhogweed + gmp)"
HOME="$WORK" "$KEYGEN" > "$PLAIN" || { echo "FAIL: lsh-keygen" >&2; exit 1; }
[ -s "$PLAIN" ] || { echo "FAIL: lsh-keygen produced an empty key" >&2; exit 1; }

echo "== 2. lsh-writekey -c aes256-cbc (PKCS#5 / AES-256-CBC) and -c none"
HOME="$WORK" "$WRITEKEY" -c aes256-cbc -p bar -o "$ENCRYPTED" < "$PLAIN" \
    || { echo "FAIL: lsh-writekey -c aes256-cbc" >&2; exit 1; }
HOME="$WORK" "$WRITEKEY" -c none -o "$NEVER" < "$PLAIN" \
    || { echo "FAIL: lsh-writekey -c none" >&2; exit 1; }
[ -s "$ENCRYPTED" ] || { echo "FAIL: no encrypted key produced" >&2; exit 1; }

echo "== 3. lsh-decrypt-key --askpass, then compare with the unencrypted copy"
HOME="$WORK" "$DECRYPTKEY" --in="$ENCRYPTED" --out="$DECRYPTED" --askpass="$ASKPASS" \
    || { echo "FAIL: lsh-decrypt-key" >&2; exit 1; }

if cmp -s "$DECRYPTED" "$NEVER"; then
    echo "PASS: decrypted key is byte-identical to the unencrypted copy"
    exit 0
fi
echo "FAIL: decrypted key differs from the unencrypted copy" >&2
exit 1
