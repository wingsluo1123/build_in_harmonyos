# ulogd 2.0.9 — build notes

## Disabled modules
- **nfct**: requires `libnetfilter_conntrack >= 1.1.0` (not published on ohpcd)
- **nfacct**: requires `libnetfilter_acct >= 1.0.3` (not published on ohpcd)
- Output plugins (pgsql, mysql, sqlite3, dbi, pcap, json): disabled for minimal build

## Active modules
- **nflog**: requires `libnetfilter_log >= 1.0.2` (available on ohpcd)
- Built-in filters and output plugins (GPRINT, LOGEMU, OPRINT, SYSLOG, XML, NACCT, GRAPHITE)

## OHOS-specific
- config.sub patched for aarch64-unknown-linux-ohos triple
- HMDFS umask 077 temp-dir fix applied in-recipe (same pattern as libnetfilter_log)
- CPPFLAGS suppress conflicting OHOS sysroot uapi headers (linux/socket.h, linux/netfilter/nfnetlink.h)
