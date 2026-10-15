# zerolang 0.3.4 — HarmonyOS PC (aarch64) 适配

zerolang 是 vercel-labs 发布的面向 agent 的 graph-native 编程语言。其编译器
`zero` 是自包含 C 程序（`native/zero-c`），像 Homebrew formula 一样用
`make -C native/zero-c OUT=<bin>/zero` 即可构建。

## 构建

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

产物：`bin/zero`（编译器 CLI，约 15MB）。

## 关键适配点

1. **无需 node**：`native/zero-c/src/embedded_{skills,stdlib_graph,runtime_sources}.inc`
   三个嵌入资源已在 release 归档内预生成并提交；make 判定其 up-to-date 便不触发
   node 重新生成，因此本配方只依赖系统 C 编译器（cc/clang）。
2. **纯 C、aarch64 无限制**：编译器本体无平台内联汇编，上游已内置
   `zero-elf-aarch64` 直接后端。
3. **只读 /tmp**：构建与 smoke 子进程把 `TMPDIR/TMP/TEMP` 指到可写 build 目录。
   process_exec / http_listen / program_graph 三个 native smoke 源码硬编码 `/tmp`
   绝对路径（忽略 `$TMPDIR`，只读 `/tmp` 上 EROFS 必然失败）；配方在编译前将
   `/tmp/zero-*` 字面量改写为 `SMOKE_TMP` 宏（指向同一可写目录），不改逻辑、仅重定向
   临时目录，使 5 个 smoke 在只读 /tmp 上 5/5 通过。
4. **上游测试**：上游官方测试套件共 15 个用例 = native/zero-c/tests 下 5 个 C 冒烟程序
   （全部在 build() 内编译运行，结果写入包内 `res/upstream_test_result.json`，test_package
   每次预检转发 `HMBS_UPSTREAM_TEST_RESULT` 证据）+ tests/zero-cli.test.ts 的 10 个
   node:test CLI 契约用例（独立 JS 驱动套件，要求 node 运行时与可运行的 direct-backend
   宿主目标 runnableDirectTarget；该目标上游仅定义 darwin-arm64/linux-musl-x64，
   linux-aarch64/OHOS 无定义，10 个用例在锁定、无依赖的 OHOS 构建环境以 environment gap
   如实披露，不归零、不伪装 100%）。

## 验证

- 本地：`make -C native/zero-c OUT=.../zero` 成功；5/5 native C 冒烟通过；
  `zero --version` 输出 `zero 0.3.4`；hello-world 经 init/import/check/run 输出 `hello`。
- 上游测试口径：官方合计 15（5 native C 冒烟 + 10 node:test CLI 契约）；OHOS 环境
  实测 5/5（native C 冒烟），10 个 node:test CLI 契约用例为 environment gap。
- 真机：以 HarmonyOS aarch64 预检实际结果为准（conan create 日志）。
