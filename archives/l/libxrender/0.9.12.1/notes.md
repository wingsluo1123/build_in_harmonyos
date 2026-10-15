# libXrender 0.9.12.1

This revision binds the published libx11/6.4.0 ABI closure required by
Cairo-GObject and librsvg. Upstream source remains libXrender 0.9.12.

The native configuration detects HarmonyOS through config.guess/config.sub;
it does not force a cross-compilation host. The private configure execution
copy retains the earlier exact two-site HMDFS umask adjustment. No installed
tool or dependency cache is modified.

Compile-only and link flags are separated for the actual native raw compiler.
Final executable/shared ELF bytes are signed, with regular byte-identical
SONAME aliases. Installed pkg-config metadata is relative to pcfiledir.

Native r006 validation passed: shared/static Conan create RC 0, three real
installed-package consumers and one HarmonyOS signed relocated-provider test
per mode. The original source registers no suite; make -j1 check RC 0. Modes,
symbol checks and assertions are not accumulated as additional independent cases.

Official native finish r003 returned RC 0. Local CI completed 1/1, with L0/L1/L5
PASS and W5 PASS. Its genuine writer-generated .ci-result.json remains ignored runtime state,
archived with the original transaction; the public finish summary embeds its
result and hashes, and exact raw logs are included. Legacy clean-verify could not locate its tarball context;
this warning is not a G0 PASS. Actual recipe clean creates passed in r006 and
official G2. Legacy separate release/debug tar archives are absent; the real
Conan cache archive has independently verified bytes/hash and was not uploaded.

Knowledge increment: E16334 demonstrates a private installed .la view can leak
producer RUNPATH despite successful consumers. r006 uses actual .so/.a files
without .la metadata and verifies the installed ELF has no RPATH/RUNPATH.

The software PR contains only this revision, software-level version metadata
and its KV/MD draft pair. Internal workflow/tool repairs remain private task
execution copies. X server drawing, GTK/wxWidgets full delivery, platform CI
and AI Review are not established by this library's local results.

Platform CI #92187 identified two tracked runtime markers at the JC gate.
They were removed from version control while preserving their exact original
local bytes and transaction archive. No recipe, source, patch or test changed.
