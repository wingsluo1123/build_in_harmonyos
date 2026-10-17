# 嵌入式运行时借用宿主既有备用信号栈：补充 E224 的初始化边界

本条是知识补强候选，B资格由复审决定；建议主编评估独立子条目或并入E224。
E224已命中同族回收机制，不申报整个sigaltstack家族零命中。

## 错误特征

```text
E224-cleanup-only: HOST_STACK_AT_INIT=overwritten
E224-cleanup-only: REAL_PROLOG_CALL=1
E224-cleanup-only: HOST_STACK_AFTER_CLEANUP=lost; RC=1
current-installed: HOST_STACK_AT_INIT=preserved
current-installed: REAL_PROLOG_CALL=1
current-installed: HOST_STACK_AFTER_CLEANUP=preserved; RC=0
```

两个版本都成功调用真实Prolog。失败是新增的宿主注册不变量断言，不是原始上游CTest失败。
当前比较完整注册三元组：`ss_sp`、`ss_size`、`ss_flags`。

## 触发条件与根因

宿主先在当前OS线程注册一块大小为`SIGSTKSZ`的备用栈H，再初始化嵌入式VM。
旧初始化函数不查询当前注册，直接分配S并`sigaltstack(&S,NULL)`，立即覆盖H。
即使之后按E224在释放S前先注销，H也不会因此自动恢复。
因此“当前VM自己分配的内存”与“当前线程已经注册的资源”是两种所有权，不能合并。

本次负例是先前任务私有Release构建：原版初始化函数完全未改，本次同线程回收路径已经
查询当前注册、`SS_DISABLE`成功后才free。该回收块和源码/ELF哈希随证据保存。
初始化函数SHA256与官方10.0.2发布源码逐字一致：
`b5a4dc2e29a64a1eef29ef03700ff93de2fef6dc4ef6aa352469e7595ce80b28`。
这比仅以“旧版本失败”判断更具体：本次同线程路径的E224回收顺序已经实现，而覆盖发生在尚未清理时。
这不表示该历史基线在全部跨线程engine路径都完整满足E224。
两个构建还有其它适配差异，归因同时依赖初始化源码和发生阶段，不仅依赖二进制对照。

## 推荐处置

1. 入口查询完整注册；启用不等于VM拥有它。
2. 已有栈满足运行时要求时借用，不覆盖、不放入自有内存析构key。
3. 无可用注册时才创建自有栈，回收继续遵循E224的owner线程注销顺序。
4. 需要不同大小/标志时，建立明确保存恢复协议；不能把“借用”泛化为忽略兼容性。

SWI补丁0003已包含借用分支，本次没有再改生产运行时；新增的是机制证据和回归断言。
这不是要求任何环境都不可替换备用栈，而是要求替换必须有明确协作协议。

## 对照与独立上游语料

| 入口 | E224回收修复控制 | 当前安装包 |
|---|---|---|
| 直接C嵌入，真实算术，显式`PL_cleanup(0)` | 初始化覆盖；清理后丢失；RC1 | 初始化/清理均保留；RC0 |
| 官方`man/calc.c`及`calc.pl`，真实计算6*7 | 输出42，但注册断言失败；RC1 | 输出42且注册保留；RC0 |
| 包消费者 | 新增三元组断言可检出旧入口行为 | 29/29 Prolog + 1/1 C embedding，RC0 |

官方示例字节未修改；测试夹具用链接器`--wrap=PL_initialise`在入口前注册H、
在真实初始化返回后读取注册并consult原`calc.pl`，不替代Prolog运算。
`calc.c`调用`PL_halt()`，Release有其正常的保留内存清理策略；它不等同于显式
`PL_cleanup(0)`。两条路径分别记录，后者由直接嵌入探针和包消费者验证。
官方例是独立上游示例语料，不是第二种VM或新增CTest组。

官方示例SHA256：

- calc.c：`76a92586a9fc42fbf7c0dfa9fe2d877a16842707aa3b88e1bb13e8d1fe8e9db7`
- calc.pl：`3ab6ca86af49bea19ccee7ff7aa2782f00ce3cf9e701ba0dea5988472ebea6ee`

## 复现入口

```sh
conan test archives/s/swi/10.0.2/test_package swi/10.0.2@ohpcd/stable -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

`test_package/embed_swi.c`在进入VM前建立宿主注册，分别在初始化和完整清理后比较三元组，
恢复进入前注册后才释放自己的H。新增断言计入原来的一个embedding用例，不重复增加用例数。
独立诊断源码位于同目录的`diagnostics/host_stack_probe.c`和`calc_host_fixture.c`。
诊断编译/控制输入和实测输出见`reports/b-host-altstack.md`及`b-altstack-evidence.json`。
编译和运行均使用真实包内头文件、libswipl及公开C API。

## 查重与 E224 的可执行边界

2026-10-15，main `b544378a4ea82b4959135eebb21f5e509eeebf91`，扫描graph/doc/drafts正文及索引快照8310文件。
查询`sigaltstack|alternate.*stack|备用.*信号栈|ss_sp|SS_DISABLE`：正式机制命中E224及doc镜像；
另有无关字段/引用命中，没有发现“初始化覆盖宿主既有注册/借用不取得析构权”的独立处方。
检索命令和E224命中摘要随报告保存，不将索引/文件名零命中当成正文零命中。

```sh
rg --hidden --no-ignore -n -i 'sigaltstack|alternate.{0,25}stack|备用.{0,12}信号栈|signal.{0,12}stack|ss_sp|SS_DISABLE' knowledge/graph knowledge/doc knowledge/drafts -g '*.kv' -g '*.md'
```

| 邻近条目 | 已覆盖 | 本条补充及反证 |
|---|---|---|
| E224 | 自行分配栈的owner-thread注销与free顺序 | 宿主在VM进入前已经注册；覆盖发生在初始化。E224回收修复控制仍丢H，普通计算却成功 |
| E077/E504 | ELF签名、安装RPATH改写 | 本对照没有改写ELF；两版本都成功加载与计算，差异在注册三元组 |
| E141及itsy_bitsy草稿 | 列表/字符串序列化 | 本条不是该候选；它们已经覆盖相应方向，未重复申报 |

## 范围与禁止做法

- 只证明注册身份/大小/状态保留，没有证明宿主SIGSEGV处理器保留、真实SA_ONSTACK投递、
  所有栈大小都兼容或多个VM的完整信号互操作。不要扩大这些结论。
- 不把E224-only控制的新增断言失败计为上游原始测试失败。
- 不因借用了宿主栈，就在VM销毁时对它SS_DISABLE或free。
- 不为抹平差异而关闭信号、GC或线程；原84组配置与生产补丁保持不变。

## 证据与元信息

关联[PR #16007](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/16007)；任务10947；源码为官方swipl10.0.2完整发布归档。
原完整create仍为84/84组、消费者30/30；新增断言后消费者独立`conan test`再次30/30，RC0。
消费者日志SHA256：`7653fc45ee57a7b8fae635e05e4a29ae14b60207eeeb0d62c5c851bb9120c6c1`。
本条草稿仅申报知识补强；合并转正或并入E224、B分值均待委员会判断。

- draft: true
- contributor_id: frj__
- authors: frj__ <241250055@smail.nju.edu.cn>
- last_updated: 2026-10-15
