# E549 draft — dict 子类公开映射不是底层存储的测试 oracle

状态：草稿，正式编号由主编分配。实例：twodict 1.2，主活动 #11383，贡献归属 orrkri。Windows CPython3.12.14研究结果复用；H1-001已取得OHOS Python3.12.9原套件/消费者/W3真实通过，整体finish仍失败，未有效提审。

## 触发条件与症状

dict 子类在底层保存额外条目，却让 __iter__、keys()/items() 展示过滤后的公开映射。测试想检查底层存储，调用 super(Subclass, obj).copy()；调用父类方法不保证它在内部绕过子类映射协议。

twodict 公开视图只有 [('a', 1), ('b', 2)]，底层同时保存 [('a', 1), (1, 'a'), ('b', 2), (2, 'b')]，以支持反向查找。主机 Python 3.12 上，原 TestSetItem 的 16 项 tearDown 把父类 copy 的公开键结果误当底层缺项。同对象既有观察中 forward_a=1、reverse_1='a'，双向查询仍正确。

## 根因与最小修复

[CPython v3.12.14 dictobject.c](https://github.com/python/cpython/blob/v3.12.14/Objects/dictobject.c) 中 PyDict_Copy 对子类有快路径条件；覆盖 tp_iter 时可能走映射合并回退，读取公开键。super 选择父类实现，不承诺其内部观察方式。这不是已证实的 OHOS 专属缺陷；其他解释器/版本须核实际行为。

对确实要验证底层双向存储的断言，改原观察式，保持所有预期字典及断言：

```python
current_dict = dict(dict.items(test_case.tdict))
test_case.assertEqual(current_dict, test_case.expected_dict)
```

若要验证用户公开映射，则继续用 obj.items()/keys()；不能把两层语义混用。配套修正是 collections.abc 视图，以及让原自定义 runner 传递实际结果：

```python
result = runner.run(all_tests_suite())
sys.exit(not result.wasSuccessful())
```

保留原 all_tests_suite() 及嵌套 TestSetItem 类；普通 discovery 不能未经比较直接替换。ABC 和退出码只是已有通用做法，新增点是存储 oracle 的协议边界。

## 固定输入、命令与实际结果

[上游](https://github.com/MrS0m30n3/twodict) / [原 PyPI sdist](https://files.pythonhosted.org/packages/49/96/03307c666c1ce0c04bdc23fb69f758b4076eff39d15c56f943ba4b527e21/twodict-1.2.tar.gz)，7036B，SHA256 `20dbdfa7f14a285454d34bba1e7714aad15a376ddfd0a1c0a3c24a14763bdb45`。原入口为 `python3 -B test_twodict.py -v`。

2026-10-13 Windows AMD64 / CPython 3.12.14 既有研究：

| 修正 | 原套件输出 | rc |
|---|---|---:|
| 无 | collections.KeysView 导入失败，套件未运行 | 1 |
| 仅 ABC | 71 发现，16 失败，6 原跳过 | 0 |
| ABC + 结果传播 | 相同 71/16 失败/6 跳过 | 1 |
| 上述 + 存储观察式 | 71 发现，65 执行通过，6 原跳过，0 失败 | 0 |

六个跳过来自上游 TestOldMethods 的 Python2 条件，本次未增删。本线程新增主机软件执行为 0；Windows 探针测试副本 CRLF 仅还原为上游 LF，文本一致。单模块包直接安装模块与许可证，不宣称 distutils setup.py 在 Python 3.12 可构建。

2026-10-13 H1-001在OHOS6/armv8真实Python3.12.9 Conan包下运行同一原套件：71发现/65执行通过/6原跳过/0失败；Conan安装包消费者1流程/9断言通过，完整W3通过。日志同一对象输出public_items=[('a',1),('b',2)]，parent_copy={'a':1,'b':2}，raw_items=[('a',1),(1,'a'),('b',2),(2,'b')]；目标也确认父类copy与裸存储观察的差异。对应原候选73cd566b…，完整执行证据见软件归档reports/h1-001-w3-local-ci.log及test-report.md；本次未重跑该套件。整体finish另因G1入口/框架摘要等门返回1，不能把软件与W3通过写成已有效提审或全部门通过。

## 近邻与边界

研究卡按官方 ca72b8c6…读取正式库、草稿与公开 Issue/PR；本线程在当前 f6a25613… 的本地 knowledge 范围又查 PyDict_Copy、dict 子类及 super-copy 机制，未发现覆盖项。这是限定范围的增量比较，不是全局原创性保证。

| 近邻 | 已覆盖 | 本项差异 |
|---|---|---|
| DRAFT-ohos-collections-abc-silent-loss | ABC 别名/静默失效 | 主要问题是父类 copy 的公开映射回退 |
| E239 | Conan 失败后的诊断保留 | 修正 16 个真实断言的观察层次 |
| E363 | shell setup/派发空结果却 rc0 | 原套件实际执行，错误 oracle 与丢弃结果分列 |
| DRAFT-test-execution-gate-silent-skip-false-pass | 注册/平台门导致未执行 | 本项原始断言实际执行 |
| DRAFT-minidb-2.0.8-python-sqlite3-runtime | 运行时供应/wasSuccessful | 结果传播复用已有做法，不作为主要新增点 |

适用于公开迭代和原始存储不同的 dict 子类测试，例如隐藏反向条目或元数据；先明确断言验证哪个接口。普通 dict、非 dict 子类或只验证公开映射相等的测试不能直接套本观察式。未完成第二个软件适配，不扩大结论；自动修复为 false，须人工确认观察边界。

禁止删除反向存储预期、改算法迎合父类 copy、缩减原套件或增加 skip。不能仅看 rc0，也不能把目标供应、知识生成、W3、W4、AtomCode、官方 CI、有效提审、合入和计分混称完成。
