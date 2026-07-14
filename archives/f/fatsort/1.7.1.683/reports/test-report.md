# Test Report — fatsort 1.7.1.683

Status: PASS_WITH_UPSTREAM_LIMITATION
Date: 2026-07-14

## 探索编译

```bash
make -C src -j1 CC=clang LD=clang CFLAGS="$CFLAGS -D__LINUX__" LDFLAGS="$LDFLAGS"
```

结果: PASS，生成 `src/fatsort`。

## Staging smoke test

```bash
$TEST_PREFIX$DEFAULT_PREFIX/bin/fatsort -v
$TEST_PREFIX$DEFAULT_PREFIX/bin/fatsort -h
```

结果: PASS。

- `fatsort -v`: 输出 `fatsort 1.7.1`
- `fatsort -h`: 帮助文本正常输出

## Conan test_package

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify fatsort 1.7.1.683
```

结果: PASS。

- G1 配方完整性: PASS
- G2 conan create + test_package: PASS
- G3 系统同名库隔离: PASS
- G4 产物完整性: PASS
- L2/L4/L5: PASS（当前 verifier 未解析到 cache 路径，报告为跳过但总体 PASS）

## 上游 tests

```bash
make -j1 tests SHELL=/data/service/hnp/bin/bash CC=clang LD=clang CFLAGS="$CFLAGS -D__LINUX__" LDFLAGS="$LDFLAGS"
```

结果: FAIL（非阻塞，平台/环境限制）。

原因: 上游测试套件依赖 `/bin/bash`、bbe、valgrind、可写 `/tmp`、镜像解压/挂载等完整 Linux 测试环境；当前 HarmonyOS 环境不满足。完整输出见 `reports/upstream-tests.log`。
