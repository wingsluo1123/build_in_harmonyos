# kamailio-tlsa

Kamailio's TLSA module embeds static OpenSSL and supplies SIP TLS transport.
The 6.0.6 adaptation isolates OpenSSL symbols and fork-time thread-key ownership.
It requires a matching core; see `6.0.6/integration.md` for the OHOS foreground
core patch and `6.0.6/notes.md` for source, dependency and test evidence.
