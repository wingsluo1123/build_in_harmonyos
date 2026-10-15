# Distro OpenEuler

OpenEuler carries `sox-14.4.2` with 7 patches

All have been applied to `sox_ng`.

| Patch | Commit/Issue |
| :---- | :----: |
| sox-14.4.2-bug_1226675_fix           | c57c5e8 |
| sox-14.4.2-bug_1480678_fix           | a7d634f<BR>4281a1d<BR>a5254ef |
| sox-14.4.2-bug_1500553_fix           | #12 |
| sox-14.4.2-bug_1500554_fix           | #16 |
| sox-14.4.2-bug_1500570_fix           | #11 |
| sox-14.4.2-bug_1510923_fix           | #13 |
| sox-14.4.2-fsf_address_fix           | #47 |
| sox-14.4.2-hcom_stopwrite_big_endian | #42 |
| sox-14.4.2-installcheck_fix          | #49 |
| sox-14.4.2-lpc10                     | #45 |
| sox-14.4.2-lsx_symbols               | (*) |

(*) I can't (be bothered to) find the issue/commit in question
but 'lsx_flush' and `lsx_error` have been added to `lsx_symbols`.
