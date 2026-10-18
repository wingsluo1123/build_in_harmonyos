# krunner5 5.116.0 测试报告（真机）

- 平台: HarmonyOS PC (arm64, OHOS 6.0, clang 15, libc++)
- 日期: 2026-10-16
- 命令: `conan create . -pr:h=ohos-aarch64-full -pr:b=ohos-aarch64-full --build=missing`
  与 conan-verify G2 的 CI profile 全量干净构建
  （`-pr:h=ci/conan/profiles/ohos-aarch64 --user=ohpcd --channel=stable`）

## 1. 上游 ctest（rule4 口径）

档位: `EXCLUDE_DEPRECATED_BEFORE_AND_AT=5.91.0` → 6 个注册测试目标、27 个
QTest 用例槽位（runnercontexttest 因 VERSION_LESS 5.76.0 守卫不注册）。

本机无 dbus-run-session/dbus-daemon → build() 走"无总线分支"，以
`-E "dbusrunnertest|runnermanagersinglerunnermodetest|runnermanagertest"` 排除
3 个会话总线套件，实跑 3 个无总线套件：

| ctest 名 | 结果 | 耗时 | 用例槽位 |
|----------|------|------|----------|
| runnermatchmethodstest | Passed | 0.06–0.07s | 4 |
| runnermanagerhistorytest | Passed | 0.21s | 4 |
| testmetadataconversion | Passed | 0.06–0.08s | 1 |

`100% tests passed, 0 tests failed out of 3`。

**未执行声明**: dbusrunnertest(9) / runnermanagersinglerunnermodetest(6) /
runnermanagertest(3) 共 18 个用例因镜像无 D-Bus 工具链被排除，
**未在本机执行**（非跳过即通过）；提供 dbus-run-session + dbus-daemon 的
镜像上由同一配方在私有总线下执行（`dbus-run-session -- ctest`）。

## 2. test_package（消费者视角，31 断言）

`SUMMARY: 31 passed, 0 failed`

- KPluginMetaData/KPlugin JSON、runner.id()/description() 往返 —— 5
- match() → RunnerContext::addMatch() → matches() 全链（含 setId()
  `<runnerId>_<id>` 组合语义）、text/relevance/isValid/runner 回指、
  非匹配查询零结果 —— 9
- QueryMatch 值语义：operator< 按 relevance 及反对称、拷贝相等/不等、
  空构造无效 —— 5
- RunnerContext::matchesChanged 信号、addMatches() 批量 —— 3
- RunnerSyntax（普通查询原样保留、":q:" 占位符替换、description、多样例） —— 5
- HarmonyOS ELF: 无版本 DT_SONAME、DT_RUNPATH、.codesign 段 —— 4

（分组计数 5+9+5+3+5+4 = 31，与二进制输出 SUMMARY: 31 passed, 0 failed
及 test_package/MANIFEST.yml count: 31 一致。）

## 3. conan-verify 门禁

| 门禁 | 结果 |
|------|------|
| G1 配方完整性（name/version/source/build/package/package_info/export_sources/补丁调用/R26/conandata/test_package+MANIFEST） | ✅ PASS |
| G2 conan create（CI profile 干净构建） | ✅ PASS |
| G3 交付物检查（无 bin/，无系统同名库冲突 R26） | ✅ PASS |
| G4 综合（⚠️ 无法找到程序包 ID — 纯库包常态） | ✅ PASS |
| L2/L4/L5（无 cache 路径） | ✅ 跳过（PASS） |

## 4. 证据文件

| 文件 | 大小 | md5 |
|------|------|-----|
| reports/conan-create.log（G2 全量构建日志，含 ctest+test_package） | 49475 B | `ec9c8a2f3daea93ae542be049be1f102` |
| reports/conan-verify-report.md | 1239 B | `74466944a73569e47ef4d08c54cf2f06` |
