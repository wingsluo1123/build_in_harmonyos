# mbedtls-3 3.6.7

任务 #14531，分支 `feat/mbedtls-3-3.6.7`。真机 `CONAN_HOME=~/work/psj/ch-mb314531`，`CREATE_EXIT:0`。

官方包 `mbedtls-3.6.7.tar.bz2` 的 SHA-256 为
`a7e8bcbec0e6f761b4af24f25677626b35f762f68eef79c08677a363212d11f6`（本机下载后计算）。

## 加密扩展

SDK clang 预定义 `__linux__`、`__OHOS__`、`__unix__`。`getauxval(AT_HWCAP)=0xffffffff`，
AES、PMULL、SHA2、SHA512 位均为 1。`aesce.c.obj` 含 `aese` 16 处、`pmull` 7 处，
并导出 `mbedtls_aesce_has_support_impl`。`sha256.c.obj` 含 `sha256h`/`sha256su0`，
`sha512.c.obj` 含 `sha512h`/`sha512h2`。消费者打印 `aesce_has_support_result=1`。

## 测试

`ctest -j1`：140/140 套件，用例合计 43989/43989（失败 0，套件内 depends_on 跳过 11726）。
`-j4` 时 4 个 PSA ITS 套件因共用 cwd 文件失败（-153/-140/-139），`-j1` 对照通过。见知识草稿。

`ssl-opt.sh`：2083 项，脚本汇总失败 17、跳过 746，实际执行通过 1320/1337。
点名失败 8 条：TLS 1.0/1.1 各 1（服务器日志缺少 `Error in protocol version`）、
deflate ClientHello 1（缺少 compression 转储）、客户端发起的重协商分片 5
（缺少 `TLS_EMPTY_RENEGOTIATION_INFO`）。脚本失败计数比这 8 条多 9，退出码仍是 17。

`compat.sh`：1256 项，跳过 48，失败 108，实际执行通过 1100/1208。
108 条全部是 `m->G` 的 Camellia。同轮 `m->O` 的 Camellia 通过。制品仓 GnuTLS 3.8.10 不提供这些套件。

已执行通过率：(32263+1320+1100)/(32263+1337+1208) = 34683/34808 = 99.64%。
总数 47328 = 43989+2083+1256，跳过 12520 另计，没有少报。

消费者 `test_package`：6/6（版本、AES-128-ECB、回环、SHA-256、AES-CE 探测）。
