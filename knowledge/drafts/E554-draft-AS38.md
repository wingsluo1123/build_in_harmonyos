# Build-only coverage and runtime TESTS are different inventories

A header-only C++ source tag can omit generated Autotools files without omitting
its original test definitions. If replaying these definitions directly on a
native SDK, preserve both `check_PROGRAMS` and `TESTS`: the former may contain
intentional compile-only checks absent from the latter.

Evaluate the original feature conditions against the declared compiler standard
and selected package dependencies. Reject unknown conditions or unresolved
source mappings. Require unique runtime IDs and `TESTS` to be a subset of
`check_PROGRAMS`, not necessarily equal. Compile every enabled program, execute
each registered runtime entry, and record compilation separately from runtime
results with exact source/binary/log hashes. Never count internal assertions or
build-only targets as extra runtime cases.

The native standalone Asio 1.38.2 C++17 experiment exposed six such build-only
unit programs: coroutine and five generic protocol/header checks. It compiled
353 programs and executed 347 registered runtime programs (176 unit, 171
properties), all successfully. Packaged-header event/timer and TCP/Unicode/EOF
consumers also passed 2/2. Full log SHA-256:
`39a6b34ac9664f4f064825ad55f633ab5dd5b267b1adc89822c3c28dad226a33`.

The selected configuration excludes optional Boost stackful/OpenSSL and C++20
features; it does not claim those untested configurations. This method is not a
general substitute for arbitrary build-system logic: projects with unsupported
conditions, generated sources, unresolved per-target flags or unproven feature
states must use their real bootstrap path or fail closed.
