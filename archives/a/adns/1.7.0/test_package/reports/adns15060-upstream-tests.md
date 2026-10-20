# adns 1.7.0 HarmonyOS 测试报告

## 最终验证

- 设备工作目录：`/storage/Users/currentUser/work/psj/adns15060`
- Conan 缓存：`/storage/Users/currentUser/work/psj/adns15060/ch-adns15060`
- 构建命令：`conan create /storage/Users/currentUser/work/psj/adns15060/archives/a/adns/1.7.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --conf tools.build:jobs=2`
- `conan create` 退出码：`0`，见 `adns15060-conan-create.exit`
- 上游命令：`make check`
- 上游用例清点：`find regress -maxdepth 1 -type f -name 'case-*.sys' | wc -l`，N=102
- 最终上游结果：`UPSTREAM-SUMMARY total=102 pass=102 fail=0 notrun=0`
- 消费者测试：`PASS: adns address conversion and negative checks`；8/8 项断言通过
- 最终汇总原始日志：`adns15060-conan-create.log`（SHA-256 `ABA73C3FFD1AD76263A99B63C5AE988EF9CC959EF14273D6430085F998490F8B`）
- 上游原始 `make check` 输出：`adns15060-upstream-make-check.log`（SHA-256 `74E4CEB095F7C920F9AD13B85D832186FFCE4F3E7D06D20D869B636E269CF5AA`）
- 逐用例结果：`adns15060-upstream-results.tsv`（SHA-256 `FEBAD95E5D0142C173476A2DEF62B13D1EF77EDA3E634E839D4B5355A88B78FE`）

## 上游期望输出调整记录

首次未调整期望文本的设备运行中，`make check` 的原始失败清单为 `failed tests: 2ndservtcp connfail tcpautosysmissingserv`。完整基线日志保存在 `adns15060-upstream-baseline-unmodified-fixtures.log`（SHA-256 `76992EF6D66E77FCDC11288CB7E0AF4BE6386A87A05D89C9BAECA50DD21B87B5`）。三项均已实跑；失败来自 OHOS `strerror()` 的英文描述与上游记录平台不同，测试输入中的 errno 和 syscall 轨迹相同，轨迹均已消费完毕。仅更新 `.out` 期望字符串，未修改 `.sys` 轨迹或测试逻辑：

| 用例 | 首轮设备原始差异 | 具体原因 | 修改后 |
| --- | --- | --- | --- |
| `2ndservtcp` | `-adns warning: TCP connection failed: connect/read: No route to host (NS=172.18.45.36)`<br>`+adns warning: TCP connection failed: connect/read: Host is unreachable (NS=172.18.45.36)` | 记录的 errno 为 `EHOSTUNREACH`；HarmonyOS 的 `strerror(EHOSTUNREACH)` 返回 `Host is unreachable`。 | PASS |
| `connfail` | `-davenant.greenend.org.uk flags 2 type 1adns warning: TCP connection failed: connect: Socket operation on non-socket (NS=172.18.45.36)`<br>`+davenant.greenend.org.uk flags 2 type 1adns warning: TCP connection failed: connect: Not a socket (NS=172.18.45.36)` | 记录的 errno 为 `ENOTSOCK`；HarmonyOS 的 `strerror(ENOTSOCK)` 返回 `Not a socket`。同一用例中的四条 `ENOTSOCK` 输出均按相同方式调整。 | PASS |
| `tcpautosysmissingserv` | `-adns warning: TCP connection failed: connect/read: No route to host (NS=172.18.45.10)`<br>`+adns warning: TCP connection failed: connect/read: Host is unreachable (NS=172.18.45.10)` | 记录的 errno 为 `EHOSTUNREACH`；HarmonyOS 的 `strerror(EHOSTUNREACH)` 返回 `Host is unreachable`。 | PASS |

上述输出夹具变更由 `patches/0003-ohos-errno-messages.patch` 显式记录，并在 `test_package/MANIFEST.yml` 逐项声明。基线 runner 曾按名称前缀把 `tcpautosysmissingserv` 重复计入 `tcpautosys`；runner 已改为精确匹配完整的 `case-tcpautosysmissingserv -` 标记。最终 N 仍为 102，最终逐项结果见 TSV，全部 102 项通过。

## 最终逐用例结果

| 用例 | 状态 | 上游原始状态行 |
| --- | --- | --- |
| `1stservbroken` | PASS | `1stservbroken` |
| `1stservtotcp` | PASS | `1stservtotcp` |
| `2ndservok` | PASS | `2ndservok` |
| `2ndservtcp` | PASS | `2ndservtcp` |
| `aaaa-simple` | PASS | `aaaa-simple` |
| `aaaa-sort` | PASS | `aaaa-sort` |
| `abbrev` | PASS | `abbrev` |
| `abbrevto` | PASS | `abbrevto` |
| `addr-multi-af` | PASS | `addr-multi-af` |
| `adh-cancel` | PASS | `adh-cancel` |
| `adh-cancel2` | PASS | `adh-cancel2` |
| `adh-cancel3` | PASS | `adh-cancel3` |
| `adh-norm` | PASS | `adh-norm` |
| `adh-pipe` | PASS | `adh-pipe` |
| `adh-reverse-pipe` | PASS | `adh-reverse-pipe` |
| `alr-norm` | PASS | `alr-norm` |
| `alr-slow` | PASS | `alr-slow` |
| `arf-norm` | PASS | `arf-norm` |
| `arf-text` | PASS | `arf-text` |
| `bogus-sortlist` | PASS | `bogus-sortlist` |
| `brokenmail` | PASS | `brokenmail` |
| `child` | PASS | `child` |
| `cnametocname` | PASS | `cnametocname` |
| `comprinf` | PASS | `comprinf` |
| `connfail` | PASS | `connfail` |
| `datapluscname` | PASS | `datapluscname` |
| `datapluscnamewait` | PASS | `datapluscnamewait` |
| `dh-ptr-aaaa` | PASS | `dh-ptr-aaaa` |
| `flags10` | PASS | `flags10` |
| `flags9` | PASS | `flags9` |
| `formerr` | PASS | `formerr` |
| `huasenchem` | PASS | `huasenchem` |
| `lockup` | PASS | `lockup` |
| `longdom0` | PASS | `longdom0` |
| `longdom1` | PASS | `longdom1` |
| `longdomsrch0` | PASS | `longdomsrch0` |
| `longdomsrch1` | PASS | `longdomsrch1` |
| `longdomsrch1b` | PASS | `longdomsrch1b` |
| `longdomsrch2` | PASS | `longdomsrch2` |
| `longlab0` | PASS | `longlab0` |
| `longlab1` | PASS | `longlab1` |
| `mailboxes` | PASS | `mailboxes` |
| `manya` | PASS | `manya` |
| `manyptrwrong` | PASS | `manyptrwrong` |
| `manyptrwrongrem` | PASS | `manyptrwrongrem` |
| `manyptrwrongrst` | PASS | `manyptrwrongrst` |
| `manyptrwrongrty` | PASS | `manyptrwrongrty` |
| `monotonic` | PASS | `monotonic` |
| `ndots` | PASS | `ndots` |
| `ndots-as` | PASS | `ndots-as` |
| `ndotsbad` | PASS | `ndotsbad` |
| `noinfto` | PASS | `noinfto` |
| `norecurse` | PASS | `norecurse` |
| `norecurse2` | PASS | `norecurse2` |
| `norecurse3` | PASS | `norecurse3` |
| `norm` | PASS | `norm` |
| `owner` | PASS | `owner` |
| `poll` | PASS | `poll` |
| `polltimeout` | PASS | `polltimeout` |
| `ptr-aaaa` | PASS | `ptr-aaaa` |
| `ptr-aaaa-caps` | PASS | `ptr-aaaa-caps` |
| `ptr-aaaa-check` | PASS | `ptr-aaaa-check` |
| `ptr-aaaa-mismatch` | PASS | `ptr-aaaa-mismatch` |
| `ptr-aaaa-plain` | PASS | `ptr-aaaa-plain` |
| `ptrbaddom` | PASS | `ptrbaddom` |
| `ptrbaddom2` | PASS | `ptrbaddom2` |
| `quote` | PASS | `quote` |
| `rootquery` | PASS | `rootquery` |
| `rootqueryall` | PASS | `rootqueryall` |
| `rootqueryall-as` | PASS | `rootqueryall-as` |
| `rr_addr-binary-compat` | PASS | `rr_addr-binary-compat` |
| `search` | PASS | `search` |
| `search-as` | PASS | `search-as` |
| `searchabs` | PASS | `searchabs` |
| `sillyrp` | PASS | `sillyrp` |
| `srvbaddom` | PASS | `srvbaddom` |
| `srvha` | PASS | `srvha` |
| `srvok` | PASS | `srvok` |
| `srvqudom` | PASS | `srvqudom` |
| `srvsort` | PASS | `srvsort` |
| `tcpallfail` | PASS | `tcpallfail` |
| `tcpautosys` | PASS | `tcpautosys` |
| `tcpautosysmissingserv` | PASS | `tcpautosysmissingserv` |
| `tcpblock` | PASS | `tcpblock` |
| `tcpblockbrk` | PASS | `tcpblockbrk` |
| `tcpblockwr` | PASS | `tcpblockwr` |
| `tcpbreakin` | PASS | `tcpbreakin` |
| `tcpmultipart` | PASS | `tcpmultipart` |
| `tcpptr` | PASS | `tcpptr` |
| `timeout` | PASS | `timeout` |
| `trunc` | PASS | `trunc` |
| `unknown-flags-harmless` | PASS | `unknown-flags-harmless` |
| `unknown-flags-init` | PASS | `unknown-flags-init` |
| `unknown-flags-query` | PASS | `unknown-flags-query` |
| `unknown-flags-type` | PASS | `unknown-flags-type` |
| `unknown2` | PASS | `unknown2` |
| `unknown33` | PASS | `unknown33` |
| `unknown5` | PASS | `unknown5` |
| `unknownq` | PASS | `unknownq` |
| `unkopts` | PASS | `unkopts` |
| `v6-map` | PASS | `v6-map` |
| `v6-transport-simple` | PASS | `v6-transport-simple` |
