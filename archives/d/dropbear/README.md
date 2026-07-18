# Dropbear

Dropbear is a small SSH server and client suite for embedded and resource-constrained systems.

The HarmonyOS PC recipe builds the `dropbear`, `dbclient`, `dropbearkey`, and `dropbearconvert` executables with the bundled cryptographic libraries. Shadow-password and login-accounting features are disabled because their APIs are not consistently available on OHOS. Password input and shadow lookups have guarded fallbacks for the same reason.

Upstream: https://matt.ucc.asn.au/dropbear/dropbear.html
