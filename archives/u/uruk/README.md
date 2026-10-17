# uruk

`uruk` is a shell-based firewall configuration front end for `iptables` and
`ip6tables`.

## Features

- Applies a declarative rc file to the Linux packet-filter tables.
- Provides `uruk`, `urukctl`, and `uruk-save` command-line tools.
- Supports IPv4 and IPv6 rule generation.

## HarmonyOS adaptation

- The three shell entry points are installed with an absolute target Bash
  shebang detected during packaging.
- The recipe performs `bash -n` syntax checks before installation.
- Consumer testing uses fake firewall commands and a temporary `URUK_CONFIG`,
  so it verifies command execution without altering the host firewall.

## Dependencies

- Runtime: Bash, `iptables`, and optionally `ip6tables`

## References

- Upstream: https://mdcc.cx/uruk/
- Source package: https://packages.debian.org/source/sid/uruk
