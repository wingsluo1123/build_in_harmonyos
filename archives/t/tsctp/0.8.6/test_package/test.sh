#!/bin/sh
# test_package consumer test for tsctp 0.8.6 (HarmonyOS PC / OHOS aarch64).
#
# Consumer verification of the installed tool (tsctp is an application: there
# are no headers and no library to compile against):
#   1. upstream CLI surface — invalid option prints the upstream usage banner
#      and exits 1 (proves the packaged binary really runs on this OS)
#   2. SCTP code path — server mode reaches socket(IPPROTO_SCTP). Both outcomes
#      are legitimate: a live listener (kernel ships SCTP) or the libc error
#      "Protocol not supported" (kernel ships no SCTP). A signal/crash fails.
#   3. dependency really consumed — the statically linked libsctp entry points
#      are present in the shipped binary, so lksctp-tools was not dropped.
export PATH="$PATH:/system/bin"

fail=0
chk() { # $1=name $2=result(0=pass)
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- tsctp 0.8.6 consumer verification ---"

BIN="$(command -v tsctp 2>/dev/null || true)"
if [ -z "$BIN" ]; then
    echo "FAIL: tsctp not found in PATH ($PATH)"
    exit 1
fi
echo "binary: $BIN"

# --- 1) upstream CLI surface ------------------------------------------------
out="$("$BIN" -Z 2>&1)"
rc=$?
if [ "$rc" = "1" ] \
   && echo "$out" | grep -qF "Usage: tsctp [options] [address]" \
   && echo "$out" | grep -qF -- "-L local_address"; then
    r=0
else
    r=1
    echo "  rc=$rc"
    echo "  out=[$out]"
fi
chk "1 CLI usage surface (-Z => upstream usage banner + exit 1)" "$r"

# --- 2) SCTP code path (server mode) ---------------------------------------
PORT=$((20000 + ($$ % 20000)))
if command -v timeout >/dev/null 2>&1; then
    TO="timeout 8"
else
    TO=""
fi
# shellcheck disable=SC2086
out="$($TO "$BIN" -L 0.0.0.0 -p "$PORT" 2>&1)"
rc=$?
case "$rc" in
    139|134|136|135|132)   # SIGSEGV/SIGABRT/SIGFPE/SIGBUS/SIGILL => real bug
        r=1
        echo "  CRASH: rc=$rc out=[$out]"
        ;;
    *)
        case "$out" in
            *"Protocol not supported"*|*"Address family not supported"*)
                # Documented HarmonyOS kernel limitation: no SCTP stack.
                [ "$rc" = "1" ] && r=0 || r=1
                echo "  note: kernel SCTP stack unavailable, tsctp reported it gracefully (rc=$rc)"
                ;;
            *)
                if [ "$rc" = "124" ] || [ "$rc" = "0" ]; then
                    echo "  note: SCTP listener accepted port $PORT (kernel SCTP stack available)"
                    r=0
                else
                    r=1
                    echo "  rc=$rc out=[$out]"
                fi
                ;;
        esac
        ;;
esac
chk "2 SCTP socket path (server mode, no crash)" "$r"

# --- 3) statically linked libsctp symbols ----------------------------------
if command -v strings >/dev/null 2>&1; then
    SYMS="$(strings "$BIN" 2>/dev/null)"
else
    SYMS="$(grep -a . "$BIN" 2>/dev/null)"
fi
found=0
for sym in sctp_sendmsg sctp_recvmsg sctp_bindx; do
    if echo "$SYMS" | grep -qx "$sym"; then
        found=$((found + 1))
    elif echo "$SYMS" | grep -q "$sym"; then
        found=$((found + 1))
    else
        echo "  missing symbol: $sym"
    fi
done
[ "$found" = "3" ] && r=0 || r=1
chk "3 libsctp linked in ($found/3 upstream SCTP entry points)" "$r"

echo "--- tsctp 0.8.6 consumer: $([ "$fail" = "0" ] && echo "3/3 PASS" || echo "FAILED") ---"
exit "$fail"
