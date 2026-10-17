# libkgapi 25.12.3 notes

## Scope

This package provides the `KPim6GAPI` CMake package and Google API libraries
needed by `kmailtransport`, especially `KPim6::GAPICore`.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables KDE PIM CMake on OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips poqm translation installation.
- `BUILD_QCH=OFF` skips optional API documentation.
- `BUILD_TESTING=ON` keeps upstream fake-network CTest coverage enabled.
- Three calendar timezone serialization tests are excluded because the OHOS Qt
  runtime does not resolve the `Europe/Prague` IANA timezone and serializes a
  fixed UTC offset instead.
- `BUILD_SASL_PLUGIN=ON` builds the upstream XOAUTH2 SASL plugin.
- `0001-Accept-Conan-cyrus-sasl-CMake-target.patch` maps the repository
  `cyrus-sasl::cyrus-sasl` target to upstream's expected `Sasl2` result.
- `0002-Honor-KF_SKIP_PO_PROCESSING-for-poqm.patch` makes poqm installation
  honor the same translation-skip knob used by the other KDE recipes.
- Installed OHOS ELF files are re-signed after CMake installation.

## Verification

- Source archive SHA256 was verified against
  `3d8f6dd6e0d4274102cbf7c3dff67d8cef074e25fbf34bb8e505fd38273656b1`.
- OHOS aarch64 `conan create` passed.
- Full package reference:
  `libkgapi/25.12.3#53e0e6c3bc796050631a82dc04f1fd58:8280d4feb4ca5e782aabe7cc682779b9168511cf#3dd6b0a6c00fe66fc7de9e6bf54cae42`
- Upstream CTest passed 46/46 after excluding the three OHOS Qt timezone
  database-sensitive tests listed below.
- The package installed and signed 9 OHOS ELF files, including the
  `libkdexoauth2` SASL plugin.
- The Conan `test_package` found `KPim6GAPI`, linked a CMake consumer against
  `KPim6::GAPICore` and `KPim6::GAPICalendar`, ran CTest 1/1, and verified
  account scope plus calendar event API smoke coverage.

## Upstream Tests Not Run

- `calendar-eventcreatejobtest`
- `calendar-eventmodifyjobtest`
- `calendar-freebusyqueryjobtest`
