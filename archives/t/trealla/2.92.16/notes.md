# trealla 2.92.16

- Builds the upstream interpreter with its embedded standard library and
  bundled isocline editor.
- Optional libffi and OpenSSL integrations are disabled to keep the package
  dependency-free; POSIX threads remain enabled.
- The exact 296-case upstream shell suite is packaged and executed by
  `test_package`, followed by an independent arithmetic consumer.
- Official OHOS test and CI results remain pending.
