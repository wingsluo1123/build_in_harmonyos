# E632: C++ 构造函数未初始化成员在 libc++ 下读出巨大垃圾值

## 基本信息
- **严重度**: 2
- **类别**: memory, portability, cpp
- **作者**: HouYuxuan <f24011422@st.sandau.edu.cn>
- **来源 PR**: （待 promote 时补充 source_pr/source_commit）

## 错误特征
```
[0-9]{15,}\.[0-9]{3}|huge garbage value|uninitialized member|hasConfidence.*garbage|
                         aligninfo.*[0-9]{18,}
```

## 触发条件
- C++ 类构造函数只初始化了部分成员变量（例如只设了 `m_bUseConfidence = false`，未设 `m_Confidence` 等标量成员）
- 在 OHOS/clang/libc++ 环境下运行（libc++ 对未初始化栈内存的读取得到垃圾值）
- 程序输出中该未初始化成员被格式化输出（如 CSV/文本报告）

## 根因分析
C++ 类的构造函数未初始化全部成员时，读取这些成员属于未定义行为（UB）。在
libstdc++（Linux/gcc base 生成环境）下，未初始化栈/堆内存可能恰好为 0 或空值，
导致上游 base 输出中该字段为空；而在 libc++（OHOS clang 默认标准库）下，同一
未初始化内存读到的是残留垃圾位模式（实测为 `275541069870429653434368.000`、
`74107705259255264157978591232.000`，浮点位模式含 ASCII "fidr" 残留），使输出
出现巨大垃圾值，与上游权威 base 不一致。

实测案例：SCTK/asclite 的 `LineStyleInputParser` 构造函数为空 `{}`，`m_Confidence`
等成员未初始化。在 OHOS 上 `aligninfo` 输出中 confidence 字段出现 2.75e23 垃圾值
（base 为空），导致 hubscr test2-sastt 对比失败。

## 推荐方案
**方法**: initialize-all-members

**说明**: 在构造函数中显式初始化所有成员变量（浮点置 0.0、布尔置 false、整型置 0），
消除未初始化读取；通过 test_package/自研断言对比输出确认无巨大垃圾值。

**验证/命令**:
```
track-edit add ${SOFTWARE} ${VERSION} ${SOURCE_FILE} && \
                         refresh-patch --auto ${SOFTWARE} ${VERSION}
```

## 回退方案
**方法**: zero-init-class

**说明**: 若成员较多难以逐一初始化，可将构造函数改为使用成员初始化列表，或对对象
整体 memset 后仅设置必要字段。

## 禁止做法
- 忽略垃圾值 / 跳过测试：垃圾值是未初始化内存读取的直接证据，忽略会导致 Release
  产物在真实数据下输出错误评分。
- 仅测试 --help 路径：帮助路径不会触发未初始化成员输出路径，无法证明修复有效。

## 关键词
uninitialized member, constructor, libc++, libstdc++, garbage value, huge number output,
aligninfo, confidence, asclite, SCTK

## 相似条目
- E249（未初始化所有权标志导致 free 崩溃）：同为构造函数未初始化问题，但症状为
  SIGSEGV/invalid free，本条目症状为输出巨大垃圾值（无崩溃）
- E259（NDEBUG 使 assert 副作用不求值）：不同根因，不同症状

---
*由协作者流程生成（draft），待主编审核 promote*
