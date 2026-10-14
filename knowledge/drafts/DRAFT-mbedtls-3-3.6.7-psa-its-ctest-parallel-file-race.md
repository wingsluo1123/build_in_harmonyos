# DRAFT-mbedtls-3-3.6.7-psa-its-ctest-parallel-file-race — PSA 文件存储测试被 ctest 并行写坏（路径 B 候选）

> 配对条目：`knowledge/drafts/DRAFT-mbedtls-3-3.6.7-psa-its-ctest-parallel-file-race.kv`
> 来源：mbedtls-3 3.6.7 适配（2026-10-08，任务 #14531）

## 问题

`ctest -j4` 时 140 个套件里 4 个失败，其余通过。失败套件是
`psa_crypto_slot_management-suite`、`psa_crypto_storage_format.current-suite`、
`psa_crypto_storage_format.misc-suite`、`psa_crypto_storage_format.v0-suite`。
原样断言：

```
Persistent slot, check after purging, id=max ...................... FAILED
  (psa_import_key(&attributes, key_data->x, key_data->len, &returned_id)) == PSA_SUCCESS
  lhs = 0xffffffffffffff67 = -153
  rhs = 0x0000000000000000 = 0
```

同一次日志里还有 `lhs = -140` 与 `lhs = -139`。`-153` 是 `PSA_ERROR_DATA_INVALID`，
`-140` 是 `PSA_ERROR_DOES_NOT_EXIST`，`-139` 是 `PSA_ERROR_ALREADY_EXISTS`。
同一套件里 `id=min` 的持久槽用例是 PASS。

## 根因

PSA ITS 把密钥写成**当前工作目录**下的文件。CTest 让这些套件共用构建目录。
`-j4` 时多个套件同时创建和删除同名文件，读回的记录被别的套件改掉。
存储目录本身可写：若是权限问题，`id=min` 也不会 PASS。`/tmp` 在这台真机上只读，
但这些失败发生在构建目录，不是 `/tmp`。

对照（同一构建树，未重编）：

```
ctest -j1 -R "psa_crypto_slot_management-suite|psa_crypto_storage_format"
1/4 ... slot_management-suite   Passed  0.30 sec
2/4 ... storage_format.current  Passed  3.38 sec
3/4 ... storage_format.misc     Passed  0.04 sec
4/4 ... storage_format.v0       Passed 18.78 sec
100% tests passed out of 4
RETRY_EXIT:0
```

随后整次 `ctest -j1`：`100% tests passed out of 140`，140 行套件汇总合计
`43989/43989` 用例、失败 0、套件内 `depends_on` 跳过 11726。

## 最小解决与边界

配方里上游套件用 `ctest -j1`，不关 `ENABLE_TESTING`，也不把这四套件放进 `SKIP_TEST_SUITES`。

1. 只在「多套件共享 cwd 文件名」时串行。纯计算套件 `-j4` 可以过，本轮 AES 等套件在 `-j4` 下没有失败。
2. 更好的上游做法是每个套件一个临时目录。本轮用 `-j1` 是不改测试源码的最小改动。
3. 不注入 `__OHOS__`。Linux 上同样 `-jN` 也会踩这个竞态。

## 验证

- 反证：`-j4` 四套件失败，错误码 `-153/-140/-139`。
- 正证：同一棵构建树 `-j1` 四套件通过，随后 140/140。
- 消费者 `test_mbedtls`：`aesce_has_support_result=1`，AES-128-ECB 与 SHA-256("abc") 通过。`CREATE_EXIT:0`。

## 与既有知识的关系（七轴查重）

检索基线是 `origin/main`（`b95978a4750e7aa9a3d49af148bb3bbedf81051d`），`knowledge/graph/E*.kv` 542 条。

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | 否 | `psa_its`、`PSA ITS`、`PSA_ERROR_DATA_INVALID`、`psa_crypto_storage` 在 knowledge 下 0 命中 |
| causal_duplicate | 否 | E292 是 Arrow 测试数据路径和 `TMPDIR`，不是两个进程写同一组 ITS 文件 |
| trigger_overlap | 部分 | E292、au 0.6.0、tvm-ffi 0.1.12 的正文里出现 `ctest -j1`，触发原因分别是数据路径、浮点用例和超时 |
| solution_overlap | 部分 | 表面都是 `-j1`。本条的判据是 `-j4` 复现 `-153/-139/-140` 且 `-j1` 消失 |
| combination_novelty | 是 | PSA 相对路径文件存储加上 CTest 共用 cwd |
| boundary_novelty | 是 | 反例：没有共享文件的套件不必串行；`NOT_SUPPORTED` 不是本条 |
| test_migration_novelty | 是 | 同一构建树先并行失败、再串行通过，中间没有重编 |

**决定：** new_draft（路径 B）

## 适用边界 / 反例

- 适用：测试把状态写到相对路径文件，且 CTest 没有为每个套件设置独立工作目录。
- 反例：E292 那种缺 `ARROW_TEST_DATA` 的失败，补环境变量即可，改 `-j` 无效。
- 反例：套件已经把存储目录设成各自的临时目录时，继续 `-j1` 只是变慢，不构成本条。
