# 1.4.5 adaptation

Source SHA-256: f279606ea8317fd2c8fa6b0f591c084fdfa954612f1e7c9cb667a5f6b77387f3.
Conan dependencies are released binaries, not rebuilt unpublished prerequisites.

- Preserve source Latin-1 where required. Modern Bison gets explicit parser/lexer context and matching yyerror signature.
- Same-named WAP dispatch callbacks are independent initialized module state. Make each definition static; never use -fcommon to merge them.
- Obtain the OHOS tuple from the configured absolute compiler. Preserve and verify original config.guess bytes; recognize linux-ohos in config.sub.
- Forced pthread cancellation is unavailable. Return ENOTSUP under OHOS, preserve other-platform pthread_cancel, and test genuine wake/join.
- Target strcasecmp on the original Latin-1 pair returns equality while its C-locale toupper/tolower preserve the high bytes. Preserve all original six strings and 36 case pairs; use an independent explicit byte-order oracle only on OHOS. Production Octstr algorithms and original strcmp checks stay unchanged. Do not claim all invalid UTF-8 normalizes identically: the E5/FF counterexample has a nonzero native comparison.
- check_http.sh uses a task-build-local client PEM, not read-only /tmp. OpenSSL generates RSA2048/SHA256 matching test credentials in the isolated source tree. Do not lower security level, disable SSL or package private test keys.
- Strict adapter executes all five registered C checks and nine shell checks. Failure remains failure; cleanup binds own session/start/UID/boot and exact CONAN_HOME, excludes inaccessible foreign /proc directories, and does not signal SSH or other tasks.
- Public headers expose libxml2/OpenSSL; Conan propagates their public include/link closure.
- Upstream gw-config embeds prefix=/ and build-cache paths. The package replaces it with a relative package-prefix script; current dependency roots come from Conan buildenv_info. Version works without environment; compiler/linker flags require activating the build environment. The formal finish candidate adds a real installed-script compile/link/run test.

- Official finish r1 reproduced a shutdown race in check_pool_conn: the pool/dictionary/lock was freed before the FDSet callback thread joined. The fix stops writers, rejects new pool inserts under the pool lock during termination, extracts each cached connection under that lock and synchronously unregisters outside it, then joins FDSet before destroying the pool/lock. Keys returned by dict_keys are independent copies. This avoids both callback use-after-free and a wait-for-callback deadlock under the pool lock. Keepalive is not disabled.

Current independent r19 passed native Conan create RC0, upstream14/14, API consumers5/5 plus installed gw-config1/1, and12-phase W3_PASS with process cleanup. LogSHA256:78dd78a9e05af4eddabdee83a3170b585f68075e01a4ed180169296c617a52be.

The exact same product inputs passed official finish r2 G1/G2 and local CI substeps. Its overallRC1 only reflects legacy step5b/step8 staging/knowledge markers; its own final W3 validator rejected6 groups because it retained the old5-group expected count. Preserve that failure, do not relabel r2 W3_PASS. Independent r19 uses the corrected frozen6-group validator and reruns all tests; no cross-run stitching. The official-generated CI result is retained read-only outside the recipe.

No competition CI success or publication is claimed. External telecom hardware is not covered by local loopback tests.
