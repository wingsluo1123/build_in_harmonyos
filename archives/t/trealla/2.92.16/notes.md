# trealla 2.92.16

- Builds the upstream interpreter with its embedded standard library and
  bundled isocline editor.
- Optional libffi and OpenSSL integrations are disabled to keep the package
  dependency-free; POSIX threads remain enabled.
- Embedded library sources are generated with Conan's build-machine Python
  runtime, so cross builds never execute the target-architecture `bin2c`
  helper. A compile-and-link feature probe selects the upstream portable
  thread-signal cancellation fallback when `pthread_cancel` is unavailable.
- The exact 296-case upstream shell suite is packaged and executed by
  `test_package`, followed by an independent arithmetic consumer.
- Local OHOS arm64 `conan create` completed successfully and produced an
  AArch64 ELF interpreter. The 296-case suite and arithmetic consumer are
  packaged; runtime execution is deferred because no OHOS arm64 HDC target is
  connected.
- Official OHOS test and CI results remain pending.
