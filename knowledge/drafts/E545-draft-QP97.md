# 将 CPython 三态比较结果归一为相等谓词，恢复编码别名分支

Draft / qpack0.0.21 /任务9897 / orrkri。对应 `E545-draft-QP97.kv`；真实目标C反例与修后9/9方法、一个消费者4/4组已取得；2026-10-09正式W3已通过，L2因无bin目录跳过；尚未发布或纳入知识。

## 固定来源与问题条件

官方 [qpack tag commit](https://github.com/cesbit/qpack/tree/e55af6e2e7c8071a8533f4395682ddfb0b3018ce)，PyPI sdist SHA256 `f953e9f7d4d0946c10909c4a1de307d8d265f315b7b86c4af18b9ef1567ec845`。C、fallback、公共初始化及原suite均与tag一致；sdist的setup.cfg另有egg_info元数据。

Python3、真正加载 `qpack._qpack` 时，调用支持的Latin1别名解码非ASCII字节，可能执行错误的UTF8解码分支。已实测的最小输入：

```python
import qpack
qpack.unpackb(b'\x81\xff', decode='latin1')  # raw头0x81，单字节0xff；应得到U+00FF
```

作者私有采集脚本 `reproduce_original.py` 实际调用原C函数后，只有捕获到真实UnicodeDecodeError时才输出 `qpack latin1 dispatch: UnicodeDecodeError`。该脚本只用于留存原版观测证据，不在公开候选中，也不是知识使用者的验证入口。该签名缩小匹配范围，不能只用正常日志的latin1字样判失败。目标实际运行已取得该签名与真实UnicodeDecodeError；未改源码SHA和实际C函数身份均核验。上面的公共API输入可在原版真实C包中复现异常；修后验证使用下面的自包含命令。

## 根因与最小修法

`qpack/_qpack.c:35`在Python3把 `PyUnicode_CompareWithASCIIString` 的返回值直接作为 `PY_COMPAT_COMPARE`。其调用点1275–1280却OR组合六个UTF8别名比较，期望“相等为真”。Python2分支41行使用strcmp==0，是不同语义。

CPython [官方API说明](https://docs.python.org/3.12/c-api/unicode.html#c.PyUnicode_CompareWithASCIIString)规定小于、等于、大于分别返回-1、0、1，且这个API不抛异常。一个字符串不可能同时等于六个不同别名；至少一个比较非0，所以首个OR分支始终为真，Latin1不可达。解码器能力和locale并非这里的原因。

只修改Python3宏，保留真实C扩展与Python2原分支：

```c
#define PY_COMPAT_COMPARE(obj, str) (PyUnicode_CompareWithASCIIString(obj, str) == 0)
```

原唯一H1已在POSIX目录实际运行当前官方 `refresh-patch --auto`，生成单行+1/-1补丁，SHA256 `7ea40c69494ef654b2667dc6a045c9f6bb5b55d5c5b0392f7cd1207db1cfd6a7`；独立应用后的C SHA256 `92add8b4eb194aad506a4367167fe675e9d41bfe6ee8485278a8e850efd4e5a4`与固定修后源码一致。作者保留原补丁字节，并实际用Git apply --check和GNU patch --dry-run --fuzz=0验证。Windows初次路径处理失败与后续目标端生成分列；未手写补丁、未改框架、未禁C。补丁应用检查不等于目标软件验证。

生成补丁的四个空上下文行含统一diff要求的单空格前缀，外层git diff --check报告rc2。该机制复用正式E227，不作为本次新知识增量：保留原告警，对非补丁文件核空白，对原补丁执行真实解析/零fuzz应用检查；不改上下文或添加平台宏来消除提示。

## 真实验证入口与当前状态

Conan配方用公开Python3.12.9、profile的clang、上游setup.py及私有SHA固定setuptools84.0.0构建C扩展，使用现有OHOS签名工具。Python目标要求OHOS6/armv8/clang15/Release；这些步骤已在原唯一H1的私有环境实际完成；原公共Python完整引用与目标身份保留在原件。

KV中的 `verification_cmd` 在目标设备的实际Conan运行环境执行，`python3`须指向该目标Python，且当前包的 `lib/python` 已通过配方的运行环境加入PYTHONPATH。使用正常非优化Python，不启用 `-O` / `-OO`，并清除 `PYTHONOPTIMIZE` 或将其设为 `0`，保证断言实际执行。命令不依赖私有辅助脚本；它核真实扩展loader、公共函数身份和非ASCII Latin1结果，断言失败时不会打印PASS：

```sh
python3 -c "import importlib.machinery as m,qpack,qpack._qpack as c; assert isinstance(c.__loader__,m.ExtensionFileLoader); assert qpack.unpackb is c._unpackb; assert qpack.unpackb(bytes.fromhex('81ff'),decode='latin1') == chr(255); print('qpack latin1 native dispatch: PASS')"
```

这三个检查已在实际通过的 `test_package/functional.py` 中执行；此处给出知识使用者可直接使用的修后入口，不把文稿命令的准备另计为一次软件实测。修前采集脚本、完整suite和下面的四组消费者结果分别保留。

`test_package/functional.py`先核包内ExtensionFileLoader和公共函数身份、Python3.12.9、原测试SHA，再执行原 `qpack_test.py` 九个unittest方法（字节SHA `209a077bfbdf4f152ad7dca05cfcf643167d2c1f111bf91189a127f75c309f6a`）。没有删除或放宽原断言。

一个新增消费者程序含四组：六UTF8别名→U+00FF、六Latin1别名→U+00FF、默认bytes、UTF8严格错误/ignore-errors保留bytes并解码有效UTF8。每组核真实C、fallback及独立预期。别名行、API调用、断言与消费者程序数分别记录，不能把六个参数当六个程序。

```text
python3 -m unittest discover -s test -p qpack_test.py
python3 functional.py <Conan-package> <upstream-test-dir> <results-json>
```

原九方法实际run=9/pass=9/fail=0/error=0/skip=0；一个新增消费者程序四组run=4/pass=4/fail=0。实际包内C公共函数已加载，SOABI=cpython-312-aarch64-linux-ohos，扩展SHA25673974079526667ecba9aa984b53dd7abe66fb80563c1c9f9bb65c730337d5728。原版81ff/latin1实际抛UnicodeDecodeError，fallback得到U+00FF；观察rc0仅表示采集到缺陷，original software_pass=false。

独立conan-verify自然rc0；官方报告的G4找不到包ID与L2/L4/L5因无cache路径跳过原样保留，不能把这些标签PASS当实际执行。额外只读包回收核准确私有ref与文件SHA，不修改官方结果。此前正式W3 setup.rc0/build.rc1，full扫描115074项，JC1和JC5各命中同五个基线历史标记；后续L1/L2/L4/L5为blocked_by_JC，无.ci-result。此历史FAIL保留，原RESULT SHA2564994a494b7dc496e0c9341c5e3b6ff62bd037ebc4dc03778b7947d863059e8ad，125 raw文件逐SHA核验。

2026-10-09仅续接正式W3，未重播此前手工完成的准备、原C负例或standalone verifier。新worker自然rc0、signals=[]；官方setup/build均rc0，JC prdiff完整13文件/0错误，L0/L1/L4/L5通过，L2因无bin目录跳过。W3实际原九方法9/9、一个消费者内四组4/4，自然.ci-result.json为W3_local_ci/exit_code0；正式日志SHA256 `d58d01923d04a752fc738644062f2bcc6621bac45b52bddd7e0eca395c6e1cca`。新RESULT SHA256 `93eefd0a403b1312eb6ac30b4eda73aa6afdd96eaf50db05b32c436d7bab0a35`，两回收归档及40 raw文件逐字节/SHA已核。

当前W3实际引用 `qpack/0.0.21#d609ddcbb5c8229e8df59e966278c1a7:6b129b068851896169fae42d399fa922d239ce8a#ef9e6d61083bd36acff907cb26d551ae`，旧standalone引用 `qpack/0.0.21@ohpcd/stable#48355bd4f927709784e4e14c95d2655b:6b129b068851896169fae42d399fa922d239ce8a#ef9e6d61083bd36acff907cb26d551ae` 分列。channel/RREV不同，PID/PREV及签名.so字节相同；不得称为同一包。日志记有预下载重写再export，修订变化的因果只作推断；冻结的来源/配方/补丁/测试字节未变。此私有W3通过不替代当前PR官方CI、AtomCode原文或有效提审。

实际未改官方parser/engine已消费原H1负例stdout与修后functional-results.json：PhaseB分别返回本草稿ID/score5与同ID/score2。正常报告的qpack/latin1关键词仍可加分，返回ID不等于软件错误；以官方sig_bonus=0的只读对照，真实错误signature贡献5分，正常报告贡献0分。不能把正常报告里预期的严格UTF8异常观测误判成Latin1分派失败，不改engine或正式索引来追求零返回ID。

## 通用范围和近邻差异

适用于兼容宏把三态比较API用于相等谓词的调用点，特别是OR组合别名分支；先逐调用点核返回值合同。其他可返回-1表示异常的API须另核错误状态，不能套用本API“不抛异常”的性质。

不承诺任意codec名称、负整数或整个C/fallback合同一致；不把UTF8/Latin1别名泛化为所有Python codecs。补丁不是OHOS独有宏，而是目标上可验证的通用兼容问题。

领前近邻基于官方main `b95978a4750e7aa9a3d49af148bb3bbedf81051d`：no-host-so草稿明确排除C/fallback行为差异；libcsys Issue3015/PR9868是成功0误作长度；kaitai Issue2580/PR7862是IBM437别名未登记；E023/E039/E259和Issue2759/PR8649分别是locale/iconv/后缀/assert机制。它们不包含“三态比较→OR别名不可达→保留C的非ASCII消费者”这一窄修法。这是有范围的B02结论，不称全仓绝对原创。

申请Issue、PR、原生关系、面板绑定、当前head CI/真实AtomCode和有效提审均待闭环；完整独审及其意见修正另保留实际报告，合入、知识纳入和积分另记。当前不可提审。
