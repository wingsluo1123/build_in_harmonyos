# Automake test identity is not necessarily the result filename

An upstream suite may genuinely report all tests passing and then fail in a
separate collector that looks for `<full-test-name>.trs`. Automake removes a
configured test extension when naming its result files. Do not confuse this
accounting failure with an upstream test failure, but do not turn missing
records into success either.

Read the original TESTS inventory and the generated TEST_EXTENSIONS/result-name
contract. Preserve full original names as test identities and preserve the
denominator. Derive the corresponding stem, require a unique mapping for every
entry, and read exactly one terminal PASS from each mapped result. Independently
cross-check aggregate TOTAL/PASS/SKIP/FAIL. Unknown extension rules, duplicate
stems or missing records must fail closed.

Native libplist 2.8.0 provided the counterexample: all 43 tests passed, but the
first collector requested `empty.test.trs` instead of `empty.trs`. The initial
transaction remained FAIL. A new run with the correct explicit `.test` mapping
passed both shared/static builds, 43/43 original tests and 2/2 packaged consumers
per mode. Full log SHA-256:
`1996d1cb59884369fd364210edb965afcd3dda29096bc681ea04ff600307f132`.

This is distinct from ordering paired evidence by test ID or excluding tests:
it corrects the identity-to-result-file mapping without changing any upstream
source, assertion or registration. It applies to extension-aware Automake
collectors, not arbitrary test harnesses with unrelated filename conventions.
