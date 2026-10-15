# R02 上游测试清点 + test_package 范围分离台账 — libtwirc 0.1.2

## 1. upstream_tests_recount（上游测试入口清点，四项分类）

原始命令与输出见 `r02-logs/upstream_tests_recount_raw.log`（sha256 `e3bbf5b83ba224a74f79c480795731481eb4ea27699761f753606e8b2d2d05c5`）。

| 分类 | 清点命令 | 结果 |
|---|---|---|
| ① 测试目录/文件 | `find $SRC -maxdepth 3 \( -type d \( -iname 'test*' -o -iname 'tests' \) -o -type f \( -iname '*test*' -o -iname '*.sh' \) \)` | 零命中（无 tests/ 目录、无测试源文件） |
| ② 测试注册（Makefile/CTest/configure） | `find $SRC -maxdepth 2 -name 'Makefile*' -o -name 'CMakeLists.txt' -o -name 'configure*'` | 零命中（上游无 configure/Makefile/CMakeLists） |
| ③ README 测试声明 | `grep -inE 'test|unit.?test|make check|ctest' $SRC/README.md` | README: "I have not unit-tested it yet" |
| ④ 构建脚本 test 目标 | `grep -inE 'test|check' build-shared build-static` | 零命中（脚本仅编译链接，无 test 目标） |

**台账合计：上游测试入口 = 0**（R51 口径，未将"无测试"虚报为通过，且不据此省略本轮新增鸿蒙测试）。

## 2. test_package_scope_separation（范围分离声明）

- `archives/l/libtwirc/0.1.2/test_package/test.c`（R01 交付，3 断言：init 非空 / fresh last_error==NONE / 未连接态 / kill 干净退出）——**断言类消费者冒烟**，按赛事口径**不计入鸿蒙特有测试**，只计入 test_package 自身口径。
- 独立鸿蒙特有测试：`archives/l/libtwirc/0.1.2/harmonyos_test/harmonyos_consumer_test.c`（本轮新增）——**端到端消费者用例**（本地回环 TCP mock Twitch IRC 服务器 + libtwirc 客户端完成 PASS/NICK 握手、001 welcome 回调、PING 自动 PONG、IRCv3 tags PRIVMSG 解析、is_connected 状态断言；含 --failcap 变体证明可失败），**独立于 test_package 交付**。
- 位置对照：test_package 在 `test_package/` 目录，鸿蒙测试在 `harmonyos_test/` 目录，两者物理隔离、统计互不顶替。

## 3. 结论

- 上游测试：0 入口（证据如上）。
- 适配后统计：上游 0 用例；test_package 断言 1 项（自身口径）；鸿蒙特有测试 1 项（端到端消费者用例，正常运行 PASS exit 0 / failcap 受控失败 exit 1 证据见 r02-logs）。