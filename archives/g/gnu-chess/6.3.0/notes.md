# GNU Chess 6.3.0

- Builds the command-line engine without optional readline and gettext
  integrations.
- During OHOS shutdown, completed engine and adapter workers are joined; only
  the potentially blocked input reader is detached because the platform does
  not provide `pthread_cancel`.
- The release contains no automated upstream test suite.
- The consumer checks version/help output and completes the UCI `uci`,
  `isready`, and `quit` protocol handshake.
- Local OHOS arm64 `conan create` completed successfully and produced an
  AArch64 ELF engine. Upstream test count is 0 because the release provides no
  automated suite; the CLI/UCI runtime checks are deferred because no OHOS
  arm64 HDC target is connected.
- Official OHOS test and CI results remain pending.
