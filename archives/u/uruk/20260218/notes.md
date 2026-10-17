# uruk 20260218 adaptation notes

Uruk is a set of POSIX shell scripts and requires no compiler.  The recipe
installs the three supported entry points and rewrites their shebangs to the
Bash interpreter detected on the target.  It also runs `bash -n` on each script
during the build.

The consumer test never invokes a real firewall.  It creates temporary fake
`iptables` and `ip6tables` commands, points `URUK_CONFIG` at a temporary rc
file, and verifies that `uruk` completes while issuing rule commands to those
fakes.  `uruk-save` is exercised against the same isolated configuration.
