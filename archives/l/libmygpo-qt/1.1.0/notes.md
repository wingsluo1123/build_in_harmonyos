# libmygpo-qt 1.1.0 HarmonyOS PC

Complete UrlBuilderTest and JsonCreatorTest executables, including every QtTest slot and lifecycle hook. Consumer links installed shared library and checks config, endpoint, user agent, action values, URLs and Qt metaobject. No external service credentials or live network required.

The upstream inventory contains 32 + 5 named test slots and two lifecycle results per executable: 37 functional cases + 4 lifecycle cases = 41 QtTest results in two CTest groups. The machine-readable HMBS summary uses CTest groups as its count unit.

Pass CMAKE_POLICY_VERSION_MINIMUM=3.5 on the configure command for modern CMake. Published Qt5 CMake metadata has an obsolete ../b//mkspecs path; generate() relocates only a private build-folder copy, preserving the real dependency prefix and pointing at its installed mkspecs. The dependency cache and upstream tests are not edited.

One production-source compatibility patch explicitly serializes date/time setting values with Qt::ISODate, preserving the upstream seconds-only JSON contract. Modern Qt5's implicit QVariant-to-JSON conversion adds .000 and caused testSaveSettingsToJSON to fail (40/41 results before the fix). The original test assertion is retained.

Keep BUILD_SHARED_LIBS=OFF, matching upstream's default for internal test helper libraries without public export annotations. The production target explicitly declares SHARED and remains a shared library. Turning every helper into a shared library causes missing UrlBuilder/JsonCreator symbols at test startup on OHOS.

Source: https://github.com/gpodder/libmygpo-qt/archive/refs/tags/1.1.0.tar.gz (SHA256 `2eab976efbbdd39bae1b436e7dcd2ddffd35241432094f29b69308840a938459`).

Native validation: `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -c tools.build:jobs=1 --build=missing`.

The recipe retains all upstream tests and applies only the declared JSON date compatibility patch. Tests have bounded execution. Build jobs are limited to one to fit shared CI and device resources.
