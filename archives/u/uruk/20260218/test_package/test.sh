#!/data/service/hnp/bin/bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
bash_bin="${CONFIG_SHELL:-/data/service/hnp/bin/bash}"

printf '%s\n' "#!${bash_bin}" \
  'printf "%s\n" "$*" >> "$URUK_FAKE_LOG"' \
  'exit 0' > "${tmp}/iptables"
printf '%s\n' "#!${bash_bin}" \
  'printf "%s\n" "$*" >> "$URUK_FAKE_LOG"' \
  'exit 0' > "${tmp}/ip6tables"
chmod 755 "${tmp}/iptables" "${tmp}/ip6tables"
printf '%s\n' 'version=20260218' > "${tmp}/rc"

URUK_CONFIG="${tmp}/rc" \
URUK_IPTABLES="${tmp}/iptables" \
URUK_IP6TABLES="${tmp}/ip6tables" \
URUK_FAKE_LOG="${tmp}/calls.log" \
uruk

test -s "${tmp}/calls.log"
grep -q -- '-A ' "${tmp}/calls.log"

URUK_CONFIG="${tmp}/rc" \
URUK_IPTABLES="${tmp}/iptables" \
URUK_IP6TABLES="${tmp}/ip6tables" \
URUK_FAKE_LOG="${tmp}/calls-save.log" \
uruk-save > "${tmp}/saved.rules"
grep -q '^\*filter' "${tmp}/saved.rules"


echo "[test] uruk consumer checks passed"
