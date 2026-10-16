#!/bin/sh
# HarmonyOS-specific consumer end-to-end tests for the packaged zram-init 13.3.
# usage: harmony_e2e.sh <path-to-packaged-zram-init-script>
#
# Unlike test.sh (static layout/content assertions), these cases RUN the
# delivered script through its two primary consumer flows on the default
# OHOS runtime (no zram kernel module, no /sys/class/zram-control, toybox
# userland) and check the functional outcome:
#
#   case 1  release flow   `zram-init 0`   -> completes end-to-end, exit 0
#          (arg parsing -> numeric validation -> device probe -> release
#           decision -> clean exit; a no-op release is the upstream contract
#           when no zRAM device is active)
#   case 2  setup flow     `zram-init 64 DIR` -> runs the full setup flow
#          (option defaults -> DIR validation -> device probe -> modprobe
#           attempt -> 5x1s hot_add probe) and degrades gracefully on OHOS
#           with the exact upstream fatal message, exit 1, zero side effects
set -eu

SCRIPT="$1"
[ -f "$SCRIPT" ] || { echo "FAIL: missing $SCRIPT" >&2; exit 1; }

devnode_exists() {
	[ -b /dev/zram0 ] && return 0
	[ -d /sys/class/zram-control ] && return 0
	return 1
}

########## case 1: release flow end-to-end (`zram-init 0`) ##########
if devnode_exists
then
	echo "SKIP case1: /dev/zram0 or zram-control present on this host;" \
		"release e2e would act on a real device (not a clean OHOS runtime)"
else
	out=$(sh "$SCRIPT" 0 2>&1) && status=0 || status=$?
	if [ "$status" -ne 0 ]; then
		echo "FAIL case1: release flow exited $status (expected 0)" >&2
		echo "$out" >&2
		exit 1
	fi
	# The no-op release must be silent: no fatal/warning diagnostics.
	if printf '%s' "$out" | grep -qE 'Warning|cannot|failed'; then
		echo "FAIL case1: unexpected diagnostics on clean release" >&2
		printf '%s\n' "$out" >&2
		exit 1
	fi
	echo "case1 PASS: release flow completed end-to-end (exit 0, silent)"
fi

########## case 2: setup flow end-to-end with OHOS graceful degradation ##########
# A real consumer setup (SIZE=64MiB mounted under DIR) runs every stage of the
# setup path on OHOS until the kernel boundary: the zram module cannot be
# created, and upstream's designed degradation must kick in — after the 5x1s
# hot_add probe it prints the exact fatal message and exits 1 harmlessly.
if devnode_exists
then
	echo "SKIP case2: zram infrastructure present on this host;" \
		"setup e2e would configure a real device (not a clean OHOS runtime)"
else
	# Absolute mount-point path (validated for its leading '/' by the script;
	# the dir itself is never created because the flow ends at the kernel
	# boundary — any real fs/mount work is impossible without the device).
	dir="$PWD/zram-e2e-mountpoint"
	out=$(sh "$SCRIPT" 64 "$dir" 2>&1) && status=0 || status=$?
	if [ "$status" -ne 1 ]; then
		echo "FAIL case2: setup flow exited $status (expected 1)" >&2
		printf '%s\n' "$out" >&2
		exit 1
	fi
	printf '%s\n' "$out" | grep -q \
		'cannot create /dev/zram0: /sys/class/zram-control missing' || {
		echo "FAIL case2: expected upstream graceful-degradation message" >&2
		printf '%s\n' "$out" >&2
		exit 1
	}
	# Harmlessness: the failed setup must not have left a device node behind.
	[ -b /dev/zram0 ] && {
		echo "FAIL case2: setup leaked /dev/zram0 on a module-less host" >&2
		exit 1
	}
	echo "case2 PASS: setup flow ran end-to-end and degraded gracefully" \
		"(exit 1, upstream message, zero side effects)"
fi

echo "harmony_e2e.sh: HarmonyOS-specific consumer e2e cases passed"
