# SWI-Prolog 10.0.2

HarmonyOS PC/aarch64 原生无界面运行时，含 WAM、线程、引擎、GC、GMP、BASIC、
JSON、PCRE、YAML、SSL、archive 和 libedit。版本配方及验证说明见 [10.0.2](10.0.2/)。

```sh
conan create archives/s/swi/10.0.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -c tools.build:jobs=1
swipl -q -g 'X is 2^100,writeln(X),halt'
```

路径 C（含 B 知识补强）候选申请，最终归类由评审委员会确认。原生 `conan create` 返回 0；
所选配置全部 84 个 CTest 组及 30 条消费者测试通过，安装 ELF 和迁移运行已验证。

GUI/Java/Python/ODBC/Berkeley DB/TIPC 扩展不在本次无界面配置中。
运行时需要临时文件时，将 `TMP`、`TMPDIR` 指向当前用户的原生可写临时目录。
配方测试会实际探测 Unix socket 文件创建能力，使用任务私有临时目录并在结束后清理。
