# qt6-mqtt 6.11.1 target test report

## Status

Built and tested on the OpenHarmony PC target with the native
aarch64-linux-ohos clang 15 toolchain (profile `ohos-aarch64`, Conan
2.29.1, CMake/CTest from hnp). `conan create` returned 0, all 4
runnable upstream CTest programs passed, and the HarmonyOS consumer
feasibility test passed. Logical result: upstream 4/4 (100%) +
consumer 1/1.

## Log retention note

The raw full logs are local reproduction artefacts and are **not** part
of the pull request — only the report files are committed
(`test-report.md`, `conan-verify-report.md`). Every log path below is
the local reproduction path, and the conclusive excerpts are inlined
here so the assertions can be checked without the raw logs.

| Artefact | Log (local) | Lines | Exit code | SHA256 |
|---|---|---:|---|---|
| conan create (recipe build + upstream ctest + test_package) | `_scratch/qtmqtt-6.11.1/logs/conan-create.log` | 507 | 0 | `9f4eb71bdfe44d3b3dc0f3c6de6af95214932a77a13ea32154f84ea61a0e5145` |

Reproduction command:

```bash
conan create archives/q/qt6-mqtt/6.11.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## Upstream boundary

`ctest -N` in the recipe build tree registers **11** programs (the
`0001-tests-enable-harmonyos.patch` extends the upstream
`WIN32 OR (LINUX AND NOT CMAKE_CROSSCOMPILING)` gate with
`CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"`; without it zero tests are
registered on OHOS):

| Registered program | Runnable without external MQTT broker |
|---|---|
| module_includes | yes |
| tst_conformance_Tcp_4 | no (`MQTT_TEST_BROKER`) |
| tst_qmqttclient_Tcp_4 | no (`MQTT_TEST_BROKER`) |
| tst_qmqttconnectionproperties_Tcp_4 | no (`MQTT_TEST_BROKER`) |
| tst_qmqttlastwillproperties_Tcp_4 | no (`MQTT_TEST_BROKER`) |
| tst_qmqttpublishproperties_Tcp_4 | no (`MQTT_TEST_BROKER`) |
| tst_qmqttsubscription_Tcp_4 | no (`MQTT_TEST_BROKER`) |
| tst_qmqttsubscriptionproperties_Tcp_4 | no (`MQTT_TEST_BROKER`) |
| tst_qmqttcontrolpacket_Tcp_4 | yes |
| tst_qmqtttopicfilter_Tcp_4 | yes |
| tst_qmqtttopicname_Tcp_4 | yes |

The 7 broker-dependent programs `qFatal` in `initTestCase` when
`MQTT_TEST_BROKER`/`MQTT_TEST_BROKER_LOCATION` are absent; upstream
does not bundle a broker (GitHub v6.11.1 `tests/common/` only contains
`broker_connection.h`; Qt CI provisions the paho broker externally).
They are recorded in `test_package/MANIFEST.yml`
`conditional_upstream_tests` with `condition: MQTT_TEST_BROKER` and are
not executed, so no result is fabricated.

## Upstream result

### Test command

Executed inside the recipe `build()` with the Conan runtime
environment (`VirtualRunEnv`), after `cmake --build`:

```
ctest --test-dir <build> -R "^(module_includes|tst_(qmqttcontrolpacket|qmqtttopicfilter|qmqtttopicname)_Tcp_4)$" --output-on-failure -j1
```

### Statistics

- Command: see above; executed via `/data/service/hnp/bin/ctest`
- Total: 4 (registered runnable set; 11 registered overall)
- Passed: 4
- Failed: 0
- Skipped: 0

### Per-case results (from `_scratch/qtmqtt-6.11.1/logs/conan-create.log`)

```
1/4 Test  #1: module_includes ..................   Passed   11.12 sec
2/4 Test  #4: tst_qmqttcontrolpacket_Tcp_4 .....   Passed    0.09 sec
3/4 Test #10: tst_qmqtttopicname_Tcp_4 .........   Passed    0.08 sec
4/4 Test #11: tst_qmqtttopicfilter_Tcp_4 .......   Passed    0.07 sec

100% tests passed, 0 tests failed out of 4
```

## HarmonyOS consumer feasibility test (test_package)

The consumer compiles against the packaged native `Qt6MqttConfig.cmake`
(`cmake_find_mode=none`, upstream targets preserved) and runs on the
OHOS device:

```
qt6-mqtt/6.11.1 (test package): RUN: ./test_package
qt6-mqtt HarmonyOS consumer feasibility test passed
```

16 assertions covering: QMqttClient lifecycle/default state, MQTT 5.0
protocol selection, QMqttConnectionProperties
(sessionExpiryInterval/maximumReceive), client-level last will plus
QMqttLastWillProperties (willDelayInterval/messageExpiryInterval)
round-trip, QMqttTopicName validation and QMqttTopicFilter wildcard
matching. Source: `test_package/test_package.cpp`; inventory:
`test_package/MANIFEST.yml`.

## SONAME quality gate (E537 family)

The OHOS CMake platform module does not define the SONAME flag, so the
first build shipped `libQt6Mqtt.so` without `DT_SONAME`
(`IMPORTED_NO_SONAME TRUE` in the installed targets file, W3 L5a/L5c
failures). Fixed in the recipe with the established E537 precedent
(`archives/q/qaccessibilityclient/0.6.0`):

```python
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
```

Final artefact verification:

```
$ llvm-readelf -d <pkg>/lib/libQt6Mqtt.so | grep -iE 'soname|needed'
  (NEEDED)  libQt6Network.so.6
  (NEEDED)  libQt6Core.so.6
  (NEEDED)  libc++_shared.so
  (NEEDED)  libc.so
  (SONAME)  libQt6Mqtt.so.6
```

The installed tree now carries the full `libQt6Mqtt.so → .so.6 →
.so.6.11.1` chain and zero `IMPORTED_NO_SONAME` occurrences. Because
musl's loader ignores DT_RUNPATH, the recipe also exports the
build-tree lib dir on `LD_LIBRARY_PATH` for the in-tree CTest run.

## Dependency verification (R36)

`conan download "qtbase/6.11.1" -r=ohpcd -p="os=OHOS AND arch=armv8 AND
build_type=Release"` succeeded (package
`01d92cf349a0dd98ff915f4bd99a04430171517f`, package revision
`bc3cac65e3f838c4ef70af2d9639bb06`), then the created package consumed
exactly that binary. No `--build=missing` fallback was used.
