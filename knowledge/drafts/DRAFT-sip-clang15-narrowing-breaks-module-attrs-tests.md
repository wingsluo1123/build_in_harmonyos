# DRAFT: clang 15 的 -Wc++11-narrowing 让 sip 的 module_attrs 测试全灭

> Status: **Draft**（待审核 promote）| severity: `P2` | category: `toolchain` | Updated: 2026-09-30
> 对应: `knowledge/drafts/DRAFT-sip-clang15-narrowing-breaks-module-attrs-tests.kv`

---

**匹配关键词**：Wc++11-narrowing, non-constant-expression cannot be narrowed, signed char, char, module_attrs, sip

## 错误签名（error_signature）

```text
error: non-constant-expression cannot be narrowed from type 'signed char' to 'char' in initializer list.*\[-Wc++11-narrowing\]
```

## 错误摘录（error_excerpt）

```text
sipmodule_attrs_modulecmodule.cpp:87:26: error: non-constant-expression cannot be narrowed from type 'signed char' to 'char' in initializer list [-Wc++11-narrowing]
```

## 根因（root_cause）

sip 6.16.1 的上游测试套件在 `test/module_attrs/` 目录下会**现场生成并编译**一个
C++ 扩展模块，其中把 `signed char` 表达式用于初始化 `char`。

clang 15 将 `-Wc++11-narrowing` 视为**硬错误**而非警告；上游主要面向 GCC/MSVC，
在那些编译器上这只是警告，故生成代码在彼处合法、在此处被拒。实测该目录
**46 个用例全部报错**，其余 415 个用例正常通过。

## 推荐方案（rec_approach）

跑上游测试时导出 `CXXFLAGS` 放宽该诊断：

```bash
CXXFLAGS='-Wno-c++11-narrowing' python3 -m pytest test/
```

实测效果：`test/module_attrs` 从 46 errors 变为 **46 passed**，
整套变为 `415 passed, 33 skipped`（无失败）。

## 为什么只在该场景放宽

- 只影响**测试阶段**的编译，被打包的模块本身不受影响；
- 这是**编译器诊断差异**而非代码缺陷，因此正确做法是放宽诊断，
  而不是去改上游源码（不该为诊断差异向工程引入补丁）。

## 复现要点

```bash
python3 -m pytest test/module_attrs -q     # 46 errors（clang 15 默认）
CXXFLAGS='-Wno-c++11-narrowing' python3 -m pytest test/module_attrs -q
                                           # 46 passed
```

---

*本文件由 `knowledge/drafts/DRAFT-sip-clang15-narrowing-breaks-module-attrs-tests.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
