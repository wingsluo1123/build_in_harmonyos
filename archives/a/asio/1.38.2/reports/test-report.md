# Native standalone Asio 1.38.2 / C++17

Allowed endpoint 10.62.201.39:2222; boot
bd99f7a0-d41d-46ac-a8f8-bc089feaf6dc; UID 20020084; Clang 15/libc++/Conan 2.29.1.
Run asio-conan-w3-20261015-r1, original official source tar/SHA-256, isolated
cache and exact-byte transfer/readback with one runner launch.

| Original upstream group | Runtime result | Compiled programs |
|---|---:|---:|
| src/tests/Makefile.am, standalone C++17 | 176/176 PASS | 182/182 |
| src/tests/properties/Makefile.am | 171/171 PASS | 171/171 |
| Total | 347/347 PASS | 353/353 |

Six original compile-only targets are built but not added to the runtime test
denominator. Optional OpenSSL/Boost stackful and C++20 configurations are not
enabled, matching the declared selected feature scope; no registered case in
this configuration was removed, skipped or relabeled PASS.

Added packaged consumers: 2/2 PASS. One tests post/steady_timer; the other uses
native OHOS loopback TCP with exact UTF-8 payload, exact-length read and graceful
peer EOF. Both compile against the installed Conan headers, not the source tree.
The end-to-end case is one of the two added cases, not an extra third case.

Full Conan log SHA-256:
`39a6b34ac9664f4f064825ad55f633ab5dd5b267b1adc89822c3c28dad226a33`.
The frozen validator accepted all twelve receipt phases including runner exit,
release and postrelease. Exact collected log and graph are in the task-owned
asio-conan-w3-20261015-r1/collected directory.

Official skill finish additionally ran in asio-finish-w3-20261015-r3.
Conan-verify and the actual W3 CI step passed; the frozen validator accepted all
twelve phases, runner exit, release and no retained task process. Full collected
log SHA-256: `63a8c3ab308d1234ae002a4202339fbf39a90ccbee457f712a05f6d459054dfd`.
The exact official generated CI proof binds W3 log SHA-256
`4a8d9f3472aca796c1f9c655b11eb5ed31448c5471a3723820f98c2653bc9ae5`.
The aggregate remains PARTIAL_POST_W3 (shared pre-existing knowledge graph
warnings step5b/step8). The candidate supplies a paired draft and separate
blocking knowledge/Pre-PR contract; old failed wrappers remain failed.
Platform Review/CI and release are separate; no publication is claimed.
