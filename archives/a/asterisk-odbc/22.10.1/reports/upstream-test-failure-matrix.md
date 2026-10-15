# Upstream Test Failure Matrix - asterisk-odbc 22.10.1

## Scope and accounting

This matrix records the full-Asterisk upstream test investigation run on the
HarmonyOS device on 2026-09-10. It is evidence about the separately built
full Asterisk test runner, not a claim that the seven packaged ODBC modules
were loaded together with every full-PBX module.

The source inventory supplied during review is 724 tests. The device runner
registered 599 tests. Its normal, de-duplicated execution result is 559 PASS,
26 FAIL, and 9 NOT RUN. Three dangerous `DO_NOT_RUN` entries and two
intentional PASS/FAIL framework self-tests were not executed. The remaining
125 source-inventory entries were not registered by this runner configuration.

The category-isolation TSV has 620 raw attempts because parent and nested
category invocations overlap. Removing 27 duplicate PASS records leaves 559
PASS, 25 FAIL, and 9 NOT RUN. A separately executed explicit-only WebSocket
test supplies the 26th FAIL. This reconciliation is important: neither raw
category totals nor the consumer probe are used as the upstream denominator.

Artifact base on the device:

```text
/storage/Users/currentUser/ohos-users/codex-asterisk-odbc-upstream/
asterisk-22.10.1-20260909-162000/artifacts
```

The raw category accounting file is
`category-isolation-20260910.tsv`, SHA-256
`671d2c1378a28246d16d43fb84c04d7c749cb454eb296e6c9aab60217a2b2889`.
Each row below names its corresponding XML artifact under that directory.

## Classification rules

- **Runner fixture**: repair by staging the test's required config, sound
  data, writable temporary directory, or test service. This does not belong
  in the `asterisk-odbc` package recipe.
- **Full-PBX core/runtime**: potentially repairable, but only through a
  separately scoped Asterisk core/full-PBX HarmonyOS adaptation and a rerun of
  the affected upstream test. It is not a defect demonstrated in the ODBC
  package.
- **Full-PBX test portability / framework**: a HarmonyOS-versus-Linux semantic
  difference or a full-runner framework defect (rows 16-19). Repairable in the
  full-PBX test port, never in the `asterisk-odbc` recipe.

All five cases previously listed as pending minimal repro (rows 7, 16, 17, 18,
19) have since been reproduced with focused device probes and now carry a
confirmed cause; no row remains unassigned.

No row is classified as inherently unfixable. A test may be out of scope for
this ODBC package while still being fixable in the runner or the full-PBX port.

## The 26 failures

| # | Upstream test | First device evidence | Classification and repair boundary |
|---:|---|---|---|
| 1 | `/apps/app_voicemail/` `test_voicemail_load_config` | XML reports `NA`; the category console records `app_voicemail.c: actual_load_config: Failed to load configuration file`. The staged runner has no `voicemail.conf`. Artifact: `single-_apps_app_voicemail_-category-results.xml`. | **Runner fixture.** Stage the upstream voicemail test configuration, then rerun. Do not alter ODBC modules. |
| 2 | `/apps/app_voicemail/` `vmsayname_exec` | The test fails while playing an extension when its greeting is unavailable. The same runner lacks `voicemail.conf`, and `beep.gsm` is absent from the staged sound tree. Artifact: `single-_apps_app_voicemail_-category-results.xml`. | **Runner fixture.** Supply voicemail configuration and the required sound fixture, then rerun. |
| 3 | `/config/` `config_options_test` | `Could not parse config`. The test declares `config_test.conf`; that file is absent from the staged configuration directory. Artifact: `single-_config_-category-results.xml`. | **Runner fixture.** Stage `config_test.conf` from the upstream test fixture set. |
| 4 | `/funcs/func_env/` `func_file` | `Cannot create temporary directory: Read-only file system`; source calls `mkdtemp` on `/tmp/test_func_file.XXXXXX`. Artifact: `single-_funcs_func_env_-category-results.xml`. | **Runner fixture.** Redirect or bind the test temporary path to the runner `TMPDIR`, or patch the upstream test in a separately scoped test-port change. |
| 5 | `/funcs/func_sayfiles/` `test_SAYFILES_function` | All tested `SAYFILES()` substitutions are empty. The full-runner script disabled core, MOH, and extra sound installation; `beep.gsm` is absent. Artifact: `single-_funcs_func_sayfiles_-category-results.xml`. | **Runner fixture.** Install the sound fixtures required by this full-PBX test. |
| 6 | `/main/file/` `read_dir_test` | `Failed to create directory: /tmp/tmpdir.XXXXXX`. Artifact: `single-_main_file_-category-results.xml`. | **Runner fixture.** Same writable temporary-directory action as row 4. |
| 7 | `/main/json/` `type_timeval` | Device probe: `TZ=America/Chicago date --date=@1360251154` does produce the expected `2013-02-07T09:32:34.000000-0600`, but the built-in loader pins `TZDIR=/usr/share/zoneinfo` in `main/stdtime/tzfile.h`, that directory does not exist on the device, and `ast_tzset()` therefore falls back to GMT, so the JSON timestamp mismatches. Artifact: `single-_main_json_-category-results.xml`. | **Full-PBX core/runtime (timezone data path).** Point the built-in TZ loader at the HarmonyOS zone data, or stage a compatible tzfile tree in the full-PBX runner. Not an ODBC fix. |
| 8 | `/main/json/` `dump_load_null` | File creation returns `NULL`; source uses `/tmp/ast_json.XXXXXX`. Artifact: `single-_main_json_-category-results.xml`. | **Runner fixture.** Use a writable temporary path for this upstream test. |
| 9 | `/main/json/` `dump_load_new_file` | File creation returns `NULL`; source uses `/tmp/ast_json.XXXXXX`. Artifact: `single-_main_json_-category-results.xml`. | **Runner fixture.** Same action as row 8. |
| 10 | `/main/json/` `dump_load_file` | File creation returns `NULL`; source uses `/tmp/ast_json.XXXXXX`. Artifact: `single-_main_json_-category-results.xml`. | **Runner fixture.** Same action as row 8. |
| 11 | `/main/media_cache/` `create_update_off_nominal` | `Failed to create first tmp file: /tmp/test-media-cache-XXXXXX`. Artifact: `single-_main_media_cache_-category-results.xml`. | **Runner fixture.** Redirect the hard-coded temporary path for the test runner. |
| 12 | `/main/media_cache/` `create_update_metadata` | `Failed to create first tmp file: /tmp/test-media-cache-XXXXXX`. Artifact: `single-_main_media_cache_-category-results.xml`. | **Runner fixture.** Same action as row 11. |
| 13 | `/main/media_cache/` `create_update_nominal` | `Failed to create first tmp file: /tmp/test-media-cache-XXXXXX`. Artifact: `single-_main_media_cache_-category-results.xml`. | **Runner fixture.** Same action as row 11. |
| 14 | `/main/message/` `test_message_queue_both_nominal` | Timed out waiting for four expected user events and received zero. The runner stages only an empty `[default]` dialplan, while this test requires its dedicated message dialplan path. Artifact: `single-_main_message_-category-results.xml`. | **Runner fixture.** Stage the upstream message test dialplan/configuration and rerun. The custom-handler-only test passed, which narrows this to the dialplan event path. |
| 15 | `/main/message/` `test_message_queue_dialplan_nominal` | Timed out waiting for four expected user events and received zero. Artifact: `single-_main_message_-category-results.xml`. | **Runner fixture.** Same dedicated dialplan fixture as row 14. |
| 16 | `/main/poll/` `poll_test` | Device probe with three pollfds (`/dev/null` `POLLOUT`, `/dev/zero` `POLLIN`, empty pipe `POLLIN`): the device `poll(0)` reports only `/dev/zero`'s `POLLIN`, while the test requires two ready handles. In this build `ast_poll` and `ast_poll2` call the system `poll`/`ppoll` directly, matching the XML's return of 1. Artifact: `single-_main_poll_-category-results.xml`. | **Full-PBX test portability.** Rewrite this Linux-specific test to use a writable pipe/socket, or change the HarmonyOS POSIX layer's `/dev/null` poll behavior. Not an ODBC or Asterisk-wrapper defect. |
| 17 | `/main/test_capture/` `test_capture_stdout_stderr` | Device probe: the runner's `/bin/sh` produced stdout `zzz` and stderr `foobar`, byte-identical to the assertion. The failure is that `ast_test_capture_command()` returns from `waitpid(..., WNOHANG)` and closes the stdout/stderr pipes immediately, without draining buffered output, so a fast-exiting child loses it. Artifact: `single-_main_test_capture_-category-results.xml`. | **Full-PBX test framework (pipe-drain race).** Keep reading both pipes to EOF after the child exits before closing them and completing `open_memstream`. Not an ODBC fix. |
| 18 | `/main/test_capture/` `test_capture_with_dynamic` | Device probe: the runner's GNU `date --date=@<epoch>` succeeds and its output matches the contract the test computes through `localtime()`. The case shares the premature pipe-close path of row 17. Artifact: `single-_main_test_capture_-category-results.xml`. | **Full-PBX test framework (pipe-drain race).** Same repair as row 17; not a `date` compatibility or ODBC problem. |
| 19 | `/main/test_capture/` `test_capture_with_stdin` | Device probe: the runner's `base64` of `Mary had a little lamb.` returns `TWFyeSBoYWQgYSBsaXR0bGUgbGFtYi4=\n`, byte-identical to the assertion. The failure is again the shared capture helper closing its pipes before reading them. Artifact: `single-_main_test_capture_-category-results.xml`. | **Full-PBX test framework (pipe-drain race).** Same repair as row 17; not a `base64` or ODBC problem. |
| 20 | `/main/voicemail_api/` `nominal_msg_playback` | Test setup creates its metadata but nominal playback fails. The source notes that voicemail operations can silently fail without a real sound file; staged `beep.gsm` is absent and `app_voicemail` did not load its config. Artifact: `single-_main_voicemail_api_-category-results.xml`. | **Runner fixture.** Install voicemail config and core sound fixture, then rerun the group. |
| 21 | `/main/voicemail_api/` `nominal_forward` | Fails to forward a message between test mailboxes after setup. Artifact: `single-_main_voicemail_api_-category-results.xml`. | **Runner fixture.** Same voicemail config and sound-fixture action as row 20. |
| 22 | `/main/voicemail_api/` `nominal_remove` | Fails to remove the test mailbox message after setup. Artifact: `single-_main_voicemail_api_-category-results.xml`. | **Runner fixture.** Same action as row 20. |
| 23 | `/main/voicemail_api/` `nominal_move` | Fails to move a message from `INBOX` to `Family` after setup. Artifact: `single-_main_voicemail_api_-category-results.xml`. | **Runner fixture.** Same action as row 20. |
| 24 | `/main/voicemail_api/` `nominal_snapshot` | Expected one message but observed zero after setup. Artifact: `single-_main_voicemail_api_-category-results.xml`. | **Runner fixture.** Same action as row 20. |
| 25 | `/res/websocket/` `websocket_client_multiple_protocols` | Cannot create a client to `ws://127.0.0.1:8088/ws`. The category console shows `chan_websocket.so` failed to load because `ast_websocket_client_retrieve_by_id` is unresolved. Artifact: `single-_res_websocket_-category-results.xml`. | **Full-PBX core/runtime.** Repair the full-runner module dependency/link graph and provision the local echo endpoint in a separately scoped Asterisk core task. |
| 26 | `/res/websocket/` `websocket_client_create_and_connect` (explicit-only) | Cannot create a client to the same local `/ws` endpoint. Artifact: `single-_res_websocket_-websocket_client_create_and_connect-results.xml`. | **Full-PBX core/runtime.** Same action as row 25. This separately executed explicit-only case is the failure not present in the category TSV. |

## Runtime NOT RUN entries

These are skips, not failures. The runner recorded no detailed reason beyond
`NOT RUN`, so each needs a targeted prerequisite check before it can be
reclassified or executed:

| Category | Tests |
|---|---|
| `/main/sorcery/` | `configuration_file_wizard_retrieve_multiple_all`, `configuration_file_wizard_retrieve_multiple`, `configuration_file_wizard_retrieve_field`, `configuration_file_wizard_with_criteria`, `configuration_file_wizard_with_file_integrity`, `configuration_file_wizard`, `caching_wizard_behavior`, `apply_config` |
| `/main/stdtime/` | `timezone_watch` |

The five protected framework entries remain intentionally outside normal
execution: three dangerous `DO_NOT_RUN` tests and two PASS/FAIL self-tests.

## Repair plan and boundary

All 26 failures now carry a device-verified cause: nineteen are attributable to
omitted test-runner fixtures, two to a broken full-PBX WebSocket module graph,
one to a full-PBX timezone-data path (row 7), one to HarmonyOS `/dev/null` poll
semantics exercised by a Linux-specific test (row 16), and three to a full-PBX
test-capture pipe-drain race (rows 17-19). None demonstrates an ODBC package
runtime failure: the installed-package consumer probe passed for all seven
modules and six sample configurations.

The next full-PBX investigation should be performed on its own issue, branch,
and PR. It must first add runner-only fixtures (`TMPDIR` mapping, required
configs, sound files, and the message dialplan), then apply the timezone-data,
poll-portability, and pipe-drain repairs identified above, and only then
consider a core portability patch. No such runner change belongs in this
`asterisk-odbc` package PR.
