# pg_ivm 1.15 验证报告

## Environment

- OpenHarmony/HarmonyOS PC aarch64 真机
- Clang 15.0.4（`/data/service/hnp/bin/clang`）
- Conan 2.29.1（OHOS 适配版）
- 基线 PostgreSQL 18.3（配方自举，含 HarmonyOS 适配补丁）

## Verification

- `ohc-run.py conan-verify pg_ivm 1.15`: exit 0
  - G1 配方完整性: PASS
  - G0 预构建风险评估: 通过
  - G2 `conan create`（干净构建）: PASS
  - G3 系统同名库隔离（R26）: PASS — OHOS 无系统 `libpg_ivm`，不存在污染面
  - G4 产物完整性: PASS
  - L2 平台功能矩阵: 跳过（`L2: No bin/ directory found — skipping`，库包无 CLI 产物）
  - L4 静态安全扫描: warn（`Dangerous functions found in patches`——PG 补丁内定位危险函数，非阻断，见 notes.md 的 R8 例外说明）
  - L5 产物基线对比: 通过（`lib/ has content (library package)`）
- `ohc-run.py finish pg_ivm 1.15`: W3 本地 CI 模拟（`build_and_test.sh`）: PASS
  - JC 杂项文件: PASS（`检查模式: incremental (12 个文件)`、`[OK] 未发现杂项文件`）
  - L0 结构完整性: PASS
  - W2 PR 原子性: 仅含配方变更（12 个文件，均在 `archives/p/pg_ivm/` 下），无框架文件

## test_package

两层验证，均以真实 PostgreSQL 18.3 集群为运行环境（临时集群：`initdb` →
`pg_ctl start`（TCP 回环，OHOS 无 Unix socket）→ staging 安装扩展 →
`make installcheck` → `pg_ctl stop`）。

### 1. 冒烟测试 `test_pg_ivm.c`

| 断言 | 结果 |
|---|---|
| `lib/pg_ivm.so` 存在 | PASS（113024 字节） |
| 是合法 64 位 ELF 共享对象（ELF64 / ET_DYN） | PASS |
| `extension/pg_ivm.control` 声明 `default_version` | PASS |
| `extension/` 下打包了 `pg_ivm--*.sql` 脚本 | PASS（17 个） |

### 2. 上游回归套件（未修改任何上游用例）

上游 `Makefile` 声明 `REGRESS`（4 组）与 `ISOLATION`（9 组），
`make installcheck` 同时驱动 `pg_regress` 与 `pg_isolation_regress`，
判据为上游自带的 `expected/*.out`：

```
ok 1  - pg_ivm            928 ms
ok 2  - create_immv       126 ms
ok 3  - refresh_immv      140 ms
ok 4  - outer_join       1526 ms
# All 4 tests passed.

ok 1  - create_insert     360 ms
ok 2  - refresh_insert    443 ms
ok 3  - insert_insert     880 ms
ok 4  - create_insert2    406 ms
ok 5  - refresh_insert2   341 ms
ok 6  - insert_insert2    628 ms
ok 7  - create_insert3    350 ms
ok 8  - refresh_insert3   377 ms
ok 9  - insert_insert3    612 ms
# All 9 tests passed.
```

- Test cases（上游组）: 13
- Passed: 13
- Failed: 0
- Skipped: 0

### 3. 端到端功能证据

回归套件本身即端到端功能验证：`sql/pg_ivm.sql` 等多组用例在真实集群上
`CREATE EXTENSION pg_ivm` → `CREATE INCREMENTAL MATERIALIZED VIEW` →
对基表 INSERT/UPDATE/DELETE → 校验 IMMV 内容随增量维护结果（含外连接、
聚合、`DISTINCT`、多版本更新链 1.0→1.15 的行为），隔离测试进一步覆盖
并发事务下的增量维护语义。

## Result

**PASS** — 编译通过、13/13 上游回归组通过、冒烟测试 4/4 断言通过，
上游测试用例零修改、零跳过。
