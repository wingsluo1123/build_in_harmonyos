# xsettings 0.10 测试报告

## 1. 上游测试

- **结论**: 上游发布包无任何自动化测试（`upstream_tests_exist: false`）
- 审计证据（详见 `test_package/MANIFEST.yml`）:
  - `Makefile.am`: 仅 lib_LTLIBRARIES + HEADERS 声明，无 check/TESTS/check_PROGRAMS 目标
  - `configure.ac`: 无测试相关宏、无 AC_CONFIG_TESTDIR
  - 源码树: 无 tests/、test/ 目录，无 *_test 源文件
  - INSTALL/COPYING: 未提及测试
- 统计: discovered=0, executed=0, passed=0, failed=0, skipped=0

## 2. test_package（消费者用例）

- 源文件: `test_package/test_xsettings.c`（自研 C 主程序，**无 assert() 断言**，符合 rule12）
- 用例 4 条:

| # | 用例 | 类型 | 内容 |
|---|---|---|---|
| 1 | byte_order | L1 API | `xsettings_byte_order()` 返回合法字节序 'B'/'l' |
| 2 | list_ops | L1 API | `xsettings_list_insert/lookup/delete` 数据往返 |
| 3 | dlopen_symbols | **鸿蒙特有（非断言）** | `dlopen("libXsettings-client.so", RTLD_NOW\|RTLD_LOCAL)` + `dlsym` 解析 6 个核心 API 符号，验证 SONAME/符号表/ABI 消费者可行性；dlopen 失败时 WARN 非致命 |
| 4 | setting_copy | L1 API | `xsettings_setting_copy/equal` 拷贝与相等性 |

- 执行方式: 交叉编译（目标 armv8 OHOS / 宿主 x86_64），`can_run()=False`，测试二进制未在构建机执行——如实降级为**编译成功 + 库产物验证**：
  - `binary_built=True`（`test_xsettings_consumer` 已产出）
  - `libXsettings-client.so` 已打包（library_count=1）
- 标记行（`reports/conan-create.log:208`）:
  `HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":true,"binary_built":true,"library_count":1}`

## 3. conan create

- conan-verify G2 干净构建 PASS（`-pr:h/-pr:b = ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`）
- 主包: `libXsettings-client.so` 构建打包成功；test_package `-j1` 编译通过（HMFS 并发 EACCES 规避，见 notes.md 对话 #3）
- 全量日志: `reports/conan-create.log`

## 4. conan-verify（2026-10-12）

- **Verdict: PASS（exit 0）**——G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS
- 报告: `reports/conan-verify-report.md`

## 5. W3 本地 CI 模拟（finish run5，2026-10-12 12:03）

- 结果: **PASS**（Success 1/1，Pass rate 100%，`.ci-result.json` exit_code=0）
- 分项:
  - `L0_RESULT=pass: all checks passed`（含 L0k commands.json、L0m 目录结构、L0i 依赖在库、L0j 版本无冲突）
  - `L1_RESULT=pass: upstream tests + test_package executed`（L1a test_package 被 conan create 执行、L1b 执行证据、L1c 上游 make check 在 build 期执行——上游 check 为空目标）
  - `L1e` 负测试（R34）: **pass** —— 破坏被测包产物后用例必须失败，实测确认用例真实依赖 xsettings
  - `L2_RESULT=skip: no bin/ dir`（纯库包，无可执行文件，属预期）
  - `L4_RESULT=pass: patches clean`
  - `L5_RESULT=pass: lib/ has content`（L5a DT_SONAME=libXsettings-client.so.0 经 LINKER:-soname 修复后通过，见 notes.md 对话 #7）
- 完整日志: `reports/w3-local-ci.log`（log_sha256 与 `.ci-result.json` 一致）

## 6. W2 PR 原子性

- 结果: PASS——分支 HEAD == official/main（b644cbf8ed），staged 变更 35 文件全部位于 `archives/x/xsettings/`（34 个版本级 + 软件级 README.md + commands.json），无框架文件（scripts/ci/docs/knowledge 索引等）
- `archives/l/libXext/{README.md,manifest.yaml}` 两个工作区 M 为大小写不敏感 FS 碰撞伪影，保持 unstaged 不入 PR（notes.md 对话 #6/#8）
