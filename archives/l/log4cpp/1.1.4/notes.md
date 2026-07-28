# log4cpp 1.1.4 OpenHarmony Adaptation Notes

## Scope

- Build the upstream CMake target as a static `log4cpp` library.
- Generate the Autotools-derived `include/log4cpp/config.h` in the Conan recipe
  because upstream CMakeLists.txt does not run `configure`.
- Package headers and `liblog4cpp.a` for downstream consumers such as
  `fastnetmon`.

## Disabled / Not Included

- Upstream Autotools tests are not built in this first dependency PR because
  the current workstation has no OHOS Conan toolchain and the contest CI is
  temporarily unavailable.
- Syslog, remote syslog, and SMTP support are disabled in the generated config
  header to keep the first package focused on local logging APIs and avoid
  assuming OHOS syslog/socket mailer behavior.

## Validation

- Source tarball downloaded from the official SourceForge project download URL.
- SHA256 verified locally:
  `696113659e426540625274a8b251052cc04306d8ee5c42a0c7639f39ca90c9d6`.
- `test_package` compiles and runs a real C++ consumer covering:
  category creation, priority filtering, NDC push/pop, and stream logging to an
  `OstreamAppender`.
