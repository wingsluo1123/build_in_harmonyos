# IO::Tty 1.31.1 for HarmonyOS PC

Official IO::Tty1.31 with actual target Perl5.42.2 XS, signed native payload and two official refresh-patch generated portability patches. The real PTY descriptor is converted through libc FILE and PerlIO only for the observed OHOS EACCES stat boundary; F_DUPFD preserves standard descriptors.

All9 original programs retain64 assertions:62 applicable passed and exactly2 original non-tty guards accepted as inapplicable, with raw TAP and unchanged original source bytes retained. Three installed consumers cover XS winsize packing, actual raw PTY binary roundtrip and slave winsize ioctl. One independent HarmonyOS test verifies rejection of an unsigned private XS and successful loading after real signing at the same UID and0700 mode.

Formal W3, current-HEAD platform CI, Review and submission have separate evidence gates. Upstream1.31, adaptation revision1.31.1.
