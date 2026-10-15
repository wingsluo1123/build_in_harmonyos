# 固定记录的转换分派须检查实际载荷：MMLlib 数字音符导出

草稿，作者 `orrkri`，来源为新适配 MMLlib 1.4 / task 8956；目标软件与Conan消费者已有真实验证，尚无PR或官方知识接受。本例是跨平台源码问题，不声称OHOS专属。

## 症状和触发条件

上游 MMLFILE.rst 支持 `N0`–`N84`。普通 `T120L4N60` 可生成 1975.533205024496 Hz 的播放音符，却在 MusicXML 导出遇到 `TypeError: 'int' object is not subscriptable`；语义等价的 `T120L4O4B` 可导出 B / octave 6。`N0` 和 `P4` 均是合法休止。

固定来源为官方 PyPI MMLlib 1.4 sdist，SHA256 `c2bffd2357b8ff087b02cc1d902973eed385340667ed4c000588ad5d85111964`。原缺陷与正常对照原件为 `research/refill-root-20261013/new-candidates/mmllib-probe.json`；本轮直接复用，没有重跑筛选探针。

## 根因

`_overridden_play` 将所有音符记录为 `(bpm, art, length, dots, extra)`。外层总是 tuple，但 `extra` 有三种合法表示：字母音符的 `(octave, letter, accidental)`、数字音符的整数索引 0–83、休止哨兵 -1。

`_create_xml_doc` 解包后误用外层 `ply` 的类型判别转换路径，因此整数→音高三元组的分支永远不执行。后续 `extra[1]` 在整数上失败。可复用原则是：固定记录容器不能区分其中的多种合法载荷；归一化须检查实际载荷，并用语义相同但表示不同的输入对照。

## 修法与使用

将 `mmllib/musicxml.py` 中的判别对象从 `ply` 改为 `extra`：

```python
if not isinstance(extra, tuple) and extra != -1:
    extra = MML_NOTE2PITCH[extra]
```

继续使用上游查表，不重新定义音高、不索引 -1、不丢失字母音符原拼写。应用可调用 `mmllib.musicxml.convert_mml_file(path)` 得到 MusicXML bytes；包保留上游 `mml2musicxml <file.mml>` 与 `mmllint -q <file.mml>` 入口。

适用于解析器与导出器之间使用固定记录传递多种合法载荷的场景，如 AST 节点与序列化器。须先核每种表示的真实契约；本例不证明所有整数都是音符，不涉及损坏输入、二进制 framing、ABI 或编码问题。

## 验证与边界

原完整入口为 `python3.12 -B -m unittest discover -v`。保留 5 个原测试及 test/util.py、Loreley MML/XML 原数据；增加 3 个回归方法：数字音符与等价字母（N1/N60/N84）、N0 与 P4 休止、字母升降记号拼写。参数化子用例不另计方法总数。

本机 Windows CPython 3.12.14 的原完整 suite 为 4/5，通过修复及必要测试精度调整后为 8/8。原 `test_mml_file_meta` 唯一差异是时长 `37.89473684210526` 与 `37.89473684210527`（约 `7.1e-15` 秒）；改用 12 位小数断言时长，其余元数据仍严格字典比较。未改生产时长算法。Python 3.12 官方说明 `sum` 改用了更准确的浮点算法：[文档](https://docs.python.org/3.12/library/functions.html#sum)。

固定 setuptools 84.0.0 后端已构建 `mmllib-1.4-py3-none-any.whl`。本机一个安装包消费者流程实际读取本次 wheel 中的模块与版本、解析数字音符加休止、导出 MusicXML，并经两个包内 CLI 转换/校验；11 条断言通过。入口：`python3.12 -B test_package/consumer.py --package-folder <Conan-package-folder>`，需激活包运行环境。

H1-001固定输入head `ee8680a220e83fa3a6ef19c5a5b9052ec3f0774d`的15文件已按字节绑定。唯一H1在OHOS6.0/armv8/Clang15/Release profile下使用固定Conan Python3.12.9，实际完成完整suite8/8、Conan包及一个安装包消费者/11断言；消费者执行数字音符加休止的API和两CLI。两次Conan流程均由同一次正式finish产生，方法/场景统计不加倍。本地W3的L0/L1/L1e/L4/L5通过，L2帮助/版本探测skip；真实CLI转换和lint已由消费者覆盖。

整体finish仍为rc1，旧G0 configure、共享知识字段和SUMMARY生成问题原样保留，不声称完整框架通过。本机目标原报告位于 `archives/m/mmllib/1.4/reports/`，按仓库策略不提交生成报告；Git中的 `archives/m/mmllib/1.4/notes.md` 记录真实统计和边界，本机完整归档审计入口为 `work/mmllib-1.4/ENTRY.md`。既有原失败、主机和目标证据分列，没有发布、官方CI或有效提审回执。

## 近邻与新增点

复用筛选近邻全文比较：E226 为 os.popen bytes/str 包装；E417 为 CI 图像格式覆盖；gvariant tuple 草稿为二进制 framing 顺序与 offset；vcdimager/libxml2 草稿为 C union 回调 ABI。它们未覆盖“恒定外层记录导致合法内部整数表示未被归一化”。新抓取官方 main `f6a25613daaf1aec7170321c249d6ccf3f329593` 的有限文件名定位未见 mmllib/musicxml/payload 主题；不是全库全文唯一性证明。若发布前出现同机制新证据须重新判增量。

不应删除 N 支持、静默忽略数字音符、强制用户改字母输入、删除原断言或包装为平台专属创新。草稿未实现通用自动修复，`rec_auto_fix=false`。
